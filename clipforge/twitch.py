"""Récupération des vidéos Twitch et Kick avec yt-dlp (clips, extraits de VOD, clips populaires d'une chaîne)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlparse

from .ffmpeg_utils import ffmpeg_path

CHANNEL_RE = re.compile(r"^[A-Za-z0-9_]{2,25}$")
KICK_CHANNEL_RE = re.compile(r"^[A-Za-z0-9_-]{2,40}$")
PERIODS = {"24h": "24hr", "7j": "7d", "30j": "30d", "tout": "all"}
KICK_PERIODS = {"24h": "day", "7j": "week", "30j": "month", "tout": "all"}
SOURCES = {"twitch": "Twitch", "kick": "Kick"}


def source_of(url: str) -> str:
    """« twitch », « kick » ou « autre » selon le lien."""
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    if host.endswith("kick.com"):
        return "kick"
    if host.endswith("twitch.tv"):
        return "twitch"
    return "autre"


def channel_url(source: str, login: str) -> str:
    return f"kick.com/{login}" if source == "kick" else f"twitch.tv/{login}"


class DownloadError(RuntimeError):
    pass


def parse_time(value: str | float | int | None) -> float | None:
    """Accepte « 1:23:45 », « 83:20 », « 5000 », « 1h23m45s »."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower().replace(" ", "")
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m(?:in)?)?(?:(\d+(?:\.\d+)?)s?)?", s)
    if m and any(m.groups()) and not re.fullmatch(r"\d+(?:\.\d+)?", s):
        h, mi, se = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)
    parts = s.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    total = 0.0
    for n in nums:
        total = total * 60 + n
    return total


def normalize_channel(value: str, source: str = "twitch") -> str:
    value = (value or "").strip()
    if "twitch.tv" in value or "kick.com" in value:
        path = urlparse(value if "://" in value else "https://" + value).path.strip("/")
        value = path.split("/")[0] if path else ""
    value = value.lstrip("@")
    pattern = KICK_CHANNEL_RE if source == "kick" else CHANNEL_RE
    if not pattern.match(value):
        raise DownloadError(f"Nom de chaîne {SOURCES.get(source, 'Twitch')} invalide.")
    return value.lower()


def is_vod_url(url: str) -> bool:
    return bool(
        re.search(r"twitch\.tv/(?:videos|[^/]+/v(?:ideo)?)/\d+", url)
        or re.search(r"kick\.com/[\w-]+/videos/[\da-f]{8}-", url)
    )


def vod_start_from_url(url: str) -> float | None:
    q = parse_qs(urlparse(url).query)
    if "t" in q:
        return parse_time(q["t"][0])
    return None


def _base_opts(on_progress: Callable[[float, str], None] | None) -> dict:
    def hook(d: dict) -> None:
        if not on_progress:
            return
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            frac = (done / total) if total else 0.0
            on_progress(min(0.99, frac), "Téléchargement…")
        elif d.get("status") == "finished":
            on_progress(0.99, "Téléchargement terminé")

    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "ffmpeg_location": ffmpeg_path(),
        "retries": 3,
        "socket_timeout": 30,
    }


def _meta(info: dict, url: str = "") -> dict:
    channel = info.get("creator") or info.get("channel") or info.get("uploader") or ""
    categories = info.get("categories") or []
    source = source_of(info.get("webpage_url") or url)
    if source == "kick":
        login = (info.get("uploader_id") or channel).lower()
    else:
        login = re.sub(r"[^a-z0-9_]", "", channel.lower())
    return {
        "title": (info.get("title") or "Clip").strip(),
        "channel": channel,
        "login": login or None,
        "source": source,
        "duration": info.get("duration"),
        "url": info.get("webpage_url") or info.get("original_url"),
        "views": info.get("view_count"),
        "thumbnail": info.get("thumbnail"),
        "game": categories[0] if categories else None,
        "language": (info.get("language") or "").lower()[:2] or None,
    }


GQL_URL = "https://gql.twitch.tv/gql"
GQL_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # identifiant public du site twitch.tv


def _twitch_extra(ydl, url: str) -> dict:
    """Langue et jeu depuis l'API publique de Twitch (au mieux : on ignore toute erreur)."""
    import json

    from yt_dlp.networking import Request

    if source_of(url) != "twitch":
        return {}
    clip = re.search(r"(?:clips\.twitch\.tv/|/clip/)([A-Za-z0-9_-]+)", url)
    video = re.search(r"/videos?/(\d+)", url)
    if clip:
        query = 'query{clip(slug:"%s"){language game{name}}}' % clip.group(1)
    elif video:
        query = 'query{video(id:"%s"){game{name} owner{broadcastSettings{language}}}}' % video.group(1)
    else:
        return {}
    try:
        req = Request(GQL_URL, data=json.dumps({"query": query}).encode(),
                      headers={"Client-Id": GQL_CLIENT_ID, "Content-Type": "application/json"})
        data = json.loads(ydl.urlopen(req).read().decode("utf-8")).get("data") or {}
    except Exception:
        return {}
    node = data.get("clip") or data.get("video") or {}
    lang = node.get("language") or ((node.get("owner") or {}).get("broadcastSettings") or {}).get("language")
    game = (node.get("game") or {}).get("name")
    return {k: v for k, v in {"language": (lang or "").lower()[:2] or None, "game": game}.items() if v}


COOKIE_BROWSERS = ("firefox", "chrome", "edge", "brave", "opera", "vivaldi", "chromium", "safari")


def _with_cookies(opts: dict, cookies_browser: str | None) -> dict:
    """Utilise la session Twitch / Kick d'un navigateur (pour les VOD réservées aux abonnés)."""
    if cookies_browser in COOKIE_BROWSERS:
        opts["cookiesfrombrowser"] = (cookies_browser,)
    return opts


def download_clip(
    url: str,
    dest_dir: Path,
    on_progress: Callable[[float, str], None] | None = None,
    cookies_browser: str | None = None,
) -> tuple[str, dict]:
    import yt_dlp

    opts = _with_cookies(_base_opts(on_progress), cookies_browser)
    opts.update({
        # Version paysage d'origine (on évite les formats « portrait » recadrés par Twitch).
        # « <=? » accepte aussi les formats sans hauteur connue (clips Kick).
        "format": "best[height<=?1080][format_id!^=portrait]/bestvideo[height<=?1080]+bestaudio/best[height<=?1080]/best",
        "merge_output_format": "mp4",
        "outtmpl": {"default": str(dest_dir / "source.%(ext)s")},
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            extra = _twitch_extra(ydl, url)
    except Exception as exc:
        raise DownloadError(f"Téléchargement impossible : {_short_error(exc)}") from exc
    file = _find_source(dest_dir)
    meta = _meta(info, url)
    meta.update({k: v for k, v in extra.items() if not meta.get(k)})
    return file, meta


def parse_media_playlist(text: str, base_url: str) -> tuple[str | None, list[tuple[float, float, str]]]:
    """Lit une playlist HLS : renvoie l'URL d'initialisation éventuelle et les segments (début, fin, url)."""
    init = None
    segments: list[tuple[float, float, str]] = []
    t = 0.0
    pending: float | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-MAP:"):
            m = re.search(r'URI="([^"]+)"', line)
            if m:
                init = urljoin(base_url, m.group(1))
        elif line.startswith("#EXTINF:"):
            try:
                pending = float(line[8:].split(",")[0])
            except ValueError:
                pending = 0.0
        elif not line.startswith("#") and pending is not None:
            segments.append((t, t + pending, urljoin(base_url, line)))
            t += pending
            pending = None
    return init, segments


def download_section(
    url: str,
    start: float,
    end: float,
    dest_dir: Path,
    on_progress: Callable[[float, str], None] | None = None,
    cookies_browser: str | None = None,
) -> tuple[str, dict]:
    """Télécharge seulement un passage d'une VOD (ex. de 1:20:00 à 1:30:00).

    On lit la playlist HLS de la VOD et on ne récupère que les morceaux nécessaires,
    puis FFmpeg recoupe précisément sans réencoder.
    """
    import yt_dlp

    from .ffmpeg_utils import run

    if end <= start:
        raise DownloadError("La fin de l'extrait doit être après le début.")
    if end - start > 3 * 3600:
        raise DownloadError("Extrait trop long (3 h maximum).")
    if on_progress:
        on_progress(0.02, "Lecture des infos de la VOD…")
    opts = _with_cookies({"quiet": True, "no_warnings": True, "noplaylist": True,
                          "format": "best[height<=?1080][protocol^=m3u8]/best[height<=?1080]/best"}, cookies_browser)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            fmt = (info.get("requested_formats") or [info])[0]
            playlist_url = fmt.get("url")
            if not playlist_url or "m3u8" not in (fmt.get("protocol") or "") and ".m3u8" not in playlist_url:
                raise DownloadError("Format de VOD inattendu.")
            extra = _twitch_extra(ydl, url)
            text = _fetch(ydl, playlist_url, fmt).decode("utf-8", "replace")
            init, segments = parse_media_playlist(text, playlist_url)
            wanted = [s for s in segments if s[1] > start - 0.5 and s[0] < end + 0.5]
            if not wanted:
                total = segments[-1][1] if segments else 0
                raise DownloadError(f"Ce passage dépasse la durée de la VOD ({int(total // 3600)} h {int(total % 3600 // 60):02d}).")
            ext = ".mp4" if init or wanted[0][2].split("?")[0].endswith((".mp4", ".m4s")) else ".ts"
            raw = dest_dir / f"morceaux{ext}"
            with raw.open("wb") as out:
                if init:
                    out.write(_fetch(ydl, init, fmt))
                for i, (_, _, seg_url) in enumerate(wanted):
                    for attempt in range(3):
                        try:
                            out.write(_fetch(ydl, seg_url, fmt))
                            break
                        except Exception:
                            if attempt == 2:
                                raise
                    if on_progress:
                        on_progress(0.05 + 0.9 * (i + 1) / len(wanted), f"Téléchargement de la VOD… {i + 1}/{len(wanted)}")
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"Téléchargement impossible : {_short_error(exc)}") from exc

    offset = max(0.0, start - wanted[0][0])
    final = dest_dir / "source.mp4"
    res = run([
        ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-ss", f"{offset:.3f}", "-i", str(raw),
        "-t", f"{end - start:.3f}", "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy",
        "-avoid_negative_ts", "make_zero", "-movflags", "+faststart", str(final),
    ])
    if res.returncode != 0 or not final.exists() or final.stat().st_size < 1000:
        # Plan B : on réencode (plus lent mais toujours lisible).
        res = run([
            ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-ss", f"{offset:.3f}", "-i", str(raw),
            "-t", f"{end - start:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final),
        ])
        if res.returncode != 0:
            raise DownloadError("Impossible d'assembler le passage de la VOD.")
    raw.unlink(missing_ok=True)
    meta = _meta(info, url)
    meta.update({k: v for k, v in extra.items() if not meta.get(k)})
    meta["vod_range"] = [start, end]
    return final.name, meta


def _fetch(ydl, url: str, fmt: dict) -> bytes:
    """Télécharge un morceau HLS avec les en-têtes du format (et l'imitation de navigateur pour Kick)."""
    from yt_dlp.networking import Request

    headers = dict(fmt.get("http_headers") or {})
    extensions = {}
    if fmt.get("impersonate") or "kick.com" in url:
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget

            extensions["impersonate"] = ImpersonateTarget("chrome")
        except Exception:
            pass
    try:
        return ydl.urlopen(Request(url, headers=headers, extensions=extensions)).read()
    except Exception:
        if not extensions:
            raise
        return ydl.urlopen(Request(url, headers=headers)).read()


def channel_clips(channel: str, period: str = "7j", limit: int = 30, source: str = "twitch") -> list[dict]:
    """Liste les clips les plus vus d'une chaîne Twitch ou Kick sur une période."""
    import yt_dlp

    name = normalize_channel(channel, source)
    if source == "kick":
        url = f"https://kick.com/{name}/clips?sort=view&range={KICK_PERIODS.get(period, 'week')}"
    else:
        url = f"https://www.twitch.tv/{name}/clips?filter=clips&range={PERIODS.get(period, '7d')}"
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "playlistend": limit}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise DownloadError(f"Impossible de lister les clips : {_short_error(exc)}") from exc
    out = []
    for e in (info or {}).get("entries", [])[:limit]:
        if not e or not e.get("url"):
            continue
        out.append({
            "url": e["url"],
            "title": e.get("title") or "Clip",
            "duration": e.get("duration"),
            "views": e.get("view_count"),
            "thumbnail": e.get("thumbnail"),
            "timestamp": e.get("timestamp"),
            "channel": e.get("channel") or name,
            "game": (e.get("categories") or [None])[0],
            "source": source,
        })
    out.sort(key=lambda c: -(c.get("views") or 0))
    return out


def _find_source(dest_dir: Path) -> str:
    files = sorted(
        (f for f in dest_dir.glob("source.*") if f.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov", ".ts", ".flv")),
        key=lambda f: f.stat().st_size,
        reverse=True,
    )
    if not files:
        raise DownloadError("Le fichier vidéo n'a pas été trouvé après le téléchargement.")
    return files[0].name


_KNOWN_ERRORS = [
    (r"impersonat|curl.?cffi",
     "Kick bloque les téléchargements sans « imitation de navigateur ». Relance le lanceur ClipForge "
     "(il installe le module curl_cffi) ou tape « pip install curl_cffi »."),
    (r"subscriber-only|sub_only|must be logged",
     "cette vidéo est réservée aux abonnés. Si tu es abonné, choisis ton navigateur dans Réglages → "
     "« Compte Twitch / Kick » (en étant connecté dedans), puis réessaie."),
    (r"could not (?:find|copy|decrypt).*cookie|cookie.*(?:database|decrypt)",
     "impossible de lire la connexion du navigateur choisi. Ferme-le et réessaie, ou choisis Firefox dans les Réglages."),
    (r"does not exist|404|not found|Unable to find", "vidéo introuvable : vérifie le lien (le clip a peut-être été supprimé)."),
    (r"Unsupported URL", "ce lien n'est pas reconnu. Colle le lien d'un clip ou d'une VOD Twitch ou Kick."),
    (r"HTTP Error 403|Forbidden", "accès refusé par le site (protection anti-robots). Réessaie dans un instant."),
    (r"timed? ?out|Connection|getaddrinfo|Network", "problème de connexion Internet, réessaie dans un instant."),
    (r"geo|country", "cette vidéo n'est pas disponible dans ton pays."),
]


def _short_error(exc: Exception) -> str:
    msg = str(exc)
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)
    msg = msg.replace("ERROR: ", "")
    for pattern, french in _KNOWN_ERRORS:
        if re.search(pattern, msg, re.IGNORECASE):
            return french
    return msg[:300]
