# Implementation prompt — BlueBoat Hub

> Paste everything below the line into a fresh Claude Code session opened at
> `~/ros2_ws/src/BlueBoat-SideScanSonar`. Written 2026-11-11 from a scan of the tree on that date.

---

## Goal

Build **BlueBoat Hub**: one desktop app that starts, watches and stops every app of the BlueBoat
project, builds the ROS workspace, and opens the data folders. It is a **launcher, not a
container**: it never embeds another app's window. Each app keeps opening as its own window on
the desktop; inside the hub its tile turns into that app's **live terminal**.

Read first, in this order: `.claude/CLAUDE.md` (root rules: §1.1 deployment, §2.1 no git
commits, §3 frozen modules, CM-3, CM-7, CM-15), `terminals.txt` (the owner's own launch lines,
the source of truth for the commands below), `~/ros2_ws/env.sh`, skill `file-interfaces`
(data-root layout). Then `BlueBoat-MCS/mcs/gui/main_window.py:870` (`closeEvent`) — the reason
the Stop button works the way it does.

## Hard rules

1. **Lives in `hub/` in the superproject** (like `link_guardian/`: not a submodule, not a
   colcon package). Put a `COLCON_IGNORE` file in `hub/` **first**, so `colcon build` never
   crawls `node_modules/` or `target/`. Add `hub/.gitignore` for `node_modules/`,
   `src-tauri/target/`, `dist/`.
2. **Touch no submodule** (CM-3, frozen Control/MCS). The hub only *runs* their existing entry
   points. If an app lacks something the hub wants (e.g. a CLI flag), write it down in
   `hub/README.md` under "Requests", don't add it.
3. **No git commit / push** (root §2.1). Leave changes in the working tree.
4. **Data is read-only for the hub** (CM-7): it lists, sizes and opens folders/files; it never
   deletes, renames, moves or writes anything under `~/ros2_ws/data`, `~/worlds` or
   `~/.config/blueboat_mcs`. No delete button anywhere.
5. **The hub never sends robot commands** and does not launch `BlueBoat_launch.py` /
   `full_mission_launch.py` itself: MCS owns mission launches, E-STOP and the CM-15 safe
   shutdown. The hub launches MCS.
6. **Stopping an app = asking its window to close**, exactly like clicking its ✕ (see
   "Process model"). Never SIGTERM/SIGKILL a Qt app as the normal path: Python's default SIGTERM
   kills the process without `closeEvent`, which for MCS skips the `default` publish and can leave
   the motors in override (CM-15).

## Technology (decided — don't re-litigate)

- **Tauri 2** (Rust backend, system WebKitGTK webview) — native window, ~10 MB binary, real
  OS integration; Electron is too heavy, a Python/Qt hub would look like the other apps.
- **Frontend: Svelte 5 + TypeScript + Vite**, styling with plain CSS custom properties (design
  tokens below), no UI kit. Icons: `lucide-svelte`. Font: Inter (UI) + JetBrains Mono
  (terminals), bundled locally (offline field laptop — no CDN, no network at runtime).
- **Terminals: `@xterm/xterm`** + `@xterm/addon-fit` + `@xterm/addon-web-links` +
  `@xterm/addon-search`, WebGL addon with canvas fallback.
- **Process backend: `tmux`** (installed at `/usr/bin/tmux`). Each app runs in its own detached
  session on a private socket (`tmux -L blueboat-hub new-session -d -s <app-id> …`); the hub
  attaches to it through a PTY (`portable-pty` crate) and streams bytes to xterm.js over a Tauri
  channel. Why: apps **survive the hub being closed, crashed or rebuilt**, and on restart the hub
  lists `tmux -L blueboat-hub ls` and re-attaches — running apps reappear as terminals.
  Set `remain-on-exit on` so a crashed app's last output stays readable; the tile then shows
  "exited (code N)" with Restart / Dismiss.
- **Window control: X11 via the `x11rb` crate** (session is X11, GNOME). Find an app's windows
  by `_NET_WM_PID` over its process tree; *Stop* sends `_NET_CLOSE_WINDOW` (EWMH), *Focus* sends
  `_NET_ACTIVE_WINDOW`. No `wmctrl`/`xdotool` dependency. If no window is found (CLI process,
  Wayland), Stop falls back to sending `C-c` into the tmux pane.
- **Config: `hub/apps.toml`**, a declarative registry (below), read at start and hot-reloaded.
  Adding Belief/Replanner later must be a config edit, not code.
- Toolchain is **not installed** on this machine (no node, no cargo). Write the setup in
  `hub/README.md` and ask the user before installing anything system-wide: `rustup` (user-local),
  Node 22 LTS via `nvm` (user-local), and
  `sudo apt install libwebkit2gtk-4.1-dev libsoup-3.0-dev libjavascriptcoregtk-4.1-dev build-essential libssl-dev libayatana-appindicator3-dev librsvg2-dev`.
  NVIDIA + WebKitGTK: set `WEBKIT_DISABLE_DMABUF_RENDERER=1` in the launcher if the window is
  blank.
- Ship `hub/install.sh`: builds a release binary and writes
  `~/.local/share/applications/blueboat-hub.desktop` (with icon) so the hub starts from the GNOME
  dock. The hub is started from the desktop, **not from a sourced shell** — every command must
  set up its own environment (below).

## Command environment

Every app command is run as

```bash
bash -lc 'cd ~/ros2_ws && source env.sh && <cwd step> && exec <command>'
```

`env.sh` activates `.venv` relative to `~/ros2_ws`, so the `cd` comes first. Keep the exact
lines in `apps.toml`, not in code.

## App registry (`apps.toml`) — initial content

| id | Group | Name | cwd (from `~/ros2_ws`) | command | Notes |
|---|---|---|---|---|---|
| `mcs` | Operate | Mission Control Station | `src/BlueBoat-SideScanSonar/BlueBoat-MCS` | `python3 run.py` | Primary tile (large). Its close handles safe shutdown itself. |
| `gcs` | Operate | BlueBoat GCS | `src/BlueBoat-SideScanSonar/BlueBoat-SSS/blueboat_sss` | `python3 -m blueboat_gcs.main` | Variant: "GCS (built-in simulator)" → `--sim`. |
| `qgc` | Operate | QGroundControl | `.` | `./QGroundControl.AppImage` | Badge: "shares the MAVLink port with MAVROS — don't run during a mission" (skill `interface-inventory`). |
| `world_builder` | Simulate | World Builder | `.` | `ros2 run blueboat_sss_sim world_builder` | |
| `gazebo_world` | Simulate | Gazebo world viewer | `.` | `ros2 launch blueboat_sss_sim sim_world_launch.py world_dir:={world}` | Parameter `{world}`: picker over `~/worlds/<project>/<world>/`. |
| `sonar_simple` | Simulate / Sonar | Sonar driver (simple) | `.` | `ros2 launch blueboat_sss SSS_simple_launch.py` | Optional arg `range_length_mm`. Advanced group, collapsed by default. |
| `log_reviewer` | Analyse | Log Reviewer | `.` | `python3 src/BlueBoat-SideScanSonar/BlueBoat-Control/log_reviewer/run.py {csv?}` | Optional `{csv}`: a `*-poslog.csv` picked from `data/Robot_data` (the reviewer takes it as a positional arg). |
| `aug_studio` | Analyse | Dataset Aug Studio | `src/BlueBoat-SideScanSonar/SSS-Dataset-Aug-Studio` | `sss-aug-studio` (fall back to `python3 -m sss_aug_studio.app.main` if not on PATH) | Marked *optional*. |

Schema per entry: `id, name, group, description (one line), icon (lucide name), cwd, command,
params[] {name, kind: path|file|number|choice, root, glob, optional, default}, variants[],
singleton (default true), warning?, primary?`. Verify every command against the tree before
shipping (e.g. `ros2 pkg executables blueboat_sss_sim`), and show a tile as **unavailable** (greyed,
reason on hover) when its entry point is missing — e.g. a package not built yet.

Belief and Replanner submodules exist but contain only a `README.md`: show them as two
"Planned" ghost tiles (no launch button) so the layout already has their place.

## Build

A **Build** action always visible in the top bar: `cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build` (match whatever `BlueBoat-MCS/build.sh` / `BlueBoat-SSS/build.sh` do; do not source `install/setup.bash` before building). Options in its split-button menu: all packages, `--packages-select <pkg>` (multi-select from `colcon list -n`, `blueboat_interfaces` pinned first),
clean-then-build is **not** offered. It runs in its own tmux session `build`, its terminal opens
in the bottom drawer, progress is parsed from colcon output (`Starting >>>`, `Finished <<<`,
`Failed <<<`, the summary line) into a per-package progress strip, and the result becomes a
toast + the status pill ("Built 3 min ago · 7 packages" / "Build failed: blueboat_sss").
If any app is running, Build asks first ("MCS and GCS are running; they keep the old install
until restarted") with *Build anyway* / *Cancel* — never auto-stops apps. After a successful
build, running tiles that use a rebuilt package show a small "restart to use new build" dot.

## Data

A **Data** view (left rail) of folder cards, each: name, path, item count, total size, newest
item + age, and *Open folder* (`xdg-open`). Clicking a card expands its newest 10 entries;
clicking an entry opens it with the right tool when there is one, else `xdg-open`:

| Card | Path | Entry action |
|---|---|---|
| Sonar recordings (.svlog) | `data/SSS_data/` | open folder (GCS replay is opened from inside the GCS — no CLI flag exists; note it as a Request) |
| GCS sessions | `<data_root>/sessions/` | open folder |
| Robot logs & run folders | `data/Robot_data/` | `*-poslog.csv` → **Open in Log Reviewer**; run folder → open folder |
| Processed robot logs | `data/Processed_Robot_data/` | open |
| Controller logs | `data/{LoS,MPC,PID}_data/` (one card, three tabs) | open folder |
| Perception | `data/Perception_data/`, `Perception_models/`, `Perception_eval/` | open |
| Datasets | `data/Dataset_data/`, `data/Tile_data/` | open |
| Worlds | `~/worlds/` | world folder → **Open in Gazebo viewer** / open folder |
| Trajectories | `~/.config/blueboat_mcs/trajectories/` | open |

`<data_root>` resolves like `custom_functions.data_root`: `$BLUEBOAT_DATA_DIR`, else
`~/ros2_ws/data`. Missing folders show as a muted card ("not created yet"), not an error.
Scanning runs in Rust off the UI thread, cached, refreshed on focus and every 30 s.

## Process model

- **Launch**: tile → (params dialog if needed) → `tmux new-session -d` → attach PTY → the tile
  morphs into the terminal. Singleton apps refuse a second instance and focus the window instead.
- **States**: `idle → starting → running → stopping → exited(code)`; `running` once the process
  is alive *and* (for GUI apps) a window is mapped; the window-found event drives the "● Running"
  pill. Uptime and PID shown.
- **Stop** (polite): `_NET_CLOSE_WINDOW` to the app's windows. The app may refuse (MCS asks
  "Mission running…") — that's correct: the hub shows "waiting for the app to close…" with no
  timer that escalates. After 10 s a secondary **Force stop** appears, behind a confirmation;
  for `mcs` the dialog states: "Force-stopping MCS skips its safe shutdown (publish `default`) —
  the motors may stay in override. Use MCS's own Stop Mission first." Force = `C-c` to the pane,
  then `tmux kill-session` only after a second confirmation.
- **Restart** = Stop, wait for exit, Launch with the same params.
- **Hub quit** with apps running: dialog "N apps keep running in the background; the hub
  re-attaches next time" — *Quit hub* (default, apps untouched) / *Stop all and quit* (polite
  stop each, waits) / *Cancel*. Same on reopen: re-attach silently.
- Every session's output also goes to `~/.local/state/blueboat-hub/logs/<id>-<stamp>.log`
  (`tmux pipe-pane`), rotated, last 20 per app; "Open log" in the terminal menu.

## Design

Mood: a calm, dark, instrument-panel feel — maritime, precise, not gamer. Dark default, light
theme available, follows the system.

**Tokens** (CSS custom properties): background `#0B1016`, surface `#121A23`, raised `#18222E`,
border `#233040`, text `#E6EDF3`, muted `#8B9AAB`, accent "sonar teal" `#2DD4BF`,
running `#22C55E`, warning `#F59E0B`, error `#EF4444`, info `#38BDF8`. Radius 14 px tiles /
8 px controls, 8-pt spacing grid, one soft shadow level, 1 px borders instead of heavy shadows.
Group colour accents (thin top border on tiles): Operate teal, Simulate violet `#A78BFA`, Analyse
amber, Tools slate.

**Window layout** (default 1600×1000, usable down to 1280×720):

```
┌────┬────────────────────────────────────────────────────────────────────┐
│ ⌂  │  BlueBoat Hub   ● ROS jazzy  ● venv  ● install: built 3 min ago  [⚒ Build ▾] [⌘K] │
│ ▦  ├────────────────────────────────────────────────────────────────────┤
│ 🗀  │  OPERATE                                                          │
│ ⚒  │  ┌──────────────────────────────────┐ ┌───────────┐ ┌───────────┐ │
│ ☰  │  │ ● MCS  running 12:04  pid 41233  │ │   GCS     │ │   QGC  ⚠  │ │
│    │  │ [focus][restart][stop][⤢][⋯]      │ │  ▶ Launch │ │  ▶ Launch │ │
│    │  │ $ python3 run.py                  │ └───────────┘ └───────────┘ │
│    │  │ [mcs] launcher ready …            │                             │
│    │  │ ▌                                 │  SIMULATE                   │
│    │  └──────────────────────────────────┘ ┌───────────┐ ┌───────────┐ │
│    │  ANALYSE                              │ World Bldr│ │ Gazebo ⓟ  │ │
│    │  ┌───────────┐ ┌───────────┐          └───────────┘ └───────────┘ │
│    │  │ Log Rev.  │ │ Aug Studio│   PLANNED  ┌ Belief ┐ ┌ Replanner ┐ │
│    │  └───────────┘ └───────────┘            └ ─ ─ ─ ┘ └ ─ ─ ─ ─ ─ ┘ │
├────┴────────────────────────────────────────────────────────────────────┤
│ ▲ Build drawer (collapsed): last build ✓ 7/7 · 2m14s            [open] │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Left rail** (64 px, icons + tooltips): Apps (home), Data, Build, Logs, Settings. Bottom of
  rail: running-apps count badge.
- **Top bar**: environment status pills (ROS distro sourced OK, `.venv` present, install age,
  git branch of the superproject + "N submodules modified" read-only via `git status`), Build
  split-button, command palette.
- **App grid**: CSS grid, 12 columns, groups as labelled sections. An idle tile is 3 columns ×
  1 row: icon, name, one-line description, last run ("yesterday 18:42 · exited 0"), primary
  **Launch** button, `⋯` menu (variants, parameters, open its folder, open last log).
- **Running tile = terminal card**: on Launch the tile animates (FLIP transform, 220 ms, ease-out)
  into a 6-column × 2-row card *in its place*; neighbours reflow smoothly. Header: status dot,
  name, uptime, PID, buttons Focus window · Restart · Stop · Maximize · `⋯` (copy all, search,
  open log, clear view, detach). Body: xterm.js, fits on resize, scrollback 10 000.
  **Maximize** (`⤢` or double-click header) expands the terminal over the grid with the other
  tiles as a slim strip at the top (still launchable); `Esc` returns. **Collapse** reduces a
  running card back to tile size with a live last-line preview, for when several apps run.
  With 3+ running, offer "Tile terminals" which lays the running cards side by side.
- **Exited card**: red/grey header with exit code, output kept, Restart / Dismiss.
- **Build drawer**: bottom sheet (resizable, collapsed to one status line by default) holding the
  build terminal and the per-package progress strip; auto-opens on build start, auto-collapses
  5 s after success, stays open on failure with the first error line highlighted.
- **Command palette** (`Ctrl+K`): launch/stop/focus any app, build (all / one package), open any
  data card, jump to a terminal. Shortcuts: `Ctrl+B` build, `Ctrl+1…9` focus the n-th running
  terminal, `Ctrl+Shift+F` search in terminal.
- **Motion**: 150–220 ms transitions only, respect `prefers-reduced-motion`; a slow pulse on the
  running dot; no spinners longer than needed — skeleton shimmer for data cards.
- **Notifications**: in-app toasts (bottom-right) for exit/crash/build result; a GNOME
  notification only when the hub window is unfocused and an app crashes or a build ends.
- Empty/error states written in plain sentences ("World Builder isn't built yet — run Build").

## Code layout

```
hub/
  COLCON_IGNORE  .gitignore  README.md  install.sh  apps.toml
  package.json  vite.config.ts  tsconfig.json  index.html
  src/                      # Svelte 5
    lib/tokens.css  lib/stores/{apps,sessions,build,data}.ts
    lib/components/{Rail,TopBar,AppGrid,AppTile,TerminalCard,BuildDrawer,DataView,
                    CommandPalette,ParamDialog,ConfirmDialog,Toasts}.svelte
    lib/ipc.ts              # typed wrappers over Tauri commands/channels
  src-tauri/
    src/{main.rs, config.rs, tmux.rs, pty.rs, x11win.rs, build.rs, data.rs, env_status.rs}
    tauri.conf.json  capabilities/
```

Keep the Rust side the only place that spawns processes; the webview gets narrow typed commands
(`launch(id, params)`, `stop(id)`, `force_stop(id)`, `focus(id)`, `write_stdin(id, bytes)`,
`resize(id, cols, rows)`, `build(opts)`, `scan_data()`, …) — no generic "run shell" command
exposed to the frontend. Tauri capabilities: deny everything not used.

## Verification (do all, report honestly)

1. `cargo clippy -- -D warnings`, `cargo test` (config parsing, colcon-output parser, data-root
   resolution, tmux command construction), `npm run check` (svelte-check), `npm run build`.
2. `colcon build` from `~/ros2_ws` still lists exactly the same packages as before (`colcon list`
   before/after — `hub/` must not appear).
3. Run the hub (skill `run`): launch GCS, see its terminal; close the GCS window by hand → the
   card goes to "exited 0". Launch World Builder, press Stop → its window closes politely.
   Launch MCS, press Stop with no mission → MCS closes normally. Quit the hub with GCS running,
   reopen → GCS terminal re-attached with history. Run a single-package build and a deliberately
   failing one is **not** needed — just parse a saved failing colcon log in a unit test.
4. Data view shows the real folders listed above with correct counts; opening a poslog sends it
   to the Log Reviewer.
5. Screenshot the main view (idle, one running, maximized terminal, build drawer open) in dark
   and light, and look at them critically before calling it done.

Finish with `hub/README.md`: what it is, setup, `install.sh`, how to add an app to `apps.toml`,
the Stop semantics (and why), known limits (X11 only for window control), and the Requests
list for app owners (e.g. GCS: open a `.svlog` from the command line).
