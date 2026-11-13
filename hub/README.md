# BlueBoat Hub

One desktop app that starts, watches and stops every app of the BlueBoat project, builds the
ROS workspace and opens the data folders.

It is a **launcher, not a container**. Each app keeps opening its own window on the desktop.
Inside the hub, the app's tile turns into that app's **live terminal**.

- **Process backend: tmux.** Every app runs in its own detached session on a private
  socket (`tmux -L blueboat-hub`). Apps survive the hub being closed, crashed or rebuilt.
  When the hub opens again, the running apps reappear as terminals, with their history.
- **Stack.** Tauri 2 (Rust backend, system WebKitGTK), Svelte 5 + TypeScript, and xterm.js.
  Fonts are bundled; nothing is fetched at runtime (the field laptop is offline).
- **Location.** `hub/` in the superproject. It is not a submodule and not a colcon package
  (`COLCON_IGNORE`). It touches no submodule (CM-3), writes nothing under the data folders
  (CM-7), sends no robot command, and never starts `BlueBoat_launch.py` /
  `full_mission_launch.py`. MCS owns missions, E-STOP and the CM-15 safe shutdown.

> **Just want to install it?** Follow **[INSTALL.md](INSTALL.md)**: five steps, and it ends as
> an app on your Desktop.

## Setup (once)

User-local toolchains, plus the system libraries WebKitGTK needs:

```bash
# Rust (user-local)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal -c clippy -c rustfmt
# Node 22 LTS (user-local)
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | PROFILE=/dev/null bash
. ~/.nvm/nvm.sh && nvm install 22
# system libraries (sudo)
sudo apt install libwebkit2gtk-4.1-dev libsoup-3.0-dev libjavascriptcoregtk-4.1-dev \
  build-essential libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

`tmux` (≥ 3.3) is already installed at `/usr/bin/tmux`.

## Install

```bash
cd ~/ros2_ws/src/BlueBoat-SideScanSonar/hub
./install.sh          # release build → ~/.local/bin, .desktop entry, icon
./install.sh --clean  # same, then delete src-tauri/target (≈2 GB)
```

Then open *BlueBoat Hub* from the app grid. Right-click its dock icon → *Pin to Dash*.

The hub is started from the desktop, not from a sourced shell. Each app command builds its own
environment (next section).

### Development

```bash
. ~/.nvm/nvm.sh
npm install
npx tauri dev                                        # hot-reloading frontend
cargo build --features tauri/custom-protocol \
  --manifest-path src-tauri/Cargo.toml               # debug binary serving dist/ (run `npm run build` first)
```

### Gates

```bash
cd src-tauri && cargo clippy --all-targets -- -D warnings && cargo test
cd .. && npm run check && npm run build
```

## How apps are run

Every tile in `apps.toml` runs as:

```
bash -ic 'printf "$ <command>"; cd ~/ros2_ws && source env.sh && cd <cwd> && exec <command>'
```

- **Why `bash -ic` (interactive), not `bash -lc`.** A non-interactive shell stops at line 6
  of `~/.bashrc`. That skips `ACADOS_SOURCE_DIR` / `LD_LIBRARY_PATH` (used by the MPC
  controller) and the `/opt/ros/jazzy` source. With `-i`, an app sees exactly what a
  terminal sees.
- **The template lives in `apps.toml [defaults]`**, not in code.
- **`env.sh` activates `.venv` relative to `~/ros2_ws`**, so the `cd` comes first.

Each session's output is also written by tmux to `~/.local/state/blueboat-hub/logs/<app>-<stamp>.log`.
The newest 20 logs per app are kept, and the **Logs** view lists them.

## Stop semantics (and why)

**Stop = asking the app's window to close, exactly like clicking its ✕.** The hub sends
`_NET_CLOSE_WINDOW` (EWMH) to the app's top-level windows. It finds them by `_NET_WM_PID`
over the process tree below the tmux pane.

- **Why.** The apps do their own shutdown in `closeEvent`:
  - MCS publishes `default` and runs the CM-15 sequence before any node dies, and asks
    first when a mission is running (`BlueBoat-MCS/mcs/gui/main_window.py:870`);
  - the GCS ends a recording, disables pinging and waits for its exports.

  A `SIGTERM` (Python's default) kills the process **without** `closeEvent`, so for MCS
  the motors could stay in override.
- **The app may refuse.** MCS asks "Mission running…". The card then shows *waiting for
  the app to close…* with *Keep running*. **No timer escalates.**
- **Force stop.** After 10 s a *Force stop…* button appears, behind a confirmation (MCS's
  text warns about skipping the safe shutdown). Stage 1 sends Ctrl-C to the pane; *Kill
  session…* (`tmux kill-session`) needs a second confirmation.
  - Checked live on 2026-11-11: Ctrl-C reaches MCS's `closeEvent` (`signal(SIGINT,
    app.quit)`, then Qt 6 closes the windows; the log shows `ROS executor stopped`, exit
    0). With a mission running, the same `closeEvent` asks first. That case was not
    exercised.
- **Windowless apps.** `sonar_simple` (`window = false`), or any app when no window is
  found (Wayland), is stopped with Ctrl-C. That is the polite stop of `ros2 launch`.
- **`stop = "ctrl-c"`** (Gazebo viewer): Stop sends Ctrl-C straight away. Gazebo answers a
  window close with its own "Do you really want to exit?", and a viewer has nothing to
  save; `ros2 launch` then ends cleanly in about 3 s.
- **`after_close = "ctrl-c"`** (Gazebo viewer): once the Gazebo window is gone, if
  `ros2 launch` still runs 2 s later, Ctrl-C ends it.
- **Dialogs are never closed.** Closing a confirmation dialog would answer "Cancel".
  A window counts as a dialog only if `WM_TRANSIENT_FOR` points at another *managed*
  window. Qt points a parentless `QDialog` (World Builder's main window) at its unmapped
  client leader; that window is still closed.
- **Hub quit with apps running** asks: *Quit hub* (default; apps keep running and the hub
  re-attaches next time), *Stop all and quit* (polite stop of each, then quit when none
  are left), or *Cancel*.

## The window

- **Apps.** Tiles grouped as in `apps.toml`.
  - *Launch* morphs a tile into its terminal card. *Focus* raises the app's window;
    Restart, Stop, Collapse and Maximize are on the card (Esc leaves the maximized view).
  - With 3+ apps running, *Tile terminals* shows them side by side.
  - An exited card keeps the output and offers Restart / Dismiss.
  - Tiles whose entry point is missing are greyed, with the reason ("blueboat_sss_sim
    isn't built yet — run Build").
- **Data.** Read-only folder cards: count, size, newest item, newest 10 entries.
  - Clicking an entry opens it with the right tool: a run folder or `*-poslog.csv` opens
    in the **Log Reviewer**, a world folder in the **Gazebo viewer**, anything else
    with `xdg-open`.
  - Missing folders show as "not created yet". Scans run every 30 s and on window focus.
- **Build.** `source /opt/ros/jazzy/setup.bash && colcon build` (as `BlueBoat-MCS/build.sh`)
  in its own tmux session `build`, shown in the bottom drawer.
  - The per-package progress strip is parsed from colcon's output.
  - If apps are running, the hub asks first; it never stops them.
  - After a build, cards of running apps that use a rebuilt package show *restart to use
    new build*.
- **Logs, Settings.** Session logs; theme (system / dark / light), terminal font size, and
  where everything lives.
- **Keyboard.**
  - `Ctrl K` — command palette (launch / stop / focus / build / open).
  - `Ctrl B` — build all.
  - `Ctrl 1…9` — the n-th terminal.
  - `Ctrl Shift F` — search the terminal.
  - `Ctrl Shift C / V` — copy / paste.

## Adding an app

Edit `apps.toml`; the hub reloads it on save. A broken edit keeps the last good registry
and shows the error at the top of the Apps view. Example: the Belief tile, which replaced its
`planned = true` ghost once the package was built (the Replanner's ghost was replaced the same
way on 2026-11-13; a group with no tile left is hidden):

```toml
[[apps]]
id = "belief"                      # lowercase, digits, _
name = "Belief"
group = "operate"                  # or a new [[groups]] entry
description = "The belief map: pings + detections -> BeliefGrid, the Replanner's only input."
icon = "brain"                     # names in src/lib/icons.ts
cwd = "."                          # from the workspace
command = "ros2 launch blueboat_belief belief_launch.py area_file:={world}"
requires = [{ launch = "blueboat_belief/belief_launch.py" }]   # greys the tile until built
params = [{ name = "world", label = "World (survey area)", kind = "path", root = "~/worlds", depth = 2, marker = "metadata.yaml" }]
variants = [{ id = "sim", name = "Gazebo (sim time)", args = "use_sim_time:=true" }]
packages = ["blueboat_belief", "blueboat_belief_interfaces"]   # drives "restart to use new build"
window = false                     # no window: Stop sends Ctrl-C
stop = "ctrl-c"
```

Fields:

| Field | Meaning |
|---|---|
| `requires` | `{ ros_exe = "pkg/exe" }`, `{ launch = "pkg/file.py" }`, `{ file = "path" }` or `{ bin = "program" }`, checked on the filesystem. `fallback_command` + `fallback_requires` are used when `requires` fails (Aug Studio: `sss-aug-studio` → `python3 -m sss_aug_studio.app.main`). |
| `params` | `kind = path \| file \| number \| choice`. Written as `{name}` (required) or `{name?}` (optional) in `command`. Values are checked (inside `root`, `marker` / `glob`, number range) and shell-quoted before substitution. |
| `variants` | `{ id, name, args }`, appended to the command (GCS `--sim`). |
| `singleton` | `true` by default. A second launch focuses the running window; `false` allows several (Log Reviewer). |
| `window` | `false` for CLI apps. |
| `warning` | Badge on the tile. |
| `force_warning` | Text in the Force-stop dialog. |
| `after_close = "ctrl-c"` | See *Stop semantics*. |
| `stop = "ctrl-c"` | Stop sends Ctrl-C instead of closing the window. See *Stop semantics*. |
| `help` | Text behind the tile's ⓘ button. |
| `primary` | Wide tile. |
| `optional` | Badge. |
| `planned` | Ghost tile, no launch. |

Path placeholders: `~`, `{workspace}`, `{data_root}` (`$BLUEBOAT_DATA_DIR` as `~/.bashrc`
sets it, else `{workspace}/data`), `{superproject}`.

Data cards are `[[data]]` entries in the same file. Each has `tabs`, `depth`, `exclude`, and
`actions` that send an entry to an app parameter.

## Known limits

- **Window control is X11-only** (`x11rb`, EWMH). In a Wayland session Stop falls back to
  Ctrl-C and Focus is unavailable. The Settings view shows which mode is active.
- **GCS sessions live in `data/SSS_data/sessions/`**, not in `<data_root>/sessions/`. The
  GCS has its own `data_root` (`../../../../data/SSS_data`, relative to its cwd); the
  cards follow it.
- **A missed SIGCHLD.** Seen once on this machine: the hub's tmux server missed a SIGCHLD,
  leaving the app a zombie and its pane dead without an exit status. When a dead pane has
  no status, the hub sends its *own* tmux server a SIGCHLD (harmless: it only makes tmux
  reap its children). An exit is reported once its code is known, or after 3 s.
- **Terminal rendering.** xterm.js 6 dropped its canvas renderer, so without WebGL the
  terminals use the DOM renderer.
- **Blank window (NVIDIA).** If the hub window comes up blank, set
  `WEBKIT_DISABLE_DMABUF_RENDERER=1` in the `.desktop` `Exec=` line. It was not needed
  on this laptop (RTX 4060 + AMD iGPU, X11).
- **"Restart to use new build" for MCS.** It tracks only `blueboat_interfaces`. Mission
  launches started from MCS read the install afresh each time.

## Requests (for the app owners — the hub does not change them)

- **GCS** — open a `.svlog` replay from the command line (e.g. `--replay <file>`), so the
  Data view's *Sonar recordings* entries could open in the GCS directly. Today the entry
  opens its folder.
- **MCS** — a headless "safe quit" (CLI flag or ROS service) that runs the same CM-15 exit
  sequence as its window close. Window close is the only polite path today, and it needs
  X11.
- **World Builder** — handle SIGINT: `signal.signal(SIGINT, …)` plus a short `QTimer`
  heartbeat, as MCS does. Today a Ctrl-C (the hub's Wayland / force-stop fallback) is
  deferred until Python next runs. On 2026-11-11 it surfaced as a `KeyboardInterrupt`
  (exit 254) only when the start dialog closed.
- **Aug Studio** — install the package into the workspace venv (`pip install -e
  SSS-Dataset-Aug-Studio`) so `sss-aug-studio` is on PATH. The hub uses the
  `python3 -m sss_aug_studio.app.main` fallback meanwhile.
