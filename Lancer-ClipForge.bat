@echo off
setlocal
title ClipForge
cd /d "%~dp0"

echo.
echo  ===  ClipForge  ===
echo.

rem --- 1. Trouver Python 3.10 ou plus recent -------------------------------
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python n'est pas installe sur ce PC. Tentative d'installation automatique...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo.
    echo  Installation automatique impossible.
    echo  1. Va sur https://www.python.org/downloads/
    echo  2. Installe Python en cochant la case "Add python.exe to PATH"
    echo  3. Relance ce fichier Lancer-ClipForge.bat
    echo.
    pause
    exit /b 1
  )
  echo.
  echo  Python est installe. Ferme cette fenetre puis relance Lancer-ClipForge.bat
  pause
  exit /b 0
)

rem --- 2. Environnement de l'appli (cree une seule fois) --------------------
if not exist ".venv\Scripts\python.exe" (
  echo Premiere installation : quelques minutes, une seule fois...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
set "VPY=.venv\Scripts\python.exe"

fc /b requirements.txt ".venv\requirements.installe" >nul 2>nul
if errorlevel 1 (
  echo Installation des composants...
  "%VPY%" -m pip install --upgrade pip
  "%VPY%" -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
  echo Installation du module IA pour les sous-titres automatiques...
  "%VPY%" -m pip install -r requirements-ia.txt
  if errorlevel 1 echo [!] Module IA non installe : tout le reste fonctionne quand meme.
  copy /y requirements.txt ".venv\requirements.installe" >nul
) else (
  rem Twitch change souvent : on garde le telechargeur a jour.
  "%VPY%" -m pip install -q --upgrade yt-dlp >nul 2>nul
)

rem --- 3. Lancement ----------------------------------------------------------
echo.
echo  Si Windows demande l'autorisation reseau, accepte pour "Reseaux prives"
echo  (c'est ce qui permet d'ouvrir ClipForge sur la tablette).
echo.
"%VPY%" -m clipforge
if errorlevel 1 pause
exit /b 0

:fail
echo.
echo  Une erreur est survenue pendant l'installation (voir le message au-dessus).
echo  Verifie ta connexion Internet puis relance ce fichier.
pause
exit /b 1
