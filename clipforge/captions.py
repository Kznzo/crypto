"""Sous-titres automatiques : transcription (faster-whisper) et découpage en petits groupes de mots."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np

from .config import DATA_DIR
from .ffmpeg_utils import _NO_WINDOW, ffmpeg_path

WHISPER_DIR = DATA_DIR / "modeles-ia"
_model_cache: dict[str, object] = {}


class CaptionsUnavailable(RuntimeError):
    pass


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except Exception:
        return False


def _load_model(size: str):
    if size in _model_cache:
        return _model_cache[size]
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise CaptionsUnavailable(
            "Le module d'IA pour les sous-titres n'est pas installé. "
            "Lance « pip install faster-whisper » (le lanceur le fait automatiquement)."
        ) from exc
    WHISPER_DIR.mkdir(parents=True, exist_ok=True)
    model = None
    try:
        model = WhisperModel(size, device="auto", compute_type="auto", download_root=str(WHISPER_DIR))
    except Exception:
        model = WhisperModel(size, device="cpu", compute_type="int8", download_root=str(WHISPER_DIR))
    _model_cache.clear()
    _model_cache[size] = model
    return model


def transcribe(
    src: str | Path,
    start: float,
    end: float,
    model_size: str = "small",
    language: str | None = "fr",
    on_progress: Callable[[float, str], None] | None = None,
) -> dict:
    """Transcrit l'extrait [start, end] et renvoie des segments avec le minutage de chaque mot."""
    duration = max(0.1, end - start)
    if on_progress:
        on_progress(0.02, "Extraction du son…")
    # Le son est décodé par FFmpeg et passé directement à Whisper (tableau 16 kHz mono).
    res = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
         "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True,
        creationflags=_NO_WINDOW,
    )
    if res.returncode != 0 or len(res.stdout) < 16000 * 4 * 0.3:
        raise CaptionsUnavailable("Impossible d'extraire le son de la vidéo (le clip n'a peut-être pas de son).")
    audio = np.frombuffer(res.stdout, dtype=np.float32).copy()

    if on_progress:
        on_progress(0.06, "Chargement du modèle IA (le 1er lancement le télécharge)…")
    model = _load_model(model_size)
    if on_progress:
        on_progress(0.12, "Transcription en cours…")
    lang = None if not language or language == "auto" else language
    segments_iter, info = model.transcribe(
        audio,
        language=lang,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
        condition_on_previous_text=False,
    )
    segments = []
    for seg in segments_iter:
        words: list[dict] = []
        for w in seg.words or []:
            text = w.word.strip().replace("’", "'")
            if not text:
                continue
            item = {"w": text, "s": round(start + w.start, 3), "e": round(start + w.end, 3)}
            # Whisper coupe souvent « c'est » en « c » + « 'est » : on recolle.
            if words and (text[0] in "'-" or words[-1]["w"].endswith(("'", "-"))):
                words[-1]["w"] += text
                words[-1]["e"] = item["e"]
                continue
            words.append(item)
        if not words:
            continue
        segments.append({
            "start": words[0]["s"],
            "end": words[-1]["e"],
            "text": " ".join(x["w"] for x in words),
            "words": words,
        })
        if on_progress:
            on_progress(0.12 + 0.86 * min(1.0, seg.end / duration), "Transcription en cours…")
    return {
        "language": getattr(info, "language", lang or "fr"),
        "range": [round(start, 3), round(end, 3)],
        "model": model_size,
        "segments": segments,
    }


def retime_segment(segment: dict, new_text: str) -> dict:
    """Après une correction manuelle du texte, redistribue le minutage des mots du segment."""
    tokens = new_text.split()
    start, end = float(segment["start"]), float(segment["end"])
    old_words = segment.get("words") or []
    if [w["w"] for w in old_words] == tokens:
        return segment
    if not tokens:
        return {**segment, "text": "", "words": []}
    if len(tokens) == len(old_words):
        words = [{"w": t, "s": w["s"], "e": w["e"]} for t, w in zip(tokens, old_words)]
    else:
        weights = [max(1, len(t)) + 2 for t in tokens]
        total = sum(weights)
        words, cursor = [], start
        for t, wgt in zip(tokens, weights):
            dur = (end - start) * wgt / total
            words.append({"w": t, "s": round(cursor, 3), "e": round(cursor + dur * 0.92, 3)})
            cursor += dur
    return {**segment, "text": " ".join(tokens), "words": words}


_STRIP_PUNCT = re.compile(r"[,.;:…]+$")


def clean_word(word: str, uppercase: bool) -> str:
    word = _STRIP_PUNCT.sub("", word.strip())
    word = word.replace("’", "'")
    return word.upper() if uppercase else word


def build_caption_groups(
    transcript: dict | None,
    clip_start: float,
    clip_end: float,
    max_words: int = 3,
    max_chars: int = 22,
    uppercase: bool = True,
) -> list[dict]:
    """Découpe la transcription en petits blocs de mots, avec des temps relatifs au début du clip."""
    if not transcript:
        return []
    words: list[dict] = []
    for seg in transcript.get("segments", []):
        for i, w in enumerate(seg.get("words", [])):
            if w["e"] <= clip_start or w["s"] >= clip_end:
                continue
            text = clean_word(w["w"], uppercase)
            if not text:
                continue
            words.append({
                "w": text,
                "s": max(0.0, w["s"] - clip_start),
                "e": min(clip_end, w["e"]) - clip_start,
                "brk": i == len(seg["words"]) - 1 or bool(re.search(r"[.!?…]$", w["w"].strip())),
            })
    groups: list[dict] = []
    current: list[dict] = []

    def flush() -> None:
        if current:
            groups.append({"words": list(current), "start": current[0]["s"], "end": current[-1]["e"]})
            current.clear()

    for w in words:
        if current:
            chars = sum(len(x["w"]) + 1 for x in current) + len(w["w"])
            gap = w["s"] - current[-1]["e"]
            if len(current) >= max_words or chars > max_chars or gap > 0.7 or current[-1]["brk"]:
                flush()
        current.append(w)
    flush()
    # Le bloc reste affiché jusqu'au suivant s'il n'y a qu'une petite pause.
    clip_len = clip_end - clip_start
    for a, b in zip(groups, groups[1:]):
        if b["start"] - a["end"] < 0.6:
            a["end"] = b["start"]
        else:
            a["end"] = min(a["end"] + 0.3, b["start"])
    if groups:
        groups[-1]["end"] = min(clip_len, groups[-1]["end"] + 0.4)
    return [g for g in groups if g["end"] - g["start"] > 0.05]
