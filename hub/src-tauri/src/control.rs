//! tmux control-mode client (`tmux -C attach`), one per session.
//!
//! A normal tmux client redraws its screen with cursor movement, which gives
//! xterm.js no scrollback. Control mode instead reports every byte a pane
//! writes as `%output %<pane> <octal-escaped data>`, so the hub's terminal
//! gets the raw stream: real scrollback, search and copy.
//!
//! Attaching a view: the reader is told to wait for a marker block
//! (`display-message -p HUBMARK-n`), then takes the next block as the
//! pane's history (`capture-pane -e -S -`) and only then forwards live
//! output. `%output` seen before the capture is already part of it and
//! is dropped, so nothing appears twice.

use crate::shell::strip_ansi;
use base64::Engine;
use serde::Serialize;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, ChildStdin, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use tauri::ipc::Channel;

#[derive(Clone, Serialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
pub enum TermMsg {
    /// The pane's history, base64; replaces whatever the view showed.
    History { data: String },
    /// Live output, base64.
    Output { data: String },
    /// The control client went away (session killed / server gone).
    Ended,
}

/// Bytes handed to an output consumer other than the view (the colcon parser).
pub type Sink = Box<dyn FnMut(&[u8]) + Send>;

enum Attach {
    Idle,
    AwaitMarker { n: u64, ch: Channel<TermMsg> },
    AwaitCapture { ch: Channel<TermMsg> },
    Live { ch: Channel<TermMsg> },
}

struct Shared {
    attach: Attach,
    line: LineTracker,
    sink: Option<Sink>,
}

pub struct ControlClient {
    child: Mutex<Child>,
    stdin: Mutex<ChildStdin>,
    shared: Arc<Mutex<Shared>>,
    alive: Arc<AtomicBool>,
    marker: AtomicU64,
    pane_id: String,
    size: Mutex<Option<(u16, u16)>>,
}

fn b64(data: &[u8]) -> String {
    base64::engine::general_purpose::STANDARD.encode(data)
}

impl ControlClient {
    /// Spawn `tmux … -C attach-session -t =<name>` (stdin/stdout piped).
    pub fn spawn(mut cmd: std::process::Command, name: &str, pane_id: &str, sink: Option<Sink>) -> Result<Arc<ControlClient>, String> {
        cmd.args(["-C", "attach-session", "-t", &format!("={name}")])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        let mut child = cmd.spawn().map_err(|e| format!("tmux -C: {e}"))?;
        let stdin = child.stdin.take().ok_or("tmux -C: no stdin")?;
        let stdout = child.stdout.take().ok_or("tmux -C: no stdout")?;
        let shared = Arc::new(Mutex::new(Shared {
            attach: Attach::Idle,
            line: LineTracker::default(),
            sink,
        }));
        let alive = Arc::new(AtomicBool::new(true));
        let client = Arc::new(ControlClient {
            child: Mutex::new(child),
            stdin: Mutex::new(stdin),
            shared: shared.clone(),
            alive: alive.clone(),
            marker: AtomicU64::new(1),
            pane_id: pane_id.to_string(),
            size: Mutex::new(None),
        });
        std::thread::Builder::new()
            .name(format!("tmux-C {name}"))
            .spawn(move || reader(stdout, shared, alive))
            .map_err(|e| e.to_string())?;
        Ok(client)
    }

    pub fn alive(&self) -> bool {
        self.alive.load(Ordering::SeqCst)
    }

    fn write(&self, cmd: &str) -> Result<(), String> {
        let mut w = self.stdin.lock().unwrap();
        w.write_all(cmd.as_bytes())
            .and_then(|_| w.flush())
            .map_err(|e| format!("tmux -C: {e}"))
    }

    fn target(&self) -> String {
        if self.pane_id.starts_with('%') && self.pane_id[1..].chars().all(|c| c.is_ascii_digit()) {
            format!(" -t {}", self.pane_id)
        } else {
            String::new()
        }
    }

    /// Start streaming to a view: history first, then live output.
    pub fn attach(&self, ch: Channel<TermMsg>) -> Result<(), String> {
        let n = self.marker.fetch_add(1, Ordering::SeqCst);
        self.shared.lock().unwrap().attach = Attach::AwaitMarker { n, ch };
        let t = self.target();
        self.write(&format!("display-message -p HUBMARK-{n}\ncapture-pane -p -e -J -S -{t}\n"))
    }

    pub fn detach(&self) {
        self.shared.lock().unwrap().attach = Attach::Idle;
    }

    /// Keystrokes from the view, as literal bytes (`send-keys -H`).
    pub fn send_input(&self, data: &[u8]) -> Result<(), String> {
        let t = self.target();
        let mut cmds = String::new();
        for chunk in data.chunks(96) {
            cmds.push_str("send-keys");
            cmds.push_str(&t);
            cmds.push_str(" -H");
            for b in chunk {
                cmds.push_str(&format!(" {b:02x}"));
            }
            cmds.push('\n');
        }
        self.write(&cmds)
    }

    pub fn resize(&self, cols: u16, rows: u16) -> Result<(), String> {
        let (cols, rows) = (cols.clamp(20, 1000), rows.clamp(5, 500));
        let mut size = self.size.lock().unwrap();
        if *size == Some((cols, rows)) {
            return Ok(());
        }
        *size = Some((cols, rows));
        drop(size);
        self.write(&format!("refresh-client -C {cols}x{rows}\n"))
    }

    pub fn last_line(&self) -> String {
        self.shared.lock().unwrap().line.last.clone()
    }

    pub fn kill(&self) {
        self.detach();
        let mut c = self.child.lock().unwrap();
        let _ = c.kill();
        let _ = c.wait();
    }
}

impl Drop for ControlClient {
    fn drop(&mut self) {
        if let Ok(mut c) = self.child.lock() {
            let _ = c.kill();
            let _ = c.wait();
        }
    }
}

fn reader(stdout: std::process::ChildStdout, shared: Arc<Mutex<Shared>>, alive: Arc<AtomicBool>) {
    let mut r = BufReader::with_capacity(64 * 1024, stdout);
    let mut line = Vec::with_capacity(4096);
    let mut block: Option<Vec<Vec<u8>>> = None;
    loop {
        line.clear();
        match r.read_until(b'\n', &mut line) {
            Ok(0) | Err(_) => break,
            Ok(_) => {}
        }
        if line.last() == Some(&b'\n') {
            line.pop();
        }
        if let Some(body) = block.as_mut() {
            if line.starts_with(b"%end ") || line.starts_with(b"%error ") {
                let body = block.take().unwrap_or_default();
                on_block(&shared, body);
            } else {
                body.push(line.clone());
            }
            continue;
        }
        if line.starts_with(b"%begin ") {
            block = Some(vec![]);
        } else if let Some(data) = decode_output_line(&line) {
            on_output(&shared, &data);
        } else if line.starts_with(b"%exit") {
            break;
        }
    }
    alive.store(false, Ordering::SeqCst);
    let mut sh = shared.lock().unwrap();
    match std::mem::replace(&mut sh.attach, Attach::Idle) {
        Attach::AwaitMarker { ch, .. } | Attach::AwaitCapture { ch } | Attach::Live { ch } => {
            let _ = ch.send(TermMsg::Ended);
        }
        Attach::Idle => {}
    }
}

fn on_block(shared: &Mutex<Shared>, body: Vec<Vec<u8>>) {
    let mut sh = shared.lock().unwrap();
    let next = match std::mem::replace(&mut sh.attach, Attach::Idle) {
        Attach::AwaitMarker { n, ch } => {
            if body.len() == 1 && body[0] == format!("HUBMARK-{n}").as_bytes() {
                Attach::AwaitCapture { ch }
            } else {
                Attach::AwaitMarker { n, ch }
            }
        }
        Attach::AwaitCapture { ch } => {
            let hist = join_history(&body);
            if ch.send(TermMsg::History { data: b64(&hist) }).is_ok() {
                Attach::Live { ch }
            } else {
                Attach::Idle
            }
        }
        other => other,
    };
    sh.attach = next;
}

fn on_output(shared: &Mutex<Shared>, data: &[u8]) {
    let mut sh = shared.lock().unwrap();
    sh.line.feed(data);
    if let Some(sink) = sh.sink.as_mut() {
        sink(data);
    }
    if let Attach::Live { ch } = &sh.attach {
        if ch.send(TermMsg::Output { data: b64(data) }).is_err() {
            sh.attach = Attach::Idle;
        }
    }
}

/// History lines → one terminal write: CRLF-joined, trailing blank rows
/// (the empty bottom of the pane) dropped.
pub fn join_history(lines: &[Vec<u8>]) -> Vec<u8> {
    let mut end = lines.len();
    while end > 0 && lines[end - 1].iter().all(|b| b.is_ascii_whitespace()) {
        end -= 1;
    }
    // capture-pane returns whole screens: the empty rows between an app's
    // last output and tmux's "ended" line at the bottom would show as a gap.
    let mut out = Vec::new();
    let mut blanks = 0;
    let mut first = true;
    for l in &lines[..end] {
        let blank = l.iter().all(|b| b.is_ascii_whitespace());
        blanks = if blank { blanks + 1 } else { 0 };
        if blanks > 2 {
            continue;
        }
        if !first {
            out.extend_from_slice(b"\r\n");
        }
        first = false;
        out.extend_from_slice(l);
    }
    if end > 0 {
        // leave the cursor on a fresh line and reset attributes
        out.extend_from_slice(b"\x1b[0m\r\n");
    }
    out
}

/// `%output %12 hello\015\012` → `hello\r\n`. tmux escapes bytes below
/// 0x20 and the backslash as `\ooo`; everything else is passed through.
pub fn decode_output_line(line: &[u8]) -> Option<Vec<u8>> {
    let rest = line.strip_prefix(b"%output ")?;
    let sp = rest.iter().position(|&b| b == b' ');
    let payload = match sp {
        Some(i) => &rest[i + 1..],
        None => &[][..],
    };
    let mut out = Vec::with_capacity(payload.len());
    let mut i = 0;
    while i < payload.len() {
        let b = payload[i];
        if b == b'\\'
            && i + 3 < payload.len()
            && payload[i + 1..i + 4].iter().all(|c| (b'0'..=b'7').contains(c))
        {
            let v = (payload[i + 1] - b'0') as u32 * 64
                + (payload[i + 2] - b'0') as u32 * 8
                + (payload[i + 3] - b'0') as u32;
            out.push(v as u8);
            i += 4;
        } else {
            out.push(b);
            i += 1;
        }
    }
    Some(out)
}

/// Keeps the last non-blank output line for a collapsed card's preview.
#[derive(Default)]
pub struct LineTracker {
    cur: Vec<u8>,
    pub last: String,
}

impl LineTracker {
    pub fn feed(&mut self, data: &[u8]) {
        for &b in data {
            if b == b'\n' || b == b'\r' {
                self.finish();
            } else if self.cur.len() < 2048 {
                self.cur.push(b);
            }
        }
    }

    fn finish(&mut self) {
        if !self.cur.is_empty() {
            let s = strip_ansi(&self.cur);
            let t = s.trim_end();
            if !t.trim().is_empty() {
                self.last = t.chars().take(300).collect();
            }
            self.cur.clear();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decodes_octal_escapes() {
        assert_eq!(decode_output_line(b"%output %3 hello\\015\\012").unwrap(), b"hello\r\n");
        assert_eq!(decode_output_line(b"%output %3 a\\134b").unwrap(), b"a\\b");
        assert_eq!(decode_output_line(b"%output %3 \\033[1mX").unwrap(), b"\x1b[1mX");
        // UTF-8 passes through untouched
        assert_eq!(decode_output_line("%output %3 é".as_bytes()).unwrap(), "é".as_bytes());
        // a lone or short backslash sequence is literal
        assert_eq!(decode_output_line(b"%output %3 x\\9").unwrap(), b"x\\9");
        assert_eq!(decode_output_line(b"%output %3 x\\01").unwrap(), b"x\\01");
        assert_eq!(decode_output_line(b"%output %3 \\000").unwrap(), b"\0");
        assert_eq!(decode_output_line(b"%output %3").unwrap(), b"");
        assert!(decode_output_line(b"%begin 1 2 0").is_none());
    }

    #[test]
    fn history_join() {
        let lines = vec![b"one".to_vec(), b"two".to_vec(), b"".to_vec(), b"  ".to_vec()];
        assert_eq!(join_history(&lines), b"one\r\ntwo\x1b[0m\r\n");
        assert_eq!(join_history(&[b"".to_vec()]), b"");
        let gap: Vec<Vec<u8>> = [&b"a"[..], b"", b"", b"", b"", b"", b"end"].iter().map(|l| l.to_vec()).collect();
        assert_eq!(join_history(&gap), b"a\r\n\r\n\r\nend\x1b[0m\r\n");
    }

    #[test]
    fn last_line() {
        let mut t = LineTracker::default();
        t.feed(b"first\r\n\x1b[32msecond\x1b[0m\r\n   \r\n");
        assert_eq!(t.last, "second");
        t.feed(b"partial");
        assert_eq!(t.last, "second");
        t.feed(b"\n");
        assert_eq!(t.last, "partial");
    }
}
