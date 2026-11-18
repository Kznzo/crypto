"""Descriptions, hashtags et bios."""
import pytest

from clipforge import social


def _project(lang="en", title="smol shroud", game="World of Warcraft", channel="shroud"):
    return {
        "origin": {"channel": channel, "game": game, "language": lang},
        "edit": {"title": {"text": title}},
        "transcript": None,
    }


@pytest.mark.parametrize("variant", [0, 1, 2, 3])
def test_hashtag_limits_and_order(variant):
    texts = social.publish_texts(_project(), "auto", variant)
    assert texts["lang"] == "en"
    limits = {"tiktok": 5, "reels": 5, "shorts": 3, "youtube": 3}
    for plat, n in limits.items():
        tags = [h["tag"] for h in texts["platforms"][plat]["hashtags"]]
        assert 1 <= len(tags) <= n
        assert len(set(tags)) == len(tags)
        assert "#shroud" in tags  # le streamer passe toujours en premier (après #shorts)
    assert texts["platforms"]["shorts"]["hashtags"][0]["tag"] == "#shorts"
    assert "#worldofwarcraft" in texts["platforms"]["tiktok"]["text"]
    assert len(texts["platforms"]["youtube"]["title"]) <= 100
    assert sum(len(t) + 1 for t in texts["platforms"]["youtube"]["tags"]) <= 500


def test_language_choice():
    fr = social.publish_texts(_project(lang="fr", title="x", channel="Gotaga", game="Fortnite"))
    assert fr["lang"] == "fr"
    assert "#twitchfr" in fr["platforms"]["tiktok"]["text"]
    assert "Gotaga" in fr["platforms"]["tiktok"]["text"]  # titre « x » remplacé par une accroche
    # Sous-titres traduits en anglais → textes en anglais.
    p = _project(lang="fr")
    p["transcript"] = {"language": "en", "segments": []}
    assert social.publish_texts(p)["lang"] == "en"
    assert social.publish_texts(p, "fr")["lang"] == "fr"


def test_unknown_game_gets_a_tag():
    assert social.game_tags("Super Jeu Inconnu 3") == ["#superjeuinconnu3"]
    assert social.game_tags("Call of Duty: Black Ops 7") == ["#callofduty", "#cod"]
    assert social.slug_tag("Pokémon") == "#pokemon"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_bios_respect_limits(lang):
    bios = social.generate_bios({
        "account_name": "ClipZone", "streamers": ["shroud", "Tarik", "xQc"],
        "games": ["Valorant", "World of Warcraft"], "lang": lang, "link": "discord.gg/abc",
    })
    for plat in ("tiktok", "instagram", "youtube"):
        assert bios[plat], plat
        assert all(len(b) <= social.BIO_LIMITS[plat] for b in bios[plat])
    assert "#shroud" in bios["hashtags"]


def test_bios_without_profile():
    bios = social.generate_bios({})
    assert bios["tiktok"] and bios["instagram"] and bios["youtube"]


def test_library_stats():
    stats = social.library_stats([
        {"origin": {"channel": "shroud", "game": "Valorant"}, "exports": {"tiktok": {"status": "fini"}}},
        {"origin": {"channel": "shroud", "game": "WoW"}, "exports": {}},
        {"origin": {"channel": "xQc"}, "exports": {"tiktok": {"status": "erreur"}}},
    ])
    assert stats["channels"][0] == ("shroud", 2)
    assert stats["exports"] == {"tiktok": 1}


@pytest.mark.parametrize("title, junk", [
    ("x", True), ("ahaha", False), ("hcmmcgcgg", True), (",tymdgndnntynty", True), ("etsutrdts", True),
    ("PIERRE POLE", False), ("Splat", False), ("smol shroud", False), ("LE BONHEUR", False), ("Niveau 60", False),
])
def test_junk_titles(title, junk):
    assert social.is_junk_title(title) is junk
