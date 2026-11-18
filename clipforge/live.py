"""Clippeur automatique en direct : regarde un live Twitch et crée les clips tout seul.

Pour chaque chaîne surveillée :
- le flux du live est enregistré en continu dans une mémoire tampon (les dernières minutes, morceaux de 2 s) ;
  les coupures pub de Twitch sont ignorées ;
- le chat est lu en direct (pics de messages, « clip it », KEKW, LUL, Pog…) et le son est analysé (cris, rires) ;
- quand ça s'emballe, l'appli découpe le moment (montée + réaction) à la durée choisie, crée un projet,
  et lance le montage automatique si demandé ;
- le bouton « Clipper maintenant » garde les dernières secondes, comme le bouton clip de Twitch.
"""
from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import numpy as np

from .config import DATA_DIR, clip_seconds, load_settings
from .ffmpeg_utils import _NO_WINDOW, ffmpeg_path, run

LIVE_DIR = DATA_DIR / "live"
STATE_FILE = LIVE_DIR / "surveillance.json"
BUFFER_SECONDS = 240  # mémoire tampon du live (doit couvrir la plus longue durée de clip + marge)
REACTION_DELAY = 3.0  # le chat réagit quelques secondes après le moment
SENSITIVITY = {"faible": 3.0, "normale": 2.2, "forte": 1.6}
QUALITIES = {"1080": 1080, "720": 720}
GQL_URL = "https://gql.twitch.tv/gql"
GQL_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

# Mots du chat qui comptent plus qu'un message ordinaire.
CLIP_WORDS = re.compile(r"\bclip(?:ped|pez|ez|it| it| that| ça| ca)?\b", re.I)
HYPE_WORDS = re.compile(
    r"\b(KEKW|LULW?|OMEGALUL|ICANT|LMAO+|LOL+|MDR+|PTDR+|XD+|Pog(?:gers|Champ|U)?|W+|WW+|"
    r"monkaS|monkaW|D:|WTF|OMG|NO+O|YOO+|HOLY|INSANE|CINEMA|GG)\b", re.I,
)


def _now() -> float:
    return time.time()


def _parse_pdt(value: str) -> float:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp()


def parse_live_playlist(text: str, base_url: str) -> dict:
    """Lit une playlist HLS live de Twitch : séquence, segments (heure exacte, durée, pub ou non)."""
    seq = 0
    target = 2.0
    segments = []
    pdt = None
    dur = None
    title = ""
    ended = False
    init = None  # segments fMP4 : en-tête commun (#EXT-X-MAP) ; segments TS : aucun
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-MAP:"):
            m = re.search(r'URI="([^"]+)"', line)
            init = urljoin(base_url, m.group(1)) if m else None
        elif line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            seq = int(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-TARGETDURATION:"):
            target = float(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-PROGRAM-DATE-TIME:"):
            try:
                pdt = _parse_pdt(line.split(":", 1)[1])
            except ValueError:
                pdt = None
        elif line.startswith("#EXTINF:"):
            body = line[8:]
            d, _, title = body.partition(",")
            try:
                dur = float(d)
            except ValueError:
                dur = 2.0
        elif line.startswith("#EXT-X-ENDLIST"):
            ended = True
        elif line and not line.startswith("#") and dur is not None:
            segments.append({
                "seq": seq + len(segments),
                "pdt": pdt,
                "dur": dur,
                "ad": bool(title) and title.strip() != "live",  # Twitch marque le vrai direct « live »
                "url": urljoin(base_url, line),
                "init": init,
            })
            if pdt is not None:
                pdt += dur
            dur, title = None, ""
    return {"segments": segments, "target": target, "ended": ended}


def game_matches(game: str | None, wanted: str | None) -> bool:
    """Le jeu du live correspond-il au filtre ? (« Grand Theft Auto V » ≠ « Grand Theft Auto VI »)."""
    if not wanted:
        return True
    return (game or "").strip().lower() == wanted.strip().lower()


def chat_weight(text: str) -> float:
    w = 1.0
    if CLIP_WORDS.search(text):
        w += 5.0  # les viewers qui écrivent « clip it » : signal très fort
    if HYPE_WORDS.search(text):
        w += 1.0
    if len(text.split()) >= 2 and text.upper() == text and any(c.isalpha() for c in text):
        w += 0.5  # UNE PHRASE CRIÉE EN MAJUSCULES (un emote seul ne compte pas)
    return w


class LiveWatcher:
    def __init__(self, channel: str, options: dict):
        self.channel = channel
        self.options = options
        self.dir = LIVE_DIR / channel
        self.state = "demarrage"
        self.message = "Démarrage…"
        self.stream: dict = {}
        self.segments: deque[dict] = deque()
        self.audio: deque[tuple[float, float]] = deque()  # (heure, dB) toutes les 0,5 s
        self.chat: deque[tuple[float, float]] = deque()  # (heure de réception, poids)
        self.latency = 6.0
        self.score = 0.0
        self.chat_rate = 0.0
        self.clips: list[dict] = []
        self.events: deque[dict] = deque(maxlen=30)
        self.started = _now()
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        self._analyzed_seq = -1
        self._pending: dict | None = None
        self._last_peak = 0.0
        self._last_eval = 0.0
        self._ydl = None
        self._threads: list[threading.Thread] = []

    # -- cycle de vie ---------------------------------------------------------
    def start(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        for target in (self._record_loop, self._chat_loop, self._analyze_loop):
            t = threading.Thread(target=target, daemon=True, name=f"live-{self.channel}-{target.__name__}")
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self.stop_event.set()
        self.state = "arret"
        self.message = "Arrêté"

    def _log(self, text: str, kind: str = "info") -> None:
        self.events.appendleft({"t": _now(), "text": text, "kind": kind})

    def _sleep(self, seconds: float) -> bool:
        return self.stop_event.wait(seconds)

    def _http(self):
        if self._ydl is None:
            import yt_dlp

            self._ydl = yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True})
        return self._ydl

    def _get(self, url: str, data: bytes | None = None, headers: dict | None = None, timeout: float = 15) -> bytes:
        from yt_dlp.networking import Request

        req = Request(url, data=data, headers=headers or {})
        with self._http().urlopen(req) as res:
            return res.read()

    # -- infos de la chaîne ----------------------------------------------------
    def _stream_info(self) -> dict:
        query = ('query{user(login:"%s"){displayName broadcastSettings{language} '
                 'stream{title viewersCount game{name}}}}' % self.channel)
        try:
            raw = self._get(GQL_URL, json.dumps({"query": query}).encode(),
                            {"Client-Id": GQL_CLIENT_ID, "Content-Type": "application/json"})
            user = (json.loads(raw).get("data") or {}).get("user") or {}
        except Exception:
            return {}
        stream = user.get("stream") or {}
        return {
            "display": user.get("displayName") or self.channel,
            "language": ((user.get("broadcastSettings") or {}).get("language") or "").lower()[:2] or None,
            "live": bool(stream),
            "title": stream.get("title"),
            "viewers": stream.get("viewersCount"),
            "game": (stream.get("game") or {}).get("name"),
        }

    def _resolve(self) -> str | None:
        """URL de la playlist du live (meilleure qualité ≤ réglage), ou None si la chaîne est hors ligne."""
        try:
            info = self._http().extract_info(f"https://www.twitch.tv/{self.channel}", download=False)
        except Exception as exc:
            if re.search(r"not currently live|is offline|does not exist", str(exc), re.I):
                return None
            raise
        if not info or not info.get("is_live"):
            return None
        max_h = QUALITIES.get(str(self.options.get("quality", "1080")), 1080)
        fmts = [f for f in info.get("formats", []) if f.get("vcodec") != "none" and (f.get("height") or 0) <= max_h]
        if not fmts:
            return None
        best = max(fmts, key=lambda f: ((f.get("height") or 0), (f.get("fps") or 0)))
        self.stream["quality"] = f"{best.get('height')}p{int(best.get('fps') or 30)}"
        return best["url"]

    # -- enregistrement --------------------------------------------------------
    def _record_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                info = self._stream_info()
                if info:
                    self.stream.update(info)
                wanted = self._wanted_game()
                live = info.get("live", True)
                url = self._resolve() if live and game_matches(self.stream.get("game"), wanted) else None
            except Exception as exc:
                self.state, self.message = "erreur", f"Impossible de lire la chaîne : {str(exc)[:160]}"
                if self._sleep(30):
                    break
                continue
            if not live or (not url and game_matches(self.stream.get("game"), wanted)):
                self.state, self.message = "attente", "Hors ligne : en attente du début du live…"
                if self._sleep(60):
                    break
                continue
            if not game_matches(self.stream.get("game"), wanted):
                # Pas le bon jeu : on n'enregistre rien et on revérifie chaque minute.
                self.state = "pause_jeu"
                self.message = f"Joue à {self.stream.get('game') or 'autre chose'} : pas {wanted}, en attente…"
                self._cleanup(all_files=False)
                if self._sleep(60):
                    break
                continue
            self.state, self.message = "direct", "En direct : surveillance du chat et du son"
            self._log(f"Live détecté ({self.stream.get('quality', '')}) : surveillance lancée", "ok")
            self._follow(url)
        self._cleanup(all_files=True)

    def _follow(self, url: str) -> None:
        last_seq = self.segments[-1]["seq"] if self.segments else -1
        failures = 0
        last_info = _now()
        inits: dict[str, Path] = {}
        while not self.stop_event.is_set():
            t0 = _now()
            try:
                pl = parse_live_playlist(self._get(url).decode("utf-8", "replace"), url)
                failures = 0
            except Exception:
                failures += 1
                if failures >= 4:
                    self._log("Flux interrompu : nouvelle connexion…", "warn")
                    return
                self._sleep(2)
                continue
            for seg in pl["segments"]:
                if seg["seq"] <= last_seq:
                    continue
                last_seq = seg["seq"]
                if seg["ad"]:
                    if not self.stream.get("in_ad"):
                        self._log("Pub Twitch en cours : ignorée", "info")
                    self.stream["in_ad"] = True
                    continue
                self.stream["in_ad"] = False
                init_path = None
                try:
                    if seg["init"]:
                        if seg["init"] not in inits:
                            init_path = self.dir / f"init_{len(inits)}.mp4"
                            init_path.write_bytes(self._get(seg["init"]))
                            inits[seg["init"]] = init_path
                        init_path = inits[seg["init"]]
                    data = self._get(seg["url"])
                except Exception:
                    continue
                path = self.dir / f"seg_{seg['seq']:09d}.{'m4s' if init_path else 'ts'}"
                path.write_bytes(data)
                pdt = seg["pdt"] if seg["pdt"] is not None else (
                    (self.segments[-1]["pdt"] + self.segments[-1]["dur"]) if self.segments else _now() - self.latency)
                with self.lock:
                    self.segments.append({"seq": seg["seq"], "pdt": pdt, "dur": seg["dur"], "path": path,
                                          "init": init_path})
                self.latency = max(0.5, _now() - (pdt + seg["dur"]))
            self._cleanup()
            if pl["ended"]:
                self._log("Le live est terminé", "info")
                return
            if _now() - last_info > 60:  # titre, jeu et viewers à jour
                info = self._stream_info()
                if info:
                    self.stream.update(info)
                    if not info.get("live"):
                        return
                    if not game_matches(info.get("game"), self._wanted_game()):
                        self._log(f"Le streamer est passé sur {info.get('game')} : pause", "info")
                        return
                last_info = _now()
            self._sleep(max(0.5, min(2.0, pl["target"] / 2) - (_now() - t0)))

    def _cleanup(self, all_files: bool = False) -> None:
        limit = _now() - BUFFER_SECONDS
        with self.lock:
            while self.segments and (all_files or self.segments[0]["pdt"] < limit - self.latency):
                seg = self.segments.popleft()
                seg["path"].unlink(missing_ok=True)
            while self.audio and self.audio[0][0] < limit - 60:
                self.audio.popleft()
            while self.chat and self.chat[0][0] < limit - 60:
                self.chat.popleft()
        if all_files and self.dir.exists():
            shutil.rmtree(self.dir, ignore_errors=True)

    # -- chat ------------------------------------------------------------------
    def _chat_loop(self) -> None:
        from websockets.sync.client import connect

        backoff = 2
        while not self.stop_event.is_set():
            try:
                with connect("wss://irc-ws.chat.twitch.tv:443", open_timeout=15, close_timeout=2) as ws:
                    ws.send(f"NICK justinfan{random.randint(10000, 99999)}")
                    ws.send(f"JOIN #{self.channel}")
                    backoff = 2
                    while not self.stop_event.is_set():
                        try:
                            data = ws.recv(timeout=5)
                        except TimeoutError:
                            continue
                        now = _now()
                        for line in str(data).split("\r\n"):
                            if line.startswith("PING"):
                                ws.send("PONG :tmi.twitch.tv")
                            elif " PRIVMSG " in line:
                                text = line.split(" :", 2)[-1] if line.startswith(":") else line.split(" :", 1)[-1]
                                with self.lock:
                                    self.chat.append((now, chat_weight(text)))
            except Exception:
                if self._sleep(backoff):
                    break
                backoff = min(60, backoff * 2)

    # -- analyse et détection ----------------------------------------------------
    def _analyze_loop(self) -> None:
        while not self._sleep(3):
            try:
                self._analyze_audio()
                self._detect()
            except Exception as exc:  # une erreur d'analyse ne doit pas arrêter la surveillance
                self._log(f"Analyse : {str(exc)[:120]}", "warn")

    @staticmethod
    def _assemble(segs: list[dict], dest: Path) -> tuple[Path, list[dict]] | None:
        """Recolle des segments consécutifs en un fichier lisible (en-tête fMP4 + fragments, ou TS)."""
        if not segs:
            return None
        init = segs[0].get("init")
        segs = [s for s in segs if s.get("init") == init and s["path"].exists()]
        if not segs:
            return None
        dest = dest.with_suffix(".mp4" if init else ".ts")
        with dest.open("wb") as out:
            if init and init.exists():
                out.write(init.read_bytes())
            for s in segs:
                out.write(s["path"].read_bytes())
        return dest, segs

    def _analyze_audio(self) -> None:
        with self.lock:
            todo = [s for s in self.segments if s["seq"] > self._analyzed_seq]
        if not todo:
            return
        self._analyzed_seq = todo[-1]["seq"]
        built = self._assemble(todo, self.dir / "analyse")
        if not built:
            return
        tmp, todo = built
        proc = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-v", "error", "-i", str(tmp), "-vn", "-ac", "1",
             "-ar", "8000", "-f", "s16le", "-"],
            capture_output=True, creationflags=_NO_WINDOW,
        )
        tmp.unlink(missing_ok=True)
        if proc.returncode != 0 or not proc.stdout:
            return
        audio = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        hop = 4000
        n = len(audio) // hop
        if n == 0:
            return
        db = 20 * np.log10(np.sqrt(np.mean(audio[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-10))
        t0 = todo[0]["pdt"]
        with self.lock:
            for i, v in enumerate(db):
                self.audio.append((t0 + i * 0.5, float(v)))

    def _series(self, t_from: float, t_to: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
        """Temps (contenu du live), score du chat et score du son, toutes les 0,5 s."""
        times = np.arange(t_from, t_to, 0.5)
        with self.lock:
            audio = list(self.audio)
            chat = list(self.chat)
        # Chat : heure de réception → moment du live qui l'a provoqué.
        shift = self.latency + REACTION_DELAY
        ct = np.array([c[0] - shift for c in chat]) if chat else np.zeros(0)
        cw = np.array([c[1] for c in chat]) if chat else np.zeros(0)
        rate = np.zeros(len(times))
        for i, t in enumerate(times):
            m = (ct >= t - 2.5) & (ct < t + 2.5)
            rate[i] = cw[m].sum() / 5.0 if len(ct) else 0.0
        self.chat_rate = float(rate[-10:].mean()) if len(rate) else 0.0
        if audio:
            at = np.array([a[0] for a in audio])
            ad = np.convolve(np.array([a[1] for a in audio]), np.ones(4) / 4, mode="same")
            db = np.interp(times, at, ad, left=np.nan, right=np.nan)
        else:
            db = np.full(len(times), np.nan)
        chat_active = float(np.median(rate)) >= 0.3 if len(rate) else False
        med_rate = float(np.median(rate)) if len(rate) else 0.0
        chat_score = (rate - med_rate) / max(0.5, med_rate * 0.6)
        valid = db[~np.isnan(db)]
        med_db = float(np.median(valid)) if len(valid) else -40.0
        audio_score = np.nan_to_num((db - med_db) / 4.0, nan=0.0)
        return times, chat_score, audio_score, chat_active

    def _detect(self) -> None:
        with self.lock:
            if len(self.segments) < 5:
                return
            buf_start = self.segments[0]["pdt"]
            buf_end = self.segments[-1]["pdt"] + self.segments[-1]["dur"]
        # On n'évalue que les moments dont la réaction du chat est déjà arrivée.
        horizon = min(buf_end, _now() - self.latency - REACTION_DELAY - 2.5)
        t_from = max(buf_start, horizon - 180)
        if horizon - t_from < 20:
            return
        times, chat_s, audio_s, chat_active = self._series(t_from, horizon)
        score = (0.65 * np.clip(chat_s, -2, 8) + 0.35 * np.clip(audio_s, -2, 8)) if chat_active else np.clip(audio_s, -2, 8)
        self.score = float(score[-6:].max()) if len(score) else 0.0
        thr = SENSITIVITY.get(self.options.get("sensitivity", "normale"), 2.2)
        self.stream["threshold"] = thr
        length = self._length()
        cooldown = max(45.0, length)
        recent = times > max(self._last_eval, horizon - 12)
        self._last_eval = horizon
        if self._pending:
            p = self._pending
            above = recent & (score >= thr)
            if above.any():
                i = int(np.argmax(np.where(recent, score, -99)))
                if score[i] > p["score"]:
                    p.update(peak=float(times[i]), score=float(score[i]))
            if not above.any() or horizon - p["since"] > 10:
                self._pending = None
                self._schedule_clip(p["peak"], p["score"], "auto")
            return
        if not recent.any():
            return
        cand = np.where(recent & (score >= thr))[0]
        if len(cand) and times[cand[0]] - self._last_peak >= cooldown and self._clips_last_hour() < self._max_per_hour():
            i = int(cand[np.argmax(score[cand])])
            self._pending = {"peak": float(times[i]), "score": float(score[i]), "since": horizon}

    def _wanted_game(self) -> str:
        if "game" in self.options:
            return self.options.get("game") or ""
        return load_settings().get("game_filter", "")

    def _length(self) -> float:
        settings = load_settings()
        return clip_seconds(settings, self.options.get("length") or settings.get("clip_length"))

    def _max_per_hour(self) -> int:
        return int(self.options.get("max_per_hour") or 12)

    def _clips_last_hour(self) -> int:
        return sum(1 for c in self.clips if c["t"] > _now() - 3600 and c["reason"] != "manuel")

    # -- création des clips ------------------------------------------------------
    def clip_now(self) -> bool:
        """Garde les dernières secondes du live (comme le bouton clip de Twitch)."""
        with self.lock:
            if not self.segments:
                return False
            end = self.segments[-1]["pdt"] + self.segments[-1]["dur"]
        length = self._length()
        self._start_cut(end - length, end, "manuel", 0.0)
        return True

    def _schedule_clip(self, peak: float, score: float, reason: str) -> None:
        length = self._length()
        start = peak - length * 0.65  # la montée avant le moment, puis la réaction
        end = start + length
        self._last_peak = peak
        self._log(f"Moment fort détecté (score {score:.1f}) : clip en préparation", "ok")

        def wait_and_cut() -> None:
            # On attend que la fin du moment soit dans la mémoire tampon.
            for _ in range(120):
                with self.lock:
                    have = self.segments[-1]["pdt"] + self.segments[-1]["dur"] if self.segments else 0
                if have >= end + 1 or self.stop_event.is_set():
                    break
                time.sleep(1)
            self._cut(start, end, reason, score)

        threading.Thread(target=wait_and_cut, daemon=True).start()

    def _start_cut(self, start: float, end: float, reason: str, score: float) -> None:
        threading.Thread(target=self._cut, args=(start, end, reason, score), daemon=True).start()

    def _cut(self, start: float, end: float, reason: str, score: float) -> None:
        from . import pipeline, projects

        with self.lock:
            segs = [s for s in self.segments if s["pdt"] + s["dur"] > start - 0.5 and s["pdt"] < end + 0.5]
        if not segs:
            self._log("Clip impossible : le moment n'est plus en mémoire", "warn")
            return
        start = max(start, segs[0]["pdt"])
        end = min(end, segs[-1]["pdt"] + segs[-1]["dur"])
        when = datetime.fromtimestamp(start).strftime("%H:%M")
        display = self.stream.get("display") or self.channel
        origin = {
            "channel": display, "login": self.channel, "source": "twitch", "live": True,
            "url": f"https://www.twitch.tv/{self.channel}", "game": self.stream.get("game"),
            "language": self.stream.get("language"), "stream_title": self.stream.get("title"),
            "live_reason": reason, "live_score": round(score, 1),
        }
        project = projects.new_project(f"{display} – live {when}", origin)
        d = projects.project_dir(project["id"])
        built = self._assemble(segs, d / "live")
        if not built:
            projects.delete(project["id"])
            self._log("Clip impossible : le moment n'est plus en mémoire", "warn")
            return
        raw, segs = built
        start = max(start, segs[0]["pdt"])
        end = min(end, segs[-1]["pdt"] + segs[-1]["dur"])
        res = run([
            ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-ss", f"{start - segs[0]['pdt']:.3f}", "-i", str(raw),
            "-t", f"{end - start:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(d / "source.mp4"),
        ])
        raw.unlink(missing_ok=True)
        if res.returncode != 0:
            projects.delete(project["id"])
            err = res.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] if res.stderr else []
            self._log(f"Clip impossible : erreur pendant le découpage {' '.join(err)[:160]}", "warn")
            return
        try:
            projects.finalize_source(project["id"], "source.mp4")
        except Exception as exc:
            self._log(f"Clip créé mais analyse impossible : {exc}", "warn")
        label = {"auto": "moment fort", "manuel": "clip manuel"}.get(reason, reason)
        self.clips.insert(0, {"t": _now(), "id": project["id"], "reason": reason, "score": round(score, 1),
                              "duration": round(end - start, 1)})
        self._log(f"Clip créé ({label}, {end - start:.0f} s)", "ok")
        if self.options.get("auto"):
            settings = load_settings()
            pipeline.start_auto_chain(project["id"], self.options.get("formats") or settings.get("default_formats"))

    # -- état pour l'interface ---------------------------------------------------------
    def status(self) -> dict:
        with self.lock:
            buffered = (self.segments[-1]["pdt"] + self.segments[-1]["dur"] - self.segments[0]["pdt"]) if self.segments else 0
            chat_per_min = sum(1 for c in self.chat if c[0] > _now() - 60)
        return {
            "channel": self.channel,
            "state": self.state,
            "message": self.message,
            "options": self.options,
            "stream": {k: v for k, v in self.stream.items()},
            "latency": round(self.latency, 1),
            "buffered": round(buffered),
            "chat_per_min": chat_per_min,
            "score": round(self.score, 2),
            "threshold": SENSITIVITY.get(self.options.get("sensitivity", "normale"), 2.2),
            "clips": self.clips[:20],
            "events": list(self.events)[:12],
            "started": self.started,
        }


class LiveManager:
    def __init__(self) -> None:
        self.watchers: dict[str, LiveWatcher] = {}
        self.lock = threading.Lock()

    def _save(self) -> None:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        data = {"watchers": [{"channel": w.channel, "options": w.options} for w in self.watchers.values()]}
        STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

    def start(self, channel: str, options: dict) -> LiveWatcher:
        with self.lock:
            old = self.watchers.pop(channel, None)
            if old:
                old.stop()
            w = LiveWatcher(channel, options)
            self.watchers[channel] = w
            w.start()
            self._save()
            return w

    def stop(self, channel: str) -> bool:
        with self.lock:
            w = self.watchers.pop(channel, None)
            if w:
                w.stop()
            self._save()
            return w is not None

    def get(self, channel: str) -> LiveWatcher | None:
        return self.watchers.get(channel)

    def list(self) -> list[dict]:
        return [w.status() for w in self.watchers.values()]

    def restore(self) -> None:
        """Reprend la surveillance des chaînes après un redémarrage de l'appli.

        Au tout premier lancement, on surveille les streamers favoris des réglages (OhnePixel par défaut).
        """
        if not STATE_FILE.exists():
            for channel in load_settings().get("favorite_streamers", []):
                if re.fullmatch(r"[a-z0-9_]{2,25}", channel or ""):
                    self.start(channel, {})
            return
        try:
            data = json.loads(STATE_FILE.read_text("utf-8"))
        except (OSError, ValueError):
            return
        for item in data.get("watchers", []):
            if item.get("channel"):
                self.start(item["channel"], item.get("options") or {})


manager = LiveManager()
