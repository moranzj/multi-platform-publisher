<div align="center">

# Multi-Platform Video Publisher (Pubblicatore video multiplatform)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · **Italiano** · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Un video → **Bilibili · Kuaishou · Douyin** — le tre pagine di pubblicazione, compilate per te.

Gratuito e open source (MIT) · Exe portatile, senza installazione · Compila e si ferma: il pulsante “Pubblica” lo premi tu

[⬇️ Scarica (exe portatile)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Tutorial passo a passo (inglese)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="modulo">
  <img src="docs/images/app-run.png" width="32%" alt="log">
  <img src="docs/images/app-done.png" width="32%" alt="finito">
</p>

## Cosa fa

Compili il modulo **una volta sola** — lo strumento apre le pagine di pubblicazione delle tre piattaforme nel tuo Chrome/Edge e inserisce tutto: upload del video, titolo, descrizione, hashtag, copertina e programmazione. Alla fine le pagine restano aperte — le controlli e premi tu “Pubblica”. Lo strumento non invia mai senza il tuo comando.

- **Bilibili / Kuaishou / Douyin** — un video, pubblicazione in blocco
- Titoli e descrizioni per piattaforma, hashtag, copertina (carica un'immagine oppure usa automaticamente il primo fotogramma del video)
- **Pubblicazione immediata o programmata** (finestre validate per piattaforma: Bilibili +5 min–15 giorni, Kuaishou +1 h–14 giorni, Douyin +2 h–14 giorni)
- Tag “maniglia di gioco” per Douyin (la versione web di Kuaishou non ha questa voce)
- Anteprima e controlli prima di aprire qualsiasi cosa: lunghezza titolo/descrizione, numero di tag, rapporto copertina, dimensione file
- Log in tempo reale, screenshot per ogni fase, modelli cronologici (fino a 50)
- Nessuna estensione browser — accedi una volta per piattaforma con QR code, la sessione resta salvata

> L'interfaccia è in cinese; il [tutorial](docs/tutorial-en.md) spiega ogni campo con gli screenshot.

## Scarica ed esegui (Windows 10/11)

1. Scarica `multi-platform-publisher-<version>-exe.zip` da [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Estrai in una cartella **scrivibile** (non in Program Files).
3. Doppio clic su **`多平台发布器.exe`** — servono solo Chrome o Edge. Primo avvio: premi “重新登录” (Accesso di nuovo) e scansiona il QR code una volta per piattaforma.

> L'exe non è firmato, quindi qualche antivirus può segnalarlo — falso positivo tipico di PyInstaller; aggiungilo alla whitelist. Preferisci il codice sorgente? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # autotest dell'ambiente
python cli.py login     # accesso QR, tre schede
python cli.py publish --video "D:\v\clip.mp4" --title "Titolo" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Comportamento predefinito: compila tutto e **si ferma** — controlli le pagine e premi tu Pubblica (`--auto` abilita l'invio automatico; `--now` pubblica subito).

## FAQ

| Sintomo | Rimedio |
|---|---|
| Bloccato sulla pagina di accesso | Sessione scaduta — “重新登录” e nuova scansione |
| “profile is busy” | Chiudi la finestra del browser della run precedente |
| L'antivirus segnala l'exe | Falso positivo PyInstaller — whitelist |
| Un hashtag non diventa “pillola” | L'argomento non esiste sulla piattaforma — riformula |
| CAPTCHA | Risolvilo una volta a mano; pubblicare molto spesso può attivare controlli |

## Note e limiti

- Le piattaforme vengono elaborate in sequenza; ~3–8 min per video (dipende dalla dimensione del file)
- La sessione sta in `profile/` — **non condividerla mai** (sono i tuoi account)
- Un redesign della piattaforma può rompere i selettori; le correzioni vanno in `platforms/<piattaforma>.py`
- Non è un'API ufficiale e non è affiliato a Bilibili, Kuaishou o Douyin. L'automazione del browser può violare i termini delle piattaforme — prova con un account secondario e pubblica responsabilmente, a tuo rischio.

## Licenza

[MIT](LICENSE)
