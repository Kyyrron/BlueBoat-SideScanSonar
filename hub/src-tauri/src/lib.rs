//! BlueBoat Hub — a launcher, not a container: it starts, watches and stops
//! the project's apps (each in its own tmux session, each keeping its own
//! window), builds the workspace and opens the data folders.

pub mod build;
pub mod commands;
pub mod config;
pub mod control;
pub mod data;
pub mod env_status;
pub mod history;
pub mod hub;
pub mod paths;
pub mod procs;
pub mod shell;
pub mod tmux;
pub mod x11win;

use std::sync::atomic::Ordering;
use std::sync::Arc;
use tauri::{Emitter, Manager};

/// Every command the webview may call (also the app ACL manifest in build.rs).
pub const COMMANDS: &[&str] = &[
    "list_apps",
    "param_choices",
    "launch",
    "stop",
    "cancel_stop",
    "force_stop",
    "focus",
    "restart",
    "dismiss",
    "sessions",
    "attach",
    "detach",
    "write_stdin",
    "resize",
    "list_packages",
    "build",
    "cancel_build",
    "build_state",
    "scan_data",
    "open_path",
    "open_url",
    "open_app_folder",
    "open_in_app",
    "list_logs",
    "env_status",
    "quit_hub",
];

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.show();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            let hub = hub::Hub::new(app.handle().clone());
            hub.start();
            app.manage(hub);
            Ok(())
        })
        .on_window_event(|window, event| match event {
            tauri::WindowEvent::CloseRequested { api, .. } => {
                let hub = window.state::<Arc<hub::Hub>>();
                if hub.quitting.load(Ordering::SeqCst) {
                    return;
                }
                let live = hub.live_sessions();
                if !live.is_empty() {
                    api.prevent_close();
                    let _ = window.emit("quit-requested", &live);
                }
            }
            tauri::WindowEvent::Focused(f) => {
                let hub = window.state::<Arc<hub::Hub>>();
                hub.focused.store(*f, Ordering::SeqCst);
                if *f {
                    hub.request_data_scan();
                }
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            commands::list_apps,
            commands::param_choices,
            commands::launch,
            commands::stop,
            commands::cancel_stop,
            commands::force_stop,
            commands::focus,
            commands::restart,
            commands::dismiss,
            commands::sessions,
            commands::attach,
            commands::detach,
            commands::write_stdin,
            commands::resize,
            commands::list_packages,
            commands::build,
            commands::cancel_build,
            commands::build_state,
            commands::scan_data,
            commands::open_path,
            commands::open_url,
            commands::open_app_folder,
            commands::open_in_app,
            commands::list_logs,
            commands::env_status,
            commands::quit_hub,
        ])
        .build(tauri::generate_context!())
        .expect("BlueBoat Hub failed to start")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(hub) = app.try_state::<Arc<hub::Hub>>() {
                    hub.shutdown();
                }
            }
        });
}

#[cfg(test)]
mod tests {
    use super::COMMANDS;

    /// The command list, the ACL manifest (build.rs) and the window's
    /// capability must name the same commands: nothing exposed by accident.
    #[test]
    fn acl_lists_agree() {
        let build_rs = include_str!("../build.rs");
        let caps = include_str!("../capabilities/main.json");
        let lib = include_str!("lib.rs");
        for c in COMMANDS {
            assert!(build_rs.contains(&format!("\"{c}\"")), "{c} missing from build.rs");
            let perm = format!("\"allow-{}\"", c.replace('_', "-"));
            assert!(caps.contains(&perm), "{perm} missing from capabilities/main.json");
            assert!(lib.contains(&format!("commands::{c},")), "{c} missing from generate_handler!");
        }
        let n_caps = caps.matches("\"allow-").count();
        assert_eq!(n_caps, COMMANDS.len(), "capabilities allow a command that does not exist");
    }
}
