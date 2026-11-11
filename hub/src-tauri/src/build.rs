//! colcon build: output parser and build state.
//!
//! The build runs in its own tmux session `build`; its output is fed here
//! line by line (ANSI stripped, `\r` status redraws split off) and turned
//! into the per-package progress strip and the final result.

use crate::shell::strip_ansi;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum PkgStatus {
    Building,
    Finished,
    Failed,
    Aborted,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct PkgProgress {
    pub name: String,
    pub status: PkgStatus,
    pub seconds: Option<f64>,
}

#[derive(Debug, Default, Clone)]
pub struct ColconParser {
    buf: Vec<u8>,
    pub pkgs: Vec<PkgProgress>,
    pub summary: Vec<String>,
    pub failed: Vec<String>,
    pub aborted: Vec<String>,
    pub stderr_pkgs: Vec<String>,
    pub first_error: Option<String>,
    in_summary: bool,
    stderr_block: Option<(String, Option<String>, Option<String>)>,
    /// first error-looking line (else first line) of each package's stderr block
    stderr_first: Vec<(String, String)>,
}

fn pkg_after(line: &str, prefix: &str) -> Option<(String, Option<f64>)> {
    let rest = line.strip_prefix(prefix)?.trim_start();
    let rest = rest.strip_prefix("<<<").or_else(|| rest.strip_prefix(">>>"))?.trim();
    let (name, tail) = match rest.find(" [") {
        Some(i) => (&rest[..i], Some(&rest[i + 2..])),
        None => (rest, None),
    };
    let secs = tail.and_then(|t| {
        let num: String = t.chars().take_while(|c| c.is_ascii_digit() || *c == '.').collect();
        num.parse().ok()
    });
    if name.is_empty() || name.contains(' ') {
        return None;
    }
    Some((name.to_string(), secs))
}

fn list_after_colon(s: &str) -> Vec<String> {
    s.split_once(':')
        .map(|(_, r)| r.split_whitespace().map(String::from).collect())
        .unwrap_or_default()
}

impl ColconParser {
    /// Feed raw terminal bytes. Returns true if the visible state changed.
    pub fn feed(&mut self, data: &[u8]) -> bool {
        let mut changed = false;
        for &b in data {
            if b == b'\n' || b == b'\r' {
                let line = strip_ansi(&self.buf);
                self.buf.clear();
                changed |= self.line(&line);
            } else if self.buf.len() < 16 * 1024 {
                self.buf.push(b);
            }
        }
        changed
    }

    fn set(&mut self, name: String, status: PkgStatus, seconds: Option<f64>) {
        match self.pkgs.iter_mut().find(|p| p.name == name) {
            Some(p) => {
                p.status = status;
                if seconds.is_some() {
                    p.seconds = seconds;
                }
            }
            None => self.pkgs.push(PkgProgress { name, status, seconds }),
        }
    }

    pub fn line(&mut self, raw: &str) -> bool {
        let line = raw.trim_end();
        if line.trim().is_empty() {
            return false;
        }
        // stderr blocks: `--- stderr: pkg` … `---`
        if let Some(pkg) = line.strip_prefix("--- stderr: ") {
            self.stderr_block = Some((pkg.trim().to_string(), None, None));
            return false;
        }
        if let Some((pkg, first_err, first_any)) = self.stderr_block.as_mut() {
            if line == "---" {
                let pick = first_err.clone().or_else(|| first_any.clone());
                if let Some(l) = pick {
                    self.stderr_first.push((pkg.clone(), l));
                }
                self.stderr_block = None;
            } else {
                if first_any.is_none() {
                    *first_any = Some(line.trim().to_string());
                }
                if first_err.is_none() && line.to_ascii_lowercase().contains("error") {
                    *first_err = Some(line.trim().to_string());
                }
            }
            return false;
        }
        if let Some((n, _)) = pkg_after(line, "Starting") {
            self.set(n, PkgStatus::Building, None);
            return true;
        }
        if let Some((n, s)) = pkg_after(line, "Finished") {
            self.set(n, PkgStatus::Finished, s);
            return true;
        }
        if let Some((n, s)) = pkg_after(line, "Failed") {
            if self.first_error.is_none() {
                self.first_error = Some(
                    self.stderr_first
                        .iter()
                        .find(|(p, _)| p == &n)
                        .map(|(_, l)| l.clone())
                        .unwrap_or_else(|| line.trim().to_string()),
                );
            }
            if !self.failed.contains(&n) {
                self.failed.push(n.clone());
            }
            self.set(n, PkgStatus::Failed, s);
            return true;
        }
        if let Some((n, s)) = pkg_after(line, "Aborted") {
            self.set(n, PkgStatus::Aborted, s);
            return true;
        }
        if line.starts_with("Summary:") {
            self.in_summary = true;
            if !self.summary.iter().any(|s| s == line.trim()) {
                self.summary.push(line.trim().to_string());
            }
            return true;
        }
        if self.in_summary && line.starts_with("  ") {
            let t = line.trim();
            if self.summary.iter().any(|s| s == t) {
                return false;
            }
            self.summary.push(t.to_string());
            if t.contains("failed:") {
                for p in list_after_colon(t) {
                    if !self.failed.contains(&p) {
                        self.failed.push(p);
                    }
                }
            } else if t.contains("aborted:") {
                self.aborted = list_after_colon(t);
            } else if t.contains("stderr output:") {
                self.stderr_pkgs = list_after_colon(t);
            }
            return true;
        }
        false
    }

    pub fn finished(&self) -> Vec<String> {
        self.pkgs
            .iter()
            .filter(|p| p.status == PkgStatus::Finished)
            .map(|p| p.name.clone())
            .collect()
    }
}

/// What the top bar, the drawer and `build.json` show.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BuildState {
    pub running: bool,
    pub session: Option<String>,
    pub started_ms: i64,
    pub finished_ms: Option<i64>,
    /// `--packages-select` list; empty = all packages.
    pub selection: Vec<String>,
    /// Number of packages expected (selection, else every package).
    pub expected: usize,
    pub packages: Vec<PkgProgress>,
    pub summary: Vec<String>,
    pub failed: Vec<String>,
    pub first_error: Option<String>,
    pub exit_code: Option<i32>,
    pub ok: Option<bool>,
}

impl BuildState {
    pub fn absorb(&mut self, p: &ColconParser) {
        self.packages = p.pkgs.clone();
        self.summary = p.summary.clone();
        self.failed = p.failed.clone();
        self.first_error = p.first_error.clone();
    }

    pub fn finish(&mut self, exit_code: Option<i32>, now_ms: i64) {
        self.running = false;
        self.finished_ms = Some(now_ms);
        self.exit_code = exit_code;
        self.ok = Some(exit_code == Some(0) && self.failed.is_empty());
        // packages still "building" when the session ended were interrupted
        for p in self.packages.iter_mut() {
            if p.status == PkgStatus::Building {
                p.status = PkgStatus::Aborted;
            }
        }
        if self.ok == Some(false) && self.first_error.is_none() {
            self.first_error = Some(match exit_code {
                Some(c) => format!("colcon exited with code {c}"),
                None => "the build was interrupted".into(),
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A real colcon run captured through a tmux pane (`pipe-pane`):
    /// one package fails, three are aborted, status lines redraw with `\r`.
    const FAILED: &[u8] = include_bytes!("../tests/fixtures/colcon_failed.log");

    #[test]
    fn parses_saved_failing_build() {
        let mut p = ColconParser::default();
        // feed in uneven chunks, as the control client delivers it
        for chunk in FAILED.chunks(37) {
            p.feed(chunk);
        }
        let status = |n: &str| p.pkgs.iter().find(|x| x.name == n).map(|x| x.status);
        assert_eq!(status("bad_pkg"), Some(PkgStatus::Failed));
        assert_eq!(status("after_pkg"), Some(PkgStatus::Aborted));
        assert_eq!(status("good_pkg"), Some(PkgStatus::Aborted));
        assert_eq!(status("slow_pkg"), Some(PkgStatus::Aborted));
        assert_eq!(p.pkgs.len(), 4);
        assert_eq!(p.failed, vec!["bad_pkg"]);
        assert_eq!(p.aborted, vec!["after_pkg", "good_pkg", "slow_pkg"]);
        assert_eq!(p.stderr_pkgs, vec!["bad_pkg"]);
        assert_eq!(p.summary[0], "Summary: 0 packages finished [5.48s]");
        let fe = p.first_error.clone().unwrap();
        assert!(fe.contains("deliberate failure"), "{fe}");
        assert_eq!(p.pkgs.iter().find(|x| x.name == "bad_pkg").unwrap().seconds, Some(0.53));

        let mut st = BuildState { running: true, ..Default::default() };
        st.absorb(&p);
        st.finish(Some(1), 10);
        assert_eq!(st.ok, Some(false));
        assert!(!st.running);
    }

    #[test]
    fn successful_build() {
        let mut p = ColconParser::default();
        p.feed(b"Starting >>> blueboat_interfaces\r\n\x1b]0;colcon build [0/2 done]\x07[0.6s] [0/2 complete]\r     \rFinished <<< blueboat_interfaces [12.31s]\r\nStarting >>> blueboat_sss\r\nFinished <<< blueboat_sss [3.2s]\r\n\r\nSummary: 2 packages finished [15.9s]\r\n");
        assert_eq!(p.finished(), vec!["blueboat_interfaces", "blueboat_sss"]);
        assert!(p.failed.is_empty());
        assert_eq!(p.pkgs[0].seconds, Some(12.31));
        let mut st = BuildState::default();
        st.absorb(&p);
        st.finish(Some(0), 1);
        assert_eq!(st.ok, Some(true));
        assert!(st.first_error.is_none());
    }

    #[test]
    fn interrupted_build() {
        let mut p = ColconParser::default();
        p.feed(b"Starting >>> blueboat_control\n");
        let mut st = BuildState::default();
        st.absorb(&p);
        st.finish(None, 1);
        assert_eq!(st.ok, Some(false));
        assert_eq!(st.packages[0].status, PkgStatus::Aborted);
        assert_eq!(st.first_error.as_deref(), Some("the build was interrupted"));
    }

    #[test]
    fn ignores_lookalikes() {
        let mut p = ColconParser::default();
        assert!(!p.line("Starting the thing"));
        assert!(!p.line("  1 package failed: x")); // not in a summary
        assert!(p.pkgs.is_empty() && p.failed.is_empty());
    }
}
