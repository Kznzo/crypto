"""Outils autour de FFmpeg : localisation, analyse des fichiers, exécution avec progression."""
from __future__ import annotations

import functools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

# Sous Windows, on évite qu'une fenêtre console s'ouvre à chaque appel FFmpeg.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class FFmpegError(RuntimeError):
    pass


@functools.lru_cache(maxsize=1)
def ffmpeg_path() -> str:
    """FFmpeg du système s'il existe, sinon celui fourni par imageio-ffmpeg."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - dépend de l'installation
        raise FFmpegError(
            "FFmpeg est introuvable. Installe-le (https://ffmpeg.org) ou lance "
            "« pip install imageio-ffmpeg »."
        ) from exc


@functools.lru_cache(maxsize=1)
def ffprobe_path() -> str | None:
    found = shutil.which("ffprobe")
    if found:
        return found
    sibling = Path(ffmpeg_path()).with_name("ffprobe" + (".exe" if sys.platform == "win32" else ""))
    return str(sibling) if sibling.exists() else None


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, creationflags=_NO_WINDOW, **kwargs)


def _parse_rate(value: str | None) -> float:
    if not value or value in ("0/0", "N/A"):
        return 0.0
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            return float(num) / float(den) if float(den) else 0.0
        except ValueError:
            return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def probe(path: str | Path) -> dict:
    """Retourne largeur, hauteur, durée, fps et présence d'audio d'une vidéo."""
    path = str(path)
    probe_exe = ffprobe_path()
    if probe_exe:
        res = run([probe_exe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
        if res.returncode == 0:
            data = json.loads(res.stdout.decode("utf-8", "replace") or "{}")
            video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
            audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
            if video:
                rotation = 0
                for side in video.get("side_data_list", []) or []:
                    if "rotation" in side:
                        rotation = int(float(side["rotation"]))
                width, height = int(video["width"]), int(video["height"])
                if abs(rotation) in (90, 270):
                    width, height = height, width
                duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
                return {
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "fps": _parse_rate(video.get("avg_frame_rate")) or _parse_rate(video.get("r_frame_rate")) or 30.0,
                    "has_audio": audio is not None,
                    "vcodec": video.get("codec_name", ""),
                }
    return _probe_with_ffmpeg(path)


def _probe_with_ffmpeg(path: str) -> dict:
    res = run([ffmpeg_path(), "-hide_banner", "-i", path])
    text = res.stderr.decode("utf-8", "replace")
    dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    video = re.search(r"Stream #.*?Video:.*?(\d{2,5})x(\d{2,5})", text)
    if not video:
        raise FFmpegError(f"Impossible de lire la vidéo : {Path(path).name}")
    fps = re.search(r"(\d+(?:\.\d+)?) fps", text)
    vcodec = re.search(r"Stream #.*?Video:\s*([a-z0-9_]+)", text)
    duration = 0.0
    if dur:
        duration = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    width, height = int(video.group(1)), int(video.group(2))
    if re.search(r"rotate\s*:\s*-?(90|270)", text) or re.search(r"rotation of -?(90|270)", text):
        width, height = height, width
    return {
        "width": width,
        "height": height,
        "duration": duration,
        "fps": float(fps.group(1)) if fps else 30.0,
        "has_audio": "Audio:" in text,
        "vcodec": vcodec.group(1) if vcodec else "",
    }


BROWSER_CODECS = {"h264", "vp8", "vp9", "av1"}


def make_preview_proxy(src: str | Path, dest: str | Path) -> None:
    """Copie légère en H.264 720p pour les vidéos que le navigateur ne sait pas lire (HEVC, MKV…)."""
    res = run(
        [
            ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-i", str(src),
            "-vf", "scale=-2:'min(720,ih)'", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dest),
        ]
    )
    if res.returncode != 0:
        raise FFmpegError("Impossible de préparer l'aperçu de la vidéo.")


def run_with_progress(
    args: list[str],
    total_seconds: float,
    on_progress: Callable[[float], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> None:
    """Lance FFmpeg en lisant « -progress pipe:1 » pour suivre l'avancement (0 → 1)."""
    cmd = [ffmpeg_path(), "-hide_banner", "-nostdin", "-y", "-progress", "pipe:1", "-nostats", *args]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=_NO_WINDOW,
    )
    stderr_tail: list[str] = []

    import threading

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for raw in proc.stderr:
            stderr_tail.append(raw.decode("utf-8", "replace").rstrip())
            if len(stderr_tail) > 40:
                del stderr_tail[:-40]

    t = threading.Thread(target=_drain_stderr, daemon=True)
    t.start()
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace").strip()
        if cancel_check and cancel_check():
            proc.kill()
            proc.wait()
            raise FFmpegError("Annulé")
        if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
            try:
                micro = int(line.split("=", 1)[1])
            except ValueError:
                continue
            if on_progress and total_seconds > 0:
                on_progress(max(0.0, min(1.0, micro / 1_000_000 / total_seconds)))
    proc.wait()
    t.join(timeout=2)
    if proc.returncode != 0:
        tail = "\n".join(stderr_tail[-12:])
        raise FFmpegError(f"FFmpeg a échoué (code {proc.returncode}) :\n{tail}")
    if on_progress:
        on_progress(1.0)


@functools.lru_cache(maxsize=1)
def available_hw_encoder() -> str | None:
    """Teste les encodeurs matériels H.264 et renvoie le premier qui marche vraiment."""
    candidates = ["h264_nvenc", "h264_qsv", "h264_amf"]
    if sys.platform == "darwin":
        candidates = ["h264_videotoolbox"]
    try:
        res = run([ffmpeg_path(), "-hide_banner", "-encoders"], timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    listed = res.stdout.decode("utf-8", "replace")
    for enc in candidates:
        if enc not in listed:
            continue
        try:
            test = run(
                [
                    ffmpeg_path(), "-hide_banner", "-v", "error", "-f", "lavfi", "-i",
                    "color=black:s=1080x1920:d=0.2", "-pix_fmt", "yuv420p", "-c:v", enc, "-f", "null", "-",
                ],
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if test.returncode == 0:
            return enc
    return None


def extract_frame(src: str | Path, t: float, dest: str | Path, width: int = 640) -> None:
    res = run(
        [
            ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(src),
            "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4", str(dest),
        ]
    )
    if res.returncode != 0:
        raise FFmpegError(res.stderr.decode("utf-8", "replace")[-500:])
