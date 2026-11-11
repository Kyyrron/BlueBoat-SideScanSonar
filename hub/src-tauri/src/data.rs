//! Data view: read-only folder cards (CM-7 — the hub lists, sizes and
//! opens; it never writes, moves or deletes anything under these roots).

use crate::config::{mtime_ms, DataCardCfg, EntryAction};
use crate::paths::Resolver;
use crate::shell::wildcard_match;
use serde::Serialize;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DataCardView {
    pub id: String,
    pub name: String,
    pub icon: String,
    pub description: String,
    pub tabs: Vec<DataTabView>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DataTabView {
    pub label: String,
    pub path: String,
    pub exists: bool,
    pub count: usize,
    pub total_bytes: u64,
    pub newest_name: Option<String>,
    pub newest_ms: Option<i64>,
    /// the 10 newest entries
    pub entries: Vec<DataEntry>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DataEntry {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub bytes: u64,
    pub mtime_ms: i64,
    pub action: Option<EntryActionView>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EntryActionView {
    pub label: String,
    pub app: String,
    pub param: String,
    /// what is passed to the app (the entry, or the matching file inside it)
    pub target: String,
}

/// Recursive size without following symlinks; capped so a pathological tree
/// can't stall the scan thread.
pub fn tree_size(p: &Path) -> u64 {
    let mut total = 0u64;
    let mut stack = vec![p.to_path_buf()];
    let mut visited = 0usize;
    while let Some(d) = stack.pop() {
        let Ok(meta) = std::fs::symlink_metadata(&d) else {
            continue;
        };
        if meta.is_dir() {
            if let Ok(rd) = std::fs::read_dir(&d) {
                for e in rd.flatten() {
                    visited += 1;
                    if visited > 500_000 {
                        return total;
                    }
                    stack.push(e.path());
                }
            }
        } else {
            total += meta.len();
        }
    }
    total
}

fn entry_paths(dir: &Path, depth: u32, exclude: &[String]) -> Vec<PathBuf> {
    let mut out = vec![];
    let Ok(rd) = std::fs::read_dir(dir) else {
        return out;
    };
    for e in rd.flatten() {
        let name = e.file_name().to_string_lossy().into_owned();
        if name.starts_with('.') || exclude.iter().any(|x| x == &name) {
            continue;
        }
        let p = e.path();
        if depth > 1 {
            if p.is_dir() {
                out.extend(entry_paths(&p, depth - 1, &[]));
            }
        } else {
            out.push(p);
        }
    }
    out
}

pub fn resolve_action(entry: &Path, is_dir: bool, actions: &[EntryAction]) -> Option<EntryActionView> {
    let name = entry.file_name()?.to_str()?;
    for a in actions {
        match a.when.as_deref() {
            Some("file") if is_dir => continue,
            Some("dir") if !is_dir => continue,
            _ => {}
        }
        if let Some(g) = &a.glob {
            if !wildcard_match(g, name) {
                continue;
            }
        }
        let target = if let Some(pat) = &a.contains {
            if !is_dir {
                continue;
            }
            let mut found: Vec<PathBuf> = std::fs::read_dir(entry)
                .map(|rd| {
                    rd.flatten()
                        .map(|e| e.path())
                        .filter(|p| {
                            p.is_file()
                                && p.file_name()
                                    .and_then(|n| n.to_str())
                                    .is_some_and(|n| wildcard_match(pat, n))
                        })
                        .collect()
                })
                .unwrap_or_default();
            found.sort();
            match found.into_iter().next() {
                Some(f) => f,
                None => continue,
            }
        } else if let Some(m) = &a.marker {
            if !is_dir || !entry.join(m).is_file() {
                continue;
            }
            entry.to_path_buf()
        } else {
            entry.to_path_buf()
        };
        return Some(EntryActionView {
            label: a.label.clone(),
            app: a.app.clone(),
            param: a.param.clone(),
            target: target.to_string_lossy().into_owned(),
        });
    }
    None
}

pub fn scan_card(card: &DataCardCfg, res: &Resolver) -> DataCardView {
    let tabs = card
        .tabs
        .iter()
        .map(|t| {
            let path = res.expand(&t.path);
            let exists = path.is_dir();
            let mut entries: Vec<(PathBuf, i64, u64)> = entry_paths(&path, card.depth.max(1), &card.exclude)
                .into_iter()
                .map(|p| {
                    let m = mtime_ms(&p);
                    let b = tree_size(&p);
                    (p, m, b)
                })
                .collect();
            entries.sort_by_key(|e| std::cmp::Reverse(e.1));
            let count = entries.len();
            let total_bytes: u64 = entries.iter().map(|e| e.2).sum();
            let newest = entries.first().map(|(p, m, _)| (p.clone(), *m));
            let shown = entries
                .iter()
                .take(10)
                .map(|(p, m, b)| {
                    let is_dir = p.is_dir();
                    DataEntry {
                        name: p
                            .strip_prefix(&path)
                            .map(|r| r.to_string_lossy().into_owned())
                            .unwrap_or_default(),
                        path: p.to_string_lossy().into_owned(),
                        is_dir,
                        bytes: *b,
                        mtime_ms: *m,
                        action: resolve_action(p, is_dir, &card.actions),
                    }
                })
                .collect();
            DataTabView {
                label: t.label.clone(),
                path: path.to_string_lossy().into_owned(),
                exists,
                count,
                total_bytes,
                newest_name: newest.as_ref().and_then(|(p, _)| {
                    p.strip_prefix(&path).ok().map(|r| r.to_string_lossy().into_owned())
                }),
                newest_ms: newest.map(|(_, m)| m),
                entries: shown,
            }
        })
        .collect();
    DataCardView {
        id: card.id.clone(),
        name: card.name.clone(),
        icon: card.icon.clone(),
        description: card.description.clone(),
        tabs,
    }
}

/// `true` if `p` lies under one of `roots` (both canonicalized, so `..`
/// and symlinks can't escape). Gates `open_path`.
pub fn is_under_any(p: &Path, roots: &[PathBuf]) -> bool {
    let Ok(cp) = p.canonicalize() else {
        return false;
    };
    roots
        .iter()
        .filter_map(|r| r.canonicalize().ok())
        .any(|r| cp.starts_with(&r))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::DataTabCfg;

    fn tmp(tag: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("bbhub-data-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn scans_counts_sizes_and_actions() {
        let root = tmp("scan");
        let robot = root.join("data/Robot_data");
        std::fs::create_dir_all(robot.join("2026_11_11-12_06_36-sim-poslog")).unwrap();
        std::fs::write(robot.join("2026_11_11-12_06_36-sim-poslog/2026_11_11-12_06_36-sim-poslog.csv"), "abcd").unwrap();
        std::fs::write(robot.join("2026_11_10-poslog.csv"), "12").unwrap();
        std::fs::write(robot.join(".hidden"), "zzzz").unwrap();
        let res = Resolver {
            home: root.clone(),
            ws: root.clone(),
            data_root: root.join("data"),
            superproject: root.clone(),
        };
        let card = DataCardCfg {
            id: "robot".into(),
            name: "Robot".into(),
            icon: "folder".into(),
            description: String::new(),
            tabs: vec![
                DataTabCfg { label: "Robot_data".into(), path: "{data_root}/Robot_data".into() },
                DataTabCfg { label: "missing".into(), path: "{data_root}/nope".into() },
            ],
            depth: 1,
            exclude: vec![],
            actions: vec![
                EntryAction { label: "Open in Log Reviewer".into(), app: "log_reviewer".into(), param: "csv".into(), when: Some("file".into()), glob: Some("*-poslog.csv".into()), contains: None, marker: None },
                EntryAction { label: "Open in Log Reviewer".into(), app: "log_reviewer".into(), param: "csv".into(), when: Some("dir".into()), glob: None, contains: Some("*-poslog.csv".into()), marker: None },
            ],
        };
        let v = scan_card(&card, &res);
        let t = &v.tabs[0];
        assert!(t.exists);
        assert_eq!(t.count, 2, "hidden files are not counted");
        assert_eq!(t.total_bytes, 4 + 2, "hidden files are not sized either");
        for e in &t.entries {
            let a = e.action.as_ref().expect("both entries open in the reviewer");
            assert!(a.target.ends_with("-poslog.csv"));
        }
        assert!(!v.tabs[1].exists);
        assert_eq!(v.tabs[1].count, 0);
        assert!(is_under_any(&robot.join("2026_11_10-poslog.csv"), std::slice::from_ref(&robot)));
        assert!(!is_under_any(&robot.join("../.."), std::slice::from_ref(&robot)));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn worlds_two_levels_with_marker() {
        let root = tmp("worlds");
        std::fs::create_dir_all(root.join("pool/w1")).unwrap();
        std::fs::write(root.join("pool/w1/world.sdf"), "").unwrap();
        std::fs::create_dir_all(root.join("pool/w2")).unwrap();
        let actions = vec![EntryAction { label: "Open in Gazebo viewer".into(), app: "gazebo_world".into(), param: "world".into(), when: Some("dir".into()), glob: None, contains: None, marker: Some("world.sdf".into()) }];
        let ents = entry_paths(&root, 2, &[]);
        assert_eq!(ents.len(), 2);
        let with: Vec<bool> = ents.iter().map(|p| resolve_action(p, true, &actions).is_some()).collect();
        assert_eq!(with.iter().filter(|b| **b).count(), 1);
        let _ = std::fs::remove_dir_all(&root);
    }
}
