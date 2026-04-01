#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== ZapretDesktop Build Script ==="

command -v git >/dev/null 2>&1 || { echo "git is required but not installed. Install with: sudo apt-get install git"; exit 1; }

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
VENV_PIP="$SCRIPT_DIR/venv/bin/pip"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Installing Python dependencies..."
$VENV_PYTHON -m pip install --upgrade pip
$VENV_PIP install eel requests

echo "Checking system dependencies..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y nftables git
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y nftables git
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm nftables git
fi

if [ ! -d "data" ]; then
    echo "Cloning zapret..."
    git clone https://github.com/Sergeydigl3/zapret-discord-youtube-linux.git data/
fi

echo "Downloading zapret dependencies..."
cd data
bash service.sh download-deps --default
cd ..

echo "Creating desktop file..."
$VENV_PYTHON -c "
import sys
sys.path.insert(0, '.')
import functions as fn
fn.desktop(True)
"

echo "=== Build complete! ==="
echo "Run: $VENV_PYTHON app.py"
