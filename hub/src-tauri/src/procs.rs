//! Process tree from `/proc`: an app's windows are found by the
//! `_NET_WM_PID` of any process below its tmux pane (`ros2 launch` → `gz`,
//! AppImage runtime → QGroundControl, …).

use std::collections::{HashMap, HashSet};

/// `/proc/<pid>/stat` → (pid, ppid). The command name sits in parentheses
/// and may itself contain spaces or `)`, so parse after the *last* `)`.
pub fn parse_stat(s: &str) -> Option<(u32, u32)> {
    let open = s.find('(')?;
    let close = s.rfind(')')?;
    let pid = s[..open].trim().parse().ok()?;
    let mut rest = s[close + 1..].split_whitespace();
    let _state = rest.next()?;
    let ppid = rest.next()?.parse().ok()?;
    Some((pid, ppid))
}

/// parent → children for every live process.
pub fn snapshot() -> HashMap<u32, Vec<u32>> {
    let mut children: HashMap<u32, Vec<u32>> = HashMap::new();
    if let Ok(rd) = std::fs::read_dir("/proc") {
        for e in rd.flatten() {
            let name = e.file_name();
            let Some(pid) = name.to_str().and_then(|n| n.parse::<u32>().ok()) else {
                continue;
            };
            if let Ok(stat) = std::fs::read_to_string(format!("/proc/{pid}/stat")) {
                if let Some((p, ppid)) = parse_stat(&stat) {
                    children.entry(ppid).or_default().push(p);
                }
            }
        }
    }
    children
}

/// `root` and every process below it.
pub fn descendants(root: u32, children: &HashMap<u32, Vec<u32>>) -> HashSet<u32> {
    let mut out = HashSet::new();
    let mut stack = vec![root];
    while let Some(p) = stack.pop() {
        if out.insert(p) {
            if let Some(c) = children.get(&p) {
                stack.extend(c.iter().copied());
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stat_parsing() {
        assert_eq!(parse_stat("41233 (python3) S 41200 41233 41233 0 -1"), Some((41233, 41200)));
        assert_eq!(parse_stat("7 (weird ) name) R 1 7 7"), Some((7, 1)));
        assert_eq!(parse_stat("garbage"), None);
    }

    #[test]
    fn tree() {
        let mut m: HashMap<u32, Vec<u32>> = HashMap::new();
        m.insert(1, vec![10, 20]);
        m.insert(10, vec![11]);
        m.insert(11, vec![12]);
        let d = descendants(10, &m);
        assert_eq!(d, [10, 11, 12].into_iter().collect());
        assert!(!d.contains(&20));
    }

    #[test]
    fn live_proc_has_self() {
        let me = std::process::id();
        let snap = snapshot();
        assert!(snap.values().any(|c| c.contains(&me)));
    }
}
