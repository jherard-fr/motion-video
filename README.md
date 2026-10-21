# Motion vidéo

Un studio de création de vidéos en motion design piloté par Claude. Vous décrivez votre film dans une page de travail (un Artifact) : vos médias et ce que vous voulez en faire, les médias à générer, l'enchaînement ou l'esprit du film, les transitions et les animations. Claude vous présente des planches avec des extraits animés à commenter, génère les médias, rédige une narration que vous pouvez modifier, propose des voix et des styles de sous-titres, puis rend le MP4 final. Vous pouvez ensuite retoucher le film à la main dans HyperFrames Studio.

Il suffit de dire à Claude « motion vidéo » ou « je veux faire une vidéo sur… ».

## Ce qu'il faut avoir

- **Un abonnement Claude** (Pro, Max, Team ou Enterprise) et **Claude Code** : l'application de bureau Claude (onglet Code) ou Claude Code dans un terminal.
- **Un compte GitHub** avec l'invitation au dépôt acceptée (le dépôt est privé). Aucun connecteur GitHub n'est nécessaire dans Claude : l'installation passe par Git, qui vous demandera de vous connecter à GitHub dans le navigateur la première fois.
- **Une clé OpenRouter** (images, plans vidéo, musique) et **une clé ElevenLabs** (voix off). Voir plus bas.
- Un ordinateur Windows ou Mac avec environ 2 Go d'espace libre.

## 1. Accepter l'invitation GitHub

Vous avez reçu un e-mail de GitHub « invited you to collaborate on jherard-fr/motion-video ». Cliquez sur **View invitation**, puis **Accept invitation**. Sans compte GitHub, créez-en un gratuitement sur github.com avec l'adresse qui a reçu l'invitation.

## 2. Installer les logiciels nécessaires

### Windows

Ouvrez **PowerShell** (menu Démarrer, tapez « PowerShell ») et collez ces commandes une par une. Acceptez les éventuelles demandes d'autorisation.

```powershell
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Python.Python.3.12 -e
winget install --id Gyan.FFmpeg -e
winget install --id Google.Chrome -e
```

**Fermez PowerShell et rouvrez-le** (pour que les nouveaux programmes soient reconnus), puis :

```powershell
python -m pip install requests
npx --yes hyperframes skills
```

La dernière commande installe les skills HyperFrames (le moteur de montage) pour Claude.

Si vous n'avez pas encore Claude Code en ligne de commande :

```powershell
irm https://claude.ai/install.ps1 | iex
```

### Mac

Ouvrez le **Terminal**. Si Homebrew n'est pas installé, installez-le depuis brew.sh. Puis :

```bash
brew install git node python ffmpeg
brew install --cask google-chrome
python3 -m pip install requests
npx --yes hyperframes skills
curl -fsSL https://claude.ai/install.sh | bash
```

## 3. Installer la skill

Dans PowerShell (Windows) ou le Terminal (Mac) :

```bash
claude plugin marketplace add jherard-fr/motion-video
claude plugin install motion-video@motion-video
```

La première fois, une fenêtre de connexion GitHub peut s'ouvrir : connectez-vous avec le compte qui a accepté l'invitation.

Redémarrez ensuite l'application Claude (ou relancez `claude`).

**Plus simple :** vous pouvez aussi ouvrir l'application Claude, onglet Code, et coller ce message :

> Installe pour moi le plugin Claude Code du dépôt privé GitHub jherard-fr/motion-video : vérifie que Git, Node.js, Python avec le module requests, ffmpeg et Google Chrome sont installés (installe ce qui manque), lance `npx --yes hyperframes skills`, puis `claude plugin marketplace add jherard-fr/motion-video` et `claude plugin install motion-video@motion-video`. Explique-moi chaque étape où je dois agir.

## 4. Déposer vos clés

Créez un dossier `.motion-video` dans votre dossier personnel :
- Windows : `C:\Users\<votre nom>\.motion-video\`
- Mac : `~/.motion-video/`

Placez-y deux fichiers texte, chacun contenant uniquement la clé, sur une seule ligne :

| Fichier | Clé | Où l'obtenir |
|---|---|---|
| `openrouter.txt` | OpenRouter | openrouter.ai, menu **Keys**, **Create Key**. Ajoutez du crédit (menu **Credits**) et fixez une limite mensuelle sur la clé, par exemple 20 $. |
| `elevenlabs.txt` | ElevenLabs | elevenlabs.io, **Developers**, **API Keys**, **Create API Key**. Cochez au minimum les permissions **Text to Speech**, **Voices** (lecture) et **User** (lecture). |

Ne partagez jamais ces fichiers et ne les mettez pas dans un dossier synchronisé publiquement.

Ordre de grandeur des coûts pour un film d'une minute : 0,05 $ par image générée, 0,40 à 0,60 $ par plan vidéo de 5 secondes, 0,08 $ pour la musique. La voix off utilise le quota de caractères de votre abonnement ElevenLabs. La skill annonce toujours le coût avant de générer, et vous prévient quand une clé approche de sa limite.

## 5. Vérifier l'installation

Dans Claude (onglet Code), demandez : « vérifie l'installation de motion vidéo ». Claude lance un contrôle qui affiche une ligne par élément :

```
OK      Python 3.12.7
OK      module Python requests
OK      ffmpeg
...
OK      OpenRouter répond : 20.0 $ restants
OK      ElevenLabs répond : 30000 caractères restants

Tout est prêt.
```

Chaque ligne « MANQUE » indique quoi installer.

## 6. Utiliser la skill

Dites par exemple à Claude : « motion vidéo : un film de 30 secondes pour présenter notre atelier de céramique ». Claude crée le projet dans `Documents/Videos/` et vous donne le lien de la page de travail. Ensuite, à chaque étape :

1. Remplissez ou commentez dans la page, puis cliquez sur le bouton de validation.
2. Revenez dans la conversation et dites « c'est prêt ».

Les étapes : brief, planches animées, médias générés, narration (texte, voix, sous-titres), aperçu puis MP4 final. À la fin, Claude propose d'ouvrir le film dans **HyperFrames Studio**, un éditeur dans le navigateur avec la timeline du film : vous pouvez y changer un texte, une durée ou l'ordre des plans, puis demander un nouveau rendu.

## Mises à jour

Pour récupérer la dernière version :

```bash
claude plugin marketplace update motion-video
claude plugin update motion-video@motion-video
```

Puis redémarrez Claude.

## En cas de problème

- **« Clé introuvable »** : vérifiez le nom des fichiers (`openrouter.txt`, `elevenlabs.txt`) et le dossier `.motion-video`.
- **« missing the permission text_to_speech »** : activez la permission Text to Speech sur la clé ElevenLabs.
- **« LIMITE ATTEINTE »** : le crédit OpenRouter ou le quota ElevenLabs est épuisé ; la date de remise à zéro est indiquée.
- **Échec de `claude plugin marketplace add`** : vérifiez que l'invitation GitHub est acceptée et que Git est installé, puis relancez la commande.
