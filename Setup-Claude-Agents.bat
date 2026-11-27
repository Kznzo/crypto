@echo off
setlocal
title Claude agents setup
cd /d "%~dp0"

set "BLENDER_MCP_SRC=git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp"
set "ROBLOX_MCP_BAT=%LOCALAPPDATA%\Roblox\mcp.bat"
set "HAVE_CLAUDE="
set "NEED_RERUN="

echo.
echo  ===  Claude agents for Blender and Roblox Studio: setup  ===
echo.

rem --- 1. uv: starts the Blender MCP server ----------------------------------
echo == 1/5 uv ==
where uvx >nul 2>nul
if not errorlevel 1 goto :uv_ok
echo   Installing uv...
winget install --id=astral-sh.uv -e --accept-package-agreements --accept-source-agreements
set "NEED_RERUN=1"
goto :git
:uv_ok
echo   [ok] uv is installed

rem --- 2. git: needed to download the Blender MCP server ---------------------
:git
echo.
echo == 2/5 git ==
where git >nul 2>nul
if not errorlevel 1 goto :git_ok
echo   Installing git...
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
set "NEED_RERUN=1"
goto :after_tools
:git_ok
echo   [ok] git is installed

:after_tools
if not defined NEED_RERUN goto :server
echo.
echo  uv and/or git were just installed.
echo  Close this window, then double-click Setup-Claude-Agents.bat again to finish.
echo.
pause
exit /b 0

rem --- 3. Download the Blender MCP server now so Claude starts it quickly -----
:server
echo.
echo == 3/5 Blender MCP server ==
echo   Downloading the official Blender MCP server, first time only...
call uvx --from "%BLENDER_MCP_SRC%" blender-mcp --help >nul 2>nul
if errorlevel 1 goto :server_fail
echo   [ok] Blender MCP server ready
goto :plugin
:server_fail
echo   [!] Download failed. Check your internet connection and run this file again.

rem --- 4. blender-skills plugin for Claude Code -------------------------------
:plugin
echo.
echo == 4/5 blender-skills plugin ==
where claude >nul 2>nul
if errorlevel 1 goto :no_claude
set "HAVE_CLAUDE=1"
call claude plugin marketplace add ra100/blender-claude-plugin >nul 2>nul
call claude plugin install blender-skills@blender-claude-marketplace >nul 2>nul
call claude plugin list 2>nul | findstr /i /c:"blender-skills@blender-claude-marketplace" >nul
if errorlevel 1 goto :plugin_fail
echo   [ok] blender-skills plugin installed
goto :roblox
:plugin_fail
echo   [!] Plugin install failed. Accept the blender-skills plugin when Claude Code offers it.
goto :roblox
:no_claude
echo   [!] The 'claude' command isn't installed.
echo       Using the Claude desktop app? Accept the plugin when Claude Code offers it.

rem --- 5. Roblox Studio MCP server ---------------------------------------------
:roblox
echo.
echo == 5/5 Roblox Studio ==
if not defined HAVE_CLAUDE goto :roblox_quick
call claude mcp list 2>nul | findstr /i "roblox" >nul
if not errorlevel 1 goto :roblox_ok
if not exist "%ROBLOX_MCP_BAT%" goto :roblox_missing
call claude mcp add --scope user Roblox_Studio -- cmd.exe /c "%ROBLOX_MCP_BAT%" >nul 2>nul
if errorlevel 1 goto :roblox_quick
echo   [ok] Roblox Studio connected to Claude Code
goto :done
:roblox_ok
echo   [ok] Roblox Studio is already connected to Claude Code
goto :done
:roblox_missing
echo   [!] Roblox Studio's MCP launcher was not found.
echo       Open Roblox Studio, turn on 'Enable Studio as MCP server', then run this file again.
goto :done
:roblox_quick
echo   [!] In Roblox Studio use: Assistant, then ..., then Manage MCP Servers,
echo       then Quick connect, then Claude Code.

:done
echo.
echo  ===  Done. Still to do by hand  ===
echo  - Blender 5.1 or newer: install the 'MCP' add-on from Blender Lab.
echo    The download link and steps are in BLENDER-ROBLOX.md, step 2.
echo    Then: Edit, Preferences, System, Network, Allow Online Access.
echo  - Roblox Studio: Assistant, then ..., then Manage MCP Servers,
echo    turn on 'Enable Studio as MCP server'.
echo  - Open Claude Code in this folder, say yes to 'trust this folder',
echo    then type /test-blender and /test-roblox
echo.
pause
exit /b 0
