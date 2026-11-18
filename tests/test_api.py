"""Tests de l'API web (sans réseau)."""
import io

import pytest

from fastapi.testclient import TestClient

from clipforge.config import load_settings
from clipforge.server import app

local = TestClient(app)


def test_info_and_settings():
    info = local.get("/api/info").json()
    assert set(info["platforms"]) == {"tiktok", "reels", "shorts", "youtube"}
    assert info["is_local"] is True
    s = local.get("/api/settings").json()
    assert "access_key" not in s
    r = local.put("/api/settings", json={"quality": "rapide", "access_key": "pirate"})
    assert r.status_code == 200 and r.json()["quality"] == "rapide"
    assert load_settings()["access_key"] != "pirate"
    assert local.put("/api/settings", json={"whisper_model": "inconnu"}).status_code == 400
    assert local.put("/api/settings", json={"promo_email": "pas-un-email"}).status_code == 400
    r = local.put("/api/settings", json={"promo_email": " clips@exemple.com ", "promo_outro": False})
    assert r.json()["promo_email"] == "clips@exemple.com" and r.json()["promo_outro"] is False
    assert local.get("/api/promo-preview?kind=intro&platform=tiktok").status_code == 400
    r = local.get("/api/promo-preview?kind=outro&platform=reels")
    assert r.status_code == 200 and r.headers["content-type"] == "video/mp4"


def test_tablet_needs_key():
    tablet = TestClient(app, client=("192.168.1.42", 50000))
    assert tablet.get("/api/projects").status_code == 401
    assert tablet.get("/").status_code == 401
    key = load_settings()["access_key"]
    r = tablet.get(f"/?key={key}", follow_redirects=False)
    assert r.status_code == 303
    assert tablet.get("/api/projects").status_code == 200  # le cookie suffit ensuite
    assert tablet.get("/api/qr.svg").status_code == 403  # le QR code reste réservé au PC


def test_bios_endpoint():
    r = local.get("/api/bios").json()
    assert {"profile", "stats", "bios"} <= set(r)
    r = local.post("/api/bios", json={"profile": {"streamers": "shroud, xQc", "games": "Valorant", "lang": "en"}}).json()
    assert r["profile"]["streamers"] == ["shroud", "xQc"]
    assert all(len(b) <= 80 for b in r["bios"]["tiktok"])
    assert local.get("/api/bios").json()["profile"]["streamers"] == ["shroud", "xQc"]


def test_bad_inputs():
    assert local.post("/api/projects/url", json={"url": "pas un lien"}).status_code == 400
    r = local.post("/api/projects/url", json={"url": "https://www.twitch.tv/videos/123"})
    assert r.status_code == 400  # une VOD demande un début et une fin
    r = local.post("/api/projects/upload", files={"file": ("virus.exe", io.BytesIO(b"x"), "application/octet-stream")})
    assert r.status_code == 400
    assert local.get("/api/projects/../../etc").status_code == 404
    assert local.get("/api/projects/inexistant1").status_code == 404
    assert local.get("/api/channel-clips?channel=pas%20valide%20!").status_code == 400


def test_clip_length_setting_and_split(tmp_path):
    from clipforge import projects
    from clipforge.ffmpeg_utils import ffmpeg_path, run
    assert local.put("/api/settings", json={"clip_length": 50}).status_code == 400
    assert local.put("/api/settings", json={"clip_length": 30, "promo_outro": True}).status_code == 200
    # Vidéo de 3 min avec deux passages forts.
    p = projects.new_project("Live", {"channel": "Test", "source": "twitch"})
    d = projects.project_dir(p["id"])
    res = run([ffmpeg_path(), "-hide_banner", "-v", "error", "-y",
               "-f", "lavfi", "-i", "testsrc2=s=640x360:r=15:d=180",
               "-f", "lavfi", "-i", "sine=frequency=500:d=180",
               "-filter_complex", "[1:a]volume='if(between(t,30,45)+between(t,120,135),1,0.02)':eval=frame[a]",
               "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
               str(d / "source.mp4")])
    assert res.returncode == 0
    p = projects.finalize_source(p["id"], "source.mp4", auto_layout=False)
    # Durée choisie 30 s, fin de 3,6 s comprise → 26,4 s de clip au meilleur endroit.
    assert p["edit"]["end"] - p["edit"]["start"] == pytest.approx(26.4, abs=1.6)
    assert len(p["highlights"]) >= 2
    r = local.post(f"/api/projects/{p['id']}/auto-trim", json={"length": 45})
    assert r.status_code == 200 and r.json()["end"] - r.json()["start"] <= 41.41
    from clipforge import pipeline
    import time
    job = pipeline.start_split(p["id"], 2)
    for _ in range(240):
        if job.status in ("fini", "erreur"):
            break
        time.sleep(0.5)
    assert job.status == "fini", job.error
    children = [x for x in projects.load_all() if (x.get("origin") or {}).get("parent") == p["id"]]
    assert len(children) == 2
    for c in children:
        assert c["status"] == "pret"
        assert c["edit"]["end"] - c["edit"]["start"] == pytest.approx(26.4, abs=1.6)
        assert c["source"]["duration"] < 35  # seul le passage est gardé
    local.put("/api/settings", json={"clip_length": 61})
