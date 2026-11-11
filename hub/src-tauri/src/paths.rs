//! Where things live: the hub's own directory, its state directory and the
//! placeholder expansion used by `apps.toml` (`~`, `{workspace}`,
//! `{data_root}`, `{superproject}`, `{home}`).

use std::path::{Path, PathBuf};

/// Fixed locations, resolved once at start.
#[derive(Debug, Clone)]
pub struct Paths {
    pub home: PathBuf,
    /// `hub/` in the superproject: holds `apps.toml` and `tmux.conf`.
    pub hub_dir: PathBuf,
    /// The superproject checkout (parent of `hub/`).
    pub superproject: PathBuf,
    /// `~/.local/state/blueboat-hub` (or `$XDG_STATE_HOME/blueboat-hub`).
    pub state_dir: PathBuf,
    /// `<state_dir>/logs`: one file per app session (tmux `pipe-pane`).
    pub logs_dir: PathBuf,
}

impl Paths {
    pub fn from_env() -> Paths {
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("/"));
        // The binary is built from this checkout, so the compile-time path is
        // the right default; BLUEBOAT_HUB_DIR overrides it.
        let hub_dir = std::env::var_os("BLUEBOAT_HUB_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|| {
                Path::new(env!("CARGO_MANIFEST_DIR"))
                    .parent()
                    .map(Path::to_path_buf)
                    .unwrap_or_else(|| PathBuf::from("."))
            });
        let superproject = hub_dir
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or_else(|| hub_dir.clone());
        let state_base = std::env::var_os("XDG_STATE_HOME")
            .map(PathBuf::from)
            .filter(|p| p.is_absolute())
            .unwrap_or_else(|| home.join(".local/state"));
        let state_dir = state_base.join("blueboat-hub");
        let logs_dir = state_dir.join("logs");
        Paths {
            home,
            hub_dir,
            superproject,
            state_dir,
            logs_dir,
        }
    }

    pub fn apps_toml(&self) -> PathBuf {
        self.hub_dir.join("apps.toml")
    }

    pub fn tmux_conf(&self) -> PathBuf {
        self.hub_dir.join("tmux.conf")
    }
}

/// Resolves the path placeholders of `apps.toml`. Built per config load,
/// because the workspace comes from `[defaults] workspace`.
#[derive(Debug, Clone)]
pub struct Resolver {
    pub home: PathBuf,
    pub ws: PathBuf,
    pub data_root: PathBuf,
    pub superproject: PathBuf,
}

impl Resolver {
    pub fn new(paths: &Paths, workspace: &str, data_dir_env: Option<&str>) -> Resolver {
        let ws = expand_home(workspace, &paths.home);
        let data_root = data_root_from(data_dir_env, &ws, &paths.home);
        Resolver {
            home: paths.home.clone(),
            ws,
            data_root,
            superproject: paths.superproject.clone(),
        }
    }

    /// Expand a configured path. Relative results are taken from the workspace.
    pub fn expand(&self, s: &str) -> PathBuf {
        let s = s.trim();
        let p = if let Some(rest) = s.strip_prefix("{workspace}") {
            join_rest(&self.ws, rest)
        } else if let Some(rest) = s.strip_prefix("{data_root}") {
            join_rest(&self.data_root, rest)
        } else if let Some(rest) = s.strip_prefix("{superproject}") {
            join_rest(&self.superproject, rest)
        } else if let Some(rest) = s.strip_prefix("{home}") {
            join_rest(&self.home, rest)
        } else {
            expand_home(s, &self.home)
        };
        if p.is_absolute() {
            p
        } else {
            self.ws.join(p)
        }
    }
}

fn join_rest(base: &Path, rest: &str) -> PathBuf {
    let r = rest.trim_start_matches('/');
    if r.is_empty() {
        base.to_path_buf()
    } else {
        base.join(r)
    }
}

/// `~` and `~/x` → home; anything else unchanged.
pub fn expand_home(s: &str, home: &Path) -> PathBuf {
    if s == "~" {
        home.to_path_buf()
    } else if let Some(rest) = s.strip_prefix("~/") {
        home.join(rest)
    } else {
        PathBuf::from(s)
    }
}

/// Same precedence as `custom_functions.data_root` for a process started
/// from the workspace: `$BLUEBOAT_DATA_DIR` (when non-empty), else
/// `<workspace>/data`. A relative `$BLUEBOAT_DATA_DIR` is taken from the
/// workspace, which is the cwd every app command starts in.
pub fn data_root_from(env: Option<&str>, ws: &Path, home: &Path) -> PathBuf {
    match env.map(str::trim) {
        Some(v) if !v.is_empty() => {
            let p = expand_home(v, home);
            if p.is_absolute() {
                p
            } else {
                ws.join(p)
            }
        }
        _ => ws.join("data"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn res() -> Resolver {
        Resolver {
            home: PathBuf::from("/home/u"),
            ws: PathBuf::from("/home/u/ros2_ws"),
            data_root: PathBuf::from("/home/u/ros2_ws/data"),
            superproject: PathBuf::from("/home/u/ros2_ws/src/SP"),
        }
    }

    #[test]
    fn data_root_precedence() {
        let ws = Path::new("/home/u/ros2_ws");
        let home = Path::new("/home/u");
        assert_eq!(data_root_from(None, ws, home), ws.join("data"));
        assert_eq!(data_root_from(Some(""), ws, home), ws.join("data"));
        assert_eq!(data_root_from(Some("  "), ws, home), ws.join("data"));
        assert_eq!(
            data_root_from(Some("/mnt/field"), ws, home),
            PathBuf::from("/mnt/field")
        );
        assert_eq!(
            data_root_from(Some("~/bb_data"), ws, home),
            PathBuf::from("/home/u/bb_data")
        );
        assert_eq!(
            data_root_from(Some("rel/data"), ws, home),
            PathBuf::from("/home/u/ros2_ws/rel/data")
        );
    }

    #[test]
    fn expand_placeholders() {
        let r = res();
        assert_eq!(r.expand("~/worlds"), PathBuf::from("/home/u/worlds"));
        assert_eq!(r.expand("{data_root}/Robot_data"), PathBuf::from("/home/u/ros2_ws/data/Robot_data"));
        assert_eq!(r.expand("{workspace}"), PathBuf::from("/home/u/ros2_ws"));
        assert_eq!(r.expand("{superproject}/hub"), PathBuf::from("/home/u/ros2_ws/src/SP/hub"));
        assert_eq!(r.expand("QGroundControl.AppImage"), PathBuf::from("/home/u/ros2_ws/QGroundControl.AppImage"));
        assert_eq!(r.expand("."), PathBuf::from("/home/u/ros2_ws/."));
        assert_eq!(r.expand("/abs/x"), PathBuf::from("/abs/x"));
    }
}
