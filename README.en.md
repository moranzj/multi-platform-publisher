<div align="center">

# Multi-Platform Video Publisher

[简体中文](README.md) · **English** · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

One video → **Bilibili · Kuaishou · Douyin** — all three publishing pages, filled for you.

Free & open source (MIT) · Portable exe, no install · Fill-and-stop: you press “Publish” yourself

[⬇️ Download (portable exe)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Step-by-step tutorial](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="form">
  <img src="docs/images/app-run.png" width="32%" alt="run log">
  <img src="docs/images/app-done.png" width="32%" alt="done">
</p>

## What it does

Fill the form **once** — the tool opens the three platforms' upload pages in your Chrome/Edge and fills everything in: video upload, title, description, hashtags, cover and schedule. When it's done, the pages just sit there — you review them and press “Publish” yourself. The tool never submits without your say-so.

- **Bilibili / Kuaishou / Douyin** — one video, batch published
- Per-platform titles & descriptions, hashtags, cover (upload an image, or use the video's first frame automatically)
- **Publish now or scheduled** (windows validated per platform: Bilibili +5 min–15 d, Kuaishou +1 h–14 d, Douyin +2 h–14 d)
- “Game pendant” tag for Douyin (the Kuaishou web page has no such entry)
- Preview & checks before anything opens: title/description length, tag counts, cover ratio, file size
- Live run log, per-step screenshots, history templates (up to 50)
- No browser extension — log in to each platform once by QR code, then stay logged in

> The app's UI is in Chinese; the [tutorial](docs/tutorial-en.md) explains every field with screenshots.

## Download & run (Windows 10/11)

1. Grab `multi-platform-publisher-<version>-exe.zip` from [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Unzip into any **writable** folder (not Program Files).
3. Double-click **`多平台发布器.exe`** — it needs Chrome or Edge, nothing else. First run: click “重新登录” (Re-login) and scan the QR code once per platform.

> The exe is unsigned, so some antivirus tools may flag it — a common PyInstaller false positive; just whitelist it. Prefer source? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # environment self-check
python cli.py login     # QR login, three tabs
python cli.py publish --video "D:\v\clip.mp4" --title "Title" --ks-topics "#topic1 #topic2" --date 2026-11-20 --time 06:00
```

Default behavior: fill everything and **stop** — you review the pages and click Publish yourself (`--auto` enables auto-submit; `--now` publishes immediately).

## FAQ

| Symptom | Fix |
|---|---|
| Stuck on login | Session expired — “重新登录” and scan again |
| “profile is busy” | Close the browser window left over from the previous run |
| Antivirus flags the exe | PyInstaller false positive — whitelist it |
| Topic didn't become a pill | The topic doesn't exist on that platform — reword it |
| CAPTCHA | Solve it once manually; very frequent publishing can trigger checks |

## Notes & limitations

- Platforms run one after another; ~3–8 min per video (depends on file size)
- The login state lives in `profile/` — **never share it** (it *is* your account)
- Platform redesigns can break selectors; fixes go in `platforms/<platform>.py`
- This is not an official API and is not affiliated with Bilibili, Kuaishou or Douyin. Browser automation may violate the platforms' terms — test with a spare account and publish responsibly, at your own risk.

## License

[MIT](LICENSE)
