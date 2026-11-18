"""Textes de publication : descriptions, hashtags et bios de profil (TikTok, Instagram, YouTube).

Pas de magie ni de fausses statistiques : les choix suivent les règles connues des plateformes
(nombre de hashtags utile, limites de caractères, rôle de chaque type de hashtag) et
s'appuient sur les infos du clip (streamer, jeu, langue) et sur l'historique de tes projets.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# ---------------------------------------------------------------------------
# Règles des plateformes
# ---------------------------------------------------------------------------
PLATFORM_RULES = {
    "tiktok": {
        "max_tags": 5,
        "tip": {
            "fr": "3 à 5 hashtags suffisent : TikTok lit surtout les mots de la description pour te placer dans les recherches.",
            "en": "3 to 5 hashtags are enough: TikTok mostly reads the words of your caption to rank you in search.",
        },
    },
    "reels": {
        "max_tags": 5,
        "tip": {
            "fr": "Instagram recommande 3 à 5 hashtags précis plutôt qu'une longue liste.",
            "en": "Instagram recommends 3 to 5 specific hashtags rather than a long list.",
        },
    },
    "shorts": {
        "max_tags": 3,
        "tip": {
            "fr": "Les 3 premiers hashtags s'affichent au-dessus du titre ; au-delà de 15, YouTube les ignore tous.",
            "en": "The first 3 hashtags show above the title; with more than 15, YouTube ignores them all.",
        },
    },
    "youtube": {
        "max_tags": 3,
        "tip": {
            "fr": "Colle les « tags » dans le champ Tags de YouTube Studio et ajoute le fichier de sous-titres .srt.",
            "en": "Paste the tags into the Tags field of YouTube Studio and upload the .srt subtitle file.",
        },
    },
}
BIO_LIMITS = {"tiktok": 80, "instagram": 150, "youtube": 1000}

# Hashtags de communauté par jeu / catégorie Twitch.
GAME_TAGS: dict[str, list[str]] = {
    "just chatting": ["#justchatting", "#irl"],
    "irl": ["#irl", "#irlstream"],
    "league of legends": ["#leagueoflegends", "#lol"],
    "valorant": ["#valorant", "#valorantclips"],
    "fortnite": ["#fortnite", "#fortniteclips"],
    "minecraft": ["#minecraft", "#minecraftmemes"],
    "grand theft auto v": ["#gta5", "#gtarp"],
    "grand theft auto vi": ["#gta6", "#gta"],
    "counter-strike": ["#cs2", "#counterstrike"],
    "apex legends": ["#apexlegends", "#apex"],
    "call of duty": ["#callofduty", "#cod"],
    "warzone": ["#warzone", "#callofduty"],
    "overwatch": ["#overwatch2", "#overwatch"],
    "rocket league": ["#rocketleague", "#rl"],
    "world of warcraft": ["#worldofwarcraft", "#wow"],
    "ea sports fc": ["#eafc", "#fut"],
    "elden ring": ["#eldenring", "#fromsoftware"],
    "dead by daylight": ["#deadbydaylight", "#dbd"],
    "rust": ["#rust", "#rustgame"],
    "marvel rivals": ["#marvelrivals"],
    "teamfight tactics": ["#tft", "#teamfighttactics"],
    "hearthstone": ["#hearthstone"],
    "dota 2": ["#dota2"],
    "pubg": ["#pubg"],
    "escape from tarkov": ["#tarkov", "#escapefromtarkov"],
    "chess": ["#chess", "#chesstok"],
    "pokémon": ["#pokemon"],
    "pokemon": ["#pokemon"],
    "the sims": ["#thesims", "#sims4"],
    "roblox": ["#roblox"],
    "lethal company": ["#lethalcompany"],
    "stardew valley": ["#stardewvalley"],
    "music": ["#music", "#livemusic"],
    "art": ["#art", "#digitalart"],
    "sports": ["#sports"],
}
NON_GAMING = {"just chatting", "irl", "music", "art", "sports", "chess", "talk shows & podcasts"}

BROAD = {
    "en": {
        "tiktok": ["#twitchclips", "#fyp", "#streamer", "#viral"],
        "reels": ["#twitchclips", "#streamer", "#reels", "#viral"],
        "shorts": ["#shorts", "#twitchclips", "#streamer"],
        "youtube": ["#twitchclips", "#streamer", "#funnymoments"],
    },
    "fr": {
        "tiktok": ["#twitchfr", "#pourtoi", "#streamerfr", "#fyp"],
        "reels": ["#twitchfr", "#streamerfr", "#reels", "#humour"],
        "shorts": ["#shorts", "#twitchfr", "#streamerfr"],
        "youtube": ["#twitchfr", "#bestof", "#streamerfr"],
    },
}

WHY = {
    "streamer": {"fr": "Le streamer : ses fans cherchent ce hashtag", "en": "The streamer: their fans search this tag"},
    "jeu": {"fr": "Le jeu : touche la communauté du jeu", "en": "The game: reaches that game's community"},
    "niche": {"fr": "Niche : peu de concurrence, public très ciblé", "en": "Niche: less competition, very targeted"},
    "large": {"fr": "Large : grosse audience, plus de concurrence", "en": "Broad: big audience, more competition"},
    "format": {"fr": "Format : classe la vidéo dans le bon flux", "en": "Format: puts the video in the right feed"},
}

EMOJIS = ["😭", "💀", "😂", "🔥", "😱"]
HOOK_FALLBACK = {
    "en": ["{s} wasn't ready for this", "Bro really said that", "Chat could not believe this", "This is why we love {s}", "Nobody expected this"],
    "fr": ["{s} ne s'attendait pas à ça", "Il a vraiment dit ça", "Le chat n'en revenait pas", "C'est pour ça qu'on aime {s}", "Personne ne l'avait vu venir"],
}
CTA = {
    "en": ["Follow for daily {s} clips 🔔", "Follow for more clips like this 👀", "Follow for the best {p} moments 🎮"],
    "fr": ["Abonne-toi pour plus de clips de {s} 🔔", "Abonne-toi pour d'autres clips comme ça 👀", "Abonne-toi pour les meilleurs moments de {p} 🎮"],
}
CREDIT = {
    "en": "🎥 @{s} on Twitch (twitch.tv/{l})",
    "fr": "🎥 Clip du live de {s} sur Twitch (twitch.tv/{l})",
}
CREDIT_NO_CHANNEL = {"en": "🎥 Twitch clip", "fr": "🎥 Clip Twitch"}


def _login(origin: dict) -> str:
    return origin.get("login") or re.sub(r"[^a-z0-9_]", "", (origin.get("channel") or "").lower())


def slug_tag(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^0-9A-Za-z_]", "", text).lower()
    return f"#{text}" if 2 <= len(text) <= 30 else ""


def game_tags(game: str | None) -> list[str]:
    if not game:
        return []
    g = game.lower().strip()
    for key, tags in GAME_TAGS.items():
        if g == key or g.startswith(key):
            return list(tags)
    tag = slug_tag(game)
    return [tag] if tag else []


def _uniq(items: list) -> list:
    seen, out = set(), []
    for it in items:
        key = it[0] if isinstance(it, tuple) else it
        if key and key.lower() not in seen:
            seen.add(key.lower())
            out.append(it)
    return out


def content_language(project: dict, override: str | None = None) -> str:
    """Langue des textes : choix manuel, sinon langue des sous-titres, sinon langue de la chaîne Twitch."""
    if override in ("fr", "en"):
        return override
    tr = project.get("transcript") or {}
    lang = tr.get("language") or (project.get("origin") or {}).get("language")
    return "fr" if lang == "fr" else "en"


def pick_hashtags(project: dict, platform: str, lang: str, variant: int = 0) -> list[dict]:
    origin = project.get("origin") or {}
    channel = origin.get("channel") or ""
    game = origin.get("game")
    s_tag = slug_tag(channel)
    g_tags = game_tags(game)
    broad = list(BROAD[lang][platform])
    if game and game.lower() not in NON_GAMING:
        broad.insert(1, "#gaming")
    # Rotation des hashtags larges selon la version demandée.
    if variant and len(broad) > 2:
        k = variant % (len(broad) - 1)
        broad = [broad[0], *broad[1:][k:], *broad[1:][:k]]

    candidates: list[tuple[str, str]] = []
    if platform == "shorts":
        candidates.append(("#shorts", "format"))
    if s_tag:
        candidates.append((s_tag, "streamer"))
    if g_tags:
        candidates.append((g_tags[0], "jeu"))
    if s_tag and platform in ("tiktok", "reels") and variant % 2 == 0:
        candidates.append((f"{s_tag}clips", "niche"))
    elif len(g_tags) > 1:
        candidates.append((g_tags[1], "niche"))
    for tag in broad:
        kind = "format" if tag in ("#reels", "#shorts") else "large"
        candidates.append((tag, kind))
    tags = _uniq(candidates)[: PLATFORM_RULES[platform]["max_tags"]]
    return [{"tag": t, "kind": k, "why": WHY[k]["fr"]} for t, k in tags]  # explications pour toi : en français


def is_junk_title(text: str | None) -> bool:
    """Titres de clips inutilisables : « x », « ahaha », tapotage au clavier (« hcmmcgcgg »)…"""
    letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", text or "")
    if len(re.sub(r"[^\w]", "", text or "")) < 4:
        return True
    words = re.findall(r"[A-Za-zÀ-ÿ]+", text or "")
    if len(words) == 1 and len(letters) >= 7:
        vowels = sum(1 for c in letters.lower() if c in "aeiouàâäéèêëîïôöùûü")
        if vowels / len(letters) < 0.25:
            return True
    return False


def _hook(project: dict, lang: str, variant: int) -> str:
    channel = (project.get("origin") or {}).get("channel") or ("le streamer" if lang == "fr" else "the streamer")
    hook = ((project.get("edit") or {}).get("title") or {}).get("text") or ""
    if is_junk_title(hook):
        hook = HOOK_FALLBACK[lang][variant % len(HOOK_FALLBACK[lang])].format(s=channel)
    return hook.strip()


def youtube_tags(project: dict, lang: str) -> list[str]:
    origin = project.get("origin") or {}
    channel = origin.get("channel") or ""
    game = origin.get("game") or ""
    words = []
    if channel:
        words += [channel, f"{channel} clips", f"{channel} twitch"]
        words += [f"{channel} funny moments"] if lang == "en" else [f"{channel} best of", f"{channel} moments drôles"]
    if game:
        words += [game, f"{game} clips"] + ([f"{game} funny moments"] if lang == "en" else [f"{game} fr"])
    words += ["twitch clips", "twitch highlights", "streamer"] if lang == "en" else ["twitch fr", "clip twitch", "best of twitch"]
    out, total = [], 0
    for w in _uniq(words):
        if total + len(w) + 1 > 480:
            break
        out.append(w)
        total += len(w) + 1
    return out


SEND_CLIPS = {
    "en": "📩 Send your clips to {e} to be featured in our next videos!",
    "fr": "📩 Envoie tes clips à {e} pour passer dans nos prochaines vidéos !",
}


def publish_texts(project: dict, lang: str | None = None, variant: int = 0, profile: dict | None = None,
                  email: str = "") -> dict:
    """Titre, description et hashtags prêts à coller, pour chaque plateforme."""
    lang = content_language(project, lang)
    origin = project.get("origin") or {}
    channel = origin.get("channel") or ""
    hook = _hook(project, lang, variant)
    emoji = EMOJIS[variant % len(EMOJIS)]
    credit = CREDIT[lang].format(s=channel, l=_login(origin)) if channel else CREDIT_NO_CHANNEL[lang]
    cta = CTA[lang][variant % len(CTA[lang])].format(s=channel or "Twitch", p="Twitch")
    email = (email or "").strip()
    if email:
        cta = f"{cta}\n{SEND_CLIPS[lang].format(e=email)}"
    out: dict = {"lang": lang, "variant": variant, "platforms": {}}
    for platform in ("tiktok", "reels", "shorts", "youtube"):
        tags = pick_hashtags(project, platform, lang, variant)
        tag_line = " ".join(t["tag"] for t in tags)
        entry: dict = {"hashtags": tags, "tip": PLATFORM_RULES[platform]["tip"]["fr"]}
        if platform == "tiktok":
            entry["text"] = f"{hook} {emoji}\n\n{credit}\n{cta}\n\n{tag_line}"
        elif platform == "reels":
            entry["text"] = f"{hook} {emoji}\n.\n{credit}\n{cta}\n.\n{tag_line}"
        elif platform == "shorts":
            title = f"{hook} {emoji}"
            entry["title"] = title[:100]
            entry["text"] = f"{credit}\n{cta}\n\n{tag_line}"
        else:
            prefix = f"{channel} - " if channel and channel.lower() not in hook.lower() else ""
            entry["title"] = f"{prefix}{hook} {emoji}"[:100]
            game = origin.get("game")
            ctx = (f"{channel} on {game}." if lang == "en" else f"{channel} sur {game}.") if channel and game else ""
            sub = ("Subscribe for more Twitch clips every week! 🔔" if lang == "en"
                   else "Abonne-toi pour plus de clips Twitch chaque semaine ! 🔔")
            entry["text"] = "\n".join([f"{hook} {emoji}", *([ctx] if ctx else []), "", credit, sub, "", tag_line])
            entry["tags"] = youtube_tags(project, lang)
        out["platforms"][platform] = entry
    return out


def publish_txt(texts: dict, platform: str) -> str:
    """Version texte simple (fichier .txt déposé à côté de la vidéo exportée)."""
    e = texts["platforms"][platform]
    parts = []
    if e.get("title"):
        parts += ["TITRE / TITLE :", e["title"], ""]
    parts += ["DESCRIPTION :", e["text"]]
    if e.get("tags"):
        parts += ["", "TAGS :", ", ".join(e["tags"])]
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Bios de profil
# ---------------------------------------------------------------------------

def library_stats(projects_list: list[dict]) -> dict:
    """Ce que tu clippes le plus : chaînes, jeux, langues, formats exportés."""
    channels, games, langs, exports = Counter(), Counter(), Counter(), Counter()
    for p in projects_list:
        o = p.get("origin") or {}
        if o.get("channel"):
            channels[o["channel"]] += 1
        if o.get("game"):
            games[o["game"]] += 1
        lang = (p.get("transcript") or {}).get("language") or o.get("language")
        if lang:
            langs[lang] += 1
        for k, v in (p.get("exports") or {}).items():
            if v.get("status") == "fini":
                exports[k] += 1
    return {
        "projects": len(projects_list),
        "channels": channels.most_common(8),
        "games": games.most_common(8),
        "languages": langs.most_common(3),
        "exports": dict(exports),
    }


def _join(names: list[str], lang: str, limit: int) -> str:
    names = [n for n in names if n][:limit]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    sep = " & " if lang == "en" else " et "
    return ", ".join(names[:-1]) + sep + names[-1]


def _fit(options: list[str], limit: int) -> list[str]:
    out = []
    for o in options:
        o = re.sub(r"[ \t]+", " ", o).strip()
        if o and len(o) <= limit and o not in out:
            out.append(o)
    return out


def generate_bios(profile: dict) -> dict:
    """Plusieurs propositions de bio par plateforme, dans les limites de caractères."""
    lang = "fr" if profile.get("lang") == "fr" else "en"
    streamers = [s.strip() for s in profile.get("streamers", []) if s.strip()]
    games = [g.strip() for g in profile.get("games", []) if g.strip()]
    name = (profile.get("account_name") or "").strip()
    link = (profile.get("link") or "").strip()
    freq = profile.get("frequency") or ("daily" if lang == "en" else "chaque jour")
    P = P1 = "Twitch"
    s1, s2, s3 = _join(streamers, lang, 1), _join(streamers, lang, 2), _join(streamers, lang, 3)
    g1, g2 = _join(games, lang, 1), _join(games, lang, 2)
    who = s2 or ("your favorite streamers" if lang == "en" else "tes streamers préférés")
    who1 = s1 or P1
    main_tags = ["#twitchclips"]
    fr_tags = ["#twitchfr"]

    if lang == "en":
        tiktok = [
            f"Best {who} clips 🎬 New every day",
            f"Daily {who1} clips 💀 Follow for more",
            f"{who} moments you missed 👀",
            f"{g1} clips from {who1} 🎮 Daily" if g1 else f"{P} moments you missed 👀 Daily",
            f"Your daily dose of {P} 🎬🔥",
        ]
        insta = [
            f"🎬 Best {who} clips\n{'🎮 ' + g2 + chr(10) if g2 else ''}🔔 New clips {freq}\n{'👇 ' + link if link else main_tags[0] + ' #streamer'}",
            f"{P} moments you missed 👀\n{'Clips of ' + s3 + chr(10) if s3 else ''}Posting {freq} 🔥\n{link or main_tags[0]}",
            f"{name + ' | ' if name else ''}{who1} clips 💀\n🎮 {g1 or 'Gaming'} • 🔔 {freq}\n{link}",
        ]
        yt = (
            f"Welcome{' to ' + name if name else ''}! 🎬\n\n"
            f"Here you'll find the best and funniest clips from {s3 or P + ' streamers'}"
            f"{' playing ' + g2 if g2 else ''}, edited for you {freq}.\n\n"
            "🔔 Subscribe and turn on notifications so you never miss a moment.\n"
            f"🎥 All clips are credited to their streamers. Go support them on {P}!\n"
            f"{chr(10) + '📩 ' + link if link else ''}"
        )
    else:
        tiktok = [
            f"Les meilleurs clips de {who} 🎬",
            f"Clips de {who1} {freq} 💀",
            f"Les moments de {who} que t'as ratés 👀",
            f"Clips {g1} de {who1} 🎮" if g1 else f"Les moments {P1} que t'as ratés 👀",
            f"Ta dose quotidienne de {P} 🎬🔥",
        ]
        insta = [
            f"🎬 Les meilleurs clips de {who}\n{'🎮 ' + g2 + chr(10) if g2 else ''}🔔 Nouveaux clips {freq}\n{'👇 ' + link if link else fr_tags[0] + ' #clipfr'}",
            f"Les moments {P} que t'as ratés 👀\n{'Clips de ' + s3 + chr(10) if s3 else ''}Un clip {freq} 🔥\n{link or fr_tags[0]}",
            f"{name + ' | ' if name else ''}Clips de {who1} 💀\n🎮 {g1 or 'Gaming'} • 🔔 {freq}\n{link}",
        ]
        yt = (
            f"Bienvenue{' sur ' + name if name else ''} ! 🎬\n\n"
            f"Ici tu trouveras les meilleurs clips et les moments les plus drôles de {s3 or 'tes streamers ' + P}"
            f"{' sur ' + g2 if g2 else ''}, montés pour toi {freq}.\n\n"
            "🔔 Abonne-toi et active la cloche pour ne rien rater.\n"
            f"🎥 Tous les clips sont crédités : va soutenir les streamers sur {P} !\n"
            f"{chr(10) + '📩 ' + link if link else ''}"
        )

    niche = _uniq([slug_tag(s) for s in streamers[:3]] + [slug_tag(s) + "clips" for s in streamers[:2] if slug_tag(s)]
                  + [t for g in games[:2] for t in game_tags(g)[:1]])
    broad = _uniq(main_tags + ["#streamer", "#gaming"] if lang == "en" else fr_tags + ["#clipfr", "#streamerfr"])
    base_kw = (["twitch clips", "twitch highlights", "funny moments"] if lang == "en"
               else ["clips twitch", "best of twitch", "twitch fr"])
    keywords = _uniq(streamers[:3] + [f"{s} clips" for s in streamers[:2]] + games[:2] + base_kw)
    return {
        "lang": lang,
        "tiktok": _fit(tiktok, BIO_LIMITS["tiktok"]),
        "instagram": _fit(insta, BIO_LIMITS["instagram"]),
        "youtube": _fit([yt], BIO_LIMITS["youtube"]),
        "hashtags": [t for t in niche if t] + broad,
        "youtube_keywords": keywords,
        "limits": BIO_LIMITS,
        "tips": [
            "TikTok : mets aussi ton mot-clé principal (streamer ou jeu) dans ton nom affiché, ça aide la recherche.",
            "Instagram : les hashtags de la bio sont cliquables, garde-en 1 ou 2 maximum.",
            "YouTube : ajoute les mots-clés dans YouTube Studio → Paramètres → Chaîne → Mots clés.",
        ],
    }
