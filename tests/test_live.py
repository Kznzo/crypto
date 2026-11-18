"""Clippeur en direct : lecture de playlist, chat, filtre de jeu et détection des moments forts."""
import time
from collections import deque

from clipforge import live


PLAYLIST = """#EXTM3U
#EXT-X-VERSION:6
#EXT-X-TARGETDURATION:2
#EXT-X-MEDIA-SEQUENCE:100
#EXT-X-MAP:URI="init.mp4"
#EXT-X-PROGRAM-DATE-TIME:2026-11-18T12:00:00.000Z
#EXTINF:2.000,live
seg100.m4s
#EXT-X-PROGRAM-DATE-TIME:2026-11-18T12:00:02.000Z
#EXTINF:2.000,Amazon|123456
ad101.m4s
#EXT-X-PROGRAM-DATE-TIME:2026-11-18T12:00:04.000Z
#EXTINF:2.000,live
seg102.m4s
"""


def test_parse_live_playlist_marks_ads_and_init():
    pl = live.parse_live_playlist(PLAYLIST, "https://cdn.example/v1/playlist/x.m3u8")
    segs = pl["segments"]
    assert [s["seq"] for s in segs] == [100, 101, 102]
    assert [s["ad"] for s in segs] == [False, True, False]  # la pub est ignorée
    assert segs[0]["init"] == "https://cdn.example/v1/playlist/init.mp4"
    assert segs[2]["pdt"] - segs[0]["pdt"] == 4.0


def test_chat_weight_and_game_filter():
    assert live.chat_weight("clip it") > live.chat_weight("KEKW") > live.chat_weight("salut")
    assert live.chat_weight("OMEGALUL") == 2.0
    assert live.game_matches("Grand Theft Auto VI", "grand theft auto vi")
    assert not live.game_matches("Grand Theft Auto V", "Grand Theft Auto VI")  # GTA 5 ≠ GTA 6
    assert not live.game_matches("Just Chatting", "Grand Theft Auto VI")
    assert live.game_matches("Just Chatting", "")  # pas de filtre


def _watcher_with_chat_spike():
    w = live.LiveWatcher("test", {"sensitivity": "normale", "length": 30})
    now = time.time()
    w.latency = 2.0
    content_now = now - w.latency
    # 200 s de live en mémoire (faux segments de 2 s).
    w.segments = deque({"seq": i, "pdt": content_now - 200 + 2 * i, "dur": 2.0, "path": None, "init": None}
                       for i in range(100))
    w.audio = deque((content_now - 200 + 0.5 * i, -30.0) for i in range(400))
    horizon = now - w.latency - live.REACTION_DELAY - 2.5
    chat = []
    for i in range(int(200 / 0.5)):  # chat calme : 2 messages par seconde
        t = content_now - 200 + 0.5 * i
        chat.append((t + w.latency + live.REACTION_DELAY, 1.0))
    for k in range(80):  # gros pic de chat 6 s avant l'horizon
        t = horizon - 7 + k * 0.05
        chat.append((t + w.latency + live.REACTION_DELAY, 2.0))
    w.chat = deque(sorted(chat))
    return w, horizon


def test_detection_triggers_one_clip_around_the_peak(monkeypatch):
    w, horizon = _watcher_with_chat_spike()
    calls = []
    monkeypatch.setattr(w, "_schedule_clip", lambda peak, score, reason: calls.append((peak, score, reason)))
    monkeypatch.setattr(w, "_length", lambda: 26.4)
    w._detect()
    assert w._pending is not None  # moment fort repéré
    time.sleep(0.6)
    w._detect()  # le pic est passé : le clip est programmé
    assert len(calls) == 1
    peak, score, reason = calls[0]
    assert reason == "auto" and score >= live.SENSITIVITY["normale"]
    assert horizon - 9 <= peak <= horizon - 1
    # Pas un deuxième clip juste après (délai minimum entre deux clips).
    w._detect()
    assert len(calls) == 1


def test_quiet_chat_does_not_clip(monkeypatch):
    w, _ = _watcher_with_chat_spike()
    w.chat = deque(c for c in w.chat if c[1] == 1.0)  # pas de pic
    calls = []
    monkeypatch.setattr(w, "_schedule_clip", lambda *a: calls.append(a))
    w._detect()
    time.sleep(0.6)
    w._detect()
    assert not calls and w._pending is None
