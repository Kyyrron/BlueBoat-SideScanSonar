# Install BlueBoat Hub (Linux)

Five steps. At the end, BlueBoat Hub is an app on your Desktop and in the app grid, like any
other. Tested on Ubuntu 24.04 (GNOME, X11) with ROS 2 Jazzy.

**Before you start:** the workspace is built at least once (`~/ros2_ws`, with `env.sh`
and `.venv`), as described in the main README.

## 1. Get the code

The hub is the `hub/` folder of this repository:

```bash
cd ~/ros2_ws/src
git clone --recurse-submodules https://github.com/Kyyrron/BlueBoat-SideScanSonar.git   # skip if already there
cd BlueBoat-SideScanSonar/hub
```

## 2. Install the system libraries (once, needs sudo)

```bash
sudo apt install tmux libwebkit2gtk-4.1-dev libsoup-3.0-dev libjavascriptcoregtk-4.1-dev \
  build-essential libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

## 3. Install Rust and Node (once, no sudo)

Both install in your home folder only.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal -c clippy
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | PROFILE=/dev/null bash
. ~/.nvm/nvm.sh && nvm install 22
```

## 4. Build and install

```bash
./install.sh
```

This takes about two minutes the first time. It builds the app and creates:

- a **BlueBoat Hub icon on your Desktop**;
- an entry in the **app grid** (press Super, type "BlueBoat Hub");
- the program itself, at `~/.local/bin/blueboat-hub`.

Nothing is installed outside your home folder.

## 5. Open it

Double-click the Desktop icon, or open it from the app grid. To keep it in the dock:
right-click its icon → **Pin to Dash**.

---

## Later

| To… | Run (in `hub/`) |
|---|---|
| Update after a `git pull` | `./install.sh` |
| Free disk space (≈2 GB of build files) | `./install.sh --clean` |
| Install without the Desktop icon | `./install.sh --no-desktop-icon` |
| Remove the app | `./install.sh --uninstall` |

## If something goes wrong

- **`Missing: …`** — a tool from steps 2–3 is not installed. Run that step again.
- **The window opens blank** (some NVIDIA setups) — edit
  `~/.local/share/applications/blueboat-hub.desktop` and change `Exec=env ` to
  `Exec=env WEBKIT_DISABLE_DMABUF_RENDERER=1 `. Then run `./install.sh` again to refresh
  the Desktop copy.
- **The Desktop icon asks "Allow Launching"** — right-click it → *Allow Launching*.
- **The Stop button only sends Ctrl-C** — you are in a Wayland session. Window control
  needs X11: choose *Ubuntu on Xorg* at the login screen.

How the hub works, how to add an app, and why Stop closes windows instead of killing
processes: [README.md](README.md).
