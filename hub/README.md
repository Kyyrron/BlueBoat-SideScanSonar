# BlueBoat Hub

One desktop app to start, watch and stop every BlueBoat app, build the ROS workspace and open
the data folders.

The Hub is a **launcher**. Each app still opens its own window. In the Hub, the app's tile
turns into its **live terminal**.

- Every app runs in its own **tmux** session (socket `tmux -L blueboat-hub`). Apps keep
  running if the Hub is closed or crashes; when the Hub opens again they reappear with their
  history.
- Built with Tauri 2 (Rust, WebKitGTK), Svelte 5 + TypeScript and xterm.js. Nothing is
  fetched from the internet at runtime (fonts are bundled).
- It is not a submodule and not a colcon package (`COLCON_IGNORE`).
- It sends no robot command and never starts a mission launch itself. Missions, E-STOP and
  the safe shutdown belong to MCS.

## Install

Step by step: **[INSTALL.md](INSTALL.md)**. In short:

```bash
sudo apt install tmux libwebkit2gtk-4.1-dev libsoup-3.0-dev libjavascriptcoregtk-4.1-dev \
  build-essential libssl-dev libayatana-appindicator3-dev librsvg2-dev
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal -c clippy
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | PROFILE=/dev/null bash
. ~/.nvm/nvm.sh && nvm install 22

cd ~/ros2_ws/src/BlueBoat-SideScanSonar/hub
./install.sh
```

The workspace `~/ros2_ws` must have been built once (with `env.sh` and `.venv`).

| Command (in `hub/`) | Does |
|---|---|
| `./install.sh` | Build and install (also after a `git pull`) |
| `./install.sh --clean` | Same, then delete `src-tauri/target` (about 2 GB) |
| `./install.sh --no-desktop-icon` | Install without the Desktop shortcut |
| `./install.sh --uninstall` | Remove the Hub (apps already running keep running in tmux) |

Installed, all in your home folder:

- `~/.local/bin/blueboat-hub`
- `~/.local/share/applications/blueboat-hub.desktop` (app grid)
- `~/Desktop/blueboat-hub.desktop` (Desktop icon)
- icons in `~/.local/share/icons/hicolor/`

Open it from the Desktop or the app grid. Start it from the desktop, not from a sourced shell:
each app builds its own environment.

## Use

| View | What it holds |
|---|---|
| **Apps** | One tile per app, grouped. *Launch* turns the tile into its terminal. *Focus* raises the app's window. Restart, Stop, Collapse, Maximize are on the card (Esc leaves Maximize). With 3+ apps, *Tile terminals* shows them side by side. A greyed tile names what is missing (for example "isn't built yet — run Build"). |
| **Data** | Read-only folder cards: count, size, newest entries. Clicking an entry opens it: a run folder or `*-poslog.csv` in the Log Reviewer, a world folder in the Gazebo viewer, anything else with `xdg-open`. Rescanned every 30 s and on window focus. |
| **Build** | `source /opt/ros/jazzy/setup.bash && colcon build` in its own tmux session, with per-package progress. Asks first if apps are running (never stops them). Afterwards, cards of apps using a rebuilt package say *restart to use new build*. |
| **Logs** | Each session's output, in `~/.local/state/blueboat-hub/logs/` (newest 20 per app). |
| **Settings** | Theme, terminal font size, where everything lives, X11 or Wayland mode. |

Keyboard:

| Keys | Action |
|---|---|
| `Ctrl K` | Command palette (launch, stop, focus, build, open) |
| `Ctrl B` | Build all |
| `Ctrl 1` … `Ctrl 9` | Show the n-th terminal |
| `Ctrl Shift F` | Search the terminal |
| `Ctrl Shift C` / `Ctrl Shift V` | Copy / paste |

## How Stop works (safety)

**Stop = closing the app's window, exactly like its ✕ button.** The Hub sends
`_NET_CLOSE_WINDOW` to the app's windows. It does not kill the process.

Why: the apps shut down cleanly when their window closes. MCS runs its safe shutdown
(`default` before any node stops) and asks first if a mission is running. The GCS ends its
recording and stops pinging. A plain kill would skip this, and with MCS the thrusters could
stay in override.

- **The app may say no** (MCS: "Mission running…"). The card waits, with *Keep running*.
  Nothing escalates on its own.
- **Force stop.** After 10 s a *Force stop…* button appears, behind a confirmation. It sends
  Ctrl-C. *Kill session…* (`tmux kill-session`) needs a second confirmation.
- **Apps without a window** (sonar driver, Belief, Replanner), or any app when no window is
  found: Stop sends Ctrl-C, the normal way to stop `ros2 launch`.
- **Gazebo viewer:** Stop sends Ctrl-C straight away (`stop = "ctrl-c"`). If its window is
  closed by hand and `ros2 launch` still runs 2 s later, the Hub sends Ctrl-C
  (`after_close = "ctrl-c"`).
- **Dialogs are never closed** (closing one would answer "Cancel").
- **Quitting the Hub with apps running** asks: *Quit hub* (apps keep running), *Stop all and
  quit*, or *Cancel*.

## Configuration: `apps.toml`

Every tile, group and data card is defined in `apps.toml`. The Hub reloads it on save. A
broken edit keeps the last good version and shows the error at the top of the Apps view.

Every app runs as:

```
bash -ic '<print the command>; cd ~/ros2_ws && source env.sh && cd <cwd> && exec <command>'
```

`bash -ic` (interactive) runs `~/.bashrc` as a terminal does, so ROS and the acados variables
for the MPC controller are set. The template is `[defaults] template` in `apps.toml`.

### Adding an app

Example (the Belief tile):

```toml
[[apps]]
id = "belief"                      # lowercase, digits, _
name = "Belief"
group = "operate"                  # or a new [[groups]] entry
description = "The belief map: pings + detections -> BeliefGrid, the Replanner's only input."
icon = "brain"                     # names in src/lib/icons.ts
cwd = "."                          # relative to the workspace
command = "ros2 launch blueboat_belief belief_launch.py area_file:={world}"
requires = [{ launch = "blueboat_belief/belief_launch.py" }]   # greys the tile until built
params = [{ name = "world", label = "World (survey area)", kind = "path", root = "~/worlds", depth = 2, marker = "metadata.yaml" }]
variants = [{ id = "sim", name = "Gazebo (sim time)", args = "use_sim_time:=true" }]
packages = ["blueboat_belief", "blueboat_belief_interfaces"]   # drives "restart to use new build"
window = false                     # no window: Stop sends Ctrl-C
stop = "ctrl-c"
```

| Field | Meaning |
|---|---|
| `requires` | `{ ros_exe = "pkg/exe" }`, `{ launch = "pkg/file.py" }`, `{ file = "path" }` or `{ bin = "program" }`. `fallback_command` + `fallback_requires` are used when `requires` fails. |
| `params` | `kind = path \| file \| number \| choice`. Used in `command` as `{name}` (required) or `{name?}` (optional). Values are checked and shell-quoted. |
| `variants` | `{ id, name, args }`, appended to the command (for example GCS `--sim`). |
| `singleton` | `true` by default: a second launch focuses the running window. |
| `window` | `false` for command-line apps. |
| `stop`, `after_close` | `"ctrl-c"`: see *How Stop works*. |
| `warning`, `force_warning` | Badge on the tile; text in the Force-stop dialog. |
| `help` | Text behind the tile's ⓘ button. |
| `primary`, `optional`, `planned` | Wide tile; badge; ghost tile that cannot launch. |
| `packages` | colcon packages whose rebuild shows *restart to use new build*. |

Path placeholders: `~`, `{workspace}`, `{data_root}` (`$BLUEBOAT_DATA_DIR`, else
`{workspace}/data`), `{superproject}`. Data cards are `[[data]]` entries in the same file.

## Development

```bash
. ~/.nvm/nvm.sh
npm install
npx tauri dev                       # hot-reloading frontend
```

Checks before a change is done:

```bash
cd src-tauri && cargo clippy --all-targets -- -D warnings && cargo test
cd .. && npm run check && npm run build
```

## Layout

| Path | What |
|---|---|
| `apps.toml` | App registry (tiles, groups, build command, data cards) |
| `install.sh` | Build and install script |
| `src/` | Frontend (Svelte, TypeScript) |
| `src-tauri/` | Backend (Rust): tmux, X11 window control, data scans |
| `tmux.conf` | Settings of the Hub's tmux server |
| `INSTALL.md` | Step-by-step install guide |

## Known limits

- **Window control needs X11.** In a Wayland session Stop falls back to Ctrl-C and Focus does
  not work. Choose *Ubuntu on Xorg* at login.
- **Blank window** (some NVIDIA setups): add `WEBKIT_DISABLE_DMABUF_RENDERER=1` to the
  `Exec=` line of the `.desktop` file (see INSTALL.md).
- **GCS sessions** are in `~/ros2_ws/data/SSS_data/sessions/`, not `<data_root>/sessions/`
  (the GCS has its own data root).
- **MCS "restart to use new build"** tracks only `blueboat_interfaces`. Missions started from
  MCS read the install fresh each time.
- **Aug Studio** runs through its fallback `python3 -m sss_aug_studio.app.main` until the
  package is installed in the venv (`pip install -e SSS-Dataset-Aug-Studio`).
- Without WebGL the terminals use xterm.js's slower DOM renderer.
