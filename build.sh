#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== ZapretDesktop Build Script ==="

# Check for required commands
command -v git >/dev/null 2>&1 || { echo "git is required but not installed. Install with: sudo apt-get install git"; exit 1; }

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install eel requests

# Install system dependencies
echo "Checking system dependencies..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y nftables git
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y nftables git
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --noconfirm nftables git
fi

# Clone zapret if not exists
if [ ! -d "data" ]; then
    echo "Cloning zapret..."
    git clone https://github.com/Sergeydigl3/zapret-discord-youtube-linux.git data/
fi

# Download zapret dependencies
echo "Downloading zapret dependencies..."
cd data
bash service.sh download-deps --default
cd ..

# Create desktop file
echo "Creating desktop file..."
python3 -c "
import sys
sys.path.insert(0, '.')
import functions as fn
fn.desktop(True)
"

echo "=== Build complete! ==="
echo "Run: ./venv/bin/python3 app.py"
