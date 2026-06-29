#!/bin/bash
set -e

# =============================================================================
# GCP Instance Basic Setup Script
# Installs glaciercore (which now bundles zebraflow as a workspace package)
# and configures useful tools/aliases.
#
# Usage: ./basic_setup_gcp.sh [profile]
#   Run with --list-profiles to see available profiles
#   Default: no profile-specific aliases
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILES_FILE="$SCRIPT_DIR/profiles.json"
PROFILE="${1:-}"

# =============================================================================
# Profile functions (reads from profiles.json)
# =============================================================================

apply_profile() {
    local profile="$1"
    
    if ! jq -e ".[\"$profile\"]" "$PROFILES_FILE" > /dev/null 2>&1; then
        echo "Unknown profile: $profile"
        return 1
    fi
    
    echo "" >> ~/.bashrc
    echo "# Profile: $profile" >> ~/.bashrc
    jq -r ".[\"$profile\"] | to_entries[] | \"alias \\(.key)='\\(.value)'\"" "$PROFILES_FILE" >> ~/.bashrc
    
    echo "Profile '$profile' aliases added to ~/.bashrc"
    return 0
}

show_profile_aliases() {
    local profile="$1"
    
    if jq -e ".[\"$profile\"]" "$PROFILES_FILE" > /dev/null 2>&1; then
        echo ""
        echo "Profile '$profile' aliases:"
        jq -r ".[\"$profile\"] | to_entries[] | \"  \\(.key)     - \\(.value)\"" "$PROFILES_FILE"
    fi
}

list_profiles() {
    local profiles
    profiles=$(jq -r 'keys | join(", ")' "$PROFILES_FILE")
    echo "Available profiles: $profiles"
}

# Handle --list-profiles flag
if [ "$PROFILE" = "--list-profiles" ]; then
    list_profiles
    exit 0
fi

echo "=========================================="
echo "  GCP Basic Setup Script"
echo "=========================================="
echo ""

# -----------------------------------------------------------------------------
# 1. Install useful system packages
# -----------------------------------------------------------------------------
echo "[1/5] Installing system packages (tmux, htop, jq)..."
sudo apt update
sudo apt install -y tmux htop jq

# -----------------------------------------------------------------------------
# 2. Create virtual environment with system-site-packages
# -----------------------------------------------------------------------------
echo ""
echo "[2/5] Creating virtual environment..."
python3 -m venv ~/venv-glaciercore --system-site-packages
source ~/venv-glaciercore/bin/activate

# -----------------------------------------------------------------------------
# 3. Clone and install glaciercore
# -----------------------------------------------------------------------------
echo ""
echo "[3/5] Cloning and installing glaciercore (includes zebraflow as a workspace package)..."
cd ~
if [ ! -d "glaciercore" ]; then
    git clone git@github.com:Corintis/glaciercore.git
fi
cd glaciercore
# Install uv, cython, then the glaciercore workspace.
# zebraflow is a workspace member (packages/zebraflow) and is installed
# automatically as an editable dependency of the meta package below.
pip install uv
uv pip install cython
uv pip install --group dev --no-build-isolation --no-binary h5py --editable "."
uv pip install --group dev --no-build-isolation  --no-binary h5py --editable "./glaciercore_scripts"

# -----------------------------------------------------------------------------
# 4. Clone Notion_API and install requests
# -----------------------------------------------------------------------------
echo ""
echo "[4/5] Cloning Notion_API..."
cd ~
if [ ! -d "Notion_API" ]; then
    git clone git@github.com:Corintis/Notion_API.git
fi
pip install requests python-dotenv

# Bootstrap .env from .env.example at the repo root if not already present
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$REPO_ROOT/.env.example" ] && [ ! -f "$REPO_ROOT/.env" ]; then
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
    echo "Created $REPO_ROOT/.env from .env.example — edit it with your real Notion credentials before running the Notion script."
elif [ -f "$REPO_ROOT/.env" ]; then
    echo ".env already exists at $REPO_ROOT/.env, leaving it untouched."
fi

# -----------------------------------------------------------------------------
# 5. Setup aliases in .bashrc and configure tmux
# -----------------------------------------------------------------------------
echo ""
echo "[5/5] Setting up aliases and tmux..."

# Check if aliases already exist to avoid duplicates
if ! grep -q "# GCP Setup Aliases" ~/.bashrc 2>/dev/null; then
    cat << EOF >> ~/.bashrc

# GCP Setup Aliases
alias fire='source ~/venv-glaciercore/bin/activate'
alias glock='cd ~/glaciercore && source ~/venv-glaciercore/bin/activate'
EOF
    echo "Base aliases added to ~/.bashrc"
else
    echo "Base aliases already exist in ~/.bashrc, skipping..."
fi

# Profile-specific aliases (defined in profiles.sh)
if [ -n "$PROFILE" ]; then
    if ! grep -q "# Profile: $PROFILE" ~/.bashrc 2>/dev/null; then
        apply_profile "$PROFILE"
    else
        echo "Profile '$PROFILE' aliases already exist in ~/.bashrc, skipping..."
    fi
fi

# Configure tmux for mouse scrolling
if ! grep -q "set -g mouse on" ~/.tmux.conf 2>/dev/null; then
    cat << EOF >> ~/.tmux.conf
# Enable mouse mode for scrolling/pane selection
set -g mouse on
EOF
    echo "Tmux mouse mode enabled in ~/.tmux.conf"
else
    echo "Tmux mouse mode already configured, skipping..."
fi

# -----------------------------------------------------------------------------
# Done!
# -----------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Available aliases:"
echo "  fire   - Activate the glaciercore virtual environment"
echo "  glock  - Go to glaciercore and activate venv"
if [ -n "$PROFILE" ]; then
    show_profile_aliases "$PROFILE"
fi
echo ""
echo "To apply aliases now, run: source ~/.bashrc"
echo "Mouse scrolling will be enabled in your next tmux session."
echo ""
