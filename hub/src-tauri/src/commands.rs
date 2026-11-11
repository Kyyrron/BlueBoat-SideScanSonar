//! The webview's whole reach: narrow, typed commands. There is no generic
//! "run a shell command" entry point; every process is spawned in Rust from
//! `apps.toml` entries.

use crate::build::BuildState;
use crate::config::{self, Group, ParamChoice, ParamSpec, Variant};
use crate::control::TermMsg;
use crate::data::{self, DataCardView};
use crate::env_status::{self, EnvProbe, GitStatus};
use crate::history::AppRun;
use crate::hub::{now_ms, xdg_open, Hub, LaunchOutcome, SessionView};
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tauri::ipc::Channel;
use tauri::State;

type H<'a> = State<'a, Arc<Hub>>;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AppView {
    pub id: String,
    pub name: String,
    pub group: String,
    pub description: String,
    pub help: Option<String>,
    pub icon: String,
    pub singleton: bool,
    pub window: bool,
    /// "close" | "ctrl-c"
    pub stop: crate::config::StopMode,
    pub warning: Option<String>,
    pub force_warning: Option<String>,
    pub primary: bool,
    pub planned: bool,
    pub optional: bool,
    pub params: Vec<ParamSpec>,
    pub variants: Vec<Variant>,
    pub available: bool,
    pub reason: Option<String>,
    pub fallback: bool,
    pub command: String,
    pub cwd: String,
    pub last_run: Option<AppRun>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AppsView {
    pub groups: Vec<Group>,
    pub apps: Vec<AppView>,
    pub errors: Vec<String>,
    pub config_path: String,
    pub loaded_ms: i64,
}

#[tauri::command]
pub async fn list_apps(hub: H<'_>) -> Result<AppsView, String> {
    let lc = hub.config.read().unwrap();
    let res = lc.resolver.clone();
    let mut apps = vec![];
    let mut groups = vec![];
    if let Some(cfg) = &lc.cfg {
        groups = cfg.groups.clone();
        for a in &cfg.apps {
            let choice = config::choose_command(a, &res);
            apps.push(AppView {
                id: a.id.clone(),
                name: a.name.clone(),
                group: a.group.clone(),
                description: a.description.clone(),
                help: a.help.clone(),
                icon: a.icon.clone(),
                singleton: a.singleton,
                window: a.window,
                stop: a.stop,
                warning: a.warning.clone(),
                force_warning: a.force_warning.clone(),
                primary: a.primary,
                planned: a.planned,
                optional: a.optional,
                params: a.params.clone(),
                variants: a.variants.clone(),
                available: choice.is_ok(),
                reason: choice.as_ref().err().cloned(),
                fallback: choice.as_ref().is_ok_and(|c| c.fallback),
                command: choice.map(|c| c.command).unwrap_or_else(|_| a.command.clone()),
                cwd: a.cwd.clone(),
                last_run: hub.history_for(&a.id),
            });
        }
    }
    Ok(AppsView {
        groups,
        apps,
        errors: lc.errors.clone(),
        config_path: hub.paths.apps_toml().to_string_lossy().into_owned(),
        loaded_ms: lc.loaded_ms,
    })
}

#[tauri::command]
pub async fn param_choices(hub: H<'_>, app: String, param: String) -> Result<Vec<ParamChoice>, String> {
    let a = hub.app_entry(&app).ok_or("unknown app")?;
    let p = a
        .params
        .iter()
        .find(|p| p.name == param)
        .ok_or("unknown parameter")?;
    Ok(config::param_choices(p, &hub.resolver()))
}

#[tauri::command]
pub async fn launch(
    hub: H<'_>,
    app: String,
    params: HashMap<String, String>,
    variant: Option<String>,
) -> Result<LaunchOutcome, String> {
    hub.inner().launch(&app, params, variant)
}

#[tauri::command]
pub async fn stop(hub: H<'_>, session: String) -> Result<(), String> {
    hub.inner().stop(&session)
}

#[tauri::command]
pub async fn cancel_stop(hub: H<'_>, session: String) -> Result<(), String> {
    hub.cancel_stop(&session)
}

#[tauri::command]
pub async fn force_stop(hub: H<'_>, session: String, kill: bool) -> Result<(), String> {
    hub.force_stop(&session, kill)
}

#[tauri::command]
pub async fn focus(hub: H<'_>, session: String) -> Result<(), String> {
    hub.focus(&session)
}

#[tauri::command]
pub async fn restart(hub: H<'_>, session: String) -> Result<(), String> {
    hub.inner().restart(&session)
}

#[tauri::command]
pub async fn dismiss(hub: H<'_>, session: String) -> Result<(), String> {
    hub.inner().dismiss(&session)
}

#[tauri::command]
pub async fn sessions(hub: H<'_>) -> Result<Vec<SessionView>, String> {
    Ok(hub.session_views())
}

#[tauri::command]
pub async fn attach(hub: H<'_>, session: String, on_event: Channel<TermMsg>) -> Result<(), String> {
    hub.attach(&session, on_event)
}

#[tauri::command]
pub async fn detach(hub: H<'_>, session: String) -> Result<(), String> {
    hub.detach(&session);
    Ok(())
}

/// Keystrokes typed into a terminal (UTF-8 text from xterm.js).
#[tauri::command]
pub async fn write_stdin(hub: H<'_>, session: String, data: String) -> Result<(), String> {
    hub.write_stdin(&session, data.as_bytes())
}

#[tauri::command]
pub async fn resize(hub: H<'_>, session: String, cols: u16, rows: u16) -> Result<(), String> {
    hub.resize(&session, cols, rows)
}

#[tauri::command]
pub async fn list_packages(hub: H<'_>, force: bool) -> Result<Vec<String>, String> {
    hub.list_packages(force)
}

#[tauri::command]
pub async fn build(hub: H<'_>, packages: Vec<String>) -> Result<(), String> {
    hub.inner().start_build(packages)
}

#[tauri::command]
pub async fn cancel_build(hub: H<'_>) -> Result<(), String> {
    hub.cancel_build()
}

#[tauri::command]
pub async fn build_state(hub: H<'_>) -> Result<BuildState, String> {
    Ok(hub.build_state())
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DataView {
    pub cards: Vec<DataCardView>,
    pub scanning: bool,
}

#[tauri::command]
pub async fn scan_data(hub: H<'_>, force: bool) -> Result<DataView, String> {
    if force {
        hub.request_data_scan();
    }
    let (cards, scanning) = hub.data_cards();
    Ok(DataView { cards, scanning: scanning || force })
}

/// Open a folder or file with the desktop's default tool. Only paths under
/// a data card, the hub's logs or an app folder are accepted.
#[tauri::command]
pub async fn open_path(hub: H<'_>, path: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    if !data::is_under_any(&p, &hub.openable_roots()) {
        return Err(format!("{path} is not inside a folder the hub shows"));
    }
    xdg_open(&path)
}

/// Links clicked in a terminal: http(s) only.
#[tauri::command]
pub async fn open_url(url: String) -> Result<(), String> {
    if !(url.starts_with("http://") || url.starts_with("https://")) || url.chars().any(char::is_whitespace) {
        return Err("only http(s) links open".into());
    }
    xdg_open(&url)
}

#[tauri::command]
pub async fn open_app_folder(hub: H<'_>, app: String) -> Result<(), String> {
    let a = hub.app_entry(&app).ok_or("unknown app")?;
    let p = hub.resolver().expand(&a.cwd);
    xdg_open(&p.to_string_lossy())
}

/// "Open in Log Reviewer" / "Open in Gazebo viewer" from a data card.
#[tauri::command]
pub async fn open_in_app(hub: H<'_>, app: String, param: String, path: String) -> Result<LaunchOutcome, String> {
    let mut params = HashMap::new();
    params.insert(param, path);
    hub.inner().launch(&app, params, None)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LogFile {
    pub app: String,
    pub name: String,
    pub path: String,
    pub bytes: u64,
    pub mtime_ms: i64,
}

#[tauri::command]
pub async fn list_logs(hub: H<'_>) -> Result<Vec<LogFile>, String> {
    let mut v: Vec<LogFile> = std::fs::read_dir(&hub.paths.logs_dir)
        .map(|rd| {
            rd.flatten()
                .filter_map(|e| {
                    let name = e.file_name().to_string_lossy().into_owned();
                    if !name.ends_with(".log") {
                        return None;
                    }
                    let app = name.split('-').next()?.to_string();
                    let meta = e.metadata().ok()?;
                    Some(LogFile {
                        app,
                        path: e.path().to_string_lossy().into_owned(),
                        bytes: meta.len(),
                        mtime_ms: config::mtime_ms(&e.path()),
                        name,
                    })
                })
                .collect()
        })
        .unwrap_or_default();
    v.sort_by_key(|f| std::cmp::Reverse(f.mtime_ms));
    Ok(v)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Pill {
    pub ok: bool,
    pub label: String,
    pub detail: String,
    pub ms: Option<i64>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EnvView {
    pub ros: Pill,
    pub venv: Pill,
    pub install: Pill,
    pub git: GitStatus,
    pub x11: bool,
    pub session_type: String,
    pub tmux: Option<String>,
    pub probe: EnvProbe,
    pub workspace: String,
    pub data_root: String,
    pub config_path: String,
    pub state_dir: String,
    pub logs_dir: String,
    pub socket: String,
    pub now_ms: i64,
}

#[tauri::command]
pub async fn env_status(hub: H<'_>) -> Result<EnvView, String> {
    let res = hub.resolver();
    let probe = hub.probe();
    let ros_dir = PathBuf::from("/opt/ros/jazzy/setup.bash");
    let ros = match (&probe.ros_distro, probe.done) {
        (Some(d), _) => Pill { ok: true, label: format!("ROS {d}"), detail: "sourced in the apps' shell (~/.bashrc)".into(), ms: None },
        (None, true) => Pill {
            ok: false,
            label: "ROS not sourced".into(),
            detail: if ros_dir.is_file() {
                "~/.bashrc does not source /opt/ros/jazzy/setup.bash; env.sh still chains it through install/setup.bash".into()
            } else {
                "/opt/ros/jazzy is missing".into()
            },
            ms: None,
        },
        (None, false) => Pill { ok: ros_dir.is_file(), label: "ROS …".into(), detail: "checking the apps' shell".into(), ms: None },
    };
    let venv_ok = res.ws.join(".venv/bin/activate").is_file();
    let venv = Pill {
        ok: venv_ok,
        label: "venv".into(),
        detail: if venv_ok { format!("{}/.venv", res.ws.display()) } else { format!("{}/.venv is missing — env.sh will fail", res.ws.display()) },
        ms: None,
    };
    let setup = res.ws.join("install/setup.bash");
    let install = if setup.is_file() {
        Pill { ok: true, label: "install".into(), detail: setup.to_string_lossy().into_owned(), ms: Some(config::mtime_ms(&setup)) }
    } else {
        Pill { ok: false, label: "not built".into(), detail: format!("{} is missing — run Build", setup.display()), ms: None }
    };
    let sp = hub.paths.superproject.clone();
    let git = tauri::async_runtime::spawn_blocking(move || env_status::git_status(&sp))
        .await
        .map_err(|e| e.to_string())?;
    Ok(EnvView {
        ros,
        venv,
        install,
        git,
        x11: hub.x11_ok(),
        session_type: std::env::var("XDG_SESSION_TYPE").unwrap_or_default(),
        tmux: hub.tmux.version(),
        probe,
        workspace: res.ws.to_string_lossy().into_owned(),
        data_root: res.data_root.to_string_lossy().into_owned(),
        config_path: hub.paths.apps_toml().to_string_lossy().into_owned(),
        state_dir: hub.paths.state_dir.to_string_lossy().into_owned(),
        logs_dir: hub.paths.logs_dir.to_string_lossy().into_owned(),
        socket: crate::tmux::SOCKET.into(),
        now_ms: now_ms(),
    })
}

/// The quit dialog's answer: exit the hub (apps keep running in tmux).
#[tauri::command]
pub async fn quit_hub(app: tauri::AppHandle, hub: H<'_>) -> Result<(), String> {
    hub.quitting.store(true, std::sync::atomic::Ordering::SeqCst);
    hub.shutdown();
    app.exit(0);
    Ok(())
}
