#!/usr/bin/env bash
# BlueBoat Hub — build the release binary and put it in the GNOME app grid / dock.
#
#   ./install.sh                    build + install (no sudo)
#   ./install.sh --clean            same, then delete src-tauri/target (frees ~2 GB)
#   ./install.sh --no-desktop-icon  don't put a shortcut on the Desktop
#   ./install.sh --uninstall        remove everything listed below
#
# Installs:
#   ~/.local/bin/blueboat-hub
#   ~/.local/share/applications/blueboat-hub.desktop   (app grid / dock)
#   ~/.local/share/icons/hicolor/{256x256,scalable}/apps/blueboat-hub.{png,svg}
#   ~/Desktop/blueboat-hub.desktop                       (Desktop icon)
# Step-by-step guide: INSTALL.md.
set -euo pipefail

HUB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HUB_DIR"

CLEAN=0
DESKTOP_ICON=1
for arg in "$@"; do
  case "$arg" in
    --clean) CLEAN=1 ;;
    --no-desktop-icon) DESKTOP_ICON=0 ;;
    --uninstall) UNINSTALL=1 ;;
    *) echo "Unknown option: $arg (see the top of install.sh)" >&2; exit 2 ;;
  esac
done

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
APP_ENTRY="$HOME/.local/share/applications/blueboat-hub.desktop"

if [ "${UNINSTALL:-0}" = 1 ]; then
  rm -f "$HOME/.local/bin/blueboat-hub" "$APP_ENTRY" "$DESKTOP_DIR/blueboat-hub.desktop" \
        "$HOME/.local/share/icons/hicolor/256x256/apps/blueboat-hub.png" \
        "$HOME/.local/share/icons/hicolor/scalable/apps/blueboat-hub.svg"
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true
  echo "BlueBoat Hub removed. Apps it started keep running in tmux (tmux -L blueboat-hub ls)."
  exit 0
fi

# user-local toolchains (rustup / nvm), the hub is not built from a sourced ROS shell
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.nvm/nvm.sh"
  nvm use 22 >/dev/null 2>&1 || true
fi
[ -d "$HOME/.cargo/bin" ] && export PATH="$HOME/.cargo/bin:$PATH"

missing=()
for tool in node npm cargo tmux pkg-config; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if ! pkg-config --exists webkit2gtk-4.1 2>/dev/null; then
  missing+=("libwebkit2gtk-4.1-dev")
fi
if [ ${#missing[@]} -gt 0 ]; then
  echo "Missing: ${missing[*]} — see README.md, section Setup." >&2
  exit 1
fi

if [ ! -d node_modules ] || [ package-lock.json -nt node_modules ]; then
  npm ci
fi

# `tauri build` runs `npm run build` first (beforeBuildCommand) and embeds dist/.
npx tauri build --no-bundle

BIN="src-tauri/target/release/blueboat-hub"
install -Dm755 "$BIN" "$HOME/.local/bin/blueboat-hub"
install -Dm644 src-tauri/icons/256x256.png "$HOME/.local/share/icons/hicolor/256x256/apps/blueboat-hub.png"
install -Dm644 src-tauri/icons/icon.svg "$HOME/.local/share/icons/hicolor/scalable/apps/blueboat-hub.svg"

mkdir -p "$(dirname "$APP_ENTRY")"
cat > "$APP_ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=BlueBoat Hub
Comment=Start, watch and stop the BlueBoat apps; build the workspace; open the data folders
Exec=env BLUEBOAT_HUB_DIR=$HUB_DIR $HOME/.local/bin/blueboat-hub
Icon=blueboat-hub
Terminal=false
Categories=Development;
StartupWMClass=blueboat-hub
StartupNotify=true
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# Desktop icon (GNOME "Desktop Icons"): a copy of the entry, marked trusted so it
# opens on double-click instead of asking "Allow Launching".
if [ "$DESKTOP_ICON" = 1 ] && [ -d "$DESKTOP_DIR" ]; then
  install -Dm755 "$APP_ENTRY" "$DESKTOP_DIR/blueboat-hub.desktop"
  gio set "$DESKTOP_DIR/blueboat-hub.desktop" metadata::trusted true 2>/dev/null || true
fi

if [ "$CLEAN" = 1 ]; then
  rm -rf src-tauri/target
  echo "Removed src-tauri/target."
fi

echo "Installed BlueBoat Hub: $HOME/.local/bin/blueboat-hub"
echo "Open it from the Desktop icon, or the app grid (Super, type 'BlueBoat Hub')."
echo "Right-click its dock icon → Pin to Dash to keep it there."
