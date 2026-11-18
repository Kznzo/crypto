"""Tests des fonctions pures (sans réseau ni encodage)."""
import pytest

from clipforge import analysis, captions, sources
from clipforge.overlays import compute_placement, strip_emoji
from clipforge.render import build_video_filters, clip_bounds
from clipforge.server import _sanitize_edit


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1:23:45", 5025),
        ("83:20", 5000),
        ("5000", 5000),
        ("1h23m45s", 5025),
        ("2m", 120),
        ("90s", 90),
        ("", None),
        ("abc", None),
    ],
)
def test_parse_time(value, expected):
    assert sources.parse_time(value) == expected


def test_normalize_channel():
    assert sources.normalize_channel("https://www.twitch.tv/ZeratoR/clips") == "zerator"
    assert sources.normalize_channel("@Gotaga") == "gotaga"
    with pytest.raises(sources.DownloadError):
        sources.normalize_channel("pas valide !")


def test_vod_helpers():
    assert sources.is_vod_url("https://www.twitch.tv/videos/123456?t=1h2m3s")
    assert not sources.is_vod_url("https://www.twitch.tv/zerator/clip/AbcDef")
    assert sources.vod_start_from_url("https://www.twitch.tv/videos/1?t=1h2m3s") == 3723


def test_parse_media_playlist():
    text = """#EXTM3U
#EXT-X-MAP:URI="init-0.mp4"
#EXTINF:10.000,
0.mp4
#EXTINF:10.000,
1.mp4
#EXTINF:4.5,
2.mp4
#EXT-X-ENDLIST"""
    init, segs = sources.parse_media_playlist(text, "https://cdn.example/vod/1080p60/index-dvr.m3u8")
    assert init == "https://cdn.example/vod/1080p60/init-0.mp4"
    assert [(s, e) for s, e, _ in segs] == [(0, 10), (10, 20), (20, 24.5)]
    assert segs[2][2] == "https://cdn.example/vod/1080p60/2.mp4"


def _transcript(words):
    return {"segments": [{"start": words[0]["s"], "end": words[-1]["e"], "text": " ".join(w["w"] for w in words), "words": words}]}


def test_caption_groups():
    words = [{"w": w, "s": i * 0.4, "e": i * 0.4 + 0.35} for i, w in enumerate("salut tout le monde, ça va bien ?".split())]
    groups = captions.build_caption_groups(_transcript(words), 0, 10, max_words=3)
    texts = [" ".join(w["w"] for w in g["words"]) for g in groups]
    assert texts[0] == "SALUT TOUT LE"
    assert all(len(g["words"]) <= 3 for g in groups)
    # Les blocs s'enchaînent sans trou quand la pause est courte.
    assert groups[0]["end"] == pytest.approx(groups[1]["start"])
    # Temps relatifs au début du clip.
    shifted = captions.build_caption_groups(_transcript(words), 0.8, 10, max_words=3)
    assert shifted[0]["words"][0]["w"] == "LE"
    assert shifted[0]["start"] == pytest.approx(0.0)


def test_add_word_glues_pieces():
    words = []
    for i, w in enumerate([" c", "'est", " 44", ",000", " don", "'t", " stop", " !", " peut", "-être"]):
        captions.add_word(words, w, i, i + 0.5)
    assert [w["w"] for w in words] == ["c'est", "44,000", "don't", "stop!", "peut-être"]
    assert words[0]["s"] == 0 and words[0]["e"] == 1.5


def test_retime_segment():
    seg = {"start": 1.0, "end": 3.0, "text": "a b", "words": [{"w": "a", "s": 1.0, "e": 1.5}, {"w": "b", "s": 2.0, "e": 3.0}]}
    same_count = captions.retime_segment(seg, "x y")
    assert [w["w"] for w in same_count["words"]] == ["x", "y"]
    assert same_count["words"][1]["s"] == 2.0
    more = captions.retime_segment(seg, "un deux trois")
    assert len(more["words"]) == 3
    assert more["words"][0]["s"] == pytest.approx(1.0)
    assert more["words"][-1]["e"] <= 3.0


def test_fit_rect_to_aspect():
    src_aspect = 16 / 9
    r = analysis.fit_rect_to_aspect({"x": 0, "y": 0, "w": 1, "h": 1}, 9 / 16, src_aspect)
    assert (r["w"] * src_aspect) / r["h"] == pytest.approx(9 / 16, rel=1e-3)
    assert r["h"] == pytest.approx(1)


def test_strip_emoji():
    assert strip_emoji("Il pète un câble 😱🔥") == "Il pète un câble"
    assert strip_emoji("ÇA VA ?") == "ÇA VA ?"


def test_placement_respects_safe_zone():
    edit = {"layout": "blur", "captions": {"position": "bas"}}
    for plat in ("tiktok", "reels", "shorts"):
        pl = compute_placement(plat, edit)
        assert pl.caption_center_y < pl.height * 0.8


def test_filters_and_bounds():
    source = {"width": 1920, "height": 1080, "duration": 300, "fps": 60, "has_audio": True}
    edit = {**analysis.default_edit_geometry(1920, 1080), "layout": "split", "start": 10, "end": 250}
    assert "vstack" in ";".join(build_video_filters(edit, source, "tiktok"))
    assert "pad=1920:1080" in ";".join(build_video_filters(edit, source, "youtube"))
    # Reels : 3 min max, l'export est coupé automatiquement.
    # TikTok / Reels / Shorts : 1 min 01 par défaut, réglable.
    assert clip_bounds(edit, source, "reels") == (10, 71)
    assert clip_bounds(edit, source, "tiktok", {"vertical_max_seconds": 90}) == (10, 100)
    assert clip_bounds(edit, source, "youtube") == (10, 250)
    long_edit = {**edit, "start": 0, "end": None}
    assert clip_bounds(long_edit, {**source, "duration": 4000}, "youtube") == (0, 1800)  # 30 min max


def test_sanitize_edit_clamps_values():
    current = {"start": 0, "end": 20, "layout": "blur", "title": {"text": "a"}}
    out = _sanitize_edit(
        current,
        {"layout": "n'importe quoi", "split_ratio": 5, "cam": {"x": -1, "y": 2, "w": 3, "h": 0.5},
         "title": {"text": "b"}, "evil": 1, "end": 999},
        {"duration": 30},
    )
    assert out["layout"] == "blur"
    assert out["split_ratio"] == 0.6
    assert 0 <= out["cam"]["x"] and out["cam"]["y"] + out["cam"]["h"] <= 1
    assert out["title"]["text"] == "b"
    assert "evil" not in out
    assert out["end"] == 30


def test_twitch_links():
    assert sources.source_of("https://clips.twitch.tv/AbcDef") == "twitch"
    assert sources.source_of("https://www.youtube.com/shorts/kPI9Mc35mOg") == "autre"
    assert sources.channel_url("twitch", "zerator") == "twitch.tv/zerator"
    meta = sources._meta({"channel": "ZeratoR", "categories": ["Just Chatting"],
                          "webpage_url": "https://www.twitch.tv/zerator/clip/AbcDef"})
    assert (meta["source"], meta["login"], meta["game"]) == ("twitch", "zerator", "Just Chatting")


def test_clip_seconds():
    from clipforge.config import clip_seconds
    assert clip_seconds({}) == pytest.approx(61 - 3.6)  # 1 min 01 fin comprise
    assert clip_seconds({"clip_length": 30}) == pytest.approx(26.4)
    assert clip_seconds({"clip_length": 45, "promo_outro": False}) == 45
    assert clip_seconds({"clip_length": 61, "vertical_max_seconds": 45}) == pytest.approx(41.4)  # plafonné


def test_best_window_finds_the_loud_part(tmp_path):
    from clipforge.ffmpeg_utils import ffmpeg_path, run
    src = tmp_path / "bruit.mp4"
    # 60 s : calme, puis un passage fort de 20 s à 32 s, puis calme.
    res = run([ffmpeg_path(), "-hide_banner", "-v", "error", "-y",
               "-f", "lavfi", "-i", "color=black:s=320x180:r=10:d=60",
               "-f", "lavfi", "-i", "sine=frequency=500:d=60",
               "-filter_complex", "[1:a]volume='if(between(t,20,32),1,0.02)':eval=frame[a]",
               "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(src)])
    assert res.returncode == 0, res.stderr
    start, end = analysis.best_window(src, 60, 12)
    assert 17 <= start <= 21 and end - start <= 12.01
    assert analysis.best_window(src, 60, 90) == (0.0, 60)  # vidéo plus courte que la durée voulue
