//! The tmux backend: every app runs in its own detached session on the
//! private socket `blueboat-hub`, so apps survive the hub being closed,
//! crashed or rebuilt. This module builds the argument lists (pure, tested)
//! and runs them.

use crate::shell::sh_quote;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

pub const SOCKET: &str = "blueboat-hub";
/// tmux escapes control characters in `list-*` output (`\x1f` arrives as
/// the text `\037`), so the field separator is a printable, never-typed
/// character: U+241F SYMBOL FOR UNIT SEPARATOR.
const SEP: char = '\u{241f}';

/// Pane fields read every tick. User options `@hub_*` carry the hub's own
/// metadata, so a restarted hub knows what each session is.
pub const PANE_FORMAT: &str = "#{session_name}\u{241f}#{pane_id}\u{241f}#{pane_pid}\u{241f}#{pane_dead}\u{241f}#{pane_dead_status}\u{241f}#{pane_dead_signal}\u{241f}#{session_created}\u{241f}#{@hub_app}\u{241f}#{@hub_params}\u{241f}#{@hub_variant}\u{241f}#{@hub_log}\u{241f}#{@hub_started}";

#[derive(Debug, Clone, PartialEq)]
pub struct PaneInfo {
    pub session: String,
    pub pane_id: String,
    pub pid: u32,
    pub dead: bool,
    pub dead_status: Option<i32>,
    pub dead_signal: Option<i32>,
    pub created_s: i64,
    pub app: String,
    pub params_json: String,
    pub variant: String,
    pub log: String,
    pub started_ms: i64,
}

pub fn parse_panes(out: &str) -> Vec<PaneInfo> {
    let mut v = vec![];
    for line in out.lines() {
        let f: Vec<&str> = line.split(SEP).collect();
        if f.len() < 12 {
            continue;
        }
        let num = |s: &str| s.trim().parse::<i64>().ok();
        let Some(pid) = f[2].trim().parse::<u32>().ok() else {
            continue;
        };
        let dead = f[3].trim() == "1";
        let started_ms = num(f[11]).unwrap_or_else(|| num(f[6]).unwrap_or(0) * 1000);
        // tmux gives one pane per session here; keep the first.
        if v.iter().any(|p: &PaneInfo| p.session == f[0]) {
            continue;
        }
        v.push(PaneInfo {
            session: f[0].to_string(),
            pane_id: f[1].to_string(),
            pid,
            dead,
            dead_status: if dead { num(f[4]).map(|n| n as i32) } else { None },
            dead_signal: if dead {
                num(f[5]).map(|n| n as i32).filter(|&n| n > 0)
            } else {
                None
            },
            created_s: num(f[6]).unwrap_or(0),
            app: f[7].to_string(),
            params_json: f[8].to_string(),
            variant: f[9].to_string(),
            log: f[10].to_string(),
            started_ms,
        });
    }
    v
}

/// Everything needed to start one session.
#[derive(Debug, Clone)]
pub struct NewSession {
    pub name: String,
    pub cwd: PathBuf,
    /// argv prefix, e.g. `["bash", "-ic"]`; the script is appended as one argument.
    pub shell: Vec<String>,
    pub script: String,
    pub cols: u16,
    pub rows: u16,
    pub log: Option<PathBuf>,
    /// `@hub_*` user options set on the session.
    pub meta: Vec<(String, String)>,
}

/// One tmux invocation: `new-session` + the metadata options + `pipe-pane`,
/// chained with `;` so logging starts before the app prints anything.
pub fn new_session_args(s: &NewSession) -> Vec<String> {
    let target = format!("={}:", s.name);
    let mut a: Vec<String> = vec![
        "new-session".into(),
        "-d".into(),
        "-s".into(),
        s.name.clone(),
        "-x".into(),
        s.cols.to_string(),
        "-y".into(),
        s.rows.to_string(),
        "-c".into(),
        s.cwd.to_string_lossy().into_owned(),
        "-e".into(),
        format!("BLUEBOAT_HUB_SESSION={}", s.name),
    ];
    a.extend(s.shell.iter().cloned());
    a.push(s.script.clone());
    for (k, v) in &s.meta {
        a.extend([
            ";".into(),
            "set-option".into(),
            "-t".into(),
            target.clone(),
            format!("@hub_{k}"),
            v.clone(),
        ]);
    }
    if let Some(log) = &s.log {
        a.extend([
            ";".into(),
            "pipe-pane".into(),
            "-o".into(),
            "-t".into(),
            target,
            format!("cat >> {}", sh_quote(&log.to_string_lossy())),
        ]);
    }
    a
}

pub fn kill_session_args(name: &str) -> Vec<String> {
    vec!["kill-session".into(), "-t".into(), format!("={name}")]
}

pub fn ctrl_c_args(name: &str) -> Vec<String> {
    vec!["send-keys".into(), "-t".into(), format!("={name}:"), "C-c".into()]
}

pub fn capture_args(name: &str, escapes: bool) -> Vec<String> {
    let mut v: Vec<String> = vec!["capture-pane".into(), "-p".into(), "-J".into()];
    if escapes {
        v.push("-e".into());
    }
    v.extend(["-S".into(), "-".into(), "-t".into(), format!("={name}:")]);
    v
}

/// Session names are `[a-z0-9_-]`, which tmux takes without quoting and
/// which can never contain the `:` / `.` of a target.
pub fn valid_session_name(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 64
        && s
            .chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || c == '-')
}

#[derive(Debug, Clone)]
pub struct Tmux {
    conf: PathBuf,
}

impl Tmux {
    pub fn new(conf: &Path) -> Tmux {
        Tmux {
            conf: conf.to_path_buf(),
        }
    }

    /// `tmux -L blueboat-hub -f <hub>/tmux.conf`. The config is read only
    /// when this call starts the server.
    pub fn command(&self) -> Command {
        let mut c = Command::new("tmux");
        c.arg("-L").arg(SOCKET);
        if self.conf.is_file() {
            c.arg("-f").arg(&self.conf);
        }
        c.stdin(Stdio::null());
        c
    }

    pub fn run(&self, args: &[String]) -> Result<String, String> {
        let out = self
            .command()
            .args(args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .map_err(|e| format!("tmux: {e}"))?;
        if out.status.success() {
            Ok(String::from_utf8_lossy(&out.stdout).into_owned())
        } else {
            Err(String::from_utf8_lossy(&out.stderr).trim().to_string())
        }
    }

    /// All panes; empty when no server runs on our socket.
    pub fn list_panes(&self) -> Vec<PaneInfo> {
        match self.run(&["list-panes".into(), "-a".into(), "-F".into(), PANE_FORMAT.into()]) {
            Ok(out) => parse_panes(&out),
            Err(_) => vec![],
        }
    }

    pub fn new_session(&self, s: &NewSession) -> Result<(), String> {
        self.run(&new_session_args(s)).map(|_| ())
    }

    pub fn kill_session(&self, name: &str) -> Result<(), String> {
        self.run(&kill_session_args(name)).map(|_| ())
    }

    pub fn ctrl_c(&self, name: &str) -> Result<(), String> {
        self.run(&ctrl_c_args(name)).map(|_| ())
    }

    pub fn capture(&self, name: &str, escapes: bool) -> Result<String, String> {
        self.run(&capture_args(name, escapes))
    }

    pub fn version(&self) -> Option<String> {
        Command::new("tmux")
            .arg("-V")
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_session_is_one_invocation() {
        let s = NewSession {
            name: "gcs".into(),
            cwd: "/home/u/ros2_ws".into(),
            shell: vec!["bash".into(), "-ic".into()],
            script: "cd ~/ros2_ws && source env.sh && cd x && exec python3 -m blueboat_gcs.main".into(),
            cols: 160,
            rows: 48,
            log: Some("/home/u/.local/state/blueboat-hub/logs/gcs-20261111-120000.log".into()),
            meta: vec![("app".into(), "gcs".into()), ("params".into(), "{}".into())],
        };
        let a = new_session_args(&s);
        assert_eq!(
            &a[..12],
            &["new-session", "-d", "-s", "gcs", "-x", "160", "-y", "48", "-c", "/home/u/ros2_ws", "-e", "BLUEBOAT_HUB_SESSION=gcs"]
        );
        assert_eq!(a[12], "bash");
        assert_eq!(a[13], "-ic");
        assert_eq!(a[14], s.script);
        assert_eq!(&a[15..21], &[";", "set-option", "-t", "=gcs:", "@hub_app", "gcs"]);
        assert_eq!(&a[21..27], &[";", "set-option", "-t", "=gcs:", "@hub_params", "{}"]);
        assert_eq!(
            &a[27..],
            &[";", "pipe-pane", "-o", "-t", "=gcs:", "cat >> /home/u/.local/state/blueboat-hub/logs/gcs-20261111-120000.log"]
        );
        // no argument may end in ';' except the separators themselves
        for x in &a {
            assert!(x == ";" || !x.ends_with(';'), "{x}");
        }
    }

    #[test]
    fn exact_targets() {
        assert_eq!(kill_session_args("mcs"), ["kill-session", "-t", "=mcs"]);
        assert_eq!(ctrl_c_args("gazebo_world"), ["send-keys", "-t", "=gazebo_world:", "C-c"]);
        assert_eq!(capture_args("build", false), ["capture-pane", "-p", "-J", "-S", "-", "-t", "=build:"]);
    }

    #[test]
    fn pane_parsing() {
        let s = SEP;
        let out = format!(
            "gcs{s}%3{s}41233{s}0{s}{s}{s}1762830000{s}gcs{s}{{}}{s}{s}/l/gcs.log{s}1762830000123\n\
             build{s}%4{s}41300{s}1{s}1{s}{s}1762830100{s}build{s}{s}{s}{s}\n\
             qgc{s}%5{s}41400{s}1{s}{s}9{s}1762830200{s}qgc{s}{s}{s}{s}\n\
             garbage line\n"
        );
        let v = parse_panes(&out);
        assert_eq!(v.len(), 3);
        assert_eq!(v[0].session, "gcs");
        assert_eq!(v[0].pid, 41233);
        assert!(!v[0].dead);
        assert_eq!(v[0].dead_status, None);
        assert_eq!(v[0].started_ms, 1762830000123);
        assert_eq!(v[0].log, "/l/gcs.log");
        assert!(v[1].dead);
        assert_eq!(v[1].dead_status, Some(1));
        assert_eq!(v[1].started_ms, 1762830100000);
        assert_eq!(v[2].dead_signal, Some(9));
    }

    /// The separator must survive a real tmux server (control characters
    /// come back octal-escaped). Skipped when tmux is not installed.
    #[test]
    fn separator_survives_real_tmux() {
        let sock = format!("bbhub-test-{}", std::process::id());
        let run = |args: &[&str]| {
            std::process::Command::new("tmux")
                .args(["-L", &sock, "-f", "/dev/null"])
                .args(args)
                .output()
        };
        let Ok(o) = run(&["new-session", "-d", "-s", "t", "-x", "80", "-y", "20", "sleep", "30"]) else {
            return;
        };
        assert!(o.status.success(), "{}", String::from_utf8_lossy(&o.stderr));
        let _ = run(&["set-option", "-t", "=t:", "@hub_app", "gcs"]);
        let out = run(&["list-panes", "-a", "-F", PANE_FORMAT]).unwrap();
        let _ = run(&["kill-server"]);
        let panes = parse_panes(&String::from_utf8_lossy(&out.stdout));
        assert_eq!(panes.len(), 1, "{:?}", String::from_utf8_lossy(&out.stdout));
        assert_eq!(panes[0].session, "t");
        assert_eq!(panes[0].app, "gcs");
        assert!(!panes[0].dead);
    }

    #[test]
    fn session_names() {
        assert!(valid_session_name("log_reviewer-2"));
        assert!(!valid_session_name("a:b"));
        assert!(!valid_session_name("a.b"));
        assert!(!valid_session_name(""));
    }
}
