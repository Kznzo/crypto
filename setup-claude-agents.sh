#!/usr/bin/env bash
# One-time setup for the Claude Blender + Roblox Studio agents (macOS and Linux).
# Safe to run again: every step checks first and skips what is already done.
cd "$(dirname "$0")"

BLENDER_MCP_SRC="git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp"
ROBLOX_MCP_MAC="/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP"
ADDON_LINK="https://projects.blender.org/lab/blender_mcp/releases/download/v1.0.0/mcp-1.0.0.zip?repository=https%3A%2F%2Flab.blender.org%2F&blender_version_min=5.1.0"
TODO=()

ok()   { echo "  [ok] $*"; }
warn() { echo "  [!]  $*"; }
step() { echo; echo "== $* =="; }

echo
echo "  ===  Claude agents for Blender and Roblox Studio: setup  ==="

# --- 1. uv (starts the Blender MCP server) ---------------------------------
step "1/5 uv"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if command -v uvx >/dev/null 2>&1; then
  ok "uv is installed"
else
  echo "  Installing uv (official installer from astral.sh)..."
  if curl -LsSf https://astral.sh/uv/install.sh | sh; then
    export PATH="$HOME/.local/bin:$PATH"
  fi
  if command -v uvx >/dev/null 2>&1; then ok "uv installed"; else warn "uv could not be installed"; TODO+=("Install uv: https://docs.astral.sh/uv/getting-started/installation/"); fi
fi

# --- 2. git (needed to download the Blender MCP server) ---------------------
step "2/5 git"
if git --version >/dev/null 2>&1; then
  ok "git is installed"
else
  warn "git is missing"
  TODO+=("Install git (macOS: run 'xcode-select --install'; Linux: 'sudo apt install git'), then run this script again")
fi

# --- 3. Download the Blender MCP server now, so Claude starts it quickly ----
step "3/5 Blender MCP server"
if command -v uvx >/dev/null 2>&1 && git --version >/dev/null 2>&1; then
  echo "  Downloading the official Blender MCP server (first time only)..."
  if uvx --from "$BLENDER_MCP_SRC" blender-mcp --help >/dev/null 2>&1; then
    ok "Blender MCP server ready"
  else
    warn "download failed (check your internet connection)"
    TODO+=("Run this script again when you're online")
  fi
else
  warn "skipped (needs uv and git)"
fi

# --- 4. blender-skills plugin for Claude Code -------------------------------
step "4/5 blender-skills plugin"
if command -v claude >/dev/null 2>&1; then
  claude plugin marketplace add ra100/blender-claude-plugin >/dev/null 2>&1 || true
  if claude plugin install blender-skills@blender-claude-marketplace >/dev/null 2>&1 \
     || claude plugin list 2>/dev/null | grep -q "blender-skills@blender-claude-marketplace"; then
    ok "blender-skills plugin installed"
  else
    warn "plugin install failed"
    TODO+=("In Claude Code, accept the blender-skills plugin when it's offered")
  fi
else
  warn "the 'claude' command isn't installed. Using the Claude desktop app? Accept the plugin when Claude Code offers it."
fi

# --- 5. Roblox Studio MCP server --------------------------------------------
step "5/5 Roblox Studio"
if ! command -v claude >/dev/null 2>&1; then
  warn "skipped (no 'claude' command). In Studio use Assistant > ... > Manage MCP Servers > Quick connect > Claude Code."
elif claude mcp list 2>/dev/null | grep -qi "roblox"; then
  ok "Roblox Studio is already connected to Claude Code"
elif [ -x "$ROBLOX_MCP_MAC" ]; then
  if claude mcp add --scope user Roblox_Studio -- "$ROBLOX_MCP_MAC" >/dev/null 2>&1; then
    ok "Roblox Studio connected to Claude Code"
  else
    warn "could not add the Roblox Studio server"
    TODO+=("In Studio: Assistant > ... > Manage MCP Servers > Quick connect > Claude Code")
  fi
else
  warn "Roblox Studio not found in /Applications"
  TODO+=("Install Roblox Studio, then run this script again (or use Studio's Quick connect)")
fi

# --- Summary -----------------------------------------------------------------
echo
echo "  ===  Done. Still to do by hand  ==="
for t in "${TODO[@]}"; do echo "  - $t"; done
echo "  - Blender 5.1+: install the 'MCP' add-on. Drag this link into Blender twice:"
echo "      $ADDON_LINK"
echo "    then Edit > Preferences > System > Network > Allow Online Access."
echo "  - Roblox Studio: Assistant > ... > Manage MCP Servers > turn on 'Enable Studio as MCP server'."
echo "  - Open Claude Code in this folder, say yes to 'trust this folder', then type /test-blender and /test-roblox."
echo
