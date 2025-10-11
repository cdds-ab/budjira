#!/bin/sh
# budjira installation script
# Usage: curl -LsSf https://raw.githubusercontent.com/cdds-ab/budjira/master/install.sh | sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "${CYAN}╭─ 🦖 budjira installer ─╮${NC}"
echo "${CYAN}╰────────────────────────╯${NC}"
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "${YELLOW}→${NC} Detected OS: ${GREEN}${OS}${NC} (${ARCH})"

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "${YELLOW}→${NC} uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "${GREEN}✓${NC} uv is already installed"
fi

# Clone or update budjira
INSTALL_DIR="$HOME/.local/share/budjira"
BIN_DIR="$HOME/.local/bin"

echo "${YELLOW}→${NC} Installing budjira to ${INSTALL_DIR}..."

if [ -d "$INSTALL_DIR" ]; then
    echo "${YELLOW}→${NC} Updating existing installation..."
    cd "$INSTALL_DIR"
    # Reset any local changes and remove untracked files
    git reset --hard --quiet
    git clean -fd --quiet
    git pull --quiet
else
    echo "${YELLOW}→${NC} Cloning budjira repository..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --quiet https://github.com/cdds-ab/budjira.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install dependencies with uv
echo "${YELLOW}→${NC} Installing dependencies..."
uv sync --quiet

# Create symlink in bin directory
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/.venv/bin/budjira" "$BIN_DIR/budjira"

echo ""
echo "${GREEN}✓${NC} budjira installed successfully!"
echo ""
echo "To use budjira, make sure ${CYAN}$BIN_DIR${NC} is in your PATH."
echo ""
echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
echo "  ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
echo ""
echo "Then reload your shell or run:"
echo "  ${CYAN}source ~/.bashrc${NC}  ${YELLOW}# or ~/.zshrc${NC}"
echo ""
echo "Test the installation:"
echo "  ${CYAN}budjira --version${NC}"
echo ""
