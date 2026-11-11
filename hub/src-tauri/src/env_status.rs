//! Top-bar status pills: ROS sourced, `.venv`, install age, superproject
//! branch and modified submodules (read-only git).
//!
//! The hub is started from the desktop, not from a sourced shell, so what
//! the *apps* see is probed once through the same shell they run in
//! (`bash -ic`): `ROS_DISTRO` and `BLUEBOAT_DATA_DIR` as ~/.bashrc sets them.

use serde::Serialize;
use std::path::Path;
use std::process::{Command, Stdio};

#[derive(Debug, Clone, Default, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EnvProbe {
    pub done: bool,
    pub ros_distro: Option<String>,
    pub data_dir_env: Option<String>,
    pub error: Option<String>,
}

const MARK: &str = "@@BLUEBOAT_HUB_PROBE@@";

pub fn parse_probe(stdout: &str) -> Option<(Option<String>, Option<String>)> {
    let line = stdout.lines().rev().find(|l| l.starts_with(MARK))?;
    let rest = &line[MARK.len()..];
    let mut f = rest.split('\u{1f}');
    let nz = |s: Option<&str>| s.map(str::trim).filter(|s| !s.is_empty()).map(String::from);
    Some((nz(f.next()), nz(f.next())))
}

/// Run the configured shell once and read the variables apps will see.
pub fn probe(shell: &[String], workspace: &str) -> EnvProbe {
    let Some((prog, args)) = shell.split_first() else {
        return EnvProbe { done: true, error: Some("no shell configured".into()), ..Default::default() };
    };
    let script = format!(
        "cd {workspace} 2>/dev/null; printf '\\n{MARK}%s\\037%s\\n' \"$ROS_DISTRO\" \"$BLUEBOAT_DATA_DIR\""
    );
    let out = Command::new(prog)
        .args(args)
        .arg(script)
        .stdin(Stdio::null())
        .stderr(Stdio::null())
        .stdout(Stdio::piped())
        .output();
    match out {
        Ok(o) => match parse_probe(&String::from_utf8_lossy(&o.stdout)) {
            Some((ros, data)) => EnvProbe { done: true, ros_distro: ros, data_dir_env: data, error: None },
            None => EnvProbe { done: true, error: Some("the shell probe printed nothing".into()), ..Default::default() },
        },
        Err(e) => EnvProbe { done: true, error: Some(e.to_string()), ..Default::default() },
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GitStatus {
    pub branch: Option<String>,
    pub modified_submodules: Vec<String>,
    pub other_changes: usize,
}

/// `path = X` lines of `.gitmodules`.
pub fn submodule_paths(gitmodules: &str) -> Vec<String> {
    gitmodules
        .lines()
        .filter_map(|l| {
            let (k, v) = l.trim().split_once('=')?;
            (k.trim() == "path").then(|| v.trim().to_string())
        })
        .collect()
}

/// Porcelain v1 lines → (modified submodules, other changed paths).
pub fn split_status(porcelain: &str, subs: &[String]) -> (Vec<String>, usize) {
    let mut mods = vec![];
    let mut other = 0;
    for l in porcelain.lines() {
        if l.len() < 4 {
            continue;
        }
        let path = l[3..].trim().trim_matches('"');
        if subs.iter().any(|s| s == path) {
            mods.push(path.to_string());
        } else {
            other += 1;
        }
    }
    (mods, other)
}

fn git(sp: &Path, args: &[&str]) -> Option<String> {
    Command::new("git")
        .arg("-C")
        .arg(sp)
        .args(args)
        // never take index.lock: this is a read-only view
        .env("GIT_OPTIONAL_LOCKS", "0")
        .stdin(Stdio::null())
        .stderr(Stdio::null())
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).into_owned())
}

pub fn git_status(sp: &Path) -> GitStatus {
    let branch = git(sp, &["rev-parse", "--abbrev-ref", "HEAD"]).map(|s| s.trim().to_string());
    let subs = std::fs::read_to_string(sp.join(".gitmodules"))
        .map(|t| submodule_paths(&t))
        .unwrap_or_default();
    let (mods, other) = git(sp, &["status", "--porcelain=v1", "--ignore-submodules=none"])
        .map(|s| split_status(&s, &subs))
        .unwrap_or_default();
    GitStatus { branch, modified_submodules: mods, other_changes: other }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn probe_output() {
        let out = "some bashrc noise\n\n@@BLUEBOAT_HUB_PROBE@@jazzy\u{1f}\n";
        assert_eq!(parse_probe(out), Some((Some("jazzy".into()), None)));
        let out = "@@BLUEBOAT_HUB_PROBE@@\u{1f}/mnt/d\n";
        assert_eq!(parse_probe(out), Some((None, Some("/mnt/d".into()))));
        assert_eq!(parse_probe("nothing"), None);
    }

    #[test]
    fn real_shell_probe_runs() {
        // plain sh, so the test needs no ~/.bashrc
        let p = probe(&["sh".into(), "-c".into()], "/");
        assert!(p.done && p.error.is_none(), "{p:?}");
    }

    #[test]
    fn git_parsing() {
        let gm = "[submodule \"A\"]\n\tpath = BlueBoat-Control\n\turl = x\n[submodule \"B\"]\n\tpath = BlueBoat-MCS\n";
        let subs = submodule_paths(gm);
        assert_eq!(subs, vec!["BlueBoat-Control", "BlueBoat-MCS"]);
        let st = " M BlueBoat-Control\n M .claude/CLAUDE.md\n?? hub/\n";
        let (m, o) = split_status(st, &subs);
        assert_eq!(m, vec!["BlueBoat-Control"]);
        assert_eq!(o, 2);
    }
}
