"""Dessin des textes (accroche, sous-titres, pseudo) en images PNG transparentes.

Toutes les incrustations d'un export sont regroupées en une seule « piste » d'images
lue par FFmpeg (démultiplexeur concat), ce qui marche avec n'importe quelle version de FFmpeg.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import CAPTION_STYLES, FONTS, PLATFORMS, TITLE_STYLES


# Les polices incrustées n'ont pas d'emojis : on les retire de l'image (ils restent dans la description).
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF"
    "\U00002300-\U000023FF️‍\U000E0020-\U000E007F]"
)


def strip_emoji(text: str) -> str:
    return re.sub(r"\s{2,}", " ", EMOJI_RE.sub("", text or "")).strip()


@functools.lru_cache(maxsize=64)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS.get(name, FONTS["poppins"])
    return ImageFont.truetype(str(path), size)


def hex_to_rgba(value: str | None, default=(0, 0, 0, 0)) -> tuple[int, int, int, int]:
    if not value:
        return default
    v = value.lstrip("#")
    if len(v) == 6:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), 255
    if len(v) == 8:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), int(v[6:8], 16)
    return default


# ---------------------------------------------------------------------------
# Placement des éléments selon la plateforme et la mise en page
# ---------------------------------------------------------------------------

@dataclass
class Placement:
    width: int
    height: int
    title_y: float  # haut du bloc titre (px)
    caption_center_y: float
    caption_max_w: float
    caption_size: int
    title_size: int
    title_max_w: float
    watermark_y: float
    watermark_size: int
    vertical: bool
    title_centered: bool = False  # True : title_y est le centre du bloc (et non le haut)


def compute_placement(platform: str, edit: dict) -> Placement:
    p = PLATFORMS[platform]
    W, H = p["width"], p["height"]
    caps = edit.get("captions", {})
    size_factor = {"petit": 0.82, "moyen": 1.0, "grand": 1.2}.get(caps.get("size", "moyen"), 1.0)
    if p["vertical"]:
        safe_bottom = H * (1 - p["safe_bottom"])
        layout = edit.get("layout", "blur")
        ratio = float(edit.get("split_ratio", 0.4))
        pos = caps.get("position", "auto")
        if pos == "haut":
            cy = H * 0.30
        elif pos == "milieu":
            cy = H * 0.50
        elif pos == "bas":
            cy = safe_bottom - H * 0.07
        else:  # auto
            if layout == "split":
                # Au milieu de la zone de jeu, sous la facecam.
                cy = H * (ratio + (1 - ratio) * 0.42)
            elif layout == "blur":
                cy = H * 0.68
            else:
                cy = H * 0.66
        cy = min(cy, safe_bottom - H * 0.06)
        # En mode facecam, le titre se pose à cheval sur la séparation pour ne pas cacher le visage.
        title_on_junction = layout == "split"
        return Placement(
            width=W,
            height=H,
            title_y=H * ratio if title_on_junction else H * (p["safe_top"] + 0.015),
            title_centered=title_on_junction,
            caption_center_y=cy,
            caption_max_w=W * (0.86 - p["safe_right"] * 0.5),
            caption_size=int(92 * size_factor),
            title_size=62,
            title_max_w=W * 0.84,
            watermark_y=safe_bottom - H * 0.012,
            watermark_size=38,
            vertical=True,
        )
    pos = caps.get("position", "auto")
    cy = {"haut": H * 0.18, "milieu": H * 0.5}.get(pos, H * 0.84)
    return Placement(
        width=W,
        height=H,
        title_y=H * 0.06,
        caption_center_y=cy,
        caption_max_w=W * 0.7,
        caption_size=int(74 * size_factor),
        title_size=54,
        title_max_w=W * 0.6,
        watermark_y=H * 0.94,
        watermark_size=34,
        vertical=False,
    )


# ---------------------------------------------------------------------------
# Mise en forme du texte
# ---------------------------------------------------------------------------

def wrap_words(words: list[str], fnt: ImageFont.FreeTypeFont, max_w: float) -> list[list[int]]:
    """Répartit des mots en lignes ; renvoie les indices des mots de chaque ligne."""
    space = fnt.getlength(" ")
    lines: list[list[int]] = [[]]
    width = 0.0
    for i, w in enumerate(words):
        wl = fnt.getlength(w)
        if lines[-1] and width + space + wl > max_w:
            lines.append([])
            width = 0.0
        if lines[-1]:
            width += space
        lines[-1].append(i)
        width += wl
    return [ln for ln in lines if ln]


def _balanced_lines(words: list[str], fnt: ImageFont.FreeTypeFont, max_w: float, max_lines: int) -> list[list[int]]:
    lines = wrap_words(words, fnt, max_w)
    if len(lines) == 2 and len(words) >= 3:
        # Équilibre deux lignes pour éviter un mot seul en bas.
        total = fnt.getlength(" ".join(words))
        lines = wrap_words(words, fnt, max(total * 0.55, max(fnt.getlength(w) for w in words)) + 1)
        if len(lines) > max_lines:
            lines = wrap_words(words, fnt, max_w)
    return lines


def draw_caption(canvas: Image.Image, place: Placement, words: list[str], active: int | None, style_key: str) -> None:
    cleaned = [strip_emoji(w) for w in words]
    if active is not None and not cleaned[active]:
        active = None
    keep = [i for i, w in enumerate(cleaned) if w]
    if not keep:
        return
    active = keep.index(active) if active in keep else None
    words = [cleaned[i] for i in keep]
    style = CAPTION_STYLES.get(style_key, CAPTION_STYLES["tiktok"])
    size = place.caption_size
    fnt = font(style["font"], size)
    lines = _balanced_lines(words, fnt, place.caption_max_w, 3)
    while len(lines) > 2 and size > 48:
        size -= 6
        fnt = font(style["font"], size)
        lines = _balanced_lines(words, fnt, place.caption_max_w, 3)

    ascent, descent = fnt.getmetrics()
    line_h = int((ascent + descent) * 1.08)
    block_h = line_h * len(lines)
    top = place.caption_center_y - block_h / 2
    space = fnt.getlength(" ")
    stroke = max(4, size // 11) if style.get("stroke") else 0
    color = hex_to_rgba(style["color"])
    hl = hex_to_rgba(style.get("highlight"))
    stroke_col = hex_to_rgba(style.get("stroke"), (0, 0, 0, 255))

    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    # Ombre douce sous le texte pour la lisibilité.
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)

    pop = bool(style.get("pop"))
    big = font(style["font"], int(size * 1.12)) if pop else fnt
    space += stroke * 1.2

    def word_w(i: int) -> float:
        return (big if (pop and active == i) else fnt).getlength(words[i])

    for li, line in enumerate(lines):
        line_w = sum(word_w(i) for i in line) + space * (len(line) - 1)
        x = place.width / 2 - line_w / 2
        y = top + li * line_h
        if style.get("box"):
            pad_x, pad_y = size * 0.28, size * 0.10
            draw.rounded_rectangle(
                (x - pad_x, y - pad_y, x + line_w + pad_x, y + line_h - pad_y * 0.2),
                radius=int(size * 0.25),
                fill=hex_to_rgba(style["box"]),
            )
        for i in line:
            w = words[i]
            wl = word_w(i)
            is_active = active == i
            if is_active and style.get("highlight_box"):
                pad = size * 0.12
                draw.rounded_rectangle(
                    (x - pad, y - pad * 0.3, x + wl + pad, y + line_h - pad * 0.6),
                    radius=int(size * 0.18),
                    fill=hex_to_rgba(style["highlight_box"]),
                )
            fill = hl if is_active else color
            if is_active and pop:
                by = y - size * 0.07
                sdraw.text((x + 4, by + 6), w, font=big, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
                draw.text((x, by), w, font=big, fill=fill, stroke_width=stroke, stroke_fill=stroke_col)
            else:
                sdraw.text((x + 4, y + 6), w, font=fnt, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
                draw.text((x, y), w, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_col)
            x += wl + space
    if not style.get("box"):
        bbox = shadow.getbbox()
        if bbox:
            region = shadow.crop(bbox).filter(ImageFilter.GaussianBlur(6))
            canvas.alpha_composite(region, (bbox[0], bbox[1]))
    canvas.alpha_composite(layer)


def draw_title(canvas: Image.Image, place: Placement, text: str, style_key: str) -> None:
    text = strip_emoji(text)
    if not text:
        return
    style = TITLE_STYLES.get(style_key, TITLE_STYLES["blanc"])
    size = place.title_size if style.get("box") else int(place.title_size * 1.35)
    words = text.split()
    fnt = font(style["font"], size)
    lines = wrap_words(words, fnt, place.title_max_w)
    while len(lines) > 3 and size > 34:
        size -= 4
        fnt = font(style["font"], size)
        lines = wrap_words(words, fnt, place.title_max_w)
    ascent, descent = fnt.getmetrics()
    line_h = int((ascent + descent) * 1.02)
    pad_x, pad_y = int(size * 0.55), int(size * 0.35)
    line_ws = [fnt.getlength(" ".join(words[i] for i in ln)) for ln in lines]
    box_w = max(line_ws) + pad_x * 2
    box_h = line_h * len(lines) + pad_y * 2
    if place.vertical:
        x0 = (place.width - box_w) / 2
    else:
        x0 = place.width * 0.04
    y0 = place.title_y - box_h / 2 if place.title_centered else place.title_y
    draw = ImageDraw.Draw(canvas)
    if style.get("box"):
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (x0 + 6, y0 + 10, x0 + box_w + 6, y0 + box_h + 10), radius=int(size * 0.45), fill=(0, 0, 0, 110)
        )
        bbox = shadow.getbbox()
        if bbox:
            canvas.alpha_composite(shadow.crop(bbox).filter(ImageFilter.GaussianBlur(8)), (bbox[0], bbox[1]))
        draw.rounded_rectangle((x0, y0, x0 + box_w, y0 + box_h), radius=int(size * 0.45), fill=hex_to_rgba(style["box"]))
    stroke = max(4, size // 10) if style.get("stroke") else 0
    for li, ln in enumerate(lines):
        line = " ".join(words[i] for i in ln)
        lw = line_ws[li]
        if place.vertical:
            lx = (place.width - lw) / 2
        else:
            lx = x0 + pad_x
        ly = y0 + pad_y + li * line_h - size * 0.04
        draw.text(
            (lx, ly), line, font=fnt, fill=hex_to_rgba(style["color"]),
            stroke_width=stroke, stroke_fill=hex_to_rgba(style.get("stroke"), (0, 0, 0, 255)),
        )


def draw_watermark(canvas: Image.Image, place: Placement, text: str) -> None:
    text = strip_emoji(text)
    if not text:
        return
    fnt = font("poppins-bold", place.watermark_size)
    tw = fnt.getlength(text)
    ascent, descent = fnt.getmetrics()
    th = ascent + descent
    dot = th * 0.55
    pad = place.watermark_size * 0.45
    total_w = dot + pad * 0.8 + tw
    if place.vertical:
        x = (place.width - total_w) / 2
        y = place.watermark_y - th
    else:
        x = place.width - total_w - place.width * 0.03
        y = place.height * 0.05
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (x - pad, y - pad * 0.45, x + total_w + pad, y + th + pad * 0.35),
        radius=int(th * 0.6),
        fill=(14, 14, 16, 150),
    )
    cy = y + th / 2 + th * 0.04
    draw.ellipse((x, cy - dot / 2, x + dot, cy + dot / 2), fill=(145, 70, 255, 255))
    draw.text((x + dot + pad * 0.8, y), text, font=fnt, fill=(255, 255, 255, 235))


# ---------------------------------------------------------------------------
# Piste d'incrustation complète
# ---------------------------------------------------------------------------

def _states(duration: float, title: dict, groups: list[dict]) -> list[tuple[float, float, tuple]]:
    """Découpe la durée en intervalles où l'affichage ne change pas.

    Chaque état = (titre visible ?, index du groupe de sous-titres, index du mot actif).
    """
    cuts = {0.0, duration}
    title_on = bool(title.get("enabled") and title.get("text", "").strip())
    title_end = duration
    if title_on and float(title.get("duration", 0) or 0) > 0:
        title_end = min(duration, float(title["duration"]))
        cuts.add(title_end)
    for g in groups:
        cuts.add(max(0.0, min(duration, g["start"])))
        cuts.add(max(0.0, min(duration, g["end"])))
        for w in g["words"]:
            cuts.add(max(0.0, min(duration, w["s"])))
    points = sorted(c for c in cuts if 0 <= c <= duration)
    states = []
    for a, b in zip(points, points[1:]):
        if b - a < 0.02:
            continue
        mid = (a + b) / 2
        t_on = title_on and mid < title_end
        gi, wi = None, None
        for idx, g in enumerate(groups):
            if g["start"] <= mid < g["end"]:
                gi = idx
                wi = 0
                for j, w in enumerate(g["words"]):
                    if w["s"] <= mid:
                        wi = j
                break
        states.append((a, b, (t_on, gi, wi)))
    # Fusionne les intervalles consécutifs identiques.
    merged: list[list] = []
    for a, b, key in states:
        if merged and merged[-1][2] == key and abs(merged[-1][1] - a) < 1e-6:
            merged[-1][1] = b
        else:
            merged.append([a, b, key])
    return [(a, b, k) for a, b, k in merged]


def build_overlay_track(
    out_dir: Path,
    platform: str,
    edit: dict,
    duration: float,
    groups: list[dict],
) -> Path | None:
    """Génère les images PNG + le fichier ffconcat. Renvoie None s'il n'y a rien à incruster."""
    title = edit.get("title", {})
    caps = edit.get("captions", {})
    watermark = edit.get("watermark", {})
    wm_text = strip_emoji(watermark.get("text", "")) if watermark.get("enabled") else ""
    if not caps.get("enabled"):
        groups = []
    title_ok = bool(title.get("enabled") and strip_emoji(title.get("text", "")))
    if not groups and not title_ok and not wm_text.strip():
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    place = compute_placement(platform, edit)
    style_key = caps.get("style", "tiktok")
    highlight = caps.get("highlight", True)
    rendered: dict[tuple, str] = {}
    entries: list[tuple[str, float]] = []
    for a, b, key in _states(duration, title, groups):
        t_on, gi, wi = key
        if not highlight:
            key = (t_on, gi, None)
            wi = None
        if key not in rendered:
            img = Image.new("RGBA", (place.width, place.height), (0, 0, 0, 0))
            if wm_text:
                draw_watermark(img, place, wm_text)
            if gi is not None:
                draw_caption(img, place, [w["w"] for w in groups[gi]["words"]], wi, style_key)
            if t_on:
                draw_title(img, place, title.get("text", ""), title.get("style", "blanc"))
            name = f"o{len(rendered):04d}.png"
            img.save(out_dir / name, compress_level=1)
            rendered[key] = name
        entries.append((rendered[key], b - a))
    lines = ["ffconcat version 1.0"]
    for name, dur in entries:
        lines.append(f"file '{name}'")
        lines.append(f"duration {dur:.4f}")
    # Le démultiplexeur ignore la durée de la dernière entrée : on la répète.
    lines.append(f"file '{entries[-1][0]}'")
    track = out_dir / "piste.ffconcat"
    track.write_text("\n".join(lines) + "\n", "utf-8")
    return track


def render_preview_png(platform: str, edit: dict, words: list[str] | None, dest: Path) -> None:
    """Petit aperçu des textes (utile pour les tests)."""
    place = compute_placement(platform, edit)
    img = Image.new("RGBA", (place.width, place.height), (40, 40, 48, 255))
    wm = edit.get("watermark", {})
    if wm.get("enabled"):
        draw_watermark(img, place, wm.get("text", ""))
    if words:
        draw_caption(img, place, words, 1, edit.get("captions", {}).get("style", "tiktok"))
    title = edit.get("title", {})
    if title.get("enabled"):
        draw_title(img, place, title.get("text", ""), title.get("style", "blanc"))
    img.convert("RGB").save(dest)
