"""Test de bout en bout du montage avec une vidéo générée par FFmpeg (aucun accès réseau)."""
from pathlib import Path

import pytest

from clipforge import captions, projects, render, social
from clipforge.config import load_settings
from clipforge.ffmpeg_utils import ffmpeg_path, probe, run


@pytest.fixture(scope="module")
def sample_project():
    p = projects.new_project("Test : il hurle en plein live 😱", {"channel": "TestChaine"})
    d = projects.project_dir(p["id"])
    res = run([
        ffmpeg_path(), "-hide_banner", "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=4",
        "-f", "lavfi", "-i", "sine=frequency=440:d=4",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
        str(d / "source.mp4"),
    ])
    assert res.returncode == 0, res.stderr
    p = projects.finalize_source(p["id"], "source.mp4")
    words = [{"w": w, "s": 0.3 + i * 0.5, "e": 0.3 + i * 0.5 + 0.45} for i, w in enumerate("c'est vraiment incroyable ça".split())]
    p["transcript"] = {"segments": [{"start": 0.3, "end": 2.3, "text": "x", "words": words}]}
    p["edit"]["watermark"] = {"enabled": True, "text": "twitch.tv/testchaine"}
    p["edit"]["progress_bar"] = True
    projects.save(p)
    return p


@pytest.mark.parametrize("layout", ["split", "blur", "crop"])
def test_render_vertical_layouts(sample_project, layout):
    p = projects.load(sample_project["id"])
    p["edit"]["layout"] = layout
    out = render.render_export(projects.project_dir(p["id"]), p, "tiktok", {**load_settings(), "quality": "rapide", "gpu": "off"})
    info = probe(out)
    assert (info["width"], info["height"]) == (1080, 1920)
    assert info["has_audio"]
    assert info["duration"] == pytest.approx(4, abs=0.2)


def test_render_youtube(sample_project):
    p = projects.load(sample_project["id"])
    out = render.render_export(projects.project_dir(p["id"]), p, "youtube", {**load_settings(), "quality": "rapide", "gpu": "off"})
    info = probe(out)
    assert (info["width"], info["height"]) == (1920, 1080)
    assert Path(out).name == "youtube.mp4"


def test_description_has_hashtags(sample_project):
    p = projects.load(sample_project["id"])
    texts = social.publish_texts(p, "en")
    tiktok = texts["platforms"]["tiktok"]["text"]
    assert "#testchaine" in tiktok and "#twitchclips" in tiktok
    assert texts["platforms"]["shorts"]["hashtags"][0]["tag"] == "#shorts"


def test_srt(sample_project):
    p = projects.load(sample_project["id"])
    srt = captions.build_srt(p["transcript"], 0, 4)
    assert srt.startswith("1\n00:00:00,300 --> ")
    assert "incroyable" in srt
