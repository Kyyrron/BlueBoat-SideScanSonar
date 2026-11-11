fn main() {
    // App ACL: only these commands exist for the webview; capabilities/main.json
    // allows exactly them (keep in sync with `COMMANDS` in src/lib.rs).
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "list_apps", "param_choices", "launch", "stop", "cancel_stop", "force_stop",
            "focus", "restart", "dismiss", "sessions", "attach", "detach", "write_stdin",
            "resize", "list_packages", "build", "cancel_build", "build_state", "scan_data",
            "open_path", "open_url", "open_app_folder", "open_in_app", "list_logs",
            "env_status", "quit_hub",
        ]),
    ))
    .expect("tauri-build failed");
}
