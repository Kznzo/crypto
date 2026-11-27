#!/usr/bin/env bash
# One-time setup for the Claude Blender + Roblox Studio agents (macOS and Linux).
# Safe to run again: every step checks first and skips what is already done.
cd "$(dirname "$0")"

BLENDER_MCP_SRC="git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp"
ROBLOX_MCP_MAC="/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP"
LIHFOLK_ZIP_URL="https://github.com/lihfolk-cy/v2-vault/releases/download/v2.5.0/LIH.FOLK.VAULT.V2.FULL.zip"
ADDON_ZIP_URL="https://projects.blender.org/lab/blender_mcp/releases/download/v1.0.0/mcp-1.0.0.zip"
# Blender exits 0 when the MCP add-on is enabled and online access is on.
BL_CHECK="import bpy,sys; p=bpy.context.preferences; sys.exit(0 if 'bl_ext.user_default.mcp' in p.addons.keys() and p.system.use_online_access else 4)"
TODO=()

ok()   { echo "  [ok] $*"; }
warn() { echo "  [!]  $*"; }
step() { echo; echo "== $* =="; }

echo
echo "  ===  Claude agents for Blender and Roblox Studio: setup  ==="

# --- 1. uv (starts the Blender MCP server) ---------------------------------
step "1/7 uv"
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
step "2/7 git"
if git --version >/dev/null 2>&1; then
  ok "git is installed"
else
  warn "git is missing"
  TODO+=("Install git (macOS: run 'xcode-select --install'; Linux: 'sudo apt install git'), then run this script again")
fi

# --- 3. Download the Blender MCP server now, so Claude starts it quickly ----
step "3/7 Blender MCP server"
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

# --- 4. Blender: MCP add-on + online access ----------------------------------
step "4/7 Blender MCP add-on"
BL=""
for c in "/Applications/Blender.app/Contents/MacOS/Blender" "$HOME/Applications/Blender.app/Contents/MacOS/Blender" "$(command -v blender 2>/dev/null)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then BL="$c"; break; fi
done
if [ -z "$BL" ]; then
  warn "Blender not found"
  TODO+=("Install Blender 5.1 or newer from https://www.blender.org/download/, then run this script again")
elif ! "$BL" --background --factory-startup --python-expr "import bpy,sys; sys.exit(0 if bpy.app.version >= (5,1,0) else 3)" >/dev/null 2>&1; then
  warn "your Blender is older than 5.1"
  TODO+=("Update Blender to 5.1 or newer (https://www.blender.org/download/), then run this script again")
elif "$BL" --background --python-expr "$BL_CHECK" >/dev/null 2>&1; then
  ok "MCP add-on installed, online access on"
elif pgrep -x Blender >/dev/null 2>&1 || pgrep -x blender >/dev/null 2>&1; then
  warn "Blender is open"
  TODO+=("Quit Blender, then run this script again so it can install the MCP add-on")
else
  echo "  Installing Blender Lab's MCP add-on and turning on online access..."
  zip="${TMPDIR:-/tmp}/blender-mcp-addon.zip"
  if curl -L --fail -s -o "$zip" "$ADDON_ZIP_URL" \
     && "$BL" --background --command extension install-file --repo user_default --enable "$zip" >/dev/null 2>&1 \
     && "$BL" --background --python-expr "import bpy; bpy.context.preferences.system.use_online_access = True; bpy.ops.wm.save_userpref()" >/dev/null 2>&1 \
     && "$BL" --background --python-expr "$BL_CHECK" >/dev/null 2>&1; then
    ok "MCP add-on installed and online access turned on"
  else
    warn "automatic install failed"
    TODO+=("Blender: install the MCP add-on by hand (BLENDER-ROBLOX.md, step 2)")
  fi
  rm -f "$zip"
fi

# --- 5. Claude Code plugins -----------------------------------------------------
step "5/7 Claude Code plugins (blender-skills, LihFolk)"
install_plugin() { # $1 = marketplace repo, $2 = plugin@marketplace
  claude plugin marketplace add "$1" >/dev/null 2>&1 || true
  if claude plugin install "$2" >/dev/null 2>&1 || claude plugin list 2>/dev/null | grep -q "$2"; then
    ok "$2 installed"
  else
    warn "$2 install failed"
    TODO+=("In Claude Code, accept the $2 plugin when it's offered")
  fi
}
if command -v claude >/dev/null 2>&1; then
  install_plugin ra100/blender-claude-plugin blender-skills@blender-claude-marketplace
  install_plugin lihfolk-cy/v2-vault lihfolk@lihfolk
else
  warn "the 'claude' command isn't installed. Using the Claude desktop app? Accept the plugins when Claude Code offers them."
fi

# --- 6. LihFolk vault (Obsidian) + asset pack -------------------------------
step "6/7 LihFolk vault + asset pack"
LF_HOME="${LIHFOLK_HOME:-$HOME}"
LF_ASSETS="$LF_HOME/LihFolk-Assets"
LF_VAULT="$LF_HOME/LihFolk Vault V2"
if [ -f "$LF_ASSETS/INDEX.md" ] && [ -d "$LF_VAULT" ]; then
  ok "already installed: $LF_ASSETS and $LF_VAULT"
else
  printf "  Download the LihFolk vault + asset pack now (1.4 GB, free)? [Y/n] "
  read -r ans || ans=""
  case "$ans" in
    [nN]*) warn "skipped. Run this script again any time to download it." ;;
    *)
      LF_ZIP="$LF_HOME/LihFolk-download.zip"; LF_TMP="$LF_HOME/LihFolk-temp"
      echo "  Downloading (this can take a while)..."
      if curl -L --fail --progress-bar -o "$LF_ZIP" "$LIHFOLK_ZIP_URL"; then
        echo "  Unzipping..."
        rm -rf "$LF_TMP"; mkdir -p "$LF_TMP"
        if unzip -q "$LF_ZIP" -d "$LF_TMP" 2>/dev/null || python3 -m zipfile -e "$LF_ZIP" "$LF_TMP"; then
          [ -d "$LF_ASSETS" ] || mv "$LF_TMP/LihFolk Asset Pack" "$LF_ASSETS"
          [ -d "$LF_VAULT" ] || mv "$LF_TMP/LihFolk Vault V2/LihFolk Vault V2" "$LF_VAULT"
          rm -rf "$LF_TMP" "$LF_ZIP"
          ok "asset pack: $LF_ASSETS"
          ok "Obsidian vault: $LF_VAULT"
        else
          warn "unzip failed"; TODO+=("Unzip $LF_ZIP by hand")
        fi
      else
        warn "download failed"; rm -f "$LF_ZIP"; TODO+=("Run this script again to download the LihFolk vault")
      fi
      ;;
  esac
fi
if [ -d "$LF_VAULT" ]; then
  TODO+=("Obsidian (https://obsidian.md): Open folder as vault > '$LF_VAULT' > Trust author and enable plugins")
fi

# --- 7. Roblox Studio MCP server --------------------------------------------
step "7/7 Roblox Studio"
if ! command -v claude >/dev/null 2>&1; then
  warn "skipped (no 'claude' command). In Studio use Assistant > ... > Manage MCP Servers > Quick connect > Claude Code."
elif claude mcp list 2>/dev/null | grep -qi "roblox"; then
  ok "Roblox Studio is already connected to Claude Code"
elif [ -x "$ROBLOX_MCP_MAC" ]; then
  if claude mcp add --scope user --transport stdio Roblox_Studio -- "$ROBLOX_MCP_MAC" >/dev/null 2>&1; then
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
echo "  - Roblox Studio: Assistant > ... > Manage MCP Servers > turn on 'Enable Studio as MCP server'."
echo "  - Open Claude Code in this folder, say yes to 'trust this folder', then type /test-blender, /test-roblox and /test-pipeline."
echo
