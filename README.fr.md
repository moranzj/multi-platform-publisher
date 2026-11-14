<div align="center">

# Multi-Platform Video Publisher (Éditeur vidéo multiplateforme)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · **Français** · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Une vidéo → **Bilibili · Kuaishou · Douyin** — les trois pages de publication, remplies pour vous.

Gratuit et open source (MIT) · Exe portable, sans installation · Remplit puis s'arrête : c'est vous qui appuyez sur « Publier »

[⬇️ Télécharger (exe portable)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Tutoriel pas à pas (anglais)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="formulaire">
  <img src="docs/images/app-run.png" width="32%" alt="journal">
  <img src="docs/images/app-done.png" width="32%" alt="terminé">
</p>

## Ce que ça fait

Remplissez le formulaire **une seule fois** — l'outil ouvre les pages de publication des trois plateformes dans votre Chrome/Edge et remplit tout : envoi de la vidéo, titre, description, hashtags, miniature et programmation. Une fois terminé, les pages restent ouvertes — vous les vérifiez et appuyez vous-même sur « Publier ». L'outil n'envoie jamais sans votre accord.

- **Bilibili / Kuaishou / Douyin** — une vidéo, publication en lot
- Titres et descriptions par plateforme, hashtags, miniature (image à téléverser, ou première image de la vidéo utilisée automatiquement)
- **Publication immédiate ou programmée** (fenêtres validées par plateforme : Bilibili +5 min–15 j, Kuaishou +1 h–14 j, Douyin +2 h–14 j)
- Étiquette « manette de jeu » pour Douyin (la version web de Kuaishou n'a pas cette option)
- Aperçu et vérifications avant toute ouverture : longueur titre/description, nombre de tags, ratio de miniature, taille du fichier
- Journal en direct, captures d'écran à chaque étape, modèles d'historique (jusqu'à 50)
- Aucune extension de navigateur — connexion par QR code une fois par plateforme, puis session conservée

> L'interface est en chinois ; le [tutoriel](docs/tutorial-en.md) détaille chaque champ avec des captures d'écran.

## Télécharger et exécuter (Windows 10/11)

1. Récupérez `multi-platform-publisher-<version>-exe.zip` depuis [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Décompressez dans un dossier **inscriptible** (pas dans Program Files).
3. Double-cliquez sur **`多平台发布器.exe`** — seuls Chrome ou Edge sont requis. Premier lancement : cliquez sur « 重新登录 » (reconnexion) et scannez le QR code une fois par plateforme.

> L'exe n'est pas signé ; certains antivirus peuvent le signaler — faux positif typique de PyInstaller, ajoutez-le à la liste blanche. Vous préférez les sources ? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # autodiagnostic de l'environnement
python cli.py login     # connexion QR, trois onglets
python cli.py publish --video "D:\v\clip.mp4" --title "Titre" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Comportement par défaut : tout remplir puis **s'arrêter** — vous vérifiez les pages et cliquez vous-même sur Publier (`--auto` active l'envoi automatique ; `--now` publie immédiatement).

## FAQ

| Symptôme | Solution |
|---|---|
| Bloqué sur la page de connexion | Session expirée — « 重新登录 » puis rescanner |
| « profile is busy » | Fermez la fenêtre du navigateur de l'exécution précédente |
| L'antivirus signale l'exe | Faux positif PyInstaller — liste blanche |
| Un hashtag ne devient pas une « pilule » | Le sujet n'existe pas sur la plateforme — reformulez |
| CAPTCHA | À résoudre une fois manuellement ; les publications très fréquentes peuvent déclencher des vérifications |

## Notes et limites

- Les plateformes sont traitées l'une après l'autre ; 3–8 min par vidéo (selon la taille du fichier)
- La session est stockée dans `profile/` — **ne la partagez jamais** (ce sont vos comptes)
- Une refonte d'une plateforme peut casser les sélecteurs ; les correctifs vont dans `platforms/<plateforme>.py`
- Ce n'est pas une API officielle, ni affilié à Bilibili, Kuaishou ou Douyin. L'automatisation du navigateur peut contrevenir aux conditions des plateformes — testez avec un compte secondaire et publiez de manière responsable, à vos propres risques.

## Licence

[MIT](LICENSE)
