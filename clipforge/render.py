"""Montage final : construit le graphe de filtres FFmpeg et exporte pour chaque plateforme."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from .analysis import split_heights
from .captions import build_caption_groups
from .config import CAPTION_STYLES, PLATFORMS
from .ffmpeg_utils import FFmpegError, available_hw_encoder, run_with_progress
from .overlays import build_overlay_track

QUALITY = {
    "rapide": {"preset": "veryfast", "crf": 22, "nv": "p3", "cq": 23},
    "equilibre": {"preset": "medium", "crf": 20, "nv": "p5", "cq": 21},
    "max": {"preset": "slow", "crf": 18, "nv": "p7", "cq": 19},
}


def _even(v: float) -> int:
    return max(2, int(round(v / 2)) * 2)


def _crop_px(rect: dict, src_w: int, src_h: int) -> str:
    w = min(src_w, _even(rect["w"] * src_w))
    h = min(src_h, _even(rect["h"] * src_h))
    x = int(round(min(max(0, rect["x"] * src_w), src_w - w)))
    y = int(round(min(max(0, rect["y"] * src_h), src_h - h)))
    return f"crop={w}:{h}:{x}:{y}"


def clip_bounds(edit: dict, source: dict, platform: str) -> tuple[float, float]:
    start = max(0.0, float(edit.get("start", 0)))
    end = float(edit.get("end") or source["duration"])
    end = min(end, source["duration"]) if source.get("duration") else end
    if end - start < 0.5:
        end = start + 0.5
    max_d = PLATFORMS[platform]["max_duration"]
    if max_d and end - start > max_d:
        end = start + max_d
    return start, end


def build_video_filters(edit: dict, source: dict, platform: str) -> list[str]:
    """Renvoie la liste des chaînes de filtres, qui produisent l'étiquette [base]."""
    p = PLATFORMS[platform]
    W, H = p["width"], p["height"]
    sw, sh = source["width"], source["height"]
    fps = min(60.0, source.get("fps") or 30.0)
    pre = f"[0:v]fps={fps:g},setsar=1" if (source.get("fps") or 30) > 60.5 else "[0:v]setsar=1"
    if not p["vertical"]:
        return [
            f"{pre},scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[base]"
        ]

    layout = edit.get("layout", "blur")
    if layout == "split":
        top, bottom = split_heights(float(edit.get("split_ratio", 0.4)), H)
        cam, game = edit["cam"], edit["game"]
        return [
            f"{pre},split=2[s_cam][s_game]",
            f"[s_cam]{_crop_px(cam, sw, sh)},scale={W}:{top}:force_original_aspect_ratio=increase,"
            f"crop={W}:{top},setsar=1[cam]",
            f"[s_game]{_crop_px(game, sw, sh)},scale={W}:{bottom}:force_original_aspect_ratio=increase,"
            f"crop={W}:{bottom},setsar=1[game]",
            "[cam][game]vstack=inputs=2[stack]",
            # Fine ligne de séparation entre la facecam et le jeu.
            f"[stack]drawbox=x=0:y={top - 3}:w={W}:h=6:color=black@0.85:t=fill[base]",
        ]
    if layout == "crop":
        return [
            f"{pre},{_crop_px(edit['crop'], sw, sh)},scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1[base]"
        ]
    # Fond flou : la vidéo au centre, une version agrandie et floutée derrière.
    main = edit.get("main") or {"x": 0, "y": 0, "w": 1, "h": 1}
    zoom = float(edit.get("blur_zoom", 1.0) or 1.0)
    fg_w = _even(min(W * zoom, W * 1.8))
    offset = float(edit.get("blur_offset", 0.0) or 0.0)
    return [
        f"{pre},split=2[s_bg][s_fg]",
        f"[s_bg]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
        f"boxblur=10:3,eq=brightness=-0.12:saturation=1.25,scale={W}:{H},setsar=1[bg]",
        f"[s_fg]{_crop_px(main, sw, sh)},scale={fg_w}:-2,setsar=1[fg]",
        f"[bg][fg]overlay=x=(W-w)/2:y=(H-h)/2+{int(offset * H)}:shortest=1[base]",
    ]


def encoder_args(settings: dict, fps: float) -> list[str]:
    q = QUALITY.get(settings.get("quality", "equilibre"), QUALITY["equilibre"])
    hw = available_hw_encoder() if settings.get("gpu", "auto") == "auto" else None
    common = ["-pix_fmt", "yuv420p", "-r", f"{fps:g}", "-movflags", "+faststart"]
    if hw == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", q["nv"], "-rc", "vbr", "-cq", str(q["cq"]), "-b:v", "0",
                "-maxrate", "20M", "-bufsize", "40M", "-profile:v", "high", *common]
    if hw == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", str(q["cq"]), "-profile:v", "high", *common]
    if hw == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "balanced", "-rc", "cqp", "-qp_i", str(q["cq"] - 2),
                "-qp_p", str(q["cq"]), "-profile:v", "high", *common]
    if hw == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", "14M", "-profile:v", "high", *common]
    return ["-c:v", "libx264", "-preset", q["preset"], "-crf", str(q["crf"]), "-profile:v", "high",
            "-maxrate", "20M", "-bufsize", "40M", *common]


def software_encoder_args(settings: dict, fps: float) -> list[str]:
    return encoder_args({**settings, "gpu": "off"}, fps)


def render_export(
    project_dir: Path,
    project: dict,
    platform: str,
    settings: dict,
    on_progress: Callable[[float], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    source = project["source"]
    edit = project["edit"]
    src_path = project_dir / source["file"]
    start, end = clip_bounds(edit, source, platform)
    duration = end - start
    p = PLATFORMS[platform]
    W, H = p["width"], p["height"]
    fps = min(60.0, source.get("fps") or 30.0)

    caps = edit.get("captions", {})
    style = CAPTION_STYLES.get(caps.get("style", "tiktok"), CAPTION_STYLES["tiktok"])
    groups = []
    if caps.get("enabled") and project.get("transcript"):
        groups = build_caption_groups(
            project["transcript"], start, end,
            max_words=int(caps.get("words", 3)),
            max_chars=22 if p["vertical"] else 38,
            uppercase=style.get("uppercase", True),
        )

    work = project_dir / "tmp" / platform
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    if on_progress:
        on_progress(0.01)
    track = build_overlay_track(work, platform, edit, duration, groups)

    inputs = ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(src_path)]
    filters = build_video_filters(edit, source, platform)
    label = "base"
    next_input = 1
    if track:
        inputs += ["-f", "concat", "-safe", "0", "-i", str(track)]
        filters.append(f"[{label}][{next_input}:v]overlay=0:0:format=auto:eof_action=repeat[ov]")
        label = "ov"
        next_input += 1
    if edit.get("progress_bar"):
        bar_h = 12 if p["vertical"] else 10
        bar_y = 0 if p["vertical"] else H - bar_h
        filters.append(f"color=c=0x9146FF:s={W}x{bar_h}:r={fps:g}:d={duration:.3f}[bar]")
        filters.append(
            f"[{label}][bar]overlay=x='-W+W*t/{duration:.3f}':y={bar_y}:eof_action=pass[pb]"
        )
        label = "pb"
    if edit.get("fade", True):
        fade_out = max(0.0, duration - 0.35)
        filters.append(f"[{label}]fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.3f}:d=0.35[fd]")
        label = "fd"
    filters.append(f"[{label}]format=yuv420p[vout]")

    if source.get("has_audio", True):
        audio_chain = "[0:a]aresample=48000"
        if edit.get("normalize_audio", True):
            audio_chain += ",loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"
        if edit.get("fade", True):
            audio_chain += f",afade=t=in:st=0:d=0.2,afade=t=out:st={max(0.0, duration - 0.4):.3f}:d=0.4"
        filters.append(audio_chain + "[aout]")
    else:
        filters.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{duration:.3f}[aout]")

    out_dir = project_dir / "exports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{platform}.mp4"
    tmp_out = out_dir / f".{platform}.en-cours.mp4"

    def build_args(enc: list[str]) -> list[str]:
        return [
            *inputs,
            "-filter_complex", ";".join(filters),
            "-map", "[vout]", "-map", "[aout]",
            *enc,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{duration:.3f}",
            str(tmp_out),
        ]

    try:
        run_with_progress(build_args(encoder_args(settings, fps)), duration, on_progress, cancel_check)
    except FFmpegError as exc:
        if str(exc) == "Annulé" or settings.get("gpu") == "off" or not available_hw_encoder():
            raise
        # L'encodeur de la carte graphique a échoué : on retente avec le processeur.
        run_with_progress(build_args(software_encoder_args(settings, fps)), duration, on_progress, cancel_check)
    tmp_out.replace(out_path)
    shutil.rmtree(work, ignore_errors=True)
    return out_path
