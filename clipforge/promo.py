"""Intro (YouTube 16:9) et fin (TikTok, Reels, Shorts) : « envoie tes clips » + abonne-toi + cloche.

Les séquences sont dessinées image par image avec Pillow (texte en anglais), avec un fond flou tiré
du clip, une petite animation (bouton cliqué, cloche qui sonne) et des bruitages synthétisés.
"""
from __future__ import annotations

import hashlib
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .config import PLATFORMS
from .ffmpeg_utils import _NO_WINDOW, ffmpeg_path, run
from .overlays import font, hex_to_rgba, strip_emoji

CARD_FPS = 30
DURATION = {"intro": 4.0, "outro": 3.6}

DEFAULT_TEXTS = {
    "intro": "WANT TO BE IN OUR NEXT VIDEO?",
    "outro": "SEND US YOUR CLIPS!",
    "send": "Send your clips to",
    "featured": "and get featured in our next videos",
    "notify": "Turn on notifications so you never miss a clip!",
    "no_email": "DON'T MISS THE NEXT CLIPS!",
}
# Bouton d'appel à l'action selon la plateforme (couleur, texte avant / après le clic).
BUTTONS = {
    "youtube": ("#FF0033", "SUBSCRIBE", "SUBSCRIBED"),
    "shorts": ("#FF0033", "SUBSCRIBE", "SUBSCRIBED"),
    "tiktok": ("#FE2C55", "FOLLOW", "FOLLOWING"),
    "reels": ("#0095F6", "FOLLOW", "FOLLOWING"),
}
ACCENT = "#9146FF"


# ---------------------------------------------------------------------------
# Petites fonctions d'animation
# ---------------------------------------------------------------------------

def _prog(t: float, t0: float, t1: float) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return (t - t0) / (t1 - t0)


def _ease_out(x: float) -> float:
    return 1 - (1 - x) ** 3


def _back_out(x: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _with_alpha(layer: Image.Image, a: float) -> Image.Image:
    if a >= 0.999:
        return layer
    out = layer.copy()
    out.putalpha(layer.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return out


def _fit_font(text: str, name: str, size: int, max_w: float):
    f = font(name, size)
    while f.getlength(text) > max_w and size > 18:
        size -= 2
        f = font(name, size)
    return f


def _text_layer(text: str, name: str, size: int, max_w: float, color="#FFFFFF", stroke=0) -> Image.Image:
    f = _fit_font(text, name, size, max_w)
    w = int(f.getlength(text)) + stroke * 2 + 8
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (w, asc + desc + stroke * 2 + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if stroke:
        d.text((stroke + 4, stroke + 4), text, font=f, fill=hex_to_rgba(color), stroke_width=stroke,
               stroke_fill=(0, 0, 0, 255))
    else:
        d.text((4 + 3, 4 + 5), text, font=f, fill=(0, 0, 0, 120))  # petite ombre
        d.text((4, 4), text, font=f, fill=hex_to_rgba(color))
    return img


def _pill(text: str, size: int, bg: str, fg: str = "#FFFFFF", max_w: float = 2000) -> Image.Image:
    f = _fit_font(text, "poppins", size, max_w - size * 1.6)
    tw = f.getlength(text)
    asc, desc = f.getmetrics()
    h = int((asc + desc) * 1.35)
    w = int(tw + size * 1.6)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=hex_to_rgba(bg))
    d.text(((w - tw) / 2, (h - (asc + desc)) / 2 - size * 0.02), text, font=f, fill=hex_to_rgba(fg))
    return img


def _bell(size: int, filled: bool) -> Image.Image:
    """Cloche dessinée (pas d'emoji : les polices n'en ont pas)."""
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (255, 255, 255, 255) if filled else (255, 255, 255, 230)
    d.ellipse((0.44 * s, 0.08 * s, 0.56 * s, 0.2 * s), fill=col)  # attache
    d.rounded_rectangle((0.27 * s, 0.16 * s, 0.73 * s, 0.76 * s), radius=int(0.22 * s), fill=col)  # corps
    d.rounded_rectangle((0.14 * s, 0.64 * s, 0.86 * s, 0.77 * s), radius=int(0.06 * s), fill=col)  # bord
    d.ellipse((0.42 * s, 0.76 * s, 0.58 * s, 0.92 * s), fill=col)  # battant
    if not filled:
        # Contour seulement : on évide l'intérieur.
        inner = Image.new("L", (s, s), 0)
        di = ImageDraw.Draw(inner)
        di.rounded_rectangle((0.33 * s, 0.24 * s, 0.67 * s, 0.68 * s), radius=int(0.16 * s), fill=255)
        alpha = img.getchannel("A")
        alpha.paste(0, mask=inner)
        img.putalpha(alpha)
    return img


def _bell_button(size: int, filled: bool, angle: float) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, size - 1, size - 1), fill=(255, 255, 255, 40) if not filled else hex_to_rgba(ACCENT))
    bell = _bell(int(size * 0.62), filled)
    if angle:
        bell = bell.rotate(angle, resample=Image.BICUBIC, center=(bell.width / 2, bell.height * 0.1))
    img.alpha_composite(bell, (int((size - bell.width) / 2), int((size - bell.height) / 2 + size * 0.02)))
    return img


def _cursor(scale: float) -> Image.Image:
    s = 2.2 * scale
    pts = [(0, 0), (0, 52), (13, 40), (22, 60), (31, 56), (22, 37), (40, 37)]
    pts = [(4 + x * s, 4 + y * s) for x, y in pts]
    img = Image.new("RGBA", (int(48 * s) + 12, int(64 * s) + 12), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=max(2, int(3 * scale)))
    return img


# ---------------------------------------------------------------------------
# Fond
# ---------------------------------------------------------------------------

def make_background(size: tuple[int, int], frame: Image.Image | None) -> Image.Image:
    W, H = size
    if frame is None:
        # Dégradé violet sombre quand on n'a pas d'image du clip (aperçu dans les réglages).
        grad = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        top, bottom = np.array([38, 18, 72]), np.array([10, 10, 18])
        arr = (top * (1 - grad[..., None]) + bottom * grad[..., None]).repeat(W, axis=1)
        return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")
    fr = frame.convert("RGB")
    scale = max(W / fr.width, H / fr.height)
    fr = fr.resize((int(fr.width * scale) + 1, int(fr.height * scale) + 1), Image.BILINEAR)
    left, top = (fr.width - W) // 2, (fr.height - H) // 2
    fr = fr.crop((left, top, left + W, top + H))
    small = fr.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    fr = small.resize((W, H), Image.BICUBIC)
    fr = ImageEnhance.Brightness(fr).enhance(0.42)
    tint = Image.new("RGB", (W, H), (70, 30, 140))
    return Image.blend(fr, tint, 0.18).convert("RGBA")


# ---------------------------------------------------------------------------
# Séquence complète
# ---------------------------------------------------------------------------

def _layout(kind: str, platform: str, size: tuple[int, int], email: str, headline: str) -> dict:
    W, H = size
    vertical = H > W
    color, label, label_done = BUTTONS.get(platform, BUTTONS["youtube"])
    has_email = bool(email)
    if not has_email:
        headline = DEFAULT_TEXTS["no_email"]
    if vertical:
        p = PLATFORMS.get(platform, PLATFORMS["tiktok"])
        top, bottom = H * (p["safe_top"] + 0.06), H * (1 - p["safe_bottom"])
        max_w = W * 0.86
        words = headline.split()
        # Gros titre sur deux lignes en vertical.
        half = max(1, len(words) // 2 + len(words) % 2)
        lines = [" ".join(words[:half]), " ".join(words[half:])] if len(words) > 2 else [headline]
        layers = {f"head{i}": _text_layer(t, "anton", 130, max_w, stroke=0) for i, t in enumerate(lines)}
        ys = {f"head{i}": top + i * 150 for i in range(len(lines))}
        y = top + len(lines) * 150 + 40
        if has_email:
            layers["email"] = _pill(email, 58, ACCENT, max_w=max_w)
            ys["email"] = y
            y += layers["email"].height + 34
            layers["sub"] = _text_layer(DEFAULT_TEXTS["featured"], "poppins-bold", 46, max_w, "#E8E2FF")
            ys["sub"] = y
            y += 130
        btn_size = 64
        notify_size = 40
        y_btn = max(y, (top + bottom) / 2 + 40)
        y_notify = min(bottom - 90, y_btn + 170)
    else:
        max_w = W * 0.8
        layers = {"head0": _text_layer(headline, "anton", 112, max_w)}
        ys = {"head0": H * 0.15}
        if has_email:
            layers["send"] = _text_layer(DEFAULT_TEXTS["send"], "poppins-bold", 50, max_w, "#E8E2FF")
            ys["send"] = H * 0.33
            layers["email"] = _pill(email, 64, ACCENT, max_w=max_w)
            ys["email"] = H * 0.42
        btn_size = 56
        notify_size = 40
        y_btn = H * (0.64 if has_email else 0.45)
        y_notify = y_btn + 150
    btn = _pill(label, btn_size, color)
    btn_done = _pill(label_done, btn_size, "#3A3A44", "#BDBDC6")
    bell_px = btn.height
    layers["notify"] = _text_layer(DEFAULT_TEXTS["notify"], "poppins-bold", notify_size, W * 0.86)
    ys["notify"] = y_notify
    gap = 28
    row_w = max(btn.width, btn_done.width) + gap + bell_px
    x_btn = (W - row_w) / 2
    x_bell = x_btn + max(btn.width, btn_done.width) + gap
    return {
        "layers": layers, "ys": ys, "btn": btn, "btn_done": btn_done, "bell_px": bell_px,
        "x_btn": x_btn, "x_bell": x_bell, "y_btn": y_btn,
    }


def _timeline(kind: str) -> dict:
    if kind == "intro":
        return {"click": 2.25, "bell": 3.0, "dur": DURATION["intro"]}
    return {"click": 1.75, "bell": 2.45, "dur": DURATION["outro"]}


def render_frames(kind: str, platform: str, size: tuple[int, int], bg: Image.Image, email: str, headline: str):
    """Génère les images (RGB) de la séquence, une par une."""
    W, H = size
    L = _layout(kind, platform, size, email, headline)
    tl = _timeline(kind)
    n = int(round(tl["dur"] * CARD_FPS))
    order = [k for k in L["layers"] if k.startswith("head")] + [k for k in ("send", "email", "sub") if k in L["layers"]]
    btn_w = L["btn"].width
    btn_c = (L["x_btn"] + btn_w / 2, L["y_btn"] + L["btn"].height / 2)
    bell_c = (L["x_bell"] + L["bell_px"] / 2, L["y_btn"] + L["bell_px"] / 2)
    start_c = (W * 0.82, H * 0.95)
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    for i in range(n):
        t = i / CARD_FPS
        frame = bg.copy()
        # Textes : apparition en glissant vers le haut, l'un après l'autre.
        for j, key in enumerate(order):
            a = _ease_out(_prog(t, 0.12 + 0.18 * j, 0.5 + 0.18 * j))
            if a <= 0:
                continue
            layer = L["layers"][key]
            if key == "email":
                sc = max(0.05, _back_out(_prog(t, 0.2 + 0.18 * j, 0.6 + 0.18 * j)))
                layer = layer.resize((max(1, int(layer.width * sc)), max(1, int(layer.height * sc))), Image.BICUBIC)
            x = (W - layer.width) / 2
            y = L["ys"][key] + (1 - a) * 40 + (L["layers"][key].height - layer.height) / 2
            frame.alpha_composite(_with_alpha(layer, a), (int(x), int(y)))
        # Bouton + cloche.
        a_row = _back_out(_prog(t, 0.75, 1.15)) if t > 0.75 else 0
        if a_row > 0:
            clicked = t >= tl["click"]
            btn = L["btn_done"] if clicked else L["btn"]
            press = 1 - 0.08 * math.sin(math.pi * _prog(t, tl["click"] - 0.08, tl["click"] + 0.12))
            sc = max(0.05, a_row) * press
            b = btn.resize((max(1, int(btn.width * sc)), max(1, int(btn.height * sc))), Image.BICUBIC)
            frame.alpha_composite(_with_alpha(b, min(1, a_row)), (int(btn_c[0] - b.width / 2), int(btn_c[1] - b.height / 2)))
            ring = t >= tl["bell"]
            angle = 0.0
            if ring:
                k = t - tl["bell"]
                angle = 24 * math.sin(k * 28) * math.exp(-k * 3.2)
            bell = _bell_button(L["bell_px"], ring, angle)
            bs = max(0.05, a_row)
            bell = bell.resize((max(1, int(bell.width * bs)), max(1, int(bell.height * bs))), Image.BICUBIC)
            frame.alpha_composite(_with_alpha(bell, min(1, a_row)), (int(bell_c[0] - bell.width / 2), int(bell_c[1] - bell.height / 2)))
            if ring:  # petites ondes autour de la cloche
                k = _prog(t, tl["bell"], tl["bell"] + 0.6)
                if k < 1:
                    d = ImageDraw.Draw(frame)
                    r = L["bell_px"] * (0.6 + 0.5 * k)
                    alpha = int(200 * (1 - k))
                    d.arc((bell_c[0] - r, bell_c[1] - r, bell_c[0] + r, bell_c[1] + r), 300, 360, fill=(255, 255, 255, alpha), width=6)
                    d.arc((bell_c[0] - r, bell_c[1] - r, bell_c[0] + r, bell_c[1] + r), 180, 240, fill=(255, 255, 255, alpha), width=6)
        # Ligne « active les notifications ».
        a_n = _ease_out(_prog(t, 1.0, 1.4))
        if a_n > 0:
            layer = L["layers"]["notify"]
            frame.alpha_composite(_with_alpha(layer, a_n), (int((W - layer.width) / 2), int(L["ys"]["notify"] + (1 - a_n) * 30)))
        # Curseur : va cliquer sur le bouton, puis sur la cloche.
        if 1.2 <= t <= tl["bell"] + 0.45:
            if t < tl["click"]:
                k = _ease_out(_prog(t, 1.2, tl["click"] - 0.05))
                pos = (start_c[0] + (btn_c[0] + btn_w * 0.15 - start_c[0]) * k, start_c[1] + (btn_c[1] - start_c[1]) * k)
            else:
                k = _ease_out(_prog(t, tl["click"] + 0.15, tl["bell"] - 0.05))
                p0 = (btn_c[0] + btn_w * 0.15, btn_c[1])
                pos = (p0[0] + (bell_c[0] - p0[0]) * k, p0[1] + (bell_c[1] - p0[1]) * k)
            pressing = abs(t - tl["click"]) < 0.08 or abs(t - tl["bell"]) < 0.08
            cur = _cursor(0.85 if pressing else 1.0)
            fade_out = 1 - _prog(t, tl["bell"] + 0.25, tl["bell"] + 0.45)
            frame.alpha_composite(_with_alpha(cur, fade_out), (int(pos[0]), int(pos[1])))
        # Fondu depuis / vers le noir pour enchaîner avec le clip.
        fade = min(_prog(t, 0, 0.25), 1 - _prog(t, tl["dur"] - 0.25, tl["dur"]))
        if fade < 1:
            frame = Image.blend(black, frame, max(0.0, fade))
        yield frame.convert("RGB")


def write_audio(path: Path, kind: str, sr: int = 48000) -> None:
    """Bruitages : « whoosh » d'entrée, clic sur le bouton, « ding » de la cloche."""
    tl = _timeline(kind)
    n = int(tl["dur"] * sr)
    out = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(7)

    def add(sig: np.ndarray, t: float) -> None:
        i = int(t * sr)
        j = min(n, i + len(sig))
        if i < n:
            out[i:j] += sig[: j - i]

    w = rng.uniform(-1, 1, int(0.45 * sr)).astype(np.float32)
    w = np.convolve(w, np.ones(24) / 24, mode="same")
    env = np.sin(np.linspace(0, math.pi, len(w))) ** 2
    add(0.35 * w * env, 0.08)
    click = rng.uniform(-1, 1, int(0.025 * sr)).astype(np.float32) * np.exp(-np.linspace(0, 9, int(0.025 * sr)))
    add(0.55 * click, tl["click"])
    add(0.4 * click, tl["bell"])
    tt = np.arange(int(1.3 * sr)) / sr
    ding = (np.sin(2 * math.pi * 1568 * tt) + 0.45 * np.sin(2 * math.pi * 3136 * tt) + 0.2 * np.sin(2 * math.pi * 2352 * tt))
    add((0.22 * ding * np.exp(-3.5 * tt)).astype(np.float32), tl["bell"] + 0.02)
    fade = np.ones(n, dtype=np.float32)
    k = int(0.2 * sr)
    fade[-k:] = np.linspace(1, 0, k)
    stereo = np.repeat((np.clip(out * fade, -1, 1) * 32767).astype(np.int16)[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())


def frame_from_video(src: str | Path, t: float) -> Image.Image | None:
    res = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(src),
         "-frames:v", "1", "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, creationflags=_NO_WINDOW,
    )
    if res.returncode != 0 or not res.stdout:
        return None
    import io

    return Image.open(io.BytesIO(res.stdout)).convert("RGB")


def build_card(out_dir: Path, kind: str, platform: str, email: str, headline: str | None,
               frame: Image.Image | None) -> tuple[Path, Path, float]:
    """Crée la vidéo (sans son) et le fichier son de la séquence. Renvoie (vidéo, son, durée)."""
    p = PLATFORMS[platform]
    size = (p["width"], p["height"])
    out_dir.mkdir(parents=True, exist_ok=True)
    email = strip_emoji(email or "").strip()
    headline = strip_emoji(headline or "").strip().upper() or DEFAULT_TEXTS[kind]
    bg = make_background(size, frame)
    video = out_dir / f"{kind}.mp4"
    audio = out_dir / f"{kind}.wav"
    proc = subprocess.Popen(
        [ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{size[0]}x{size[1]}", "-r", str(CARD_FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(video)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_NO_WINDOW,
    )
    assert proc.stdin is not None
    try:
        for img in render_frames(kind, platform, size, bg, email, headline):
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Impossible de créer la séquence {kind} : {err[-300:]}")
    write_audio(audio, kind)
    return video, audio, _timeline(kind)["dur"]


def preview(cache_dir: Path, kind: str, platform: str, email: str, headline: str | None,
            frame: Image.Image | None = None, frame_key: str = "") -> Path:
    """Aperçu jouable (vidéo + son) de la séquence, mis en cache."""
    key = hashlib.sha1(f"v1|{kind}|{platform}|{email}|{headline}|{frame_key}".encode()).hexdigest()[:16]
    out = cache_dir / f"{kind}-{platform}-{key}.mp4"
    if out.exists():
        return out
    work = cache_dir / f"tmp-{key}"
    video, audio, _ = build_card(work, kind, platform, email, headline, frame)
    res = run([ffmpeg_path(), "-hide_banner", "-v", "error", "-y", "-i", str(video), "-i", str(audio),
               "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)])
    for f in work.glob("*"):
        f.unlink(missing_ok=True)
    work.rmdir()
    if res.returncode != 0:
        raise RuntimeError("Impossible de créer l'aperçu.")
    return out
