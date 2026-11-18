"""Tests de l'API web (sans réseau)."""
import io

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
