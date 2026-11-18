"""Pilote automatique CLIP IT (réseau et lives simulés)."""
from clipforge import autopilot, live, pipeline, projects, sources


def test_clip_key():
    assert autopilot.clip_key("https://www.twitch.tv/kaicenat/clip/SincereMoldy-C2fu?x=1") == "sinceremoldy-c2fu"
    assert autopilot.clip_key("https://clips.twitch.tv/SincereMoldy-C2fu") == "sinceremoldy-c2fu"
    assert autopilot.clip_key("https://www.twitch.tv/videos/123") is None


def test_pilot_imports_new_clips_and_watches_top_lives(monkeypatch):
    clips = [{"url": f"https://www.twitch.tv/s{i}/clip/Slug{i}", "title": f"Clip {i}"} for i in range(6)]
    streams = [{"channel": c, "viewers": v} for c, v in (("xqc", 90000), ("lacy", 30000), ("ohnepixel", 40000),
                                                         ("petit", 10))]
    monkeypatch.setattr(sources, "game_clips", lambda *a, **k: clips)
    monkeypatch.setattr(sources, "game_streams", lambda *a, **k: streams)
    imported, started, stopped = [], [], []
    monkeypatch.setattr(pipeline, "start_import_url", lambda pid, url, *a, **k: imported.append(url))

    class FakeWatcher:
        def __init__(self, ch, opts, state="direct"):
            self.channel, self.options, self.state = ch, opts, state

    monkeypatch.setattr(live.manager, "watchers", {"ancien": FakeWatcher("ancien", {"autopilot": True}, "attente"),
                                                   "manuel": FakeWatcher("manuel", {}, "attente")})
    monkeypatch.setattr(live.manager, "start", lambda ch, opts: (started.append(ch), live.manager.watchers.__setitem__(ch, FakeWatcher(ch, opts))))
    monkeypatch.setattr(live.manager, "stop", lambda ch: (stopped.append(ch), live.manager.watchers.pop(ch, None)))

    pilot = autopilot.AutoPilot()
    pilot.options = {**autopilot.DEFAULTS, "streams": 2, "clips": 4}
    already = projects.new_project("Déjà là", {"url": "https://clips.twitch.tv/Slug0"})
    pilot._import_top_clips()
    assert len(imported) == 4 and clips[0]["url"] not in imported  # pas deux fois le même clip
    pilot._import_top_clips()
    assert len(imported) == 5  # seulement le dernier clip encore inconnu
    pilot._refresh_streams()
    # Les 2 plus gros lives + le favori OhnePixel (en live sur le jeu).
    assert set(started) == {"xqc", "lacy", "ohnepixel"}
    assert stopped == ["ancien"]  # lâché : plus en live ; « manuel » n'est jamais retiré par le pilote
    assert "manuel" in live.manager.watchers
    projects.delete(already["id"])
