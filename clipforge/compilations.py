"""Compilations YouTube : plusieurs clips Twitch assemblés en une vidéo 16:9 de 15 à 25 min (30 min maximum).

Une compilation = une liste ordonnée de projets. Chaque clip est monté en 16:9 avec ses propres
réglages (découpe, sous-titres, titre, pseudo), puis tout est collé avec une intro au début et
un écran de fin, et l'appli prépare la description avec les chapitres et les crédits.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from . import captions, projects, promo, render, social
from .config import COMPIL_TARGET, DATA_DIR, PLATFORMS, YOUTUBE_MAX_SECONDS, load_settings
from .ffmpeg_utils import available_hw_encoder, probe
from .jobs import Job, manager

COMPILS_DIR = DATA_DIR / "compilations"
ID_RE = re.compile(r"^[a-z0-9]{6,32}$")
END_CARD_SECONDS = 8.0  # écran de fin : laisse la place aux « écrans de fin » de YouTube
_lock = threading.RLock()


class CompilationNotFound(KeyError):
    pass


def compil_dir(cid: str) -> Path:
    if not ID_RE.match(cid or ""):
        raise CompilationNotFound(cid)
    return COMPILS_DIR / cid


def _path(cid: str) -> Path:
    return compil_dir(cid) / "compil.json"


def load(cid: str) -> dict:
    with _lock:
        p = _path(cid)
        if not p.exists():
            raise CompilationNotFound(cid)
        return json.loads(p.read_text("utf-8"))


def save(c: dict) -> dict:
    c["updated"] = time.time()
    d = compil_dir(c["id"])
    d.mkdir(parents=True, exist_ok=True)
    with _lock:
        tmp = d / "compil.json.tmp"
        tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(d / "compil.json")
    return c


def mutate(cid: str, fn) -> dict:
    with _lock:
        c = load(cid)
        fn(c)
        return save(c)


def create(title: str = "") -> dict:
    COMPILS_DIR.mkdir(parents=True, exist_ok=True)
    n = len(list(COMPILS_DIR.glob("*/compil.json"))) + 1
    c = {
        "id": uuid.uuid4().hex[:12],
        "created": time.time(),
        "updated": time.time(),
        "title": title.strip() or f"Best of Twitch #{n}",
        "items": [],
        "intro": True,
        "end_card": True,
        "auto_captions": True,
        "export": None,
    }
    return save(c)


def list_all() -> list[dict]:
    COMPILS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for f in COMPILS_DIR.glob("*/compil.json"):
        try:
            c = json.loads(f.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        out.append(c)
    out.sort(key=lambda c: -c["created"])
    return out


def delete(cid: str) -> None:
    d = compil_dir(cid)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Durées
# ---------------------------------------------------------------------------

def clip_duration(project: dict, settings: dict | None = None) -> float:
    if not project.get("source"):
        return 0.0
    start, end = render.clip_bounds(project["edit"], project["source"], "youtube", settings)
    return max(0.0, end - start)


def describe(c: dict, settings: dict | None = None) -> dict:
    """Compilation + infos de chaque clip + durée totale estimée."""
    settings = settings or load_settings()
    items = []
    total = 0.0
    for pid in c["items"]:
        try:
            p = projects.load(pid)
        except projects.ProjectNotFound:
            items.append({"id": pid, "missing": True})
            continue
        dur = clip_duration(p, settings)
        total += dur
        items.append({
            "id": pid,
            "title": p.get("title"),
            "channel": (p.get("origin") or {}).get("channel"),
            "game": (p.get("origin") or {}).get("game"),
            "duration": round(dur, 2),
            "ready": bool(p.get("source")),
            "has_captions": bool(p.get("transcript")),
            "has_thumb": (projects.project_dir(pid) / "miniature.jpg").exists(),
        })
    extra = (promo.DURATION["intro"] if c.get("intro") else 0) + (END_CARD_SECONDS if c.get("end_card") else 0)
    total += extra if items else 0
    lo, hi = COMPIL_TARGET
    status = ("vide" if not items else "court" if total < lo else "ideal" if total <= hi
              else "long" if total <= YOUTUBE_MAX_SECONDS else "trop_long")
    exp = c.get("export") or {}
    outdated = exp.get("status") == "fini" and (c.get("changed") or 0) > (exp.get("finished") or 0)
    return {**c, "items_info": items, "total": round(total, 2), "duration_status": status,
            "target": [lo, hi], "max": YOUTUBE_MAX_SECONDS, "outdated": outdated}


def autofill(cid: str, target: float = 20 * 60) -> dict:
    """Ajoute des clips prêts (pas encore utilisés dans une autre compilation) jusqu'à ~20 min."""
    settings = load_settings()
    used_elsewhere = {pid for other in list_all() if other["id"] != cid for pid in other["items"]}

    def apply(c: dict) -> None:
        current = describe(c, settings)["total"]
        if not c["items"]:
            current += (promo.DURATION["intro"] if c.get("intro") else 0) + (END_CARD_SECONDS if c.get("end_card") else 0)
        candidates = [p for p in projects.load_all()
                      if p.get("source") and p["id"] not in c["items"] and p["id"] not in used_elsewhere]
        candidates.sort(key=lambda p: p.get("created", 0))
        for p in candidates:
            dur = clip_duration(p, settings)
            if current >= target or current + dur > YOUTUBE_MAX_SECONDS:
                continue
            c["items"].append(p["id"])
            current += dur
        c["changed"] = time.time()

    return mutate(cid, apply)


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------

def _segment_key(project: dict, settings: dict, fps: float) -> str:
    """Empreinte d'un morceau : s'il n'a pas changé, on réutilise le rendu précédent."""
    tr = project.get("transcript") or {}
    data = json.dumps({
        "edit": project["edit"], "src": project["source"].get("file"),
        "tr": [s.get("text") for s in tr.get("segments", [])], "lang": tr.get("language"),
        "q": settings.get("quality"), "gpu": settings.get("gpu"), "fps": fps,
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(data.encode()).hexdigest()[:12]


def start_render(cid: str) -> Job:
    def on_error(job: Job, message: str) -> None:
        def apply(c: dict) -> None:
            c["export"] = {**(c.get("export") or {}), "status": "annule" if message == "Annulé" else "erreur",
                           "error": None if message == "Annulé" else message}
        try:
            mutate(cid, apply)
        except CompilationNotFound:
            pass

    def work(job: Job) -> None:
        mutate(cid, lambda c: c.update(export={"status": "en_cours", "job_id": job.id}))
        settings = load_settings()
        try:
            _render(cid, job, settings)
        except Exception as exc:
            # Si la carte graphique a lâché en route, on refait tout au processeur (réglages identiques partout).
            if str(exc) != "Annulé" and settings.get("gpu") != "off" and available_hw_encoder():
                job.set(None, "Nouvel essai avec le processeur…")
                _render(cid, job, {**settings, "gpu": "off"})
            else:
                raise

    return manager.submit(f"compil:{cid}", "compilation", "Compilation YouTube", work, queue="calcul", on_error=on_error)


def _render(cid: str, job: Job, settings: dict) -> None:
    c = load(cid)
    info = describe(c, settings)
    items = [it for it in info["items_info"] if not it.get("missing") and it.get("ready")]
    if not items:
        raise ValueError("Ajoute au moins un clip à la compilation.")
    if info["total"] > YOUTUBE_MAX_SECONDS + 0.5:
        raise ValueError("La compilation dépasse 30 minutes : retire quelques clips.")
    d = compil_dir(cid)
    seg_dir = d / "morceaux"
    seg_dir.mkdir(parents=True, exist_ok=True)
    plist = [projects.load(it["id"]) for it in items]
    fps = 60.0 if any((p["source"].get("fps") or 30) >= 48 for p in plist) else 30.0
    W, H = PLATFORMS["youtube"]["width"], PLATFORMS["youtube"]["height"]
    cancel = lambda: job.cancel_requested  # noqa: E731

    # 1. Sous-titres manquants (optionnel).
    if c.get("auto_captions") and captions.whisper_available():
        todo = [p for p in plist if p["edit"].get("captions", {}).get("enabled") and not p.get("transcript")]
        for i, p in enumerate(todo):
            job.set(0.02, f"Sous-titres du clip {i + 1}/{len(todo)}…")
            dur = p["source"]["duration"]
            e = p["edit"]
            start, end = (0.0, dur) if dur <= 300 else (max(0.0, float(e.get("start", 0)) - 2), min(dur, float(e.get("end") or dur) + 2))
            caps = e.get("captions", {})
            spoken = caps.get("spoken") or "auto"
            if spoken == "auto":
                lang = str((p.get("origin") or {}).get("language") or "").lower()[:2]
                spoken = lang if lang in captions.LANGUAGES else "auto"
            tr = captions.transcribe(projects.project_dir(p["id"]) / p["source"]["file"], start, end,
                                     settings.get("whisper_model", "small"), spoken, None,
                                     translate_to_english=bool(caps.get("english")))
            projects.mutate(p["id"], lambda proj, tr=tr: proj.update(transcript=tr))
        plist = [projects.load(p["id"]) for p in plist]

    # 2. Un morceau 16:9 par clip (réutilisé s'il n'a pas changé).
    durations = [clip_duration(p, settings) for p in plist]
    grand_total = sum(durations) or 1.0
    done = 0.0
    segments: list[Path] = []
    chapters: list[tuple[float, dict]] = []
    t_cursor = 0.0
    if c.get("intro"):
        job.set(0.04, "Intro…")
        frame = promo.frame_from_video(projects.project_dir(plist[0]["id"]) / plist[0]["source"]["file"],
                                       float(plist[0]["edit"].get("start", 0)) + 0.5)
        cv, ca, cdur = promo.build_card(d / "tmp", "intro", "youtube", settings.get("promo_email", ""),
                                        settings.get("promo_intro_text") or None, frame)
        seg = render.encode_card_segment(cv, ca, seg_dir / "intro.mp4", settings, fps, (W, H), cancel)
        segments.append(seg)
        chapters.append((0.0, {"title": "Intro"}))
        t_cursor += probe(seg)["duration"]
    keep = {"intro.mp4", "fin.mp4"}
    for i, p in enumerate(plist):
        key = _segment_key(p, settings, fps)
        seg = seg_dir / f"{p['id']}-{key}.mp4"
        keep.add(seg.name)
        if not seg.exists():
            base = done

            def prog(frac: float, base=base, i=i, dur=durations[i]) -> None:
                overall = 0.05 + 0.85 * (base + frac * dur) / grand_total
                job.set(overall, f"Clip {i + 1}/{len(plist)} : montage… {int(frac * 100)} %")

            render.render_export(
                projects.project_dir(p["id"]), p, "youtube", settings, prog, cancel,
                include_promo=False, output=seg, fixed_fps=fps, allow_fallback=False, work_name="compilation",
            )
        done += durations[i]
        job.set(0.05 + 0.85 * done / grand_total, f"Clip {i + 1}/{len(plist)} prêt")
        segments.append(seg)
        chapters.append((t_cursor, {"title": p.get("edit", {}).get("title", {}).get("text") or p.get("title"),
                                    "channel": (p.get("origin") or {}).get("channel"), "project": p}))
        t_cursor += probe(seg)["duration"]
    if c.get("end_card"):
        job.set(0.92, "Écran de fin…")
        last = plist[-1]
        frame = promo.frame_from_video(projects.project_dir(last["id"]) / last["source"]["file"],
                                       float(last["edit"].get("end") or last["source"]["duration"]) - 0.5)
        cv, ca, _ = promo.build_card(d / "tmp", "outro", "youtube", settings.get("promo_email", ""),
                                     "THANKS FOR WATCHING!", frame, END_CARD_SECONDS)
        segments.append(render.encode_card_segment(cv, ca, seg_dir / "fin.mp4", settings, fps, (W, H), cancel))
        chapters.append((t_cursor, {"title": "Thanks for watching"}))

    # 3. Assemblage final sans réencoder.
    job.set(0.95, "Assemblage de la vidéo…")
    out = d / "compilation.mp4"
    render.concat_segments(segments, out)
    shutil.rmtree(d / "tmp", ignore_errors=True)
    for f in seg_dir.glob("*.mp4"):  # on garde seulement les morceaux encore utilisés
        if f.name not in keep:
            f.unlink(missing_ok=True)
    final = probe(out)
    chap = [{"t": round(t, 2), "title": meta.get("title") or "", "channel": meta.get("channel") or "",
             "project": (meta.get("project") or {}).get("id")} for t, meta in chapters]

    def apply(c2: dict) -> None:
        c2["export"] = {
            "status": "fini", "file": out.name, "size": out.stat().st_size, "duration": round(final["duration"], 2),
            "finished": time.time(), "chapters": chap, "job_id": job.id,
        }
    mutate(cid, apply)
    texts = social.compilation_texts(load(cid), [p for p in plist], chap, None, settings.get("promo_email", ""))
    (d / "description.txt").write_text(social.compilation_txt(texts), "utf-8")
    job.set(1.0, "Compilation prête")
