"""Gestion des projets (un projet = un clip source + ses réglages de montage + ses exports)."""
from __future__ import annotations

import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from . import analysis
from .config import PLATFORMS, PROJECTS_DIR, ensure_dirs, load_settings
from .ffmpeg_utils import BROWSER_CODECS, extract_frame, make_preview_proxy, probe

_lock = threading.RLock()
ID_RE = re.compile(r"^[a-z0-9]{6,32}$")


class ProjectNotFound(KeyError):
    pass


def project_dir(pid: str) -> Path:
    if not ID_RE.match(pid or ""):
        raise ProjectNotFound(pid)
    return PROJECTS_DIR / pid


def default_edit(settings: dict | None = None) -> dict:
    settings = settings or load_settings()
    return {
        "start": 0.0,
        "end": None,
        "layout": "blur",
        "split_ratio": 0.4,
        "cam": {"x": 0.0, "y": 0.0, "w": 0.25, "h": 0.25},
        "game": {"x": 0.25, "y": 0.0, "w": 0.5, "h": 1.0},
        "crop": {"x": 0.34, "y": 0.0, "w": 0.32, "h": 1.0},
        "main": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
        "blur_zoom": 1.0,
        "blur_offset": 0.0,
        "title": {"enabled": True, "text": "", "duration": 4.0, "style": settings.get("default_title_style", "blanc")},
        "captions": {
            "enabled": True,
            "style": settings.get("default_caption_style", "tiktok"),
            "words": 3,
            "position": "auto",
            "size": "moyen",
            "highlight": True,
        },
        "watermark": {"enabled": bool(settings.get("default_watermark")), "text": settings.get("default_watermark", "")},
        "progress_bar": False,
        "normalize_audio": True,
        "fade": True,
        "auto_reason": "",
    }


def new_project(title: str = "Nouveau clip", origin: dict | None = None) -> dict:
    ensure_dirs()
    pid = uuid.uuid4().hex[:12]
    d = project_dir(pid)
    d.mkdir(parents=True)
    project = {
        "id": pid,
        "created": time.time(),
        "updated": time.time(),
        "title": title,
        "status": "import",
        "status_text": "Import en cours…",
        "error": None,
        "origin": origin or {},
        "source": None,
        "edit": default_edit(),
        "transcript": None,
        "highlights": [],
        "exports": {},
    }
    save(project)
    return project


def load(pid: str) -> dict:
    path = project_dir(pid) / "projet.json"
    with _lock:
        if not path.exists():
            raise ProjectNotFound(pid)
        return json.loads(path.read_text("utf-8"))


def save(project: dict) -> dict:
    project["updated"] = time.time()
    d = project_dir(project["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "projet.json.tmp"
    with _lock:
        tmp.write_text(json.dumps(project, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(d / "projet.json")
    return project


def update(pid: str, **fields) -> dict:
    with _lock:
        project = load(pid)
        project.update(fields)
        return save(project)


def mutate(pid: str, fn) -> dict:
    """Charge, modifie (fn(project)) et enregistre le projet sans conflit entre tâches."""
    with _lock:
        project = load(pid)
        fn(project)
        return save(project)


def list_projects() -> list[dict]:
    ensure_dirs()
    out = []
    for d in PROJECTS_DIR.iterdir():
        f = d / "projet.json"
        if f.exists():
            try:
                p = json.loads(f.read_text("utf-8"))
            except (OSError, ValueError):
                continue
            out.append(summary(p))
    out.sort(key=lambda p: -p["created"])
    return out


def summary(p: dict) -> dict:
    src = p.get("source") or {}
    return {
        "id": p["id"],
        "title": p.get("title"),
        "created": p.get("created"),
        "status": p.get("status"),
        "status_text": p.get("status_text"),
        "duration": src.get("duration"),
        "channel": (p.get("origin") or {}).get("channel"),
        "has_thumb": (project_dir(p["id"]) / "miniature.jpg").exists(),
        "exports": [k for k, v in (p.get("exports") or {}).items() if v.get("status") == "fini"],
    }


def delete(pid: str) -> None:
    d = project_dir(pid)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def finalize_source(pid: str, file_name: str, auto_layout: bool = True) -> dict:
    """Après le téléchargement / l'envoi du fichier : analyse, miniature, mise en page auto."""
    d = project_dir(pid)
    src = d / file_name
    info = probe(src)
    if info["duration"] <= 0.2:
        raise ValueError("La vidéo semble vide ou illisible.")
    if info.get("vcodec") not in BROWSER_CODECS or src.suffix.lower() not in (".mp4", ".webm", ".m4v", ".mov"):
        update(pid, status="analyse", status_text="Préparation de l'aperçu (format vidéo spécial)…")
        make_preview_proxy(src, d / "apercu.mp4")
        info["preview"] = "apercu.mp4"
    try:
        extract_frame(src, min(info["duration"] * 0.3, 5), d / "miniature.jpg", 480)
    except Exception:
        pass
    project = load(pid)
    edit = project["edit"]
    edit["start"] = 0.0
    edit["end"] = round(info["duration"], 3)
    geometry = analysis.default_edit_geometry(info["width"], info["height"])
    edit.update({k: v for k, v in geometry.items()})
    if auto_layout:
        project = update(pid, status="analyse", status_text="Analyse de la vidéo (facecam, cadrage)…")
        geometry = analysis.analyze_layout(src, info["width"], info["height"], 0, min(info["duration"], 600))
        edit.update(geometry)
    if not edit["title"].get("text") and not (project.get("origin") or {}).get("vod_range"):
        edit["title"]["text"] = project.get("title") or ""
    highlights = []
    if info["duration"] > 100:
        highlights = analysis.find_highlights(src, info["duration"], clip_len=45)
        if highlights:
            best = highlights[0]
            edit["start"], edit["end"] = best["start"], best["end"]
    project = load(pid)
    project.update(
        source={"file": file_name, **info},
        edit=edit,
        highlights=highlights,
        status="pret",
        status_text="Prêt à monter",
        error=None,
    )
    return save(project)


def describe_for_platform(project: dict, platform: str) -> dict:
    """Propose un titre et une description avec hashtags pour la publication."""
    p = PLATFORMS[platform]
    title = (project["edit"].get("title", {}).get("text") or project.get("title") or "").strip()
    channel = (project.get("origin") or {}).get("channel") or ""
    tags = list(p["hashtags"])
    if channel:
        tag = "#" + re.sub(r"[^0-9A-Za-zÀ-ÿ_]", "", channel).lower()
        if tag not in tags and len(tag) > 1:
            tags.insert(1, tag)
    credit = f"🎥 Clip du live de {channel} sur Twitch (twitch.tv/{channel.lower()})" if channel else "🎥 Clip Twitch"
    if platform == "youtube":
        text = f"{title}\n\n{credit}\n\n{' '.join(tags)}"
    elif platform == "shorts":
        text = f"{title} {' '.join(tags[:4])}"
    else:
        text = f"{title} 😂\n\n{credit}\n\n{' '.join(tags)}"
    return {"title": title, "text": text}
