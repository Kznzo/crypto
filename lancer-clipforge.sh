#!/usr/bin/env bash
# Lanceur ClipForge pour macOS et Linux.
set -e
cd "$(dirname "$0")"

PY=""
for cand in python3.12 python3.13 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10 ou plus récent est nécessaire."
  echo "  macOS : installe-le depuis https://www.python.org/downloads/ (ou « brew install python »)"
  echo "  Linux : sudo apt install python3 python3-venv"
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Première installation : quelques minutes, une seule fois…"
  "$PY" -m venv .venv
fi
VPY=.venv/bin/python

if ! cmp -s requirements.txt .venv/requirements.installe; then
  echo "Installation des composants…"
  "$VPY" -m pip install --upgrade pip
  "$VPY" -m pip install -r requirements.txt
  echo "Installation du module IA pour les sous-titres automatiques…"
  "$VPY" -m pip install -r requirements-ia.txt || echo "[!] Module IA non installé : tout le reste fonctionne quand même."
  cp requirements.txt .venv/requirements.installe
else
  # Twitch change souvent : on garde le téléchargeur à jour.
  "$VPY" -m pip install -q --upgrade yt-dlp >/dev/null 2>&1 || true
fi

exec "$VPY" -m clipforge "$@"
