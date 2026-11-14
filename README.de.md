<div align="center">

# Multi-Platform Video Publisher (Multiplattform-Videopublisher)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · **Deutsch** · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Ein Video → **Bilibili · Kuaishou · Douyin** — alle drei Upload-Seiten, automatisch ausgefüllt.

Kostenlos & Open Source (MIT) · Portable EXE, keine Installation · Ausfüllen und anhalten: Du drückst selbst auf „Veröffentlichen“

[⬇️ Download (portable EXE)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Schritt-für-Schritt-Anleitung (englisch)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="Formular">
  <img src="docs/images/app-run.png" width="32%" alt="Laufprotokoll">
  <img src="docs/images/app-done.png" width="32%" alt="fertig">
</p>

## Was es macht

Formular **einmal** ausfüllen — das Tool öffnet die Upload-Seiten der drei Plattformen in deinem Chrome/Edge und trägt alles ein: Video-Upload, Titel, Beschreibung, Hashtags, Cover und Terminplanung. Danach bleiben die Seiten einfach offen — du prüfst sie und klickst selbst auf „Veröffentlichen“. Das Tool sendet nie ohne dein Zutun.

- **Bilibili / Kuaishou / Douyin** — ein Video, Sammelveröffentlichung
- Plattformspezifische Titel & Beschreibungen, Hashtags, Cover (Bild hochladen oder automatisch das erste Videobild verwenden)
- **Sofort oder geplant veröffentlichen** (Zeitfenster werden geprüft: Bilibili +5 Min–15 Tage, Kuaishou +1 Std–14 Tage, Douyin +2 Std–14 Tage)
- „Game-Anhänger“-Tag für Douyin (die Kuaishou-Webseite hat diesen Eintrag nicht)
- Vorschau & Prüfung, bevor etwas geöffnet wird: Titel-/Beschreibungslänge, Tag-Anzahl, Cover-Verhältnis, Dateigröße
- Laufendes Protokoll, Screenshots je Schritt, Verlaufs-Vorlagen (bis zu 50)
- Keine Browser-Erweiterung — pro Plattform einmal per QR-Code anmelden, danach bleibt die Sitzung erhalten

> Die Oberfläche ist auf Chinesisch; die [Anleitung](docs/tutorial-en.md) erklärt jedes Feld mit Screenshots.

## Download & Ausführen (Windows 10/11)

1. `multi-platform-publisher-<version>-exe.zip` von [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest) herunterladen.
2. In einen **beschreibbaren** Ordner entpacken (nicht Program Files).
3. **`多平台发布器.exe`** doppelklicken — es wird nur Chrome oder Edge benötigt. Erster Start: „重新登录“ (Neu anmelden) klicken und pro Plattform einmal den QR-Code scannen.

> Die EXE ist nicht signiert, daher kann ein Virenscanner sie markieren — ein typischer PyInstaller-Fehlalarm; einfach auf die Whitelist setzen. Lieber aus dem Quellcode? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # Umgebungsselbsttest
python cli.py login     # QR-Anmeldung, drei Tabs
python cli.py publish --video "D:\v\clip.mp4" --title "Titel" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Standardverhalten: alles ausfüllen und **anhalten** — du prüfst die Seiten und klickst selbst auf Veröffentlichen (`--auto` aktiviert das automatische Absenden; `--now` veröffentlicht sofort).

## FAQ

| Symptom | Lösung |
|---|---|
| Bleibt auf der Login-Seite hängen | Sitzung abgelaufen — „重新登录“ und erneut scannen |
| „profile is busy“ | Browserfenster des letzten Laufs schließen |
| Virenscanner meldet die EXE | PyInstaller-Fehlalarm — auf die Whitelist setzen |
| Hashtag wird keine „Pille“ | Thema existiert auf der Plattform nicht — anders formulieren |
| CAPTCHA | Einmal manuell lösen; sehr häufiges Veröffentlichen kann Prüfungen auslösen |

## Hinweise & Grenzen

- Die Plattformen laufen nacheinander; ca. 3–8 Min. pro Video (je nach Dateigröße)
- Die Sitzung liegt in `profile/` — **niemandem weitergeben** (das sind deine Konten)
- Plattform-Redesigns können Selektoren brechen; Fixes in `platforms/<plattform>.py`
- Keine offizielle API und nicht mit Bilibili, Kuaishou oder Douyin verbunden. Browser-Automatisierung kann gegen die Nutzungsbedingungen verstoßen — mit Zweitaccount testen und verantwortungsvoll auf eigenes Risiko veröffentlichen.

## Lizenz

[MIT](LICENSE)
