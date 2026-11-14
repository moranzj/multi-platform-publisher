<div align="center">

# Multi-Platform Video Publisher (Çoklu Platform Video Yayıncısı)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · **Türkçe** · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Tek video → **Bilibili · Kuaishou · Douyin** — üç yayın sayfası da sizin için doldurulur.

Ücretsiz ve açık kaynak (MIT) · Taşınabilir exe, kurulum yok · Doldurur ve durur: “Yayınla” düğmesine siz basarsınız

[⬇️ İndir (taşınabilir exe)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Adım adım rehber (İngilizce)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="form">
  <img src="docs/images/app-run.png" width="32%" alt="günlük">
  <img src="docs/images/app-done.png" width="32%" alt="bitti">
</p>

## Ne yapar

Formu **tek seferde** doldurun — araç, üç platformun yükleme sayfalarını Chrome/Edge'inizde açar ve her şeyi girer: video yükleme, başlık, açıklama, hashtag'ler, kapak ve planlama. İşlem bitince sayfalar olduğu gibi kalır — siz gözden geçirir ve “Yayınla”ya kendiniz basarsınız. Araç, sizin izniniz olmadan asla göndermez.

- **Bilibili / Kuaishou / Douyin** — tek video, toplu yayın
- Platforma özel başlık ve açıklamalar, hashtag'ler, kapak (görsel yükleyin ya da videonun ilk karesi otomatik kullanılsın)
- **Hemen veya zamanlı yayın** (platform bazlı zaman aralıkları doğrulanır: Bilibili +5 dakika–15 gün, Kuaishou +1 saat–14 gün, Douyin +2 saat–14 gün)
- Douyin için “oyun kolyesi” etiketi (Kuaishou'nun web sayfasında böyle bir giriş yok)
- Herhangi bir şey açılmadan önce önizleme ve kontroller: başlık/açıklama uzunluğu, etiket sayısı, kapak oranı, dosya boyutu
- Canlı işlem günlüğü, adım başına ekran görüntüleri, geçmiş şablonları (50'ye kadar)
- Tarayıcı eklentisi gerekmez — her platforma QR kodla bir kez giriş yapın, oturum kayıtlı kalır

> Uygulama arayüzü Çince'dir; [rehber](docs/tutorial-en.md) her alanı ekran görüntüleriyle açıklar.

## İndir ve çalıştır (Windows 10/11)

1. [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest) sayfasından `multi-platform-publisher-<version>-exe.zip` dosyasını indirin.
2. **Yazılabilir** herhangi bir klasöre çıkartın (Program Files değil).
3. **`多平台发布器.exe`** dosyasına çift tıklayın — yalnızca Chrome veya Edge yeterlidir. İlk kullanımda “重新登录” (Yeniden giriş) düğmesine basıp her platform için QR kodu bir kez okutun.

> exe imzasızdır; bazı antivirüsler işaretleyebilir — PyInstaller'da tipik yanlış pozitif, beyaz listeye ekleyin. Kaynak koddan mı kullanmak istersiniz? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # ortam öz-denetimi
python cli.py login     # QR girişi, üç sekme
python cli.py publish --video "D:\v\clip.mp4" --title "Başlık" --ks-topics "#etiket1 #etiket2" --date 2026-11-20 --time 06:00
```

Varsayılan davranış: her şeyi doldur ve **dur** — sayfaları siz gözden geçirir ve Yayınla'ya kendiniz basarsınız (`--auto` otomatik gönderimi açar; `--now` hemen yayınlar).

## SSS

| Belirti | Çözüm |
|---|---|
| Giriş sayfasında takılı kalır | Oturum süresi doldu — “重新登录” ve yeniden okut |
| “profile is busy” | Önceki çalışmanın tarayıcı penceresini kapatın |
| Antivirüs exe'yi işaretliyor | PyInstaller yanlış pozitifi — beyaz listeye ekleyin |
| Hashtag “hap”e dönüşmüyor | Konu platformda yok — ifadeyi değiştirin |
| CAPTCHA | Elle bir kez çözün; çok sık yayın platform kontrollerini tetikleyebilir |

## Notlar ve sınırlar

- Platformlar sırayla işlenir; video başına ~3–8 dakika (dosya boyutuna bağlı)
- Oturum `profile/` klasöründedir — **asla paylaşmayın** (bu, hesaplarınızın ta kendisidir)
- Platform yenilemeleri seçicileri bozabilir; düzeltmeler `platforms/<platform>.py` içine yapılır
- Resmî bir API değildir ve Bilibili, Kuaishou veya Douyin ile bağlantılı değildir. Tarayıcı otomasyonu platformların kullanım şartlarını ihlal edebilir — yedek bir hesapla test edin ve sorumluluk size ait olacak şekilde yayın yapın.

## Lisans

[MIT](LICENSE)
