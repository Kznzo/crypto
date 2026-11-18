"""Pilote automatique « CLIP IT » : un seul bouton, et l'appli clippe plein de streamers toute seule.

- récupère les clips les plus vus du jeu (GTA VI par défaut) des dernières 24 h, toutes chaînes confondues ;
- surveille en direct les plus gros lives du jeu (+ les streamers favoris) et clippe leurs moments forts ;
- toutes les 10 minutes, met la liste à jour : nouveaux lives ajoutés, lives terminés (ou changés de jeu) retirés ;
- ne reprend jamais deux fois le même clip.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import deque

from . import live, pipeline, projects, sources
from .config import DATA_DIR, load_settings

STATE_FILE = DATA_DIR / "pilote-auto.json"
REFRESH_SECONDS = 10 * 60
TOP_CLIPS_EVERY = 60 * 60
DEFAULTS = {"lang": "en", "streams": 5, "clips": 10, "auto": True, "quality": "720"}


def clip_key(url: str | None) -> str | None:
    """Identifiant d'un clip Twitch, quelle que soit la forme du lien."""
    m = re.search(r"(?:/clip/|clips\.twitch\.tv/)([A-Za-z0-9_-]+)", url or "")
    return m.group(1).lower() if m else None


class AutoPilot:
    def __init__(self) -> None:
        self.running = False
        self.options = dict(DEFAULTS)
        self.started = 0.0
        self.last_refresh = 0.0
        self.last_top_clips = 0.0
        self.imported = 0
        self.seen: set[str] = set()
        self.events: deque[dict] = deque(maxlen=40)
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()

    # -- persistance ---------------------------------------------------------------
    def _save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({
            "running": self.running, "options": self.options, "seen": sorted(self.seen)[-2000:],
            "imported": self.imported,
        }, ensure_ascii=False), "utf-8")

    def restore(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            data = json.loads(STATE_FILE.read_text("utf-8"))
        except (OSError, ValueError):
            return
        self.seen = set(data.get("seen") or [])
        self.imported = int(data.get("imported") or 0)
        if data.get("running"):
            self.start(data.get("options") or {})

    def _log(self, text: str, kind: str = "info") -> None:
        self.events.appendleft({"t": time.time(), "text": text, "kind": kind})

    # -- marche / arrêt ------------------------------------------------------------------
    def start(self, options: dict | None = None) -> None:
        with self.lock:
            opts = {**DEFAULTS, **{k: v for k, v in (options or {}).items() if k in DEFAULTS}}
            opts["lang"] = opts["lang"] if re.fullmatch(r"([a-z]{2})?", str(opts["lang"])) else "en"
            opts["streams"] = max(1, min(10, int(opts["streams"])))
            opts["clips"] = max(0, min(30, int(opts["clips"])))
            opts["auto"] = bool(opts["auto"])
            opts["quality"] = "1080" if str(opts["quality"]) == "1080" else "720"
            self.options = opts
            if self.running:
                self._save()
                self.stop_event.set()  # relance la boucle avec les nouvelles options
                if self.thread:
                    self.thread.join(timeout=5)
            self.stop_event = threading.Event()
            self.running = True
            self.started = time.time()
            self.last_refresh = 0.0
            self.last_top_clips = 0.0
            self._save()
            self._log("Pilote automatique lancé", "ok")
            self.thread = threading.Thread(target=self._loop, daemon=True, name="pilote-auto")
            self.thread.start()

    def stop(self) -> None:
        with self.lock:
            self.running = False
            self.stop_event.set()
            for w in list(live.manager.watchers.values()):
                if w.options.get("autopilot"):
                    live.manager.stop(w.channel)
            self._save()
            self._log("Pilote automatique arrêté", "info")

    # -- boucle ----------------------------------------------------------------------------
    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                if time.time() - self.last_top_clips >= TOP_CLIPS_EVERY:
                    self._import_top_clips()
                    self.last_top_clips = time.time()
                self._refresh_streams()
                self.last_refresh = time.time()
            except Exception as exc:  # une erreur réseau ne doit pas arrêter le pilote
                self._log(f"Erreur : {str(exc)[:140]}", "warn")
            self._save()
            if self.stop_event.wait(REFRESH_SECONDS):
                break

    def _settings_game(self) -> str:
        return load_settings().get("game_filter") or "Grand Theft Auto VI"

    def _known_keys(self) -> set[str]:
        keys = set(self.seen)
        for p in projects.load_all():
            k = clip_key((p.get("origin") or {}).get("url"))
            if k:
                keys.add(k)
        return keys

    def _import_top_clips(self) -> None:
        n = self.options["clips"]
        if n <= 0:
            return
        game = self._settings_game()
        clips = sources.game_clips(game, "24h", self.options["lang"], limit=50)
        known = self._known_keys()
        settings = load_settings()
        formats = settings.get("default_formats") or ["tiktok", "reels", "shorts"]
        added = 0
        for c in clips:
            key = clip_key(c["url"])
            if not key or key in known:
                continue
            p = projects.new_project(c.get("title") or "Clip Twitch", {"url": c["url"], "autopilot": True})
            pipeline.start_import_url(p["id"], c["url"], self.options["auto"], formats)
            self.seen.add(key)
            known.add(key)
            added += 1
            if added >= n:
                break
        self.imported += added
        self._log(f"{added} clip(s) {game} du jour récupéré(s)" if added else "Pas de nouveau top clip pour l'instant",
                  "ok" if added else "info")

    def _refresh_streams(self) -> None:
        settings = load_settings()
        game = self._settings_game()
        streams = sources.game_streams(game, self.options["lang"], limit=30)
        wanted = [s["channel"] for s in streams[: self.options["streams"]]]
        live_now = {s["channel"] for s in streams}
        favorites = [c for c in settings.get("favorite_streamers", []) if c in live_now]
        wanted = list(dict.fromkeys(favorites + wanted))
        opts = {
            "sensitivity": "normale", "quality": self.options["quality"], "auto": self.options["auto"],
            "formats": settings.get("default_formats") or ["tiktok", "reels", "shorts"],
            "max_per_hour": 6, "autopilot": True,
        }
        added = []
        for ch in wanted:
            if ch not in live.manager.watchers:
                live.manager.start(ch, dict(opts))
                added.append(ch)
        removed = []
        for w in list(live.manager.watchers.values()):
            # On ne lâche que les chaînes ajoutées par le pilote, plus en live sur le jeu depuis un moment.
            if w.options.get("autopilot") and w.channel not in live_now and w.state in ("attente", "pause_jeu", "erreur"):
                live.manager.stop(w.channel)
                removed.append(w.channel)
        if added:
            self._log(f"Surveillance ajoutée : {', '.join(added)}", "ok")
        if removed:
            self._log(f"Plus en live sur {game} : {', '.join(removed)}", "info")

    # -- état ---------------------------------------------------------------------------
    def status(self) -> dict:
        watchers = [w for w in live.manager.watchers.values() if w.options.get("autopilot") or w.channel in
                    load_settings().get("favorite_streamers", [])]
        live_clips = sum(len(w.clips) for w in watchers)
        return {
            "running": self.running,
            "options": self.options,
            "started": self.started if self.running else None,
            "next_refresh": (self.last_refresh + REFRESH_SECONDS) if self.running and self.last_refresh else None,
            "imported": self.imported,
            "live_clips": live_clips,
            "game": self._settings_game(),
            "watchers": [{"channel": w.channel, "display": w.stream.get("display") or w.channel, "state": w.state,
                          "viewers": w.stream.get("viewers"), "clips": len(w.clips)} for w in watchers],
            "events": list(self.events)[:12],
        }


pilot = AutoPilot()
