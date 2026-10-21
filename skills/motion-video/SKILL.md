---
name: motion-video
description: Studio de création de vidéos en motion design piloté par un Artifact de travail. L'utilisateur y fournit ses médias et dit ce qu'il veut en faire, décrit les médias à générer (photos GPT Image et plans vidéo Kling via OpenRouter), l'enchaînement ou l'esprit du film, les transitions et les animations graphiques et texte ; Claude présente ensuite des planches avec extraits animés commentables, génère les médias, rédige une narration modifiable avec choix de voix ElevenLabs et style de sous-titres, puis rend le MP4 final avec HyperFrames. À utiliser dès que l'utilisateur dit « motion vidéo », veut « monter une vidéo » à partir de ses photos et vidéos, faire une vidéo animée avec titres et transitions, une vidéo avec voix off ou sous-titres, ou reprendre un projet vidéo existant dans Documents/Videos. À la fin, le film peut être retouché à la main dans HyperFrames Studio.
---

# Motion vidéo

Un projet = un dossier sur l'ordinateur + un Artifact de travail en 5 étapes (Brief, Planches, Médias générés, Narration, Rendu), puis une retouche possible dans HyperFrames Studio. L'Artifact est l'interface : l'utilisateur y saisit, commente et valide. Claude lit son état dans la base de l'Artifact, travaille en local (génération, montage HyperFrames, rendu) et republie l'étape suivante.

## Emplacements

| Quoi | Où |
|---|---|
| Projets | `~/Documents/Videos/<slug>/` (variable `MOTION_VIDEO_PROJECTS` pour un autre dossier) |
| Clés API | `~/.motion-video/openrouter.txt` et `~/.motion-video/elevenlabs.txt` (variable `MOTION_VIDEO_KEYS` pour un autre dossier, ou `OPENROUTER_API_KEY` / `ELEVENLABS_API_KEY`). Ne jamais afficher ni copier une clé ailleurs. Clé absente : expliquer à l'utilisateur où la déposer (voir le README du dépôt) et s'arrêter. |
| Scripts | `${CLAUDE_SKILL_DIR}/scripts/mv.py` (API), `${CLAUDE_SKILL_DIR}/templates/studio.html` (page). Lancer `python mv.py check` au premier usage : il vérifie Python, ffmpeg, Node et les clés. |

Structure d'un projet :

```
<slug>/
  projet.json        slug, titre, artifact_url, format, créé le
  medias/            médias fournis (récupérés de l'Artifact ou déposés à la main)
  generes/           images et vidéos générées
  audio/             voix off, musique, horodatage des mots
  film/              projet HyperFrames (compositions, BRIEF.md, STORYBOARD.md)
  rendu/             aperçu basse définition et MP4 final
  artifact/          index.html + fichiers publiés (previews/, voix/, media/)
```

## Règles permanentes

- **Limite des clés.** Lancer `python mv.py quota` au démarrage, avant chaque lot de générations et avant le rendu. Écrire le résultat dans le document `ref/quotas` de l'Artifact (la page affiche un bandeau orange en alerte, rouge à la limite). Si une commande sort avec le code 3, ou si `quota` indique `limite`, s'arrêter, dire clairement à l'utilisateur quelle clé est à sa limite, combien il reste et la date de remise à zéro, mettre à jour `ref/quotas`. Ne jamais contourner en changeant de clé.
- **Coût annoncé avant de dépenser.** Avant toute génération vidéo, estimer avec `mv.py video ... --dry-run` et indiquer le total du lot dans `projet/etat.message` et dans la conversation. Au-delà de 5 $ pour un lot, attendre l'accord explicite.
- **Kling** est le modèle vidéo retenu (via OpenRouter). Il ne génère qu'en 16:9, 9:16 et 1:1 : pour un film en 4:3 ou 3:4, générer dans le ratio le plus proche et recadrer au montage. `kwaivgi/kling-v3.0-std` pour itérer, `kwaivgi/kling-v3.0-pro` seulement pour les plans validés si l'utilisateur veut la qualité maximale. Plan vidéo issu d'une image : générer et faire valider l'image d'abord, puis l'animer (`--first-frame`).
- **Images** : `openai/gpt-image-2.5-flare` via OpenRouter (défaut de `mv.py image`), `--ref` pour partir d'une image fournie.
- **Textes affichés** : en français, pas de majuscule à chaque mot dans les titres, tiret « - » plutôt que le tiret long, pas d'émoticône (sauf demande contraire de l'utilisateur).
- **Ne jamais écraser** le brief ou les commentaires saisis par l'utilisateur : lire avant d'écrire, et passer `if_version` sur chaque écriture d'un document existant.
- **Prévenir** quand une étape longue est finie (lot de générations, rendu MP4) ou qu'une limite de clé bloque : dans la conversation, et par la skill de notification de l'utilisateur s'il en a une.

## Publication de l'Artifact

L'outil Artifact ne publie que depuis le dossier de travail ou le scratchpad. À chaque publication :

1. Copier `<projet>/artifact/` vers `<scratchpad>/motion-video/<slug>/` (copie complète, `cp -r`).
2. Publier `index.html` de cette copie avec `root` = ce dossier et `files` = les fichiers ajoutés ou modifiés (chemins relatifs : `previews/s01.html`, `voix/voix-<id>.mp3`, `media/g01.mp4`…). Les fichiers déjà publiés restent en place.
3. Première publication : `capabilities: {"db": {}, "assets": {}, "user": {}}`, `icon: "video"`, `description` d'une phrase. Ensuite ne plus passer `capabilities` ni `icon`. Enregistrer l'URL dans `projet.json`.

Les fichiers lourds (vidéos générées, aperçu) doivent rester sous 15 Mo : réencoder avec ffmpeg en 540p ou 720p pour l'Artifact (`-vf scale=-2:540 -crf 30 -an` pour les plans muets). Les originaux restent dans `generes/` et `rendu/`. Les mp3 ne passent pas par `asset: true` : les publier comme fichiers (`files`).

## Base de données de l'Artifact

Lire et écrire avec l'outil `ArtifactData` (URL du projet).

| Document / collection | Contenu | Écrit par |
|---|---|---|
| `projet/etat` | `phase` (brief, planches, generation, narration, rendu), `phase_max` (dernière étape ouverte), `statut` (`a_remplir`, `soumis`, `en_cours`), `action` (`valider` ou `commenter`), `message` (texte affiché en bandeau), `dossier` | les deux |
| `projet/brief` | `titre`, `format` (16:9, 9:16, 1:1, 4:3, 3:4), `duree`, `langue`, `diffusion`, `message`, `public`, `mode_enchainement` (`guide` ou `libre`), `enchainement`, `transitions[]` + `transitions_note`, `anim_graphique[]` + note, `anim_texte[]` + note, `couleurs[]`, `police`, `references`, `musique` (`aucune`, `fournie`, `ia`) + `musique_note`, `narration` (`oui`/`non`), `narration_intention`, `sous_titres`, `doublage`, `notes` | utilisateur |
| `medias/*` | `nom`, `type`, `taille`, `asset_id`, `url`, `local` (fichier trop lourd déposé dans `medias/` du projet), `usage`, `ordre` | utilisateur |
| `a_generer/*` | `type` (image, video), `brief`, `duree`, `source` (nom d'un média fourni), `ordre` | utilisateur |
| `scenes/*` | `ordre`, `titre`, `duree`, `description`, `medias[]`, `texte_ecran`, `animation`, `transition` (vers la scène suivante), `narration`, `apercu` (chemin publié), `apercu_type` (html, image, video) | Claude |
| `generes/*` | `ordre`, `type`, `titre`, `scene`, `url` (chemin publié), `ratio`, `prompt`, `cout`, `statut` | Claude |
| `projet/narration` | `segments[]` {scene, texte}, `voix_id`, `voix_nom`, `doublage`, `sous_titres` {actif, police, taille, position, style, couleur, accent, majuscules} | les deux |
| `ref/voix` | `liste[]` {id, nom, description, langue, genre, age, usage, url} | Claude |
| `ref/quotas` | sortie de `mv.py quota` | Claude |
| `projet/rendu` | `apercu_url`, `apercu_type`, `mp4_statut`, `mp4_chemin`, `duree`, `taille_mo`, `definition` | Claude |
| `commentaires/*` | `cible` (`scene:<id>`, `genere:<id>`, `planches`, `narration`, `sous-titres`, `rendu`), `texte`, `date`, `auteur`, `traite` | les deux |

Répondre à un commentaire : ajouter un document `commentaires/*` avec `auteur: "claude"` et la même `cible`, puis passer le commentaire d'origine à `traite: true` une fois pris en compte.

## Déroulé

À chaque reprise (« c'est prêt », « validé », « j'ai commenté ») : lire `projet/etat`, puis les documents de l'étape concernée et les `commentaires` non traités. Avant de travailler, passer `statut` à `en_cours` avec un `message` qui dit ce qui se passe ; à la fin, `statut: a_remplir`, avancer `phase` et `phase_max`, et republier si des fichiers ont changé.

### 0. Création

1. Demander seulement le sujet du film s'il n'est pas clair. Choisir un slug court (`lancement-produit`).
2. Créer l'arborescence, copier `templates/studio.html` vers `artifact/index.html` en remplaçant `__TITRE__` par le titre du projet (un nom, pas une phrase).
3. Publier (voir plus haut), puis écrire `projet/etat` = {phase: "brief", phase_max: "brief", statut: "a_remplir", dossier} et `ref/quotas`.
4. Donner le lien à l'utilisateur. Le brief demande obligatoirement le format (paysage 16:9, portrait 9:16, carré 1:1, 4:3, portrait 3:4) : la page refuse la validation sans format.

### 1. Brief → planches

1. Lire `projet/brief`, `medias`, `a_generer`.
2. Récupérer les médias fournis : `Artifact` action `read` avec `path` = `asset_id` (le fichier est enregistré localement), puis copier dans `medias/`. Pour `local: true`, vérifier que le fichier est bien dans `medias/` ; sinon le signaler dans `etat.message` et dans la conversation.
3. Regarder chaque image (Read) et extraire quelques images des vidéos (ffmpeg) pour comprendre le contenu.
4. Construire le découpage : en mode `guide`, suivre l'enchaînement décrit ; en mode `libre`, composer à partir de l'esprit et des usages indiqués. Durées cohérentes avec `duree`. Si une narration est demandée, en écrire un premier jet dès maintenant (environ 2,5 mots par seconde) pour caler les durées.
5. Pour chaque scène, écrire un extrait animé autonome `artifact/previews/sNN.html` : HTML + CSS ou GSAP chargé depuis cdnjs, au format du film, en boucle, avec les vrais médias (copier les images utilisées en basse définition dans `artifact/media/`) ou un aplat qui figure le média à générer. L'extrait montre le texte, l'animation graphique et la transition de sortie. Suivre `/hyperframes-animation` pour le choix des mouvements et `/hyperframes-creative` pour la typographie et la palette (charte du brief en priorité).
   Les images clés peuvent être générées dès cette étape (quelques centimes l'image) pour que les planches montrent le vrai rendu ; les plans vidéo attendent la validation.
   Structure éprouvée : `previews/film.css` + `previews/film.js` communs (mise à l'échelle d'une scène 1080x1920 ou 1920x1080 dans l'iframe, `splitChars`, `loop(tl)`), un fichier par scène avec un `#stage` mis à l'échelle et un `#scene` intérieur. Ne jamais animer `#stage` avec GSAP (son transform sert à la mise à l'échelle) : animer `#scene`. `loop()` accepte `#t=3.5` dans l'URL pour figer l'instant voulu.
   Vérifier les extraits avec Chrome sans fenêtre, pas avec le navigateur intégré (masqué, il ralentit les animations) : servir `artifact/` avec `python -m http.server <port libre>` en arrière-plan, puis `chrome --headless=new --window-size=540,960 --virtual-time-budget=3000 --screenshot=sNN.png "http://localhost:<port>/previews/sNN.html#t=3"` et assembler les captures avec ffmpeg `hstack`. Les textes tapés par `onUpdate` n'apparaissent pas sur une image figée : c'est normal.
6. Écrire les `scenes` (batch), répondre aux commentaires, publier, `phase: planches`.
7. Une personne réelle n'apparaît que sur ses vraies photos et vidéos : les plans générés montrent des lieux, des mains, des silhouettes de dos, jamais un visage inventé ressemblant à la personne. Pas de logo de marque ou de média dans les générations.

### 2. Planches → génération

- `action: commenter` : appliquer les commentaires, mettre à jour scènes et extraits, republier, rester en `planches`.
- `action: valider` : vérifier les quotas, estimer le coût du lot (`--dry-run`), puis générer en arrière-plan les éléments de `a_generer` et ceux que les planches ont ajoutés. Images d'abord ; plans vidéo ensuite, en `--first-frame` quand une image de départ existe. Fichiers dans `generes/`, versions légères dans `artifact/media/`, documents `generes/*` avec coût réel. Publier, `phase: generation`.

### 3. Médias générés → narration

- `commenter` : régénérer uniquement les éléments commentés (nouveau prompt corrigé), en annonçant le coût.
- `valider` : si `brief.narration` vaut `non`, passer directement au rendu (étape 5). Sinon :
  1. Rédiger la narration finale par scène dans `projet/narration.segments`.
  2. `python mv.py voices --lang <langue> --out voix.json --previews <dossier>` puis présélectionner 10 à 14 voix adaptées au ton (genre varié, usage narration ou publicité en priorité). Publier leurs extraits en fichiers `voix/voix-<id>.mp3` et écrire `ref/voix` avec `url` = ce chemin.
  3. Préremplir `sous_titres` d'après le brief (actif si `sous_titres`, style `karaoke` par défaut pour un format portrait, `contour` sinon). `phase: narration`.

### 4. Narration → rendu

- `commenter` : reprendre le texte ou le style selon les commentaires (`narration`, `sous-titres`).
- `valider` :
  0. Aucune voix choisie (`voix_id` absent) : prendre la voix recommandée dans le message de l'étape, l'écrire dans `projet/narration` et le dire.
  1. Si `doublage` : vérifier le quota ElevenLabs, puis un fichier par scène : `mv.py tts --voice <voix_id> --text-file audio/sNN.txt --out audio/sNN.mp3 --timestamps audio/sNN.json`. Ajuster les durées des scènes à la voix (voix + 0,8 s minimum).
  1 bis. Musique « L'IA propose » : `mv.py music --prompt "<style, tempo, sans voix, durée>" --out audio/musique.mp3` (Lyria 3 via OpenRouter, environ 0,08 $, environ 60 s). Couper à la durée du film avec fondus ffmpeg, volume 0,15 environ sous la voix. L'API musique d'ElevenLabs demande une permission que la clé n'a pas forcément.
  2. Si sous-titres : construire les sous-titres depuis `mots.json` (ou depuis le texte et les durées sans doublage) avec le style choisi.
  3. Montage, la méthode éprouvée : `HYPERFRAMES_SKIP_SKILLS=1 npx hyperframes init film --example blank --resolution portrait --non-interactive --skill general-video` (la variable évite que `init` réécrive les skills hyperframes). Un script `film/build_film.py` génère `index.html` en une composition unique : vidéos dans un `div.vwrap` non minuté (le `<video>` porte `data-start`), scènes en `section.clip`, sous-titres en groupes de 4 mots maximum avec le mot prononcé coloré par `tl.set`, voix en `<audio>` avec `data-duration`, volets et fondus en calques au-dessus. Plans vidéo ralentis à la durée exacte de leur scène avec ffmpeg `setpts` + `minterpolate=fps=30`. Polices Google téléchargées en woff2 dans `assets/fonts` avec `@font-face` (exigé par `check`). Pas de `onUpdate` pour les textes tapés : des lettres en `span` révélées par `stagger`. Vérifier que les sous-titres ne masquent ni un visage ni un titre de scène, et leur donner un fond si une scène est claire.
     Repères généraux : projet HyperFrames dans `film/` (`npx hyperframes init`, écrire `BRIEF.md` avec `workflow: general-video`, `flow: companion`, `storyboard: no` puisque les planches sont déjà validées dans l'Artifact). Reprendre les extraits validés comme base des compositions. Suivre `/hyperframes-core` et `/hyperframes-cli` (`check` avant tout rendu). Musique : fichier fourni ou piste proposée, voix en ducking (`/hyperframes-audio`).
  4. Rendre un aperçu `npx hyperframes render --quality draft --output ../rendu/apercu-brut.mp4`, puis normaliser le son pour les réseaux sociaux (le mixage sort autour de -28 dB) : `ffmpeg -i apercu-brut.mp4 -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k apercu.mp4` (même étape pour le MP4 final). Contrôler 6 à 8 images extraites avec ffmpeg avant de publier, réencoder en 540p sous 15 Mo vers `artifact/media/apercu.mp4`, écrire `projet/rendu.apercu_url`, publier, `phase: rendu`.

### 5. Rendu final

- `commenter` : corriger, refaire un aperçu.
- `valider` (« Générer le MP4 final ») : `npx hyperframes render --quality delivery --output ../rendu/<slug>.mp4` en arrière-plan, vérifier la durée avec ffprobe, écrire `projet/rendu` (`mp4_statut: "prêt"`, `mp4_chemin`, `duree`, `taille_mo`, `definition`), prévenir l'utilisateur, donner le chemin du fichier dans la conversation, puis proposer la retouche dans Studio (étape 6).

### 6. Retouche dans HyperFrames Studio (proposée à la fin)

HyperFrames Studio est l'éditeur de HyperFrames : il s'ouvre dans le navigateur avec la timeline complète du film (pistes, clips, textes, timings) et permet de tout modifier à la main, avec un rechargement immédiat.

1. Proposer la retouche une fois le MP4 livré. Si l'utilisateur accepte : `cd <projet>/film && npx hyperframes preview --background`, vérifier que l'URL affichée (avec `#project/film`) répond, et la donner telle quelle.
2. Expliquer en deux phrases : on lit le film, on clique un élément pour le modifier (texte, position, durée, ordre des clips), les changements sont enregistrés dans `film/index.html`. On peut aussi demander une modification à Claude en désignant l'élément cliqué : lire alors la sélection avec `npx hyperframes preview --context --json` et faire la modification dans le fichier.
3. Dès que le film a été retouché dans Studio, ne plus relancer le générateur `build_film.py` : il écraserait les retouches. Toute modification suivante se fait directement dans `index.html`.
4. Quand l'utilisateur a fini : `npx hyperframes check`, puis nouveau rendu final et normalisation du son (étape 5), mise à jour de `projet/rendu`, puis `npx hyperframes preview --stop`.
5. Variante : `npx hyperframes open` ouvre le projet dans l'application de bureau HyperFrames si elle est installée (sinon la commande affiche le lien de téléchargement). Après une session dans l'application, lancer `npx hyperframes catch-up` avant toute nouvelle modification pour connaître ce qui a changé.

## Reprendre un projet

Lire `projet.json` pour retrouver l'URL, puis `projet/etat`. Ne jamais republier sans `url` depuis une autre conversation : lire d'abord l'Artifact (`action: read`), puis publier avec `url`.

## Installation et mises à jour

La skill est distribuée comme plugin Claude Code (dépôt `jherard-fr/motion-video`). Installation, prérequis et clés : voir le README du dépôt. Si l'utilisateur demande de l'aide pour installer, suivre ce README pas à pas avec lui.
