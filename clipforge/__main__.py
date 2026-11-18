"""Démarrage : « python -m clipforge »."""
from __future__ import annotations

import argparse
import os
import socket
import threading
import time
import webbrowser


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="ClipForge : clips Twitch → TikTok, Reels, Shorts, YouTube")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CLIPFORGE_PORT", 8765)))
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    parser.add_argument("--local-only", action="store_true", help="refuser les connexions de la tablette")
    args = parser.parse_args()

    import uvicorn

    from . import __version__, server
    from .config import DATA_DIR, ensure_dirs

    ensure_dirs()
    if not _port_free(args.port):
        url = f"http://localhost:{args.port}"
        print(f"ClipForge semble déjà lancé : ouverture de {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return
    server.PORT = args.port
    host = "127.0.0.1" if args.local_only else "0.0.0.0"
    local_url = f"http://localhost:{args.port}"

    print("=" * 62)
    print(f"  ClipForge {__version__} est lancé !")
    print(f"  Sur ce PC      : {local_url}")
    tablet = None if args.local_only else server.tablet_url()
    if tablet:
        print(f"  Sur la tablette: bouton « Tablette » dans l'appli (QR code)")
        print(f"                   ou {tablet}")
    print(f"  Dossier des projets : {DATA_DIR}")
    print("  Pour quitter : ferme cette fenêtre (ou Ctrl+C).")
    print("=" * 62)

    if not args.no_browser:
        def _open() -> None:
            time.sleep(1.5)
            webbrowser.open(local_url)

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(server.app, host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
