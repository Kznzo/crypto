"""Analyse automatique : détection de la facecam, choix de la mise en page, moments forts."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .config import MODELS_DIR
from .ffmpeg_utils import _NO_WINDOW, ffmpeg_path

YUNET_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
ANALYSIS_WIDTH = 960

# Les rectangles sont toujours exprimés en fractions de l'image source (0 → 1).
Rect = dict  # {"x": float, "y": float, "w": float, "h": float}

VERTICAL_W, VERTICAL_H = 1080, 1920


@dataclass
class Detection:
    frame: int
    x: float
    y: float
    w: float
    h: float
    score: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class Cluster:
    items: list[Detection] = field(default_factory=list)
    motion: float = 0.0

    @property
    def frames(self) -> set[int]:
        return {d.frame for d in self.items}

    def mean(self, attr: str) -> float:
        return float(np.mean([getattr(d, attr) for d in self.items]))

    def std_center(self) -> float:
        return float(np.hypot(np.std([d.cx for d in self.items]), np.std([d.cy for d in self.items])))


# ---------------------------------------------------------------------------
# Lecture des images
# ---------------------------------------------------------------------------

def sample_frames(src: str | Path, count: int = 10, start: float = 0.0, end: float | None = None) -> list[np.ndarray]:
    import cv2

    cap = cv2.VideoCapture(str(src))
    frames: list[np.ndarray] = []
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = total / fps if total else 0
        if end is None or end <= 0 or (duration and end > duration):
            end = duration
        if not end or end <= start:
            end = start + 1
        span = end - start
        for i in range(count):
            t = start + span * (0.06 + 0.88 * i / max(1, count - 1))
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            h, w = frame.shape[:2]
            scale = ANALYSIS_WIDTH / w
            frames.append(cv2.resize(frame, (ANALYSIS_WIDTH, max(2, int(round(h * scale))))))
    finally:
        cap.release()
    return frames


# ---------------------------------------------------------------------------
# Détection des visages
# ---------------------------------------------------------------------------

def detect_faces(frames: list[np.ndarray]) -> list[Detection]:
    import cv2

    if not frames or not YUNET_MODEL.exists():
        return []
    h, w = frames[0].shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET_MODEL), "", (w, h), 0.6, 0.3, 50)
    out: list[Detection] = []
    for idx, frame in enumerate(frames):
        fh, fw = frame.shape[:2]
        detector.setInputSize((fw, fh))
        _, faces = detector.detect(frame)
        if faces is None:
            continue
        for f in faces:
            x, y, bw, bh = (float(v) for v in f[:4])
            if bw < 8 or bh < 8:
                continue
            out.append(Detection(idx, x / fw, y / fh, bw / fw, bh / fh, float(f[14])))
    return out


def _dist(a: Detection, bx: float, by: float, aspect: float) -> float:
    """Distance en unités de « hauteur d'image » (corrige le ratio largeur/hauteur)."""
    return float(np.hypot((a.cx - bx) * aspect, a.cy - by))


def cluster_detections(dets: list[Detection], aspect: float = 16 / 9) -> list[Cluster]:
    """Regroupe les détections d'un même visage d'une image à l'autre."""
    clusters: list[Cluster] = []
    for d in sorted(dets, key=lambda d: -d.score):
        best, best_dist = None, 1e9
        for c in clusters:
            mw = c.mean("w")
            dist = _dist(d, c.mean("cx"), c.mean("cy"), aspect)
            ratio = d.w / mw if mw else 1
            if (
                dist < 1.6 * max(mw, d.w) * aspect
                and 0.5 < ratio < 2.0
                and d.frame not in c.frames
                and dist < best_dist
            ):
                best, best_dist = c, dist
        if best is None:
            clusters.append(Cluster([d]))
        else:
            best.items.append(d)
    return clusters


def _is_group(cluster: Cluster, dets: list[Detection], aspect: float) -> bool:
    """Vrai si d'autres visages de taille comparable sont souvent juste à côté (scène IRL, plateau…)."""
    own = {id(d) for d in cluster.items}
    crowded = 0
    for d in cluster.items:
        size = d.w * aspect
        for o in dets:
            if o.frame != d.frame or id(o) in own:
                continue
            if 0.5 < o.w / d.w < 2.0 and _dist(o, d.cx, d.cy, aspect) < 4.5 * size:
                crowded += 1
                break
    return crowded >= 0.5 * len(cluster.items)


def _face_motion(cluster: Cluster, frames: list[np.ndarray]) -> float:
    """Différence moyenne de pixels de la zone du visage d'une image à l'autre.

    Une vraie webcam bouge ; une photo de joueur dans un tableau des scores non.
    """
    import cv2

    patches = []
    for d in sorted(cluster.items, key=lambda d: d.frame):
        frame = frames[d.frame]
        fh, fw = frame.shape[:2]
        x0, y0 = int(max(0, (d.cx - d.w) * fw)), int(max(0, (d.cy - d.h) * fh))
        x1, y1 = int(min(fw, (d.cx + d.w) * fw)), int(min(fh, (d.cy + d.h) * fh))
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        patches.append(cv2.resize(gray, (32, 32)).astype(np.float32))
    if len(patches) < 2:
        return 0.0
    diffs = [float(np.mean(np.abs(a - b))) for a, b in zip(patches, patches[1:])]
    return float(np.mean(diffs))


# ---------------------------------------------------------------------------
# Cadre de la webcam
# ---------------------------------------------------------------------------

def _edge_maps(frames: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    import cv2

    gx_sum, gy_sum = None, None
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gx = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
        gy = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
        gx_sum = gx if gx_sum is None else gx_sum + gx
        gy_sum = gy if gy_sum is None else gy_sum + gy
    n = max(1, len(frames))
    return gx_sum / n, gy_sum / n


def _find_border(profile: np.ndarray, positions: np.ndarray) -> int | None:
    """Renvoie la position du bord le plus net (ligne persistante) dans un profil."""
    if profile.size < 5:
        return None
    med = float(np.median(profile)) + 1e-3
    idx = int(np.argmax(profile))
    if profile[idx] > 2.6 * med and profile[idx] > 18:
        return int(positions[idx])
    return None


def estimate_cam_rect(face: Cluster, frames: list[np.ndarray]) -> Rect:
    """Devine le rectangle de la facecam autour du visage, en s'aidant des bords nets."""
    fh, fw = frames[0].shape[:2]
    cx, cy = face.mean("cx") * fw, face.mean("cy") * fh
    w, h = face.mean("w") * fw, face.mean("h") * fh
    gx, gy = _edge_maps(frames)

    # Valeurs par défaut si aucun bord n'est trouvé.
    left, right = cx - 2.3 * w, cx + 2.3 * w
    top, bottom = cy - 1.6 * h, cy + 1.9 * h

    rows = slice(int(max(0, cy - 0.6 * h)), int(min(fh, cy + 1.2 * h)))
    cols = slice(int(max(0, cx - 0.8 * w)), int(min(fw, cx + 0.8 * w)))

    # Gauche
    lo, hi = int(max(0, cx - 4.5 * w)), int(max(0, cx - 1.0 * w))
    if hi - lo > 4:
        prof = gx[rows, lo:hi].mean(axis=0)
        found = _find_border(prof, np.arange(lo, hi))
        left = found if found is not None else (0 if lo == 0 and cx - 2.3 * w < 0.03 * fw else left)
    # Droite
    lo, hi = int(min(fw, cx + 1.0 * w)), int(min(fw, cx + 4.5 * w))
    if hi - lo > 4:
        prof = gx[rows, lo:hi].mean(axis=0)
        found = _find_border(prof, np.arange(lo, hi))
        right = found if found is not None else (fw if hi == fw and cx + 2.3 * w > 0.97 * fw else right)
    # Haut
    lo, hi = int(max(0, cy - 3.0 * h)), int(max(0, cy - 0.9 * h))
    if hi - lo > 4:
        prof = gy[lo:hi, cols].mean(axis=1)
        found = _find_border(prof, np.arange(lo, hi))
        top = found if found is not None else (0 if lo == 0 and cy - 1.6 * h < 0.03 * fh else top)
    # Bas
    lo, hi = int(min(fh, cy + 1.1 * h)), int(min(fh, cy + 4.0 * h))
    if hi - lo > 4:
        prof = gy[lo:hi, cols].mean(axis=1)
        found = _find_border(prof, np.arange(lo, hi))
        bottom = found if found is not None else (fh if hi == fh and cy + 1.9 * h > 0.97 * fh else bottom)

    # Une facecam proche d'un bord de l'image y est presque toujours collée.
    if cx < 3.2 * w:
        left = 0
    if fw - cx < 3.2 * w:
        right = fw
    if cy < 2.6 * h:
        top = 0
    if fh - cy < 2.8 * h:
        bottom = fh

    left, right = max(0.0, float(left)), min(float(fw), float(right))
    top, bottom = max(0.0, float(top)), min(float(fh), float(bottom))
    # Garde-fous : le cadre doit contenir le visage avec de la marge.
    if right - left < 2.2 * w:
        left, right = max(0.0, cx - 2.0 * w), min(float(fw), cx + 2.0 * w)
    if bottom - top < 2.0 * h:
        top, bottom = max(0.0, cy - 1.4 * h), min(float(fh), cy + 1.8 * h)
    return {"x": left / fw, "y": top / fh, "w": (right - left) / fw, "h": (bottom - top) / fh}


# ---------------------------------------------------------------------------
# Géométrie des mises en page
# ---------------------------------------------------------------------------

def fit_rect_to_aspect(rect: Rect, aspect: float, src_aspect: float, anchor: tuple[float, float] | None = None) -> Rect:
    """Rogne un rectangle (en fractions) pour obtenir le ratio largeur/hauteur voulu, en pixels.

    src_aspect = largeur/hauteur de la vidéo source. anchor = point à garder au centre si possible.
    """
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    cur = (w * src_aspect) / h if h else aspect
    ax = anchor[0] if anchor else x + w / 2
    ay = anchor[1] if anchor else y + h / 2
    if cur > aspect:  # trop large → on réduit la largeur
        new_w = h * aspect / src_aspect
        nx = min(max(ax - new_w / 2, x), x + w - new_w)
        return clamp_rect({"x": nx, "y": y, "w": new_w, "h": h})
    new_h = w * src_aspect / aspect
    ny = min(max(ay - new_h / 2, y), y + h - new_h)
    return clamp_rect({"x": x, "y": ny, "w": w, "h": new_h})


def clamp_rect(rect: Rect) -> Rect:
    w = min(1.0, max(0.02, float(rect["w"])))
    h = min(1.0, max(0.02, float(rect["h"])))
    x = min(max(0.0, float(rect["x"])), 1.0 - w)
    y = min(max(0.0, float(rect["y"])), 1.0 - h)
    return {"x": round(x, 5), "y": round(y, 5), "w": round(w, 5), "h": round(h, 5)}


def split_heights(ratio: float, out_h: int = VERTICAL_H) -> tuple[int, int]:
    top = int(round(out_h * ratio / 2)) * 2
    return top, out_h - top


def game_rect_for_split(ratio: float, src_aspect: float, center_x: float = 0.5) -> Rect:
    _, bottom = split_heights(ratio)
    aspect = VERTICAL_W / bottom
    w = min(1.0, aspect / src_aspect)
    return clamp_rect({"x": center_x - w / 2, "y": 0.0, "w": w, "h": 1.0})


def crop_rect_9_16(src_aspect: float, center_x: float = 0.5) -> Rect:
    w = min(1.0, (9 / 16) / src_aspect)
    return clamp_rect({"x": center_x - w / 2, "y": 0.0, "w": w, "h": 1.0})


def default_edit_geometry(src_w: int, src_h: int) -> dict:
    src_aspect = src_w / src_h
    ratio = 0.4
    top, _ = split_heights(ratio)
    cam = fit_rect_to_aspect({"x": 0.0, "y": 0.0, "w": 0.3, "h": 0.3}, VERTICAL_W / top, src_aspect)
    return {
        "layout": "blur",
        "split_ratio": ratio,
        "cam": cam,
        "game": game_rect_for_split(ratio, src_aspect),
        "crop": crop_rect_9_16(src_aspect),
        "main": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
    }


# ---------------------------------------------------------------------------
# Analyse complète
# ---------------------------------------------------------------------------

def analyze_layout(src: str | Path, src_w: int, src_h: int, start: float = 0.0, end: float | None = None) -> dict:
    """Choisit automatiquement la meilleure mise en page verticale pour le clip."""
    geometry = default_edit_geometry(src_w, src_h)
    src_aspect = src_w / src_h
    if src_aspect < 0.75:
        # Vidéo déjà verticale (YouTube Short, TikTok…) : on la garde entière, en plein écran.
        geometry.update(
            layout="crop",
            crop=crop_rect_9_16(src_aspect),
            auto_reason="Vidéo déjà verticale : gardée en plein écran.",
        )
        return geometry
    if src_aspect < 1.2:
        geometry.update(layout="blur", auto_reason="Vidéo carrée : affichée en entier sur fond flou.")
        return geometry
    frames = sample_frames(src, 10, start, end)
    if not frames:
        return {**geometry, "auto_reason": "Impossible de lire les images : fond flou par défaut."}
    dets = detect_faces(frames)
    frame_aspect = frames[0].shape[1] / frames[0].shape[0]
    clusters = cluster_detections(dets, frame_aspect)
    n = len(frames)
    for c in clusters:
        c.motion = _face_motion(c, frames)

    # Une facecam = un visage présent la plupart du temps, qui reste au même endroit,
    # qui bouge (pas une photo), assez petit, et qui n'est pas entouré d'autres visages.
    webcams = [
        c for c in clusters
        if len(c.frames) >= max(2, int(0.5 * n))
        and c.std_center() < 0.04
        and c.motion > 3.0
        and c.mean("w") < 0.13
        and not _is_group(c, dets, frame_aspect)
    ]
    if webcams:
        cam_face = max(webcams, key=lambda c: len(c.frames) * c.mean("w"))
        cam = estimate_cam_rect(cam_face, frames)
        cam_aspect = (cam["w"] * src_aspect) / cam["h"]
        ratio = float(np.clip(VERTICAL_W / cam_aspect / VERTICAL_H, 0.28, 0.5))
        ratio = round(ratio, 3)
        top, _ = split_heights(ratio)
        cam = fit_rect_to_aspect(cam, VERTICAL_W / top, src_aspect, (cam_face.mean("cx"), cam_face.mean("cy")))
        # La partie jeu : centrée, mais on évite la facecam si elle est sur un côté.
        game_cx = 0.5
        game = game_rect_for_split(ratio, src_aspect, game_cx)
        geometry.update(
            layout="split",
            split_ratio=ratio,
            cam=cam,
            game=game,
            crop=crop_rect_9_16(src_aspect, cam_face.mean("cx")),
            auto_reason="Facecam détectée : facecam en haut, jeu en bas.",
        )
        return geometry

    frames_with_faces = {d.frame for d in dets}
    if dets and len(frames_with_faces) >= max(2, int(0.4 * n)):
        # Personnes à l'image (IRL, Just Chatting…) : recadrage 9:16 sur elles.
        weights = np.array([d.w * d.h * d.score for d in dets])
        cx = float(np.average([d.cx for d in dets], weights=weights))
        geometry.update(
            layout="crop",
            crop=crop_rect_9_16(src_aspect, cx),
            auto_reason="Personnes détectées à l'image : recadrage vertical centré sur elles.",
        )
        return geometry

    geometry.update(auto_reason="Pas de facecam détectée : vidéo entière sur fond flou.")
    return geometry


HOP = 0.5  # une mesure de volume toutes les 0,5 s


def loudness_profile(src: str | Path) -> np.ndarray | None:
    """Volume (dB) du son toutes les 0,5 s, ou None si la vidéo n'a pas de son lisible."""
    sr = 8000
    proc = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(sr),
         "-f", "s16le", "-"],
        capture_output=True,
        creationflags=_NO_WINDOW,
    )
    if proc.returncode != 0 or not proc.stdout:
        return None
    audio = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(sr * HOP)
    n = len(audio) // hop
    if n < 4:
        return None
    blocks = audio[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(blocks**2, axis=1) + 1e-10)
    return 20 * np.log10(rms)


def _snap_quiet(db: np.ndarray, t: float, before: float, after: float) -> float:
    """Décale une coupe vers le moment le plus calme proche (évite de couper au milieu d'une phrase)."""
    i0 = max(0, int((t - before) / HOP))
    i1 = min(len(db), int((t + after) / HOP) + 1)
    if i1 - i0 < 2:
        return t
    return (i0 + int(np.argmin(db[i0:i1]))) * HOP


def best_window(src: str | Path, duration: float, length: float, profile: np.ndarray | None = None) -> tuple[float, float]:
    """Meilleur passage de « length » secondes : celui où le son est le plus intense (cris, rires, hype)."""
    if duration <= length + 0.5:
        return 0.0, round(duration, 2)
    db = profile if profile is not None else loudness_profile(src)
    w = int(length / HOP)
    if db is None or len(db) <= w:
        return 0.0, round(min(duration, length), 2)
    smooth = np.convolve(db, np.ones(4) / 4, mode="same")
    sums = np.convolve(smooth, np.ones(w), mode="valid")  # somme sur chaque fenêtre possible
    start = float(np.argmax(sums)) * HOP
    # Coupes sur des moments calmes : on peut commencer un peu avant, et finir un peu plus tôt.
    start = min(max(0.0, _snap_quiet(db, start, 1.5, 0.5)), max(0.0, duration - length))
    end = min(duration, start + length)
    snapped = _snap_quiet(db, end, 1.5, 0.0)
    if end - snapped < 1.5 and snapped - start > length * 0.8:
        end = snapped
    return round(start, 2), round(end, 2)


def find_highlights(src: str | Path, duration: float, clip_len: float = 45.0, count: int = 6,
                    profile: np.ndarray | None = None) -> list[dict]:
    """Repère les passages les plus « bruyants » (cris, rires, hype) d'une longue vidéo."""
    db = profile if profile is not None else loudness_profile(src)
    if db is None or len(db) < 8:
        return []
    n = len(db)
    smooth = np.convolve(db, np.ones(4) / 4, mode="same")  # lissage sur 2 s
    # On compare au niveau sonore « normal » des 60 s autour.
    win = 120
    pad = np.pad(smooth, (win // 2, win // 2), mode="edge")
    baseline = np.array([np.median(pad[i : i + win]) for i in range(n)])
    score = smooth - baseline

    picked: list[int] = []
    min_gap = int(clip_len / HOP)
    for idx in np.argsort(-score):
        if score[idx] <= 1.5 or len(picked) >= count:
            break
        if all(abs(int(idx) - p) >= min_gap for p in picked):
            picked.append(int(idx))
    results = []
    for idx in picked:
        peak_t = idx * HOP
        start = max(0.0, peak_t - clip_len * 0.65)  # la montée avant le pic, puis la réaction
        end = min(duration, start + clip_len)
        start = max(0.0, end - clip_len)
        start = max(0.0, min(_snap_quiet(db, start, 1.5, 0.5), peak_t - 1))
        end = min(duration, start + clip_len)
        results.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "peak": round(peak_t, 2),
            "score": round(float(score[idx]), 1),
        })
    results.sort(key=lambda r: -r["score"])
    return results
