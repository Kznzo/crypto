"""Récupération des vidéos avec yt-dlp : clips et VOD Twitch, YouTube Shorts."""
from __future__ import annotations

import functools
import re
import shutil
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlparse

from .ffmpeg_utils import ffmpeg_path

CHANNEL_RE = re.compile(r"^[A-Za-z0-9_]{2,25}$")
YT_HANDLE_RE = re.compile(r"^@[\w.\-]{3,30}$")
YT_CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
PERIODS = {"24h": "24hr", "7j": "7d", "30j": "30d", "tout": "all"}
SOURCES = {"twitch": "Twitch", "youtube": "YouTube"}
MAX_YOUTUBE_SECONDS = 20 * 60  # au-delà, ce n'est plus un Short à remonter


class DownloadError(RuntimeError):
    pass


def source_of(url: str) -> str:
    """« twitch », « youtube » ou « autre » selon le lien."""
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    if host.endswith("twitch.tv"):
        return "twitch"
    if host.endswith(("youtube.com", "youtu.be")):
        return "youtube"
    return "autre"


def channel_url(source: str, login: str) -> str:
    if source == "youtube":
        return f"youtube.com/{login}"
    return f"twitch.tv/{login}"


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
    """Nom de chaîne Twitch (« zerator ») ou YouTube (« @MrBeast » ou « channel/UC… »)."""
    value = (value or "").strip()
    if source == "youtube":
        if "youtube.com" in value:
            path = urlparse(value if "://" in value else "https://" + value).path.strip("/").split("/")
            value = "/".join(path[:2]) if path and path[0] in ("channel", "c", "user") else (path[0] if path else "")
        if value.startswith("channel/") and YT_CHANNEL_ID_RE.match(value[8:]):
            return value
        if YT_CHANNEL_ID_RE.match(value):
            return f"channel/{value}"
        if value.startswith(("c/", "user/")) and re.match(r"^[\w.\-]{2,40}$", value.split("/", 1)[1]):
            return value
        handle = value if value.startswith("@") else f"@{value}"
        if not YT_HANDLE_RE.match(handle):
            raise DownloadError("Nom de chaîne YouTube invalide (exemple : @MrBeast).")
        return handle
    if "twitch.tv" in value:
        path = urlparse(value if "://" in value else "https://" + value).path.strip("/")
        value = path.split("/")[0] if path else ""
    value = value.lstrip("@")
    if not CHANNEL_RE.match(value):
        raise DownloadError("Nom de chaîne Twitch invalide.")
    return value.lower()


def is_vod_url(url: str) -> bool:
    return bool(re.search(r"twitch\.tv/(?:videos|[^/]+/v(?:ideo)?)/\d+", url))


def vod_start_from_url(url: str) -> float | None:
    q = parse_qs(urlparse(url).query)
    if "t" in q:
        return parse_time(q["t"][0])
    return None


@functools.lru_cache(maxsize=1)
def deno_path() -> str | None:
    """Moteur JavaScript dont yt-dlp a besoin pour YouTube (installé avec « pip install deno »)."""
    try:
        import deno

        path = deno.find_deno_bin()
        if path and Path(path).exists():
            return str(path)
    except Exception:
        pass
    return shutil.which("deno")


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

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "ffmpeg_location": ffmpeg_path(),
        "retries": 3,
        "socket_timeout": 30,
    }
    deno = deno_path()
    if deno:
        opts["js_runtimes"] = {"deno": {"path": deno}}
    return opts


HASHTAG_RE = re.compile(r"#([^\s#.,!?;:]+)")


def clean_title(title: str) -> str:
    """Retire les #hashtags d'un titre (« Trap Door Roulette #shorts » → « Trap Door Roulette »)."""
    return re.sub(r"\s{2,}", " ", HASHTAG_RE.sub("", title or "")).strip(" -|")


def _meta(info: dict, url: str = "") -> dict:
    source = source_of(info.get("webpage_url") or url)
    channel = info.get("creator") or info.get("channel") or info.get("uploader") or ""
    categories = info.get("categories") or []
    raw_title = (info.get("title") or "Clip").strip()
    if source == "youtube":
        login = info.get("uploader_id") or (f"channel/{info['channel_id']}" if info.get("channel_id") else "")
        # Hashtags déjà utilisés par le créateur du Short (titre, description, tags).
        found = HASHTAG_RE.findall(f"{raw_title} {info.get('description') or ''}")
        found += [t.replace(" ", "") for t in (info.get("tags") or [])]
        tags = []
        for t in found:
            t = t.lower()
            if t not in ("shorts", "short", "youtube", "youtubeshorts") and t not in tags and 2 <= len(t) <= 30:
                tags.append(t)
        title = clean_title(raw_title) or raw_title
        game = None  # les catégories YouTube (« Gaming », « Entertainment ») ne sont pas des jeux
    else:
        login = re.sub(r"[^a-z0-9_]", "", channel.lower())
        tags = []
        title = raw_title
        game = categories[0] if categories else None
    return {
        "title": title,
        "channel": channel,
        "login": login or None,
        "source": source,
        "duration": info.get("duration"),
        "url": info.get("webpage_url") or info.get("original_url"),
        "views": info.get("view_count"),
        "thumbnail": info.get("thumbnail"),
        "game": game,
        "language": (info.get("language") or "").lower()[:2] or None,
        "tags": tags[:5],
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
    """Utilise la session Twitch / YouTube d'un navigateur (VOD abonnés, contrôle « pas un robot »)."""
    if cookies_browser in COOKIE_BROWSERS:
        opts["cookiesfrombrowser"] = (cookies_browser,)
    return opts


FORMATS = {
    # Twitch : version paysage d'origine (on évite les formats « portrait » recadrés par Twitch).
    "twitch": "best[height<=?1080][format_id!^=portrait]/bestvideo[height<=?1080]+bestaudio/best[height<=?1080]/best",
    # YouTube : vidéo et son séparés, H.264 de préférence (aperçu lisible partout), 1080 de large max
    # (un Short vertical fait 1080 × 1920).
    "youtube": "bv*[vcodec^=avc1][height<=?1920][width<=?1920]+ba[ext=m4a]/bv*[height<=?1920][width<=?1920]+ba/b",
}


def download_clip(
    url: str,
    dest_dir: Path,
    on_progress: Callable[[float, str], None] | None = None,
    cookies_browser: str | None = None,
) -> tuple[str, dict]:
    import yt_dlp

    source = source_of(url)
    opts = _with_cookies(_base_opts(on_progress), cookies_browser)
    opts.update({
        "format": FORMATS.get(source, FORMATS["twitch"]),
        "merge_output_format": "mp4",
        "outtmpl": {"default": str(dest_dir / "source.%(ext)s")},
    })
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            if source == "youtube":
                info = ydl.extract_info(url, download=False)
                if (info.get("duration") or 0) > MAX_YOUTUBE_SECONDS:
                    raise DownloadError(
                        "cette vidéo YouTube dure plus de 20 minutes. ClipForge sert à remonter des Shorts "
                        "et des vidéos courtes : télécharge-la puis envoie seulement le passage voulu (onglet « Fichier vidéo »)."
                    )
                info = ydl.process_ie_result(info, download=True)
            else:
                info = ydl.extract_info(url, download=True)
            extra = _twitch_extra(ydl, url)
    except DownloadError as exc:
        raise DownloadError(f"Téléchargement impossible : {exc}") from exc
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
    """Télécharge seulement un passage d'une VOD Twitch (ex. de 1:20:00 à 1:30:00).

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
    """Télécharge un morceau HLS avec les en-têtes HTTP du format."""
    from yt_dlp.networking import Request

    return ydl.urlopen(Request(url, headers=dict(fmt.get("http_headers") or {}))).read()


def channel_clips(channel: str, period: str = "7j", limit: int = 30, source: str = "twitch") -> list[dict]:
    """Clips les plus vus d'une chaîne Twitch (sur une période) ou Shorts les plus vus d'une chaîne YouTube."""
    import yt_dlp

    name = normalize_channel(channel, source)
    if source == "youtube":
        # YouTube ne permet pas de filtrer par date : on prend les derniers Shorts et on trie par vues.
        url = f"https://www.youtube.com/{name}/shorts"
        fetch = limit * 2
    else:
        url = f"https://www.twitch.tv/{name}/clips?filter=clips&range={PERIODS.get(period, '7d')}"
        fetch = limit
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "playlistend": fetch}
    deno = deno_path()
    if deno:
        opts["js_runtimes"] = {"deno": {"path": deno}}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise DownloadError(f"Impossible de lister les vidéos : {_short_error(exc)}") from exc
    owner = (info or {}).get("channel") or (info or {}).get("uploader") or name
    out = []
    for e in (info or {}).get("entries", [])[:fetch]:
        if not e or not e.get("url"):
            continue
        thumb = e.get("thumbnail")
        if not thumb and e.get("thumbnails"):
            thumb = e["thumbnails"][-1].get("url")
        out.append({
            "url": e["url"],
            "title": (clean_title(e.get("title") or "") if source == "youtube" else e.get("title")) or "Clip",
            "duration": e.get("duration"),
            "views": e.get("view_count"),
            "thumbnail": thumb,
            "timestamp": e.get("timestamp"),
            "channel": e.get("channel") or (owner if source == "youtube" else name),
            "game": (e.get("categories") or [None])[0] if source == "twitch" else None,
            "source": source,
        })
    out.sort(key=lambda c: -(c.get("views") or 0))
    return out[:limit]


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
    (r"not a bot|confirm your age|Sign in to confirm",
     "YouTube demande de se connecter (contrôle anti-robots ou vidéo pour adultes). Dans Réglages → "
     "« Compte Twitch / YouTube », choisis le navigateur où tu es connecté à YouTube, puis réessaie."),
    (r"JavaScript runtime|\bdeno\b|n challenge|signature",
     "YouTube a besoin du module « deno ». Relance le lanceur ClipForge (il l'installe) ou tape « pip install deno »."),
    (r"subscriber-only|members-only|must be logged",
     "cette vidéo est réservée aux abonnés / membres. Si tu l'es, choisis ton navigateur dans Réglages → "
     "« Compte Twitch / YouTube » (en étant connecté dedans), puis réessaie."),
    (r"could not (?:find|copy|decrypt).*cookie|cookie.*(?:database|decrypt)",
     "impossible de lire la connexion du navigateur choisi. Ferme-le et réessaie, ou choisis Firefox dans les Réglages."),
    (r"Private video|Video unavailable|does not exist|404|not found|Unable to find",
     "vidéo introuvable ou privée : vérifie le lien (elle a peut-être été supprimée)."),
    (r"Unsupported URL", "ce lien n'est pas reconnu. Colle le lien d'un clip Twitch, d'une VOD Twitch ou d'un YouTube Short."),
    (r"HTTP Error 403|Forbidden",
     "accès refusé par le site (protection anti-robots). Réessaie dans un instant ; si ça continue avec YouTube, "
     "choisis le navigateur où tu es connecté à YouTube dans Réglages → « Compte Twitch / YouTube »."),
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
