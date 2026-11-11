//! The hub's own state files under `~/.local/state/blueboat-hub/`:
//! last run per app (`history.json`) and the last build (`build.json`).
//! Nothing here touches project data.

use serde::{de::DeserializeOwned, Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppRun {
    pub started_ms: i64,
    pub ended_ms: Option<i64>,
    pub exit_code: Option<i32>,
    pub signal: Option<i32>,
    #[serde(default)]
    pub params: HashMap<String, String>,
    #[serde(default)]
    pub variant: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct History {
    #[serde(default)]
    pub apps: HashMap<String, AppRun>,
}

pub fn load_json<T: DeserializeOwned + Default>(path: &Path) -> T {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_default()
}

/// Write via a temporary file + rename, so a crash never leaves half a file.
pub fn save_json<T: Serialize>(path: &Path, value: &T) -> std::io::Result<()> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, serde_json::to_vec_pretty(value)?)?;
    std::fs::rename(&tmp, path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip() {
        let d = std::env::temp_dir().join(format!("bbhub-hist-{}", std::process::id()));
        let p = d.join("history.json");
        let mut h = History::default();
        h.apps.insert("gcs".into(), AppRun { started_ms: 5, exit_code: Some(0), ..Default::default() });
        save_json(&p, &h).unwrap();
        let back: History = load_json(&p);
        assert_eq!(back.apps["gcs"].started_ms, 5);
        let missing: History = load_json(&d.join("nope.json"));
        assert!(missing.apps.is_empty());
        let _ = std::fs::remove_dir_all(&d);
    }
}
