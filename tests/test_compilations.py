"""Compilations YouTube : durées, chapitres, remplissage et rendu complet."""
import pytest

from clipforge import compilations, projects, social
from clipforge.config import load_settings
from clipforge.ffmpeg_utils import ffmpeg_path, probe, run


def _fake_project(duration, channel="tarik", title="Gros clip"):
    p = projects.new_project(title, {"channel": channel, "source": "twitch"})
    p["source"] = {"file": "source.mp4", "width": 1920, "height": 1080, "duration": duration, "fps": 60, "has_audio": True}
    p["edit"]["start"], p["edit"]["end"] = 0.0, duration
    p["status"] = "pret"
    return projects.save(p)


def test_describe_and_status():
    c = compilations.create("Test")
    assert compilations.describe(c)["duration_status"] == "vide"
    short = _fake_project(60)
    c = compilations.mutate(c["id"], lambda x: x.update(items=[short["id"]]))
    d = compilations.describe(c)
    assert d["duration_status"] == "court"
    assert d["total"] == pytest.approx(60 + 4 + 8)
    big = [_fake_project(400) for _ in range(3)]  # 3 × 6 min 40
    c = compilations.mutate(c["id"], lambda x: x.update(items=[short["id"]] + [b["id"] for b in big]))
    assert compilations.describe(c)["duration_status"] == "ideal"  # ≈ 21 min
    more = _fake_project(600)
    c = compilations.mutate(c["id"], lambda x: x["items"].append(more["id"]))
    assert compilations.describe(c)["duration_status"] == "trop_long"  # > 30 min


def test_autofill_targets_20_minutes_and_never_30():
    for _ in range(12):
        _fake_project(150)
    c = compilations.create("Auto")
    d = compilations.describe(compilations.autofill(c["id"]))
    assert 20 * 60 <= d["total"] <= 30 * 60


def test_youtube_chapters_rules():
    chapters = [
        {"t": 0, "label": "Intro"},
        {"t": 4, "label": "Clip A", "project": "a"},
        {"t": 30, "label": "Clip B (6 s, trop court)", "project": "b"},
        {"t": 36, "label": "Clip C", "project": "c"},
        {"t": 60, "label": "Clip D", "project": "d"},
        {"t": 90, "label": "Fin"},
    ]
    lines = social.youtube_chapters(chapters, 98)
    assert lines[0] == "00:00 Clip A"  # le premier chapitre commence à 00:00
    assert "trop court" not in " ".join(lines)  # < 10 s : reste dans le chapitre précédent
    assert lines == ["00:00 Clip A", "00:36 Clip C", "01:00 Clip D"]
    assert len(lines) >= 3
    assert social.youtube_chapters(chapters[:3], 40) == []  # moins de 3 chapitres : pas de chapitres


def test_full_compilation_render():
    pids = []
    for i, freq in enumerate((440, 660)):
        p = projects.new_project(f"Clip {i}", {"channel": f"Streamer{i}", "source": "twitch"})
        d = projects.project_dir(p["id"])
        res = run([ffmpeg_path(), "-hide_banner", "-v", "error", "-y",
                   "-f", "lavfi", "-i", f"testsrc2=s=1280x720:r=30:d=12",
                   "-f", "lavfi", "-i", f"sine=frequency={freq}:d=12",
                   "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                   str(d / "source.mp4")])
        assert res.returncode == 0
        projects.finalize_source(p["id"], "source.mp4", auto_layout=False)
        pids.append(p["id"])
    c = compilations.create("Rendu")
    compilations.mutate(c["id"], lambda x: x.update(items=pids, auto_captions=False))
    settings = {**load_settings(), "quality": "rapide", "gpu": "off", "promo_email": "clips@exemple.com"}

    class FakeJob:
        cancel_requested = False

        def set(self, *a, **k):
            pass

        id = "test"

    compilations._render(c["id"], FakeJob(), settings)
    c = compilations.load(c["id"])
    out = compilations.compil_dir(c["id"]) / "compilation.mp4"
    info = probe(out)
    assert (info["width"], info["height"]) == (1920, 1080)
    assert info["duration"] == pytest.approx(4 + 12 + 12 + 8, abs=0.5)
    assert [ch["project"] for ch in c["export"]["chapters"]] == [None, *pids, None]
    assert (compilations.compil_dir(c["id"]) / "description.txt").exists()
    # Le décodage complet ne doit produire aucune erreur (morceaux bien collés).
    res = run([ffmpeg_path(), "-v", "error", "-i", str(out), "-f", "null", "-"])
    assert res.returncode == 0 and not res.stderr.strip()
