"""Enchaînement des étapes : import → analyse → sous-titres → exports (mode 100 % automatique)."""
from __future__ import annotations

import time
from pathlib import Path

from . import analysis, captions, projects, render, twitch
from .config import PLATFORMS, load_settings
from .jobs import Job, manager


def _fail_project(pid: str, message: str) -> None:
    try:
        projects.update(pid, status="erreur", status_text="Erreur", error=message)
    except projects.ProjectNotFound:
        pass


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def start_import_url(
    pid: str, url: str, auto: bool, formats: list[str], vod_start: float | None = None, vod_end: float | None = None
) -> Job:
    def work(job: Job) -> None:
        d = projects.project_dir(pid)

        def prog(frac: float, msg: str) -> None:
            job.set(0.05 + frac * 0.75, msg)
            projects.update(pid, status_text=msg)

        cookies = load_settings().get("twitch_cookies") or None
        if vod_start is not None and vod_end is not None:
            file_name, meta = twitch.download_section(url, vod_start, vod_end, d, prog, cookies)
        else:
            file_name, meta = twitch.download_clip(url, d, prog, cookies)

        def apply_meta(p: dict) -> None:
            p["title"] = meta.get("title") or p["title"]
            p["origin"].update({k: v for k, v in meta.items() if v})
            # Le titre d'un live complet est souvent trop long pour servir d'accroche.
            if not meta.get("vod_range"):
                p["edit"]["title"]["text"] = p["title"]
            if meta.get("channel") and not p["edit"]["watermark"].get("text"):
                p["edit"]["watermark"]["text"] = f"twitch.tv/{meta['channel'].lower()}"
                p["edit"]["watermark"]["enabled"] = True

        projects.mutate(pid, apply_meta)
        job.set(0.85, "Analyse de la vidéo…")
        projects.finalize_source(pid, file_name)
        job.set(1.0, "Clip importé")
        if auto:
            start_auto_chain(pid, formats)

    return manager.submit(pid, "import", "Import du clip", work, queue="reseau",
                          on_error=lambda j, m: _fail_project(pid, m))


def start_finalize_upload(pid: str, file_name: str, auto: bool, formats: list[str]) -> Job:
    def work(job: Job) -> None:
        job.set(0.2, "Analyse de la vidéo…")
        projects.finalize_source(pid, file_name)
        job.set(1.0, "Vidéo importée")
        if auto:
            start_auto_chain(pid, formats)

    return manager.submit(pid, "import", "Analyse de la vidéo", work, queue="reseau",
                          on_error=lambda j, m: _fail_project(pid, m))


def start_auto_chain(pid: str, formats: list[str]) -> None:
    """Mode automatique : sous-titres IA (si dispo) puis exports dans tous les formats choisis."""
    project = projects.load(pid)
    if project["edit"]["captions"].get("enabled") and captions.whisper_available():
        start_transcribe(pid)
    start_render(pid, formats)


# ---------------------------------------------------------------------------
# Analyse / sous-titres
# ---------------------------------------------------------------------------

def start_reanalyze(pid: str) -> Job:
    def work(job: Job) -> None:
        p = projects.load(pid)
        src = projects.project_dir(pid) / p["source"]["file"]
        job.set(0.1, "Recherche de la facecam…")
        e = p["edit"]
        geometry = analysis.analyze_layout(src, p["source"]["width"], p["source"]["height"],
                                           float(e.get("start", 0)), e.get("end"))

        def apply(proj: dict) -> None:
            proj["edit"].update(geometry)

        projects.mutate(pid, apply)
        job.set(1.0, geometry.get("auto_reason", "Analyse terminée"))

    return manager.submit(pid, "analyse", "Mise en page automatique", work, queue="calcul")


def start_transcribe(pid: str) -> Job:
    def work(job: Job) -> None:
        settings = load_settings()
        p = projects.load(pid)
        src = projects.project_dir(pid) / p["source"]["file"]
        dur = p["source"]["duration"]
        e = p["edit"]
        if dur <= 300:
            start, end = 0.0, dur
        else:
            start = max(0.0, float(e.get("start", 0)) - 2)
            end = min(dur, float(e.get("end") or dur) + 2)

        def prog(frac: float, msg: str) -> None:
            job.set(frac, msg)

        transcript = captions.transcribe(src, start, end, settings.get("whisper_model", "small"),
                                         settings.get("language", "fr"), prog)

        def apply(proj: dict) -> None:
            proj["transcript"] = transcript
            proj["edit"]["captions"]["enabled"] = True

        projects.mutate(pid, apply)
        n = sum(len(s["words"]) for s in transcript["segments"])
        job.set(1.0, f"{n} mots reconnus")

    return manager.submit(pid, "sous-titres", "Sous-titres automatiques (IA)", work, queue="calcul")


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def start_render(pid: str, formats: list[str]) -> list[Job]:
    jobs = []
    for platform in formats:
        if platform not in PLATFORMS:
            continue
        for old in manager.active_for(pid, f"export:{platform}"):
            manager.cancel(old.id)
        jobs.append(_start_one_render(pid, platform))
    return jobs


def _start_one_render(pid: str, platform: str) -> Job:
    label = f"Export {PLATFORMS[platform]['label']}"

    def mark(status: str, **extra) -> None:
        def apply(p: dict) -> None:
            p.setdefault("exports", {})[platform] = {**p.get("exports", {}).get(platform, {}), "status": status, **extra}
        projects.mutate(pid, apply)

    def work(job: Job) -> None:
        mark("en_cours", job_id=job.id, error=None)
        settings = load_settings()
        project = projects.load(pid)
        last = [0.0]

        def prog(frac: float) -> None:
            job.set(frac, f"Montage {PLATFORMS[platform]['label']}… {int(frac * 100)} %")
            last[0] = frac

        t0 = time.time()
        out: Path = render.render_export(
            projects.project_dir(pid), project, platform, settings,
            on_progress=prog, cancel_check=lambda: job.cancel_requested,
        )
        start, end = render.clip_bounds(project["edit"], project["source"], platform)
        mark("fini", file=out.name, size=out.stat().st_size, finished=time.time(),
             duration=round(end - start, 2), seconds=round(time.time() - t0, 1), job_id=job.id)
        job.set(1.0, "Vidéo prête")

    def on_error(job: Job, message: str) -> None:
        try:
            mark("annule" if message == "Annulé" else "erreur", error=None if message == "Annulé" else message)
        except projects.ProjectNotFound:
            pass

    mark("attente")
    return manager.submit(pid, f"export:{platform}", label, work, queue="calcul", on_error=on_error)
