# ClipForge 🎬

**Transforme tes clips Twitch en vidéos prêtes à poster sur TikTok, Instagram Reels, YouTube Shorts et YouTube, avec le montage fait automatiquement.**

ClipForge tourne sur ton PC et s'utilise depuis le navigateur du PC **ou de ta tablette** (même Wi-Fi).
Tout se passe en local : tes vidéos ne sont envoyées sur aucun serveur.

---

## Ce que fait l'appli

**Importer**
- 🔗 Coller le lien d'un **clip Twitch** (`twitch.tv/…/clip/…`, `clips.twitch.tv/…`)
- 🏆 Afficher les **clips les plus vus d'une chaîne Twitch** (24 h, 7 j, 30 j, depuis toujours) et en importer plusieurs d'un coup
- 📺 Récupérer **un passage d'une VOD Twitch** (ex. de 1:20:00 à 1:30:00) : seul ce passage est téléchargé
- 📁 Envoyer un **fichier vidéo** depuis le PC ou la tablette

**Montage automatique**
- 🧠 **Détection de la facecam** : l'appli trouve la webcam du streamer dans l'image et choisit la mise en page :
  - *Facecam + jeu* : la webcam en haut, le jeu en bas (le format le plus utilisé)
  - *Vidéo entière sur fond flou*
  - *Plein écran vertical* recadré sur les personnes (IRL, Just Chatting)
  - vidéo **déjà verticale** (filmée au téléphone) : gardée entière ; la version YouTube 16:9 la place sur un fond flou
- 💬 **Sous-titres animés mot par mot** générés par IA à partir de la voix (5 styles, corrigeables à la main)
  - clips du **Twitch anglais** : sous-titres en anglais (langue reprise de la chaîne Twitch, sinon détectée par l'IA)
  - option **« Sous-titres en anglais »** : un clip en français (ou autre) est traduit en anglais
  - fichier **.srt** pour YouTube (sous-titres activables + meilleur référencement)
- 🔥 **Moments forts** : sur une longue vidéo, l'appli repère les passages où ça crie, rit ou s'emballe
- ✍️ **Titre accrocheur** en bandeau, **pseudo du streamer** (crédit), **barre de progression**
- 🔊 **Son égalisé** au niveau conseillé par les réseaux, fondus au début et à la fin
- 👀 **Aperçu en direct** de chaque format, avec les zones cachées par l'interface de TikTok / Insta / YouTube

**Exporter**

| Format | Taille | Durée max |
|---|---|---|
| TikTok | 1080 × 1920 | 10 min |
| Instagram Reels | 1080 × 1920 | 3 min (coupé automatiquement) |
| YouTube Shorts | 1080 × 1920 | 3 min (coupé automatiquement) |
| YouTube | 1920 × 1080 | illimitée |

**Textes pour publier** (onglet Exporter), en anglais ou en français selon le clip :
- **TikTok / Reels** : légende avec accroche, crédit du streamer (`twitch.tv/…`), appel à s'abonner et 5 hashtags
- **Shorts** : titre + description, `#shorts` et 3 hashtags (ceux affichés au-dessus du titre)
- **YouTube** : titre (100 caractères max), description, hashtags et **tags** pour YouTube Studio
- Hashtags choisis dans cet ordre : le **streamer** (ses fans le cherchent), le **jeu** (sa communauté), un tag **de niche**, puis des tags **larges** ; touche un hashtag pour voir pourquoi il est là. Bouton « Autre version » pour varier.
- Les textes sont aussi enregistrés dans un fichier `.txt` à côté de chaque vidéo.

**Bios de profil** (bouton « Bios » en haut) : propositions de bio **TikTok** (80 caractères), **Instagram** (150) et de description de **chaîne YouTube**, hashtags et mots-clés pour ton compte. Elles sont pré-remplies avec les streamers et les jeux que tu clippes le plus (tes stats ClipForge).

> Les statistiques internes de TikTok, Instagram et YouTube ne sont pas publiques : les propositions s'appuient sur les règles connues des plateformes (nombre de hashtags utiles, limites de caractères) et sur ta niche, pas sur des chiffres de tendances en direct.

**Mode 100 % automatique** : coche-le sur l'accueil, colle un lien… et récupère directement les vidéos dans tous les formats choisis.

---

## Installation

### Windows

1. Sur GitHub, clique sur **Code → Download ZIP**, puis décompresse le dossier (par exemple dans `Documents`).
2. Double-clique sur **`Lancer-ClipForge.bat`**.
3. Le premier lancement installe tout ce qu'il faut (Python s'il manque, puis les composants) : compte 5 à 10 minutes. Les fois suivantes, ça démarre en quelques secondes.
4. ClipForge s'ouvre tout seul dans ton navigateur. **Laisse la fenêtre noire ouverte** pendant que tu utilises l'appli (la fermer arrête ClipForge).

> Si Windows affiche « Windows a protégé votre ordinateur », clique sur *Informations complémentaires → Exécuter quand même*.
> Si le pare-feu demande l'accès au réseau, accepte pour les **réseaux privés** (c'est ce qui permet d'utiliser la tablette).

### macOS / Linux

1. Installe Python 3.10 ou plus récent ([python.org](https://www.python.org/downloads/)).
2. Télécharge et décompresse le projet.
3. macOS : double-clique sur **`Lancer-ClipForge.command`** (la première fois : clic droit → Ouvrir).
   Linux : lance `./lancer-clipforge.sh` dans un terminal.

---

## Utiliser ClipForge sur la tablette

1. Lance ClipForge sur le PC.
2. Connecte la tablette au **même Wi-Fi** que le PC.
3. Sur le PC, clique sur **« Tablette »** en haut de l'écran : un QR code s'affiche.
4. Scanne-le avec l'appareil photo de la tablette (iPad ou Android). C'est tout !
5. Astuce : dans le navigateur de la tablette, *Partager → Sur l'écran d'accueil* pour avoir ClipForge comme une vraie appli.

Le QR code contient une clé secrète : personne d'autre sur le réseau ne peut ouvrir ton ClipForge sans l'avoir scanné.
Le PC fait le travail lourd (téléchargement, IA, encodage), la tablette sert d'écran tactile : glisse les cadres au doigt, coupe le clip, choisis les styles, puis télécharge les vidéos finies directement sur la tablette.

---

## Comment faire un clip en 1 minute

1. **Accueil** → colle le lien du clip Twitch → **Importer**.
2. L'appli télécharge le clip, trouve la facecam et prépare la mise en page.
3. Onglet **Sous-titres** → *Générer les sous-titres (IA)*.
4. Onglet **Textes** → écris ton titre accrocheur.
5. Ajuste si besoin : déplace les cadres violet (facecam) et vert (jeu) sur la vidéo, coupe le début et la fin sur la barre de temps.
6. Onglet **Exporter** → coche les formats → **Créer les vidéos** → **Télécharger**.

Raccourcis sur PC : `Espace` lecture/pause, `I` début ici, `O` fin ici, `←` `→` image par image.

---

## Questions fréquentes

**Où sont rangées mes vidéos ?**
Dans le dossier `data/projets/<projet>/exports/` à côté de l'appli. Le bouton **« Ouvrir le dossier »** (onglet Exporter, sur le PC) l'ouvre directement.

**L'export est lent.**
ClipForge utilise automatiquement la carte graphique si elle le permet (NVIDIA, AMD, Intel). Sinon, choisis la qualité *Rapide* dans les **Réglages**.

**Les sous-titres ne sont pas assez précis.**
Dans **Réglages**, passe la précision sur *Très précis* (plus lent). Tu peux aussi corriger chaque phrase à la main dans l'onglet Sous-titres. La première génération télécharge le modèle d'IA (une seule fois).

**« Cette vidéo est réservée aux abonnés ».**
Beaucoup de streamers réservent leurs VOD aux abonnés. Si tu es abonné, va dans **Réglages → Compte Twitch**, choisis le navigateur où tu es connecté à Twitch (Firefox conseillé), puis réessaie.

**Mes emojis n'apparaissent pas sur la vidéo.**
Les polices incrustées n'ont pas d'emojis : ils sont retirés de l'image, mais gardés dans la description proposée.

**Le téléchargement d'un clip ne marche plus.**
Twitch change parfois son site. Le lanceur met à jour le module de téléchargement à chaque démarrage : relance simplement ClipForge.

---

## ⚠️ Droits d'auteur

Les clips appartiennent aux streamers. Avant de republier le contenu de quelqu'un d'autre, vérifie qu'il l'autorise (beaucoup de streamers ont des règles pour les « clippeurs ») et crédite-le : l'option « Pseudo / chaîne » est là pour ça.

---

## Pour les développeurs

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt -r requirements-ia.txt
python -m clipforge            # options : --port 8765 --no-browser --local-only
python -m pytest
```

```
clipforge/
  server.py       API web (FastAPI) + accès tablette protégé par clé
  pipeline.py     enchaînement import → analyse → sous-titres → exports
  sources.py      clips Twitch, top clips d'une chaîne, passages de VOD (yt-dlp + HLS)
  analysis.py     détection de facecam (YuNet), mise en page auto, moments forts
  captions.py     transcription / traduction en anglais (faster-whisper), blocs de mots, .srt
  social.py       descriptions, hashtags, tags YouTube, bios de profil, stats de la bibliothèque
  overlays.py     rendu des textes (titre, sous-titres, pseudo) en images transparentes
  render.py       graphe de filtres FFmpeg et encodage par plateforme
  static/         interface (HTML/CSS/JS sans dépendance, tactile)
  assets/         polices (licence OFL) et modèle de détection de visage (licence MIT)
```

Les données (projets, réglages, modèles d'IA) vont dans `data/` (modifiable avec la variable `CLIPFORGE_DATA`).
