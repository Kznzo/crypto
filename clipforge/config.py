"""Chemins, réglages persistants et préréglages des plateformes."""
from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
MODELS_DIR = ASSETS_DIR / "models"
STATIC_DIR = PACKAGE_DIR / "static"

DATA_DIR = Path(os.environ.get("CLIPFORGE_DATA", PACKAGE_DIR.parent / "data")).resolve()
PROJECTS_DIR = DATA_DIR / "projets"
SETTINGS_FILE = DATA_DIR / "reglages.json"

FONTS = {
    "anton": FONTS_DIR / "Anton-Regular.ttf",
    "poppins": FONTS_DIR / "Poppins-ExtraBold.ttf",
    "poppins-bold": FONTS_DIR / "Poppins-Bold.ttf",
}

# ---------------------------------------------------------------------------
# Plateformes de sortie.
# safe_top / safe_bottom / safe_right : fractions de l'image masquées par
# l'interface de l'appli (boutons, description…). On y évite le texte.
# ---------------------------------------------------------------------------
PLATFORMS: dict[str, dict] = {
    "tiktok": {
        "label": "TikTok",
        "width": 1080,
        "height": 1920,
        "vertical": True,
        "max_duration": 600,
        "recommended": "21 à 60 s",
        "safe_top": 0.09,
        "safe_bottom": 0.21,
        "safe_right": 0.13,
    },
    "reels": {
        "label": "Instagram Reels",
        "width": 1080,
        "height": 1920,
        "vertical": True,
        "max_duration": 180,
        "recommended": "15 à 90 s",
        "safe_top": 0.11,
        "safe_bottom": 0.23,
        "safe_right": 0.12,
    },
    "shorts": {
        "label": "YouTube Shorts",
        "width": 1080,
        "height": 1920,
        "vertical": True,
        "max_duration": 180,
        "recommended": "15 à 60 s",
        "safe_top": 0.10,
        "safe_bottom": 0.20,
        "safe_right": 0.12,
    },
    "youtube": {
        "label": "YouTube (16:9)",
        "width": 1920,
        "height": 1080,
        "vertical": False,
        "max_duration": None,
        "recommended": "toute durée",
        "safe_top": 0.05,
        "safe_bottom": 0.08,
        "safe_right": 0.0,
    },
}

CAPTION_STYLES: dict[str, dict] = {
    "tiktok": {
        "label": "TikTok (mot en jaune)",
        "font": "anton",
        "color": "#FFFFFF",
        "highlight": "#FFE21F",
        "stroke": "#000000",
        "box": None,
        "uppercase": True,
        "pop": True,
    },
    "vert": {
        "label": "Karaoké vert",
        "font": "poppins",
        "color": "#FFFFFF",
        "highlight": "#39FF6A",
        "stroke": "#000000",
        "box": None,
        "uppercase": True,
        "pop": True,
    },
    "violet": {
        "label": "Twitch violet",
        "font": "poppins",
        "color": "#FFFFFF",
        "highlight": "#FFFFFF",
        "highlight_box": "#9146FF",
        "stroke": "#000000",
        "box": None,
        "uppercase": False,
        "pop": False,
    },
    "boite": {
        "label": "Blanc sur fond noir",
        "font": "poppins-bold",
        "color": "#FFFFFF",
        "highlight": "#FFFFFF",
        "stroke": None,
        "box": "#000000B4",
        "uppercase": False,
        "pop": False,
    },
    "simple": {
        "label": "Classique blanc",
        "font": "poppins-bold",
        "color": "#FFFFFF",
        "highlight": "#FFFFFF",
        "stroke": "#000000",
        "box": None,
        "uppercase": False,
        "pop": False,
    },
}

TITLE_STYLES: dict[str, dict] = {
    "blanc": {"label": "Bandeau blanc", "font": "poppins", "color": "#000000", "box": "#FFFFFF"},
    "noir": {"label": "Bandeau noir", "font": "poppins", "color": "#FFFFFF", "box": "#000000E6"},
    "violet": {"label": "Bandeau violet", "font": "poppins", "color": "#FFFFFF", "box": "#9146FF"},
    "contour": {"label": "Gros texte contour", "font": "anton", "color": "#FFFFFF", "box": None, "stroke": "#000000"},
}

YOUTUBE_MAX_SECONDS = 30 * 60  # vidéos YouTube et compilations : 30 min maximum
COMPIL_TARGET = (15 * 60, 25 * 60)  # durée idéale d'une compilation YouTube


def platform_limits(settings: dict | None = None) -> dict[str, float]:
    """Durée maximale de chaque export, selon les réglages (1 min 01 par défaut pour les formats verticaux)."""
    vertical = float((settings or {}).get("vertical_max_seconds") or DEFAULT_SETTINGS["vertical_max_seconds"])
    return {k: (vertical if p["vertical"] else YOUTUBE_MAX_SECONDS) for k, p in PLATFORMS.items()}


CLIP_LENGTHS = (30, 45, 61)
OUTRO_SECONDS = 3.6  # durée de la fin « Send us your clips » (voir promo.py)


def clip_seconds(settings: dict | None = None, length: float | None = None, outro: bool | None = None) -> float:
    """Durée de clip à garder pour obtenir une vidéo verticale de « length » secondes, fin comprise."""
    settings = settings or {}
    length = float(length or settings.get("clip_length") or DEFAULT_SETTINGS["clip_length"])
    length = min(length, platform_limits(settings)["tiktok"])
    if outro is None:
        outro = settings.get("promo_outro", True)
    return round(length - (OUTRO_SECONDS if outro else 0.0), 2)


def platforms_for(settings: dict | None = None) -> dict:
    """Copie de PLATFORMS avec les durées maximales des réglages (pour l'interface)."""
    limits = platform_limits(settings)
    out = {}
    for k, p in PLATFORMS.items():
        out[k] = {**p, "max_duration": limits[k]}
        if p["vertical"]:
            m, s = divmod(int(limits[k]), 60)
            out[k]["recommended"] = f"jusqu'à {m} min {s:02d}" if m else f"jusqu'à {s} s"
    return out


DEFAULT_SETTINGS = {
    "whisper_model": "small",
    "language": "auto",  # langue parlée par défaut dans les clips (auto = détectée)
    "quality": "equilibre",  # rapide | equilibre | max
    "gpu": "auto",  # auto | off
    "default_watermark": "",
    "default_caption_style": "tiktok",
    "default_title_style": "blanc",
    "default_formats": ["tiktok", "reels", "shorts"],
    "twitch_cookies": "",  # navigateur dont on réutilise la connexion Twitch (VOD abonnés)
    "subtitles_english": False,  # traduire automatiquement les sous-titres en anglais
    "publish_lang": "auto",  # langue des descriptions : auto (celle du clip), fr ou en
    "profile": {},  # infos du compte pour les bios (nom, streamers clippés, jeux…)
    # Intro YouTube / fin TikTok-Reels-Shorts (en anglais) : « envoie tes clips » + abonne-toi + cloche.
    "vertical_max_seconds": 61,  # durée max TikTok / Reels / Shorts (fin comprise)
    "clip_length": 61,  # durée visée des vidéos verticales générées : 30, 45 ou 61 s (fin comprise)
    "promo_email": "",
    "promo_intro": True,
    "promo_outro": True,
    "promo_intro_text": "",
    "promo_outro_text": "",
    "access_key": "",
}

_settings_lock = threading.Lock()


def ensure_dirs() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    ensure_dirs()
    with _settings_lock:
        data = {}
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text("utf-8"))
            except (OSError, ValueError):
                data = {}
        merged = {**DEFAULT_SETTINGS, **data}
        if not merged.get("access_key"):
            merged["access_key"] = secrets.token_urlsafe(9)
            SETTINGS_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), "utf-8")
        return merged


def save_settings(update: dict) -> dict:
    current = load_settings()
    allowed = set(DEFAULT_SETTINGS) - {"access_key"}
    for key, value in update.items():
        if key in allowed:
            current[key] = value
    with _settings_lock:
        SETTINGS_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), "utf-8")
    return current
