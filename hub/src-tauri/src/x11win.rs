//! Window control over X11 (EWMH), pure Rust via `x11rb`.
//!
//! * find an app's windows: `_NET_CLIENT_LIST` + `_NET_WM_PID`;
//! * Stop: `_NET_CLOSE_WINDOW` — the same request the title-bar ✕ sends, so
//!   the app runs its own `closeEvent` (MCS: safe shutdown, CM-15);
//! * Focus: `_NET_ACTIVE_WINDOW`.
//!
//! No X display (Wayland session, headless) → `X11::connect` fails and the
//! hub falls back to C-c in the pane.

use serde::Serialize;
use x11rb::connection::Connection;
use x11rb::protocol::xproto::{
    AtomEnum, ClientMessageEvent, ConnectionExt as _, EventMask, Window,
};
use x11rb::rust_connection::RustConnection;

x11rb::atom_manager! {
    pub Atoms: AtomsCookie {
        _NET_CLIENT_LIST,
        _NET_WM_PID,
        _NET_CLOSE_WINDOW,
        _NET_ACTIVE_WINDOW,
        _NET_WM_NAME,
        UTF8_STRING,
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct WinInfo {
    pub id: u32,
    pub pid: u32,
    /// A dialog of another *managed* window. Qt points `WM_TRANSIENT_FOR` of
    /// a parentless top-level `QDialog` (World Builder's main window) at its
    /// unmapped client-leader window; that does not make it a dialog.
    pub transient: bool,
    pub title: String,
}

pub struct X11 {
    conn: RustConnection,
    root: Window,
    atoms: Atoms,
}

type XResult<T> = Result<T, Box<dyn std::error::Error>>;

impl X11 {
    pub fn connect() -> XResult<X11> {
        if std::env::var_os("DISPLAY").is_none() {
            return Err("no DISPLAY".into());
        }
        let (conn, screen) = x11rb::connect(None)?;
        let root = conn.setup().roots[screen].root;
        let atoms = Atoms::new(&conn)?.reply()?;
        Ok(X11 { conn, root, atoms })
    }

    /// Managed top-level windows, in mapping order.
    pub fn list(&self) -> XResult<Vec<WinInfo>> {
        let list = self
            .conn
            .get_property(false, self.root, self.atoms._NET_CLIENT_LIST, AtomEnum::WINDOW, 0, 4096)?
            .reply()?;
        let ids: Vec<u32> = list.value32().map(|it| it.collect()).unwrap_or_default();
        let mut out = Vec::with_capacity(ids.len());
        for &id in &ids {
            let pid = self
                .conn
                .get_property(false, id, self.atoms._NET_WM_PID, AtomEnum::CARDINAL, 0, 1)?
                .reply()
                .ok()
                .and_then(|r| r.value32().and_then(|mut v| v.next()));
            let Some(pid) = pid else { continue };
            let transient_for = self
                .conn
                .get_property(false, id, AtomEnum::WM_TRANSIENT_FOR, AtomEnum::WINDOW, 0, 1)?
                .reply()
                .ok()
                .and_then(|r| r.value32().and_then(|mut v| v.next()))
                .filter(|&w| w != 0 && w != id);
            let title = self
                .conn
                .get_property(false, id, self.atoms._NET_WM_NAME, self.atoms.UTF8_STRING, 0, 256)?
                .reply()
                .ok()
                .map(|r| String::from_utf8_lossy(&r.value).into_owned())
                .unwrap_or_default();
            out.push((WinInfo { id, pid, transient: false, title }, transient_for));
        }
        Ok(mark_transients(out))
    }

    fn client_message(&self, window: Window, kind: u32, data: [u32; 5]) -> XResult<()> {
        let ev = ClientMessageEvent::new(32, window, kind, data);
        self.conn.send_event(
            false,
            self.root,
            EventMask::SUBSTRUCTURE_REDIRECT | EventMask::SUBSTRUCTURE_NOTIFY,
            ev,
        )?;
        self.conn.flush()?;
        Ok(())
    }

    /// Ask the window manager to close the window, exactly like its ✕.
    pub fn close(&self, window: Window) -> XResult<()> {
        // data: timestamp (CurrentTime), source indication 2 = pager/tool
        self.client_message(window, self.atoms._NET_CLOSE_WINDOW, [0, 2, 0, 0, 0])
    }

    /// Raise and focus the window (un-minimizes it).
    pub fn activate(&self, window: Window) -> XResult<()> {
        self.client_message(window, self.atoms._NET_ACTIVE_WINDOW, [2, 0, 0, 0, 0])
    }
}

/// A window is a dialog only if it is transient for another window that is
/// itself in the managed list (not the root, not an unmapped group leader).
pub fn mark_transients(list: Vec<(WinInfo, Option<u32>)>) -> Vec<WinInfo> {
    let managed: Vec<u32> = list.iter().map(|(w, _)| w.id).collect();
    list.into_iter()
        .map(|(mut w, tf)| {
            w.transient = tf.is_some_and(|t| managed.contains(&t));
            w
        })
        .collect()
}

/// Order in which Stop closes a session's windows: dialogs are left alone
/// (closing a confirmation dialog would answer "Cancel"), secondary
/// top-levels go first and the first-mapped one — the main window — last.
pub fn close_order(wins: &[WinInfo]) -> Vec<u32> {
    let tops: Vec<&WinInfo> = wins.iter().filter(|w| !w.transient).collect();
    let mut order: Vec<u32> = tops.iter().skip(1).rev().map(|w| w.id).collect();
    if let Some(first) = tops.first() {
        order.push(first.id);
    }
    order
}

#[cfg(test)]
mod tests {
    use super::*;

    fn w(id: u32, transient: bool) -> WinInfo {
        WinInfo { id, pid: 1, transient, title: String::new() }
    }

    #[test]
    fn leader_transient_is_not_a_dialog() {
        let wb = WinInfo { id: 7, pid: 1, transient: false, title: "World Builder".into() };
        let dlg = WinInfo { id: 8, pid: 1, transient: false, title: "Save?".into() };
        // 7 → unmapped client leader 9 (not managed); 8 → 7 (managed)
        let v = mark_transients(vec![(wb, Some(9)), (dlg, Some(7))]);
        assert!(!v[0].transient);
        assert!(v[1].transient);
        assert_eq!(close_order(&v), vec![7]);
    }

    #[test]
    fn main_window_closes_last_and_dialogs_never() {
        assert_eq!(close_order(&[w(1, false), w(2, false), w(3, true), w(4, false)]), vec![4, 2, 1]);
        assert_eq!(close_order(&[w(5, true)]), Vec::<u32>::new());
        assert_eq!(close_order(&[]), Vec::<u32>::new());
    }
}
