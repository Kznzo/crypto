"""Serveur web local : l'interface s'ouvre sur le PC et sur la tablette (même Wi-Fi)."""
from __future__ import annotations

import copy
import io
import ipaddress
import re
import shutil
import socket
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, captions, pipeline, projects, twitch
from .analysis import clamp_rect
from .config import CAPTION_STYLES, FONTS_DIR, PLATFORMS, STATIC_DIR, TITLE_STYLES, load_settings, save_settings
from .ffmpeg_utils import available_hw_encoder
from .jobs import manager

app = FastAPI(title="ClipForge", version=__version__, docs_url=None, redoc_url=None)
PORT = 8765
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".ts"}


# ---------------------------------------------------------------------------
# Accès depuis la tablette : clé secrète (dans le QR code) obligatoire hors du PC.
# ---------------------------------------------------------------------------

def _is_local(request: Request) -> bool:
    host = request.client.host if request.client else ""
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host in ("localhost", "testclient")


@app.middleware("http")
async def access_guard(request: Request, call_next):
    if _is_local(request):
        return await call_next(request)
    key = load_settings()["access_key"]
    given = request.query_params.get("key")
    if given and given == key:
        response = await call_next(request)
        response.set_cookie("cf_key", key, max_age=3600 * 24 * 365, samesite="lax", httponly=True)
        return response
    if request.cookies.get("cf_key") == key:
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Accès refusé : scanne le QR code affiché sur le PC."}, status_code=401)
    return HTMLResponse(LOCKED_PAGE, status_code=401)


LOCKED_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ClipForge</title>
<style>body{font-family:system-ui,sans-serif;background:#0e0e12;color:#eee;display:grid;place-items:center;
min-height:100vh;margin:0;padding:24px;text-align:center}div{max-width:420px}h1{color:#a970ff}</style></head>
<body><div><h1>ClipForge</h1><p>Pour ouvrir ClipForge sur cet appareil, va sur le PC, clique sur
<b>« Tablette »</b> en haut de l'écran, puis scanne le QR code avec cet appareil.</p></div></body></html>"""


def lan_addresses() -> list[str]:
    ips: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith("127.")]


def tablet_url() -> str | None:
    ips = lan_addresses()
    if not ips:
        return None
    return f"http://{ips[0]}:{PORT}/?key={load_settings()['access_key']}"


# ---------------------------------------------------------------------------
# Pages et fichiers statiques
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/fonts", StaticFiles(directory=FONTS_DIR), name="fonts")


@app.get("/", include_in_schema=False)
def index(request: Request):
    if request.query_params.get("key"):
        # On retire la clé de l'adresse une fois le cookie posé.
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


# ---------------------------------------------------------------------------
# Infos & réglages
# ---------------------------------------------------------------------------

_hw = {"encoder": None, "checked": False}


def _check_hw() -> None:
    try:
        _hw["encoder"] = available_hw_encoder()
    finally:
        _hw["checked"] = True


threading.Thread(target=_check_hw, daemon=True).start()


def _font_metrics() -> dict:
    """Hauteurs (ascendante, descendante) des polices, pour que l'aperçu colle au rendu final."""
    from .config import FONTS
    from .overlays import font

    out = {}
    for name in FONTS:
        asc, desc = font(name, 1000).getmetrics()
        out[name] = [asc / 1000, desc / 1000]
    return out


@app.get("/api/info")
def info(request: Request):
    local = _is_local(request)
    return {
        "version": __version__,
        "platforms": PLATFORMS,
        "caption_styles": CAPTION_STYLES,
        "title_styles": TITLE_STYLES,
        "font_metrics": _font_metrics(),
        "whisper": captions.whisper_available(),
        "gpu_encoder": _hw["encoder"],
        "gpu_checked": _hw["checked"],
        "is_local": local,
        "tablet_url": tablet_url() if local else None,
    }


@app.get("/api/qr.svg")
def qr_svg(request: Request):
    if not _is_local(request):
        raise HTTPException(403, "Disponible seulement sur le PC.")
    url = tablet_url()
    if not url:
        raise HTTPException(404, "Aucun réseau local détecté.")
    import qrcode
    import qrcode.image.svg

    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


@app.get("/api/settings")
def get_settings():
    s = load_settings()
    s.pop("access_key", None)
    return s


@app.put("/api/settings")
async def put_settings(request: Request):
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(400, "Format invalide")
    if data.get("whisper_model") not in (None, "tiny", "base", "small", "medium", "large-v3"):
        raise HTTPException(400, "Modèle inconnu")
    if "default_formats" in data:
        data["default_formats"] = [f for f in data["default_formats"] if f in PLATFORMS]
    if data.get("twitch_cookies") not in (None, "", *twitch.COOKIE_BROWSERS):
        raise HTTPException(400, "Navigateur inconnu")
    s = save_settings(data)
    s.pop("access_key", None)
    return s


# ---------------------------------------------------------------------------
# Projets
# ---------------------------------------------------------------------------

def _load_or_404(pid: str) -> dict:
    try:
        return projects.load(pid)
    except projects.ProjectNotFound:
        raise HTTPException(404, "Projet introuvable") from None


def _formats(value) -> list[str]:
    if not value:
        return load_settings().get("default_formats", ["tiktok", "reels", "shorts"])
    if isinstance(value, str):
        value = [v for v in value.split(",") if v]
    return [f for f in value if f in PLATFORMS]


@app.get("/api/projects")
def list_projects():
    return projects.list_projects()


@app.post("/api/projects/url")
async def create_from_url(request: Request):
    data = await request.json()
    url = (data.get("url") or "").strip()
    if not re.match(r"^https?://", url):
        if re.match(r"^(www\.)?(clips\.)?twitch\.tv/", url):
            url = "https://" + url
        else:
            raise HTTPException(400, "Colle un lien qui commence par https://")
    vod_start = twitch.parse_time(data.get("vod_start"))
    vod_end = twitch.parse_time(data.get("vod_end"))
    if twitch.is_vod_url(url) and (vod_start is None or vod_end is None):
        start_from_url = twitch.vod_start_from_url(url)
        if start_from_url is not None and vod_start is None:
            vod_start = start_from_url
        if vod_start is None or vod_end is None:
            raise HTTPException(400, "Pour une VOD, indique le début et la fin du passage à récupérer.")
    if vod_start is not None and vod_end is not None and vod_end <= vod_start:
        raise HTTPException(400, "La fin doit être après le début.")
    title = data.get("title") or "Clip Twitch"
    project = projects.new_project(title, {"url": url})
    pipeline.start_import_url(
        project["id"], url, bool(data.get("auto")), _formats(data.get("formats")),
        vod_start if vod_end is not None else None, vod_end if vod_start is not None else None,
    )
    return projects.load(project["id"])


@app.post("/api/projects/upload")
async def create_from_upload(
    file: UploadFile = File(...),
    auto: bool = Form(False),
    formats: str = Form(""),
):
    ext = Path(file.filename or "video.mp4").suffix.lower()
    if ext not in VIDEO_EXT:
        raise HTTPException(400, "Format de fichier non pris en charge (mp4, mov, mkv, webm…).")
    title = Path(file.filename or "Ma vidéo").stem[:80]
    project = projects.new_project(title, {"file": file.filename})
    dest = projects.project_dir(project["id"]) / f"source{ext}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)
    pipeline.start_finalize_upload(project["id"], dest.name, auto, _formats(formats))
    return projects.load(project["id"])


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = _load_or_404(pid)
    p["jobs"] = manager.list(pid)
    p["descriptions"] = {k: projects.describe_for_platform(p, k) for k in PLATFORMS} if p.get("source") else {}
    return p


EDIT_KEYS = {
    "start", "end", "layout", "split_ratio", "cam", "game", "crop", "main", "blur_zoom", "blur_offset",
    "title", "captions", "watermark", "progress_bar", "normalize_audio", "fade",
}


def _sanitize_edit(current: dict, incoming: dict, source: dict) -> dict:
    edit = copy.deepcopy(current)
    for key, value in incoming.items():
        if key not in EDIT_KEYS:
            continue
        if key in ("cam", "game", "crop", "main"):
            edit[key] = clamp_rect(value)
        elif key in ("title", "captions", "watermark"):
            edit[key] = {**edit.get(key, {}), **{k: v for k, v in (value or {}).items()}}
        elif key == "layout":
            if value in ("split", "blur", "crop"):
                edit[key] = value
        elif key == "split_ratio":
            edit[key] = min(0.6, max(0.2, float(value)))
        elif key in ("start", "end"):
            edit[key] = None if value is None else max(0.0, min(float(value), source.get("duration") or 1e9))
        elif key == "blur_zoom":
            edit[key] = min(1.8, max(1.0, float(value)))
        elif key == "blur_offset":
            edit[key] = min(0.3, max(-0.3, float(value)))
        else:
            edit[key] = bool(value)
    if edit.get("end") is not None and edit["end"] - edit.get("start", 0) < 0.5:
        edit["end"] = min(source.get("duration") or edit["start"] + 0.5, edit["start"] + 0.5)
    return edit


@app.put("/api/projects/{pid}/edit")
async def put_edit(pid: str, request: Request):
    data = await request.json()
    p = _load_or_404(pid)
    if not p.get("source"):
        raise HTTPException(409, "La vidéo n'est pas encore prête.")

    def apply(proj: dict) -> None:
        proj["edit"] = _sanitize_edit(proj["edit"], data.get("edit", {}), proj["source"])
        if isinstance(data.get("title"), str) and data["title"].strip():
            proj["title"] = data["title"].strip()[:120]

    project = projects.mutate(pid, apply)
    return {"edit": project["edit"], "title": project["title"]}


@app.put("/api/projects/{pid}/transcript")
async def put_transcript(pid: str, request: Request):
    data = await request.json()
    p = _load_or_404(pid)
    if not p.get("transcript"):
        raise HTTPException(409, "Pas encore de sous-titres.")
    texts = data.get("segments") or []

    def apply(proj: dict) -> None:
        segs = proj["transcript"]["segments"]
        for i, item in enumerate(texts):
            if i < len(segs) and isinstance(item, dict) and isinstance(item.get("text"), str):
                segs[i] = captions.retime_segment(segs[i], item["text"])
        proj["transcript"]["segments"] = [s for s in segs if s.get("words")]

    project = projects.mutate(pid, apply)
    return project["transcript"]


@app.post("/api/projects/{pid}/transcribe")
def transcribe(pid: str):
    p = _load_or_404(pid)
    if not p.get("source"):
        raise HTTPException(409, "La vidéo n'est pas encore prête.")
    if not captions.whisper_available():
        raise HTTPException(
            501, "Le module IA des sous-titres n'est pas installé (relance le lanceur ou « pip install faster-whisper »)."
        )
    return pipeline.start_transcribe(pid).to_dict()


@app.post("/api/projects/{pid}/analyze")
def analyze(pid: str):
    p = _load_or_404(pid)
    if not p.get("source"):
        raise HTTPException(409, "La vidéo n'est pas encore prête.")
    return pipeline.start_reanalyze(pid).to_dict()


@app.post("/api/projects/{pid}/render")
async def render_project(pid: str, request: Request):
    data = await request.json()
    p = _load_or_404(pid)
    if not p.get("source"):
        raise HTTPException(409, "La vidéo n'est pas encore prête.")
    formats = _formats(data.get("formats"))
    if not formats:
        raise HTTPException(400, "Choisis au moins un format.")
    return [j.to_dict() for j in pipeline.start_render(pid, formats)]


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    _load_or_404(pid)
    for job in manager.active_for(pid):
        manager.cancel(job.id)
    projects.delete(pid)
    return {"ok": True}


@app.api_route("/api/projects/{pid}/video", methods=["GET", "HEAD"])
def source_video(pid: str):
    p = _load_or_404(pid)
    if not p.get("source"):
        raise HTTPException(404, "Vidéo pas encore prête")
    name = p["source"].get("preview") or p["source"]["file"]
    path = projects.project_dir(pid) / name
    media = "video/webm" if path.suffix.lower() == ".webm" else "video/mp4"
    return FileResponse(path, media_type=media)


@app.get("/api/projects/{pid}/thumb")
def thumb(pid: str):
    path = projects.project_dir(pid) / "miniature.jpg"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/projects/{pid}/open-folder")
def open_folder(pid: str, request: Request):
    """Ouvre le dossier des vidéos exportées dans l'explorateur de fichiers (seulement sur le PC)."""
    if not _is_local(request):
        raise HTTPException(403, "Disponible seulement sur le PC.")
    _load_or_404(pid)
    folder = projects.project_dir(pid) / "exports"
    folder.mkdir(exist_ok=True)
    import subprocess
    import sys

    try:
        if sys.platform == "win32":
            import os

            os.startfile(str(folder))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except OSError as exc:
        raise HTTPException(500, f"Impossible d'ouvrir le dossier : {exc}") from None
    return {"ok": True, "path": str(folder)}


def _safe_name(text: str) -> str:
    text = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE).strip()
    return re.sub(r"\s+", "_", text)[:60] or "clip"


@app.api_route("/api/projects/{pid}/exports/{platform}", methods=["GET", "HEAD"])
def get_export(pid: str, platform: str, download: int = 0):
    p = _load_or_404(pid)
    exp = (p.get("exports") or {}).get(platform)
    if platform not in PLATFORMS or not exp or exp.get("status") != "fini":
        raise HTTPException(404, "Export introuvable")
    path = projects.project_dir(pid) / "exports" / exp["file"]
    if not path.exists():
        raise HTTPException(404, "Fichier supprimé")
    name = f"{_safe_name(p.get('title') or 'clip')}_{platform}.mp4"
    if download:
        return FileResponse(path, media_type="video/mp4", filename=name)
    return FileResponse(path, media_type="video/mp4")


# ---------------------------------------------------------------------------
# Tâches & Twitch
# ---------------------------------------------------------------------------

@app.get("/api/jobs")
def jobs(project: str | None = None):
    return manager.list(project)


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    return {"ok": manager.cancel(job_id)}


@app.get("/api/channel-clips")
def channel_clips(channel: str, period: str = "7j"):
    try:
        return twitch.channel_clips(channel, period)
    except twitch.DownloadError as exc:
        raise HTTPException(400, str(exc)) from None
