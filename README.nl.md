<div align="center">

# Multi-Platform Video Publisher (Multiplatform videopubliceerder)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · **Nederlands** · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Eén video → **Bilibili · Kuaishou · Douyin** — alle drie de publicatiepagina's, voor je ingevuld.

Gratis & open source (MIT) · Draagbare exe, geen installatie · Vult en stopt: jij drukt zelf op “Publiceren”

[⬇️ Downloaden (draagbare exe)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Stap-voor-stap handleiding (Engels)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="formulier">
  <img src="docs/images/app-run.png" width="32%" alt="logboek">
  <img src="docs/images/app-done.png" width="32%" alt="klaar">
</p>

## Wat het doet

Vul het formulier **één keer** in — de tool opent de uploadpagina's van de drie platforms in je Chrome/Edge en vult alles in: video-upload, titel, beschrijving, hashtags, omslag en planning. Daarna blijven de pagina's gewoon open — jij controleert ze en drukt zelf op “Publiceren”. De tool verstuurt nooit zonder jouw akkoord.

- **Bilibili / Kuaishou / Douyin** — één video, bulkpublicatie
- Platformspecifieke titels & beschrijvingen, hashtags, omslag (afbeelding uploaden of automatisch het eerste videobeeld gebruiken)
- **Direct of gepland publiceren** (tijdvensters worden per platform gevalideerd: Bilibili +5 min–15 dagen, Kuaishou +1 u–14 dagen, Douyin +2 u–14 dagen)
- “Game-hanger”-tag voor Douyin (de webpagina van Kuaishou heeft dat niet)
- Voorbeeld & controles vóór er iets wordt geopend: titel-/beschrijvingslengte, aantal tags, verhouding van de omslag, bestandsgrootte
- Live logboek, schermafbeeldingen per stap, historische sjablonen (tot 50)
- Geen browserextensie — log per platform één keer in met een QR-code, daarna blijft de sessie bewaard

> De interface is in het Chinees; de [handleiding](docs/tutorial-en.md) legt elk veld uit met schermafbeeldingen.

## Downloaden & uitvoeren (Windows 10/11)

1. Haal `multi-platform-publisher-<version>-exe.zip` op van [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Pak het uit in een **beschrijfbare** map (niet in Program Files).
3. Dubbelklik op **`多平台发布器.exe`** — er is alleen Chrome of Edge nodig. Eerste keer: klik op “重新登录” (Opnieuw inloggen) en scan per platform eenmalig de QR-code.

> De exe is niet ondertekend, dus sommige antivirusprogramma's markeren hem mogelijk — een veelvoorkomende PyInstaller vals alarm; zet hem op de whitelist. Liever uit de broncode? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # omgevingszelftest
python cli.py login     # QR-login, drie tabbladen
python cli.py publish --video "D:\v\clip.mp4" --title "Titel" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Standaardgedrag: alles invullen en **stoppen** — jij bekijkt de pagina's en klikt zelf op Publiceren (`--auto` zet automatisch verzenden aan; `--now` publiceert meteen).

## FAQ

| Symptoom | Oplossing |
|---|---|
| Blijf hangen op de inlogpagina | Sessie verlopen — “重新登录” en opnieuw scannen |
| “profile is busy” | Sluit het browservenster van de vorige run |
| Antivirus markeert de exe | PyInstaller vals alarm — whitelist |
| Hashtag wordt geen “pil” | Het onderwerp bestaat niet op dat platform — herformuleer |
| CAPTCHA | Los het één keer handmatig op; heel vaak publiceren kan controles triggeren |

## Kanttekeningen & beperkingen

- De platforms worden na elkaar verwerkt; ~3–8 min per video (afhankelijk van bestandsgrootte)
- De sessie staat in `profile/` — **deel dit nooit** (het zijn je accounts)
- Een platform-redesign kan selectors breken; fixes gaan in `platforms/<platform>.py`
- Geen officiële API en niet gelieerd aan Bilibili, Kuaishou of Douyin. Browserautomatisering kan in strijd zijn met de voorwaarden van de platforms — test met een tweede account en publiceer verantwoord, op eigen risico.

## Licentie

[MIT](LICENSE)
