@echo off
setlocal
title Claude agents setup
cd /d "%~dp0"

set "BLENDER_MCP_SRC=git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp"
set "LIHFOLK_ZIP_URL=https://github.com/lihfolk-cy/v2-vault/releases/download/v2.5.0/LIH.FOLK.VAULT.V2.FULL.zip"
set "ROBLOX_MCP_BAT=%LOCALAPPDATA%\Roblox\mcp.bat"
set "LF_ASSETS=%USERPROFILE%\LihFolk-Assets"
set "LF_VAULT=%USERPROFILE%\LihFolk Vault V2"
set "LF_ZIP=%USERPROFILE%\LihFolk-download.zip"
set "LF_TMP=%USERPROFILE%\LihFolk-temp"
set "HAVE_CLAUDE="
set "NEED_RERUN="

echo.
echo  ===  Claude agents for Blender and Roblox Studio: setup  ===
echo.

rem --- 1. uv: starts the Blender MCP server ----------------------------------
echo == 1/6 uv ==
where uvx >nul 2>nul
if not errorlevel 1 goto :uv_ok
echo   Installing uv...
winget install --id=astral-sh.uv -e --accept-package-agreements --accept-source-agreements
if errorlevel 1 echo   [!] Automatic install failed. Install uv from https://docs.astral.sh/uv/getting-started/installation/
set "NEED_RERUN=1"
goto :git
:uv_ok
echo   [ok] uv is installed

rem --- 2. git: needed to download the Blender MCP server ---------------------
:git
echo.
echo == 2/6 git ==
where git >nul 2>nul
if not errorlevel 1 goto :git_ok
echo   Installing git...
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
if errorlevel 1 echo   [!] Automatic install failed. Install git from https://git-scm.com/download/win
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
echo == 3/6 Blender MCP server ==
echo   Downloading the official Blender MCP server, first time only...
call uvx --from "%BLENDER_MCP_SRC%" blender-mcp --help >nul 2>nul
if errorlevel 1 goto :server_fail
echo   [ok] Blender MCP server ready
goto :plugins
:server_fail
echo   [!] Download failed. Check your internet connection and run this file again.

rem --- 4. Claude Code plugins: blender-skills and LihFolk ----------------------
:plugins
echo.
echo == 4/6 Claude Code plugins: blender-skills, LihFolk ==
where claude >nul 2>nul
if errorlevel 1 goto :no_claude
set "HAVE_CLAUDE=1"
call claude plugin marketplace add ra100/blender-claude-plugin >nul 2>nul
call claude plugin install blender-skills@blender-claude-marketplace >nul 2>nul
call claude plugin marketplace add lihfolk-cy/v2-vault >nul 2>nul
call claude plugin install lihfolk@lihfolk >nul 2>nul
call claude plugin list 2>nul | findstr /i /c:"blender-skills@blender-claude-marketplace" >nul
if errorlevel 1 (echo   [!] blender-skills not installed. Accept it when Claude Code offers it.) else (echo   [ok] blender-skills plugin installed)
call claude plugin list 2>nul | findstr /i /c:"lihfolk@lihfolk" >nul
if errorlevel 1 (echo   [!] LihFolk not installed. Accept it when Claude Code offers it.) else (echo   [ok] LihFolk plugin installed)
goto :vault
:no_claude
echo   [!] The 'claude' command isn't installed.
echo       Using the Claude desktop app? Accept the plugins when Claude Code offers them.

rem --- 5. LihFolk vault for Obsidian + asset pack ------------------------------
:vault
echo.
echo == 5/6 LihFolk vault + asset pack ==
if not exist "%LF_ASSETS%\INDEX.md" goto :vault_ask
if not exist "%LF_VAULT%" goto :vault_ask
echo   [ok] Already installed: %LF_ASSETS%
echo        and %LF_VAULT%
goto :roblox
:vault_ask
set "LF_ANS=Y"
set /p "LF_ANS=  Download the LihFolk vault + asset pack now, 1.4 GB, free? [Y/n] "
if /i "%LF_ANS%"=="n" goto :vault_skip
if /i "%LF_ANS%"=="no" goto :vault_skip
echo   Downloading, this can take a while...
curl.exe -L --fail --progress-bar -o "%LF_ZIP%" "%LIHFOLK_ZIP_URL%"
if errorlevel 1 goto :vault_dl_fail
echo   Unzipping...
if exist "%LF_TMP%" rmdir /s /q "%LF_TMP%"
mkdir "%LF_TMP%"
tar -xf "%LF_ZIP%" -C "%LF_TMP%"
if errorlevel 1 goto :vault_unzip_fail
if not exist "%LF_ASSETS%" move "%LF_TMP%\LihFolk Asset Pack" "%LF_ASSETS%" >nul
if not exist "%LF_VAULT%" move "%LF_TMP%\LihFolk Vault V2\LihFolk Vault V2" "%LF_VAULT%" >nul
rmdir /s /q "%LF_TMP%"
del "%LF_ZIP%"
echo   [ok] Asset pack: %LF_ASSETS%
echo   [ok] Obsidian vault: %LF_VAULT%
goto :roblox
:vault_dl_fail
echo   [!] Download failed. Check your internet connection and run this file again.
if exist "%LF_ZIP%" del "%LF_ZIP%"
goto :roblox
:vault_unzip_fail
echo   [!] Unzip failed. Unzip %LF_ZIP% by hand: right-click, Extract All.
goto :roblox
:vault_skip
echo   [!] Skipped. Run this file again any time to download it.

rem --- 6. Roblox Studio MCP server ---------------------------------------------
:roblox
echo.
echo == 6/6 Roblox Studio ==
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
if exist "%LF_VAULT%" echo  - Obsidian, from https://obsidian.md: Open folder as vault, pick
if exist "%LF_VAULT%" echo    %LF_VAULT%  then Trust author and enable plugins.
echo  - Open Claude Code in this folder, say yes to 'trust this folder',
echo    then type /test-blender, /test-roblox and /test-pipeline
echo.
pause
exit /b 0
