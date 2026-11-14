<div align="center">

# Multi-Platform Video Publisher (Wieloplatformowy wydawca wideo)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · **Polski** · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Jedno wideo → **Bilibili · Kuaishou · Douyin** — wszystkie trzy strony publikacji wypełnione za Ciebie.

Darmowe i otwartoźródłowe (MIT) · Przenośny exe, bez instalacji · Wypełnia i zatrzymuje się: przycisk „Publikuj” naciskasz sam

[⬇️ Pobierz (przenośny exe)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Samouczek krok po kroku (angielski)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="formularz">
  <img src="docs/images/app-run.png" width="32%" alt="dziennik">
  <img src="docs/images/app-done.png" width="32%" alt="gotowe">
</p>

## Co to robi

Wypełnij formularz **raz** — narzędzie otwiera strony publikacji trzech platform w Twoim Chrome/Edge i wprowadza wszystko: wysyłkę wideo, tytuł, opis, hashtagi, miniaturę i harmonogram. Po zakończeniu strony po prostu czekają — sprawdzasz je i sam naciskasz „Publikuj”. Narzędzie nigdy nie wysyła bez Twojego polecenia.

- **Bilibili / Kuaishou / Douyin** — jedno wideo, publikacja hurtowa
- Tytuły i opisy osobno dla każdej platformy, hashtagi, miniatura (wgraj obraz albo automatycznie użyj pierwszej klatki wideo)
- **Publikacja natychmiastowa lub planowana** (okna czasowe sprawdzane per platforma: Bilibili +5 min–15 dni, Kuaishou +1 h–14 dni, Douyin +2 h–14 dni)
- Znacznik „maneta gry” dla Douyina (strona internetowa Kuaishou nie ma tej opcji)
- Podgląd i kontrole przed otwarciem czegokolwiek: długość tytułu/opisu, liczba tagów, proporcje miniatury, rozmiar pliku
- Podglądany na żywo dziennik, zrzuty ekranu każdego etapu, szablony historii (do 50)
- Bez rozszerzeń przeglądarki — wystarczy zalogować się raz na platformę kodem QR

> Interfejs jest po chińsku; [samouczek](docs/tutorial-en.md) wyjaśnia każde pole wraz ze zrzutami ekranu.

## Pobierz i uruchom (Windows 10/11)

1. Pobierz `multi-platform-publisher-<version>-exe.zip` ze strony [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Rozpakuj do dowolnego katalogu **z prawem zapisu** (nie Program Files).
3. Podwójnie kliknij **`多平台发布器.exe`** — wystarczy Chrome lub Edge. Pierwsze uruchomienie: kliknij „重新登录” (ponowne logowanie) i zeskanuj kod QR raz na każdą platformę.

> Exe jest niepodpisany, więc część antywirusów może go flagować — typowy fałszywy alarm PyInstallera; dodaj do wyjątków. Wolisz z kodu źródłowego? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # autotest środowiska
python cli.py login     # logowanie QR, trzy karty
python cli.py publish --video "D:\v\clip.mp4" --title "Tytuł" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Domyślne zachowanie: wypełnij wszystko i **zatrzymaj się** — sprawdzasz strony i sam klikasz Publikuj (`--auto` włącza automatyczne wysyłanie; `--now` publikuje natychmiast).

## FAQ

| Objaw | Rozwiązanie |
|---|---|
| Utknięcie na stronie logowania | Sesja wygasła — „重新登录” i zeskanuj ponownie |
| „profile is busy” | Zamknij okno przeglądarki z poprzedniego uruchomienia |
| Antywirus flaguje exe | Fałszywy alarm PyInstallera — dodaj do wyjątków |
| Hashtag nie stał się „pigułką” | Temat nie istnieje na platformie — przeformułuj |
| CAPTCHA | Rozwiąż raz ręcznie; bardzo częste publikowanie może uruchomić kontrole |

## Uwagi i ograniczenia

- Platformy przetwarzane są po kolei; ~3–8 min na wideo (zależnie od rozmiaru pliku)
- Sesja leży w `profile/` — **nigdy jej nie udostępniaj** (to Twoje konta)
- Przeprojektowanie platformy może zepsuć selektory; poprawki w `platforms/<platforma>.py`
- To nie jest oficjalne API i nie jest powiązane z Bilibili, Kuaishou ani Douyin. Automatyzacja przeglądarki może naruszać regulaminy platform — testuj na zapasowym koncie i publikuj odpowiedzialnie, na własne ryzyko.

## Licencja

[MIT](LICENSE)
