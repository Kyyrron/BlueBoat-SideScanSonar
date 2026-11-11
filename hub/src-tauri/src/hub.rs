//! The hub's core: session registry, the 1 Hz tick, launch / polite stop /
//! restart, the build session, the data scan and config hot reload.
//!
//! The Rust side is the only place that spawns processes; the webview only
//! reaches the narrow commands in `commands.rs`.

use crate::build::{BuildState, ColconParser};
use crate::config::{self, AfterClose, AppEntry, HubConfig};
use crate::control::{ControlClient, Sink, TermMsg};
use crate::data::{self, DataCardView};
use crate::env_status::{self, EnvProbe};
use crate::history::{self, AppRun, History};
use crate::paths::{Paths, Resolver};
use crate::procs;
use crate::shell::sh_quote;
use crate::tmux::{NewSession, PaneInfo, Tmux};
use crate::x11win::{self, WinInfo, X11};
use serde::Serialize;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Mutex, RwLock};
use std::time::{Duration, Instant};
use tauri::ipc::Channel;
use tauri::{AppHandle, Emitter};
use tauri_plugin_notification::NotificationExt;

pub const BUILD_SESSION: &str = "build";
const LOGS_PER_APP: usize = 20;

pub fn now_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

pub struct LoadedConfig {
    pub cfg: Option<HubConfig>,
    pub errors: Vec<String>,
    pub resolver: Resolver,
    pub loaded_ms: i64,
}

struct StopState {
    requested_at: Instant,
    requested_ms: i64,
    ctrl_c_sent: bool,
}

struct Session {
    name: String,
    app_id: String,
    pane_id: String,
    pid: u32,
    dead: bool,
    exit_code: Option<i32>,
    signal: Option<i32>,
    started_ms: i64,
    params: HashMap<String, String>,
    variant: Option<String>,
    log: Option<String>,
    client: Option<Arc<ControlClient>>,
    stop: Option<StopState>,
    windows: Vec<WinInfo>,
    had_window: bool,
    first_seen: Instant,
    restart_pending: bool,
    exit_handled: bool,
    /// when the pane was first seen dead (its exit status may lag behind)
    dead_since: Option<Instant>,
}

impl Session {
    fn from_pane(p: &PaneInfo) -> Session {
        Session {
            name: p.session.clone(),
            app_id: if p.app.is_empty() { p.session.clone() } else { p.app.clone() },
            pane_id: p.pane_id.clone(),
            pid: p.pid,
            dead: p.dead,
            exit_code: p.dead_status,
            signal: p.dead_signal,
            started_ms: p.started_ms,
            params: serde_json::from_str(&p.params_json).unwrap_or_default(),
            variant: Some(p.variant.clone()).filter(|v| !v.is_empty()),
            log: Some(p.log.clone()).filter(|v| !v.is_empty()),
            client: None,
            stop: None,
            windows: vec![],
            had_window: false,
            first_seen: Instant::now(),
            restart_pending: false,
            exit_handled: false,
            dead_since: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct SessionView {
    pub name: String,
    pub app: String,
    /// starting | running | stopping | exited
    pub state: String,
    pub pid: u32,
    pub started_ms: i64,
    pub exit_code: Option<i32>,
    pub signal: Option<i32>,
    pub windows: Vec<WinInfo>,
    pub stop_requested_ms: Option<i64>,
    pub params: HashMap<String, String>,
    pub variant: Option<String>,
    pub log: Option<String>,
    /// a package this app uses was rebuilt after it started
    pub stale: bool,
    pub last_line: String,
    pub restart_pending: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ExitEvent {
    pub session: String,
    pub app: String,
    pub app_name: String,
    pub exit_code: Option<i32>,
    pub signal: Option<i32>,
    /// the hub asked it to stop (or restart)
    pub expected: bool,
    /// the session vanished (killed outside the hub)
    pub removed: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
#[serde(tag = "outcome")]
pub enum LaunchOutcome {
    Started { session: String },
    /// a singleton already runs; its window was brought forward
    AlreadyRunning { session: String, focused: bool },
}

/// An exit seen by the tick, handled after the session lock is released.
struct ExitRecord {
    ev: ExitEvent,
    started_ms: i64,
    params: HashMap<String, String>,
    variant: Option<String>,
    /// first tick after the hub started: record history, no toast
    quiet: bool,
}

pub struct BuildTracker {
    pub state: BuildState,
    pub parser: ColconParser,
}

pub struct Hub {
    pub app: AppHandle,
    pub paths: Paths,
    pub tmux: Tmux,
    pub config: RwLock<LoadedConfig>,
    sessions: Mutex<BTreeMap<String, Session>>,
    x11: Mutex<Option<X11>>,
    x11_ok: AtomicBool,
    pub build: Arc<Mutex<BuildTracker>>,
    history: Mutex<History>,
    data: Mutex<Vec<DataCardView>>,
    data_scanning: AtomicBool,
    data_tx: Mutex<Option<mpsc::Sender<()>>>,
    pub focused: AtomicBool,
    pub quitting: AtomicBool,
    probe: RwLock<EnvProbe>,
    last_emit: Mutex<String>,
    first_tick_done: AtomicBool,
    packages: Mutex<Option<Vec<String>>>,
    tick_lock: Mutex<()>,
    last_nudge: Mutex<Option<Instant>>,
}

fn x11_list(x: &Mutex<Option<X11>>, ok: &AtomicBool) -> Vec<WinInfo> {
    let mut g = x.lock().unwrap();
    if g.is_none() {
        *g = X11::connect().ok();
    }
    let res = g.as_ref().map(|c| c.list());
    match res {
        Some(Ok(v)) => {
            ok.store(true, Ordering::SeqCst);
            v
        }
        Some(Err(_)) => {
            *g = None; // reconnect next time
            ok.store(false, Ordering::SeqCst);
            vec![]
        }
        None => {
            ok.store(false, Ordering::SeqCst);
            vec![]
        }
    }
}

impl Hub {
    pub fn new(app: AppHandle) -> Arc<Hub> {
        let paths = Paths::from_env();
        let tmux = Tmux::new(&paths.tmux_conf());
        let env_data = std::env::var("BLUEBOAT_DATA_DIR").ok();
        let resolver = Resolver::new(&paths, "~/ros2_ws", env_data.as_deref());
        let history: History = history::load_json(&paths.state_dir.join("history.json"));
        let last_build: BuildState = history::load_json(&paths.state_dir.join("build.json"));
        let hub = Arc::new(Hub {
            app,
            tmux,
            config: RwLock::new(LoadedConfig { cfg: None, errors: vec![], resolver, loaded_ms: 0 }),
            sessions: Mutex::new(BTreeMap::new()),
            x11: Mutex::new(None),
            x11_ok: AtomicBool::new(false),
            build: Arc::new(Mutex::new(BuildTracker { state: last_build, parser: ColconParser::default() })),
            history: Mutex::new(history),
            data: Mutex::new(vec![]),
            data_scanning: AtomicBool::new(false),
            data_tx: Mutex::new(None),
            focused: AtomicBool::new(true),
            quitting: AtomicBool::new(false),
            probe: RwLock::new(EnvProbe::default()),
            last_emit: Mutex::new(String::new()),
            first_tick_done: AtomicBool::new(false),
            packages: Mutex::new(None),
            tick_lock: Mutex::new(()),
            last_nudge: Mutex::new(None),
            paths,
        });
        let _ = std::fs::create_dir_all(&hub.paths.logs_dir);
        hub.load_config();
        hub
    }

    /// Background threads: tick, config watcher, environment probe, data scan.
    pub fn start(self: &Arc<Self>) {
        let h = self.clone();
        std::thread::Builder::new()
            .name("hub-tick".into())
            .spawn(move || loop {
                h.tick();
                std::thread::sleep(Duration::from_millis(1000));
            })
            .expect("tick thread");

        let h = self.clone();
        std::thread::spawn(move || {
            let (shell, ws) = {
                let lc = h.config.read().unwrap();
                let d = lc.cfg.as_ref().map(|c| c.defaults.clone()).unwrap_or_default();
                (d.shell, d.workspace)
            };
            let p = env_status::probe(&shell, &ws);
            *h.probe.write().unwrap() = p;
            h.load_config(); // the probe may change the data root
            h.request_data_scan();
            let _ = h.app.emit("env", ());
        });

        self.start_config_watcher();
        self.start_data_thread();
    }

    // ---------------------------------------------------------------- config

    pub fn load_config(&self) {
        let path = self.paths.apps_toml();
        let parsed = std::fs::read_to_string(&path)
            .map_err(|e| format!("{}: {e}", path.display()))
            .and_then(|t| config::parse(&t));
        let data_env = {
            let p = self.probe.read().unwrap();
            if p.done {
                p.data_dir_env.clone()
            } else {
                std::env::var("BLUEBOAT_DATA_DIR").ok()
            }
        };
        {
            let mut lc = self.config.write().unwrap();
            match parsed {
                Ok(cfg) => {
                    let errs = config::validate(&cfg);
                    if errs.is_empty() {
                        lc.resolver = Resolver::new(&self.paths, &cfg.defaults.workspace, data_env.as_deref());
                        lc.cfg = Some(cfg);
                        lc.errors.clear();
                    } else {
                        // keep the last good registry; show what is wrong
                        lc.errors = errs;
                    }
                }
                Err(e) => lc.errors = vec![format!("apps.toml: {e}")],
            }
            lc.loaded_ms = now_ms();
        }
        *self.packages.lock().unwrap() = None;
        let _ = self.app.emit("config", ());
    }

    fn start_config_watcher(self: &Arc<Self>) {
        use notify::{RecursiveMode, Watcher};
        let h = self.clone();
        let target = self.paths.apps_toml();
        let dir = self.paths.hub_dir.clone();
        std::thread::spawn(move || {
            let (tx, rx) = mpsc::channel::<()>();
            let t2 = target.clone();
            let watcher = notify::recommended_watcher(move |res: notify::Result<notify::Event>| {
                if let Ok(ev) = res {
                    if ev.paths.iter().any(|p| p == &t2) {
                        let _ = tx.send(());
                    }
                }
            });
            let Ok(mut watcher) = watcher else { return };
            if watcher.watch(&dir, RecursiveMode::NonRecursive).is_err() {
                return;
            }
            while rx.recv().is_ok() {
                // debounce editor save bursts
                std::thread::sleep(Duration::from_millis(250));
                while rx.try_recv().is_ok() {}
                h.load_config();
            }
            drop(watcher);
        });
    }

    pub fn resolver(&self) -> Resolver {
        self.config.read().unwrap().resolver.clone()
    }

    pub fn app_entry(&self, id: &str) -> Option<AppEntry> {
        let lc = self.config.read().unwrap();
        lc.cfg.as_ref()?.apps.iter().find(|a| a.id == id).cloned()
    }

    pub fn probe(&self) -> EnvProbe {
        self.probe.read().unwrap().clone()
    }

    pub fn x11_ok(&self) -> bool {
        self.x11_ok.load(Ordering::SeqCst)
    }

    // ------------------------------------------------------------------ tick

    pub fn tick(self: &Arc<Self>) {
        let Ok(_guard) = self.tick_lock.try_lock() else {
            return;
        };
        let panes = self.tmux.list_panes();
        let table = procs::snapshot();
        let wins = x11_list(&self.x11, &self.x11_ok);
        let first = !self.first_tick_done.swap(true, Ordering::SeqCst);
        let after_close: HashMap<String, Option<AfterClose>> = {
            let lc = self.config.read().unwrap();
            lc.cfg
                .as_ref()
                .map(|c| c.apps.iter().map(|a| (a.id.clone(), a.after_close)).collect())
                .unwrap_or_default()
        };
        let mut exits: Vec<ExitRecord> = vec![];
        let mut relaunch = vec![];
        let mut ctrl_c = vec![];
        let mut adopt_build: Option<PaneInfo> = None;
        let mut nudge = false;
        {
            let mut sessions = self.sessions.lock().unwrap();
            let present: HashSet<&str> = panes.iter().map(|p| p.session.as_str()).collect();
            for p in &panes {
                let is_new = !sessions.contains_key(&p.session);
                let s = sessions
                    .entry(p.session.clone())
                    .or_insert_with(|| Session::from_pane(p));
                if is_new && s.app_id == BUILD_SESSION {
                    adopt_build = Some(p.clone());
                }
                s.pid = p.pid;
                s.pane_id = p.pane_id.clone();
                s.dead = p.dead;
                s.exit_code = p.dead_status;
                s.signal = p.dead_signal;
                if s.dead && s.dead_since.is_none() {
                    s.dead_since = Some(Instant::now());
                }
                // tmux marks a pane dead on pty EOF and fills in the status
                // when it reaps the child; seen on this machine: a SIGCHLD
                // the server missed, leaving a zombie and no status.
                let status_known = s.exit_code.is_some() || s.signal.is_some();
                if s.dead && !status_known {
                    nudge = true;
                }
                let exit_final = status_known
                    || s.dead_since.is_some_and(|t| t.elapsed() >= Duration::from_secs(3));
                if s.dead {
                    s.windows.clear();
                } else {
                    let tree = procs::descendants(p.pid, &table);
                    s.windows = wins.iter().filter(|w| tree.contains(&w.pid)).cloned().collect();
                    if !s.windows.is_empty() {
                        s.had_window = true;
                    }
                }
                if s.client.as_ref().is_none_or(|c| !c.alive()) {
                    let sink = (s.app_id == BUILD_SESSION).then(|| self.build_sink());
                    s.client = ControlClient::spawn(self.tmux.command(), &s.name, &s.pane_id, sink).ok();
                }
                if let Some(st) = s.stop.as_mut() {
                    if !s.dead
                        && !st.ctrl_c_sent
                        && after_close.get(&s.app_id).copied().flatten() == Some(AfterClose::CtrlC)
                        && s.windows.is_empty()
                        && st.requested_at.elapsed() >= Duration::from_secs(2)
                    {
                        st.ctrl_c_sent = true;
                        ctrl_c.push(s.name.clone());
                    }
                }
                if s.dead && exit_final && !s.exit_handled {
                    s.exit_handled = true;
                    exits.push(ExitRecord {
                        ev: ExitEvent {
                            session: s.name.clone(),
                            app: s.app_id.clone(),
                            app_name: String::new(),
                            exit_code: s.exit_code,
                            signal: s.signal,
                            expected: s.stop.is_some() || s.restart_pending,
                            removed: false,
                        },
                        started_ms: s.started_ms,
                        params: s.params.clone(),
                        variant: s.variant.clone(),
                        quiet: first,
                    });
                }
                if s.dead && exit_final && s.restart_pending {
                    s.restart_pending = false;
                    relaunch.push((s.name.clone(), s.app_id.clone(), s.params.clone(), s.variant.clone()));
                }
            }
            let gone: Vec<String> = sessions
                .keys()
                .filter(|k| !present.contains(k.as_str()))
                .cloned()
                .collect();
            for g in gone {
                if let Some(s) = sessions.remove(&g) {
                    if let Some(c) = &s.client {
                        c.kill();
                    }
                    if !s.exit_handled {
                        exits.push(ExitRecord {
                            ev: ExitEvent {
                                session: s.name.clone(),
                                app: s.app_id.clone(),
                                app_name: String::new(),
                                exit_code: None,
                                signal: None,
                                expected: s.stop.is_some() || s.restart_pending,
                                removed: true,
                            },
                            started_ms: s.started_ms,
                            params: s.params.clone(),
                            variant: s.variant.clone(),
                            quiet: first,
                        });
                    }
                }
            }
        }
        if nudge {
            self.nudge_server();
        }
        if let Some(p) = adopt_build {
            self.adopt_build(&p);
        }
        for name in ctrl_c {
            let _ = self.tmux.ctrl_c(&name);
        }
        for x in exits {
            self.on_exit(x);
        }
        for (name, app_id, params, variant) in relaunch {
            let _ = self.tmux.kill_session(&name);
            self.sessions.lock().unwrap().remove(&name);
            if let Err(e) = self.launch(&app_id, params, variant) {
                let _ = self.app.emit("toast", serde_json::json!({ "kind": "error", "text": format!("Restart failed: {e}") }));
            }
        }
        self.emit_sessions(false);
    }

    /// Ask our tmux server to reap finished children (SIGCHLD). Harmless:
    /// SIGCHLD only makes it call waitpid; used when a dead pane has no
    /// exit status yet. At most once a second.
    fn nudge_server(&self) {
        {
            let mut last = self.last_nudge.lock().unwrap();
            if last.is_some_and(|t| t.elapsed() < Duration::from_secs(1)) {
                return;
            }
            *last = Some(Instant::now());
        }
        let Ok(pid) = self.tmux.run(&["display-message".into(), "-p".into(), "#{pid}".into()]) else {
            return;
        };
        let pid = pid.trim();
        if !pid.is_empty() && pid.chars().all(|c| c.is_ascii_digit()) {
            let _ = std::process::Command::new("kill")
                .args(["-CHLD", pid])
                .stdin(std::process::Stdio::null())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .status();
        }
    }

    fn build_sink(&self) -> Sink {
        let tracker = self.build.clone();
        let app = self.app.clone();
        Box::new(move |data: &[u8]| {
            let mut g = tracker.lock().unwrap();
            let t = &mut *g;
            if !t.state.running {
                return;
            }
            if t.parser.feed(data) {
                t.state.absorb(&t.parser);
                let st = t.state.clone();
                drop(g);
                let _ = app.emit("build", &st);
            }
        })
    }

    /// A `build` session the hub did not start (the hub was restarted):
    /// rebuild the parser state from the pane's history.
    fn adopt_build(&self, p: &PaneInfo) {
        // Lock first, then capture: output the sink receives meanwhile waits
        // for the lock and lands in the new parser instead of being lost.
        let mut g = self.build.lock().unwrap();
        if g.state.started_ms == p.started_ms && !g.state.running && g.state.finished_ms.is_some() {
            return; // already recorded
        }
        let text = self.tmux.capture(BUILD_SESSION, false).unwrap_or_default();
        let mut parser = ColconParser::default();
        parser.feed(text.as_bytes());
        let own = g.state.running && g.state.started_ms == p.started_ms;
        let (selection, expected) = if own {
            (g.state.selection.clone(), g.state.expected)
        } else {
            let sel: Vec<String> = serde_json::from_str(&p.params_json).unwrap_or_default();
            let n = sel.len();
            (sel, n)
        };
        g.state = BuildState {
            running: true,
            session: Some(BUILD_SESSION.into()),
            started_ms: p.started_ms,
            selection,
            expected,
            ..Default::default()
        };
        g.state.absorb(&parser);
        g.parser = parser;
        let st = g.state.clone();
        drop(g);
        let _ = self.app.emit("build", &st);
    }

    fn on_exit(&self, x: ExitRecord) {
        let ExitRecord { mut ev, started_ms, params, variant, quiet } = x;
        if ev.app == BUILD_SESSION {
            let st = {
                let mut g = self.build.lock().unwrap();
                if !g.state.running {
                    return;
                }
                let t = &mut *g;
                t.state.absorb(&t.parser);
                t.state.finish(ev.exit_code, now_ms());
                t.state.clone()
            };
            let _ = history::save_json(&self.paths.state_dir.join("build.json"), &st);
            *self.packages.lock().unwrap() = None;
            let _ = self.app.emit("build", &st);
            if !quiet {
                let _ = self.app.emit("build-finished", &st);
                if !self.focused.load(Ordering::SeqCst) {
                    let body = if st.ok == Some(true) {
                        format!("Build finished · {} packages", st.packages.len())
                    } else {
                        format!("Build failed: {}", if st.failed.is_empty() { "see the build log".into() } else { st.failed.join(", ") })
                    };
                    self.notify("BlueBoat Hub", &body);
                }
            }
            return;
        }
        ev.app_name = self.app_entry(&ev.app).map(|a| a.name).unwrap_or_else(|| ev.app.clone());
        {
            let mut h = self.history.lock().unwrap();
            let rec = h.apps.entry(ev.app.clone()).or_default();
            if rec.started_ms <= started_ms {
                *rec = AppRun {
                    started_ms,
                    ended_ms: Some(now_ms()),
                    exit_code: ev.exit_code,
                    signal: ev.signal,
                    params,
                    variant,
                };
            }
            let _ = history::save_json(&self.paths.state_dir.join("history.json"), &*h);
        }
        if quiet {
            return;
        }
        let crashed = !ev.expected && (ev.exit_code.is_some_and(|c| c != 0) || ev.signal.is_some());
        if crashed && !self.focused.load(Ordering::SeqCst) {
            let what = match (ev.exit_code, ev.signal) {
                (_, Some(s)) => format!("killed by signal {s}"),
                (Some(c), _) => format!("exited with code {c}"),
                _ => "ended".into(),
            };
            self.notify("BlueBoat Hub", &format!("{} {what}", ev.app_name));
        }
        let _ = self.app.emit("app-exited", &ev);
    }

    fn notify(&self, title: &str, body: &str) {
        let _ = self.app.notification().builder().title(title).body(body).show();
    }

    pub fn history_for(&self, app: &str) -> Option<AppRun> {
        self.history.lock().unwrap().apps.get(app).cloned()
    }

    // --------------------------------------------------------------- views

    pub fn session_views(&self) -> Vec<SessionView> {
        let lc = self.config.read().unwrap();
        let pkgs: HashMap<String, Vec<String>> = lc
            .cfg
            .as_ref()
            .map(|c| c.apps.iter().map(|a| (a.id.clone(), a.packages.clone())).collect())
            .unwrap_or_default();
        let windowed: HashMap<String, bool> = lc
            .cfg
            .as_ref()
            .map(|c| c.apps.iter().map(|a| (a.id.clone(), a.window)).collect())
            .unwrap_or_default();
        drop(lc);
        let (built, built_ms) = {
            let b = self.build.lock().unwrap();
            if b.state.running {
                (vec![], 0)
            } else {
                (
                    b.state
                        .packages
                        .iter()
                        .filter(|p| p.status == crate::build::PkgStatus::Finished)
                        .map(|p| p.name.clone())
                        .collect::<Vec<_>>(),
                    b.state.finished_ms.unwrap_or(0),
                )
            }
        };
        let x11 = self.x11_ok();
        let sessions = self.sessions.lock().unwrap();
        sessions
            .values()
            .map(|s| {
                let gui = windowed.get(&s.app_id).copied().unwrap_or(false);
                let state = if s.dead {
                    "exited"
                } else if s.stop.is_some() {
                    "stopping"
                } else if gui && x11 && !s.had_window && s.first_seen.elapsed() < Duration::from_secs(90) {
                    "starting"
                } else {
                    "running"
                };
                let stale = !s.dead
                    && s.started_ms < built_ms
                    && pkgs
                        .get(&s.app_id)
                        .is_some_and(|ps| ps.iter().any(|p| built.contains(p)));
                SessionView {
                    name: s.name.clone(),
                    app: s.app_id.clone(),
                    state: state.into(),
                    pid: s.pid,
                    started_ms: s.started_ms,
                    exit_code: s.exit_code,
                    signal: s.signal,
                    windows: s.windows.clone(),
                    stop_requested_ms: s.stop.as_ref().map(|st| st.requested_ms),
                    params: s.params.clone(),
                    variant: s.variant.clone(),
                    log: s.log.clone(),
                    stale,
                    last_line: s.client.as_ref().map(|c| c.last_line()).unwrap_or_default(),
                    restart_pending: s.restart_pending,
                }
            })
            .collect()
    }

    pub fn emit_sessions(&self, force: bool) {
        let views = self.session_views();
        let json = serde_json::to_string(&views).unwrap_or_default();
        let mut last = self.last_emit.lock().unwrap();
        if force || *last != json {
            *last = json;
            drop(last);
            let _ = self.app.emit("sessions", &views);
        }
    }

    pub fn live_sessions(&self) -> Vec<String> {
        self.sessions
            .lock()
            .unwrap()
            .values()
            .filter(|s| !s.dead)
            .map(|s| s.name.clone())
            .collect()
    }

    // --------------------------------------------------------------- launch

    fn new_log_path(&self, app_id: &str) -> PathBuf {
        let dir = &self.paths.logs_dir;
        let _ = std::fs::create_dir_all(dir);
        // rotate: keep the newest LOGS_PER_APP - 1, the new one makes LOGS_PER_APP
        let prefix = format!("{app_id}-");
        let mut mine: Vec<PathBuf> = std::fs::read_dir(dir)
            .map(|rd| {
                rd.flatten()
                    .map(|e| e.path())
                    .filter(|p| is_log_of(p, &prefix))
                    .collect()
            })
            .unwrap_or_default();
        mine.sort();
        while mine.len() >= LOGS_PER_APP {
            let old = mine.remove(0);
            let _ = std::fs::remove_file(old);
        }
        let stamp = chrono::Local::now().format("%Y%m%d-%H%M%S").to_string();
        let mut p = dir.join(format!("{app_id}-{stamp}.log"));
        let mut n = 2;
        while p.exists() {
            p = dir.join(format!("{app_id}-{stamp}-{n}.log"));
            n += 1;
        }
        p
    }

    fn defaults(&self) -> config::Defaults {
        self.config
            .read()
            .unwrap()
            .cfg
            .as_ref()
            .map(|c| c.defaults.clone())
            .unwrap_or_default()
    }

    pub fn launch(
        self: &Arc<Self>,
        app_id: &str,
        raw: HashMap<String, String>,
        variant: Option<String>,
    ) -> Result<LaunchOutcome, String> {
        let app = self
            .app_entry(app_id)
            .ok_or_else(|| format!("No app `{app_id}` in apps.toml"))?;
        let res = self.resolver();
        let defaults = self.defaults();
        let choice = config::choose_command(&app, &res)?;
        let mut values = HashMap::new();
        for p in &app.params {
            if let Some(v) = config::validate_param(p, raw.get(&p.name).map(String::as_str), &res)? {
                values.insert(p.name.clone(), v);
            }
        }
        let variant_args = match variant.as_deref().filter(|v| !v.is_empty()) {
            Some(v) => Some(
                app.variants
                    .iter()
                    .find(|x| x.id == v)
                    .ok_or_else(|| format!("{} has no variant `{v}`", app.name))?
                    .args
                    .clone(),
            ),
            None => None,
        };

        let name = {
            let sessions = self.sessions.lock().unwrap();
            if app.singleton {
                if let Some(s) = sessions.values().find(|s| s.app_id == app.id && !s.dead) {
                    let name = s.name.clone();
                    drop(sessions);
                    let focused = self.focus(&name).is_ok();
                    return Ok(LaunchOutcome::AlreadyRunning { session: name, focused });
                }
            }
            let taken = |n: &str| sessions.contains_key(n);
            if app.singleton || !taken(&app.id) {
                app.id.clone()
            } else {
                (2..).map(|i| format!("{}-{i}", app.id)).find(|n| !taken(n)).unwrap_or_default()
            }
        };
        // a dead singleton session is replaced (its output is in its log file)
        if self.sessions.lock().unwrap().contains_key(&name) {
            let _ = self.tmux.kill_session(&name);
            if let Some(s) = self.sessions.lock().unwrap().remove(&name) {
                if let Some(c) = s.client {
                    c.kill();
                }
            }
        }

        let mut command = config::render_command(&choice.command, &app.params, &values);
        if let Some(args) = &variant_args {
            command.push(' ');
            command.push_str(args);
        }
        let script = format!(
            "printf '\\033[2m$ %s\\033[0m\\n' {}; {}",
            sh_quote(&format!("{command}    (in {})", app.cwd)),
            config::render_script(&defaults, &app.cwd, &command)
        );
        let log = self.new_log_path(&app.id);
        let started = now_ms();
        let spec = NewSession {
            name: name.clone(),
            cwd: res.ws.clone(),
            shell: defaults.shell.clone(),
            script,
            cols: 160,
            rows: 48,
            log: Some(log.clone()),
            meta: vec![
                ("app".into(), app.id.clone()),
                ("params".into(), serde_json::to_string(&values).unwrap_or_default()),
                ("variant".into(), variant.clone().unwrap_or_default()),
                ("log".into(), log.to_string_lossy().into_owned()),
                ("started".into(), started.to_string()),
            ],
        };
        self.tmux.new_session(&spec)?;
        {
            let mut h = self.history.lock().unwrap();
            h.apps.insert(
                app.id.clone(),
                AppRun { started_ms: started, params: values, variant, ..Default::default() },
            );
            let _ = history::save_json(&self.paths.state_dir.join("history.json"), &*h);
        }
        let h = self.clone();
        std::thread::spawn(move || h.tick());
        Ok(LaunchOutcome::Started { session: name })
    }

    fn with_session<T>(&self, name: &str, f: impl FnOnce(&mut Session) -> T) -> Result<T, String> {
        let mut sessions = self.sessions.lock().unwrap();
        let s = sessions
            .get_mut(name)
            .ok_or_else(|| format!("No session `{name}` (it may have just ended)"))?;
        Ok(f(s))
    }

    fn fresh_windows(&self, pid: u32) -> Vec<WinInfo> {
        let table = procs::snapshot();
        let tree = procs::descendants(pid, &table);
        x11_list(&self.x11, &self.x11_ok)
            .into_iter()
            .filter(|w| tree.contains(&w.pid))
            .collect()
    }

    /// Polite stop: ask the app's windows to close, exactly like their ✕.
    /// No timer escalates; the app may refuse (MCS asks first).
    pub fn stop(self: &Arc<Self>, name: &str) -> Result<(), String> {
        let (pid, dead, already, windowed) = self.with_session(name, |s| {
            (s.pid, s.dead, s.stop.is_some(), s.app_id != BUILD_SESSION)
        })?;
        if dead {
            return Err("It has already exited".into());
        }
        if already {
            return Ok(()); // never re-send: a second close could answer the app's own dialog
        }
        let app = self.with_session(name, |s| s.app_id.clone())?;
        let window_app = windowed
            && self
                .app_entry(&app)
                .is_some_and(|a| a.window && a.stop == config::StopMode::Close);
        let wins = if window_app { self.fresh_windows(pid) } else { vec![] };
        let order = x11win::close_order(&wins);
        let mut ctrl_c_sent = false;
        if order.is_empty() {
            // no window (CLI app, launch file, Wayland): C-c is its polite stop
            self.tmux.ctrl_c(name)?;
            ctrl_c_sent = true;
        } else {
            let g = self.x11.lock().unwrap();
            let x = g.as_ref().ok_or("No X11 connection")?;
            for w in order {
                x.close(w).map_err(|e| e.to_string())?;
            }
        }
        self.with_session(name, |s| {
            s.stop = Some(StopState { requested_at: Instant::now(), requested_ms: now_ms(), ctrl_c_sent });
        })?;
        self.emit_sessions(true);
        Ok(())
    }

    /// "Keep running": forget a stop request the app declined.
    pub fn cancel_stop(&self, name: &str) -> Result<(), String> {
        self.with_session(name, |s| {
            s.stop = None;
            s.restart_pending = false;
        })?;
        self.emit_sessions(true);
        Ok(())
    }

    /// Force stop, behind the UI's confirmations: stage 1 = C-c into the
    /// pane, stage 2 = `tmux kill-session`.
    pub fn force_stop(&self, name: &str, kill: bool) -> Result<(), String> {
        if kill {
            self.tmux.kill_session(name)?;
        } else {
            self.tmux.ctrl_c(name)?;
            let _ = self.with_session(name, |s| {
                if s.stop.is_none() {
                    s.stop = Some(StopState { requested_at: Instant::now(), requested_ms: now_ms(), ctrl_c_sent: true });
                }
            });
        }
        self.emit_sessions(true);
        Ok(())
    }

    pub fn focus(&self, name: &str) -> Result<(), String> {
        let pid = self.with_session(name, |s| s.pid)?;
        let wins = self.fresh_windows(pid);
        let target = wins
            .iter()
            .find(|w| !w.transient)
            .or_else(|| wins.first())
            .map(|w| w.id)
            .ok_or("No window to focus — this app shows none (yet)")?;
        let g = self.x11.lock().unwrap();
        g.as_ref()
            .ok_or("No X11 connection")?
            .activate(target)
            .map_err(|e| e.to_string())
    }

    pub fn dismiss(self: &Arc<Self>, name: &str) -> Result<(), String> {
        let dead = self.with_session(name, |s| s.dead)?;
        if !dead {
            return Err("It is still running — stop it first".into());
        }
        self.tmux.kill_session(name)?;
        if let Some(s) = self.sessions.lock().unwrap().remove(name) {
            if let Some(c) = s.client {
                c.kill();
            }
        }
        self.emit_sessions(true);
        Ok(())
    }

    pub fn restart(self: &Arc<Self>, name: &str) -> Result<(), String> {
        let (dead, app, params, variant) =
            self.with_session(name, |s| (s.dead, s.app_id.clone(), s.params.clone(), s.variant.clone()))?;
        if app == BUILD_SESSION {
            return Err("Use Build to start a new build".into());
        }
        if dead {
            let _ = self.tmux.kill_session(name);
            if let Some(s) = self.sessions.lock().unwrap().remove(name) {
                if let Some(c) = s.client {
                    c.kill();
                }
            }
            self.launch(&app, params, variant).map(|_| ())
        } else {
            self.stop(name)?;
            self.with_session(name, |s| s.restart_pending = true)?;
            self.emit_sessions(true);
            Ok(())
        }
    }

    // ------------------------------------------------------------- terminal

    fn client(&self, name: &str) -> Result<Arc<ControlClient>, String> {
        self.with_session(name, |s| s.client.clone())?
            .filter(|c| c.alive())
            .ok_or_else(|| "The terminal is reconnecting — try again in a second".into())
    }

    pub fn attach(&self, name: &str, ch: Channel<TermMsg>) -> Result<(), String> {
        self.client(name)?.attach(ch)
    }

    pub fn detach(&self, name: &str) {
        if let Ok(c) = self.client(name) {
            c.detach();
        }
    }

    pub fn write_stdin(&self, name: &str, data: &[u8]) -> Result<(), String> {
        self.client(name)?.send_input(data)
    }

    pub fn resize(&self, name: &str, cols: u16, rows: u16) -> Result<(), String> {
        self.client(name)?.resize(cols, rows)
    }

    // ---------------------------------------------------------------- build

    pub fn list_packages(&self, force: bool) -> Result<Vec<String>, String> {
        if !force {
            if let Some(p) = self.packages.lock().unwrap().clone() {
                return Ok(p);
            }
        }
        let (ws, pinned) = {
            let lc = self.config.read().unwrap();
            (
                lc.resolver.ws.clone(),
                lc.cfg.as_ref().map(|c| c.build.pinned_first.clone()).unwrap_or_default(),
            )
        };
        // --log-base /dev/null: listing must not write into ~/ros2_ws/log
        let out = std::process::Command::new("colcon")
            .args(["--log-base", "/dev/null", "list", "--names-only"])
            .current_dir(&ws)
            .stdin(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .output()
            .map_err(|e| format!("colcon: {e}"))?;
        if !out.status.success() {
            return Err("colcon list failed".into());
        }
        let mut names: Vec<String> = String::from_utf8_lossy(&out.stdout)
            .lines()
            .map(|l| l.trim().to_string())
            .filter(|l| !l.is_empty())
            .collect();
        names.sort();
        let mut ordered: Vec<String> = pinned.iter().filter(|p| names.contains(p)).cloned().collect();
        ordered.extend(names.into_iter().filter(|n| !pinned.contains(n)));
        *self.packages.lock().unwrap() = Some(ordered.clone());
        Ok(ordered)
    }

    pub fn start_build(self: &Arc<Self>, packages: Vec<String>) -> Result<(), String> {
        let (defaults, build_cfg, ws) = {
            let lc = self.config.read().unwrap();
            let c = lc.cfg.as_ref().ok_or("apps.toml did not load")?;
            (c.defaults.clone(), c.build.clone(), lc.resolver.ws.clone())
        };
        if let Some(alive) = self.sessions.lock().unwrap().get(BUILD_SESSION).map(|s| !s.dead) {
            if alive {
                return Err("A build is already running".into());
            }
        }
        let all = self.list_packages(false)?;
        for p in &packages {
            if !all.contains(p) {
                return Err(format!("Unknown package `{p}`"));
            }
        }
        let _ = self.tmux.kill_session(BUILD_SESSION);
        if let Some(s) = self.sessions.lock().unwrap().remove(BUILD_SESSION) {
            if let Some(c) = s.client {
                c.kill();
            }
        }
        let started = now_ms();
        {
            let mut g = self.build.lock().unwrap();
            g.parser = ColconParser::default();
            g.state = BuildState {
                running: true,
                session: Some(BUILD_SESSION.into()),
                started_ms: started,
                expected: if packages.is_empty() { all.len() } else { packages.len() },
                selection: packages.clone(),
                ..Default::default()
            };
        }
        let script = config::render_build_script(&defaults, &build_cfg, &packages);
        let log = self.new_log_path(BUILD_SESSION);
        let spec = NewSession {
            name: BUILD_SESSION.into(),
            cwd: ws,
            shell: defaults.shell.clone(),
            script: format!("printf '\\033[2m$ %s\\033[0m\\n' {}; {script}", sh_quote(&script)),
            cols: 160,
            rows: 40,
            log: Some(log.clone()),
            meta: vec![
                ("app".into(), BUILD_SESSION.into()),
                ("params".into(), serde_json::to_string(&packages).unwrap_or_default()),
                ("log".into(), log.to_string_lossy().into_owned()),
                ("started".into(), started.to_string()),
            ],
        };
        if let Err(e) = self.tmux.new_session(&spec) {
            self.build.lock().unwrap().state.running = false;
            return Err(e);
        }
        let st = self.build.lock().unwrap().state.clone();
        let _ = self.app.emit("build", &st);
        let h = self.clone();
        std::thread::spawn(move || h.tick());
        Ok(())
    }

    pub fn cancel_build(&self) -> Result<(), String> {
        let alive = self.sessions.lock().unwrap().get(BUILD_SESSION).is_some_and(|s| !s.dead);
        if !alive {
            return Err("No build is running".into());
        }
        // colcon handles SIGINT: it aborts the running jobs and prints its summary
        self.tmux.ctrl_c(BUILD_SESSION)
    }

    pub fn build_state(&self) -> BuildState {
        self.build.lock().unwrap().state.clone()
    }

    // ----------------------------------------------------------------- data

    fn start_data_thread(self: &Arc<Self>) {
        let (tx, rx) = mpsc::channel::<()>();
        *self.data_tx.lock().unwrap() = Some(tx);
        let h = self.clone();
        std::thread::Builder::new()
            .name("hub-data".into())
            .spawn(move || loop {
                h.scan_data_now();
                match rx.recv_timeout(Duration::from_secs(30)) {
                    Ok(()) | Err(mpsc::RecvTimeoutError::Timeout) => {
                        while rx.try_recv().is_ok() {}
                    }
                    Err(mpsc::RecvTimeoutError::Disconnected) => break,
                }
            })
            .expect("data thread");
    }

    fn scan_data_now(&self) {
        self.data_scanning.store(true, Ordering::SeqCst);
        let (cards, res) = {
            let lc = self.config.read().unwrap();
            (lc.cfg.as_ref().map(|c| c.data.clone()).unwrap_or_default(), lc.resolver.clone())
        };
        let views: Vec<DataCardView> = cards.iter().map(|c| data::scan_card(c, &res)).collect();
        *self.data.lock().unwrap() = views.clone();
        self.data_scanning.store(false, Ordering::SeqCst);
        let _ = self.app.emit("data", &views);
    }

    pub fn request_data_scan(&self) {
        if let Some(tx) = self.data_tx.lock().unwrap().as_ref() {
            let _ = tx.send(());
        }
    }

    pub fn data_cards(&self) -> (Vec<DataCardView>, bool) {
        (self.data.lock().unwrap().clone(), self.data_scanning.load(Ordering::SeqCst))
    }

    /// Roots `open_path` may open: every data tab, the hub's logs, each app's folder.
    pub fn openable_roots(&self) -> Vec<PathBuf> {
        let lc = self.config.read().unwrap();
        let mut roots = vec![self.paths.logs_dir.clone()];
        if let Some(c) = &lc.cfg {
            for d in &c.data {
                for t in &d.tabs {
                    roots.push(lc.resolver.expand(&t.path));
                }
            }
            for a in &c.apps {
                if !a.planned {
                    roots.push(lc.resolver.expand(&a.cwd));
                }
            }
        }
        roots
    }

    pub fn shutdown(&self) {
        let sessions = self.sessions.lock().unwrap();
        for s in sessions.values() {
            if let Some(c) = &s.client {
                c.kill();
            }
        }
    }
}

fn is_log_of(p: &Path, prefix: &str) -> bool {
    p.file_name()
        .and_then(|n| n.to_str())
        .is_some_and(|n| {
            n.ends_with(".log")
                && n.strip_prefix(prefix)
                    .is_some_and(|rest| rest.len() >= 8 && rest[..8].chars().all(|c| c.is_ascii_digit()))
        })
}

/// Start `xdg-open` detached and reap it in the background.
pub fn xdg_open(target: &str) -> Result<(), String> {
    let mut child = std::process::Command::new("xdg-open")
        .arg(target)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map_err(|e| format!("xdg-open: {e}"))?;
    std::thread::spawn(move || {
        let _ = child.wait();
    });
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn log_names() {
        assert!(is_log_of(Path::new("/l/gcs-20261111-120000.log"), "gcs-"));
        assert!(is_log_of(Path::new("/l/gcs-20261111-120000-2.log"), "gcs-"));
        assert!(!is_log_of(Path::new("/l/gcs_x-20261111-120000.log"), "gcs-"));
        assert!(!is_log_of(Path::new("/l/log_reviewer-20261111-120000.log"), "log-"));
        assert!(!is_log_of(Path::new("/l/gcs-notes.log"), "gcs-"));
    }
}
