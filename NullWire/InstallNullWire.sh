#!/bin/bash

# ==============================

# NullWire Installer / Launcher

# ==============================

# resolve base paths safely

BASE_DIR="$(dirname "$(realpath "$0")")"
RUNTIME_DIR="$BASE_DIR/Runtime"

cd "$RUNTIME_DIR" || exit

DE="$XDG_CURRENT_DESKTOP"

if [[ "$DE" == *"GNOME"* ]]; then
    echo "GNOME detected — tray support may require extension."
fi

chmod +x NullWire.sh

# ==============================

# Dependency Check

# ==============================

MISSING=()

check_cmd() {
command -v "$1" >/dev/null 2>&1 || MISSING+=("$1")
}

check_cmd python3
check_cmd jq
check_cmd inotifywait
check_cmd pactl
check_cmd pw-link
check_cmd pw-dump
check_cmd wpctl

# tkinter check

python3 - <<EOF 2>/dev/null || MISSING+=("python3-tk")
import tkinter
EOF

# gi check

python3 - <<EOF 2>/dev/null || MISSING+=("python3-gi" "gir1.2-appindicator3-0.1")
import gi
gi.require_version('AppIndicator3', '0.1')
EOF

# venv check

python3 -m venv --help >/dev/null 2>&1 || MISSING+=("python3-venv")

# install if needed

if [ ${#MISSING[@]} -ne 0 ]; then
echo "Missing dependencies: ${MISSING[*]}"
echo "This will install required system packages (requires sudo)."
echo "Continue? (y/n)"
read -r confirm

[[ "$confirm" != "y" ]] && exit 1

sudo apt update
sudo apt install -y \
python3 python3-venv python3-tk \
python3-gi gir1.2-appindicator3-0.1 \
jq inotify-tools \
pipewire pipewire-audio-client-libraries
fi

chmod +x NullWire.py
chmod +x NW.sh

# ==============================
# GNOME / Ubuntu Tray Support
# ==============================

DE="$XDG_CURRENT_DESKTOP"

if grep -qi ubuntu /etc/os-release && [[ "$DE" == *"GNOME"* ]]; then
    echo ""
    echo "GNOME detected (Ubuntu). Installing tray support..."

    sudo apt install -y gnome-shell-extension-appindicator

    echo ""
    echo "IMPORTANT:"
    echo "You may need to log out and back in for the tray icon to appear."
    echo ""
fi

# ==============================

# VENV SETUP

# ==============================

if [ ! -d "venv" ]; then
echo "Creating virtual environment..."
python3 -m venv venv --system-site-packages
fi

# activate venv

source venv/bin/activate

if ! python3 -c "import setproctitle" 2>/dev/null; then
echo "Installing setproctitle..."
python3 -m pip install setproctitle
fi



# ==============================

# CREATE .DESKTOP ENTRY

# ==============================

DESKTOP_FILE="$HOME/.local/share/applications/nullwire.desktop"

FULL_PATH="$(realpath "$RUNTIME_DIR/NullWire.sh")"
ICON_PATH="$(realpath "$RUNTIME_DIR/NullWire.png")"

echo "Creating desktop entry..."

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=NullWire
Exec=$FULL_PATH
Icon=$ICON_PATH
Type=Application
Terminal=false
Categories=Utility;
EOF

chmod +x "$DESKTOP_FILE"

# refresh application database (safe even if not needed)

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null

echo "Desktop entry created."

# ==============================

# OPTIONAL FIRST LAUNCH

# ==============================

echo "Installation complete. 
read 


