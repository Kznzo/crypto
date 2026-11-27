#!/usr/bin/env bash
# Double-click on macOS: opens Terminal and runs the one-time setup for the Claude Blender + Roblox agents.
cd "$(dirname "$0")"
./setup-claude-agents.sh
echo "Press Enter to close this window."
read -r _
