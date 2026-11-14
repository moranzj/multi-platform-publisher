<div align="center">

# Multi-Platform Video Publisher (Penerbit Video Multiplatform)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · **Bahasa Indonesia** · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Satu video → **Bilibili · Kuaishou · Douyin** — ketiga halaman publikasi diisi otomatis untuk Anda.

Gratis & open source (MIT) · Exe portabel, tanpa instalasi · Isi lalu berhenti: tombol “Publikasikan” Anda sendiri yang menekan

[⬇️ Unduh (exe portabel)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Tutorial langkah demi langkah (Inggris)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="formulir">
  <img src="docs/images/app-run.png" width="32%" alt="log">
  <img src="docs/images/app-done.png" width="32%" alt="selesai">
</p>

## Apa fungsinya

Isi formulir **satu kali saja** — alat ini membuka halaman unggahan ketiga platform di Chrome/Edge Anda dan mengisi semuanya: unggahan video, judul, deskripsi, tagar, sampul, dan penjadwalan. Setelah selesai, halaman-halaman itu dibiarkan terbuka — Anda periksa, lalu menekan “Publikasikan” sendiri. Alat ini tidak pernah mengirim tanpa perintah Anda.

- **Bilibili / Kuaishou / Douyin** — satu video, dipublikasikan serempak
- Judul & deskripsi per platform, tagar, sampul (unggah gambar atau otomatis pakai bingkai pertama video)
- **Publikasi langsung atau terjadwal** (rentang waktu divalidasi per platform: Bilibili +5 menit–15 hari, Kuaishou +1 jam–14 hari, Douyin +2 jam–14 hari)
- Tag “hiasan game” untuk Douyin (halaman web Kuaishou tidak memiliki opsi ini)
- Pratinjau & pemeriksaan sebelum ada yang dibuka: panjang judul/deskripsi, jumlah tag, rasio sampul, ukuran berkas
- Log berjalan real-time, tangkapan layar per langkah, templat riwayat (hingga 50)
- Tanpa ekstensi browser — cukup login sekali per platform lewat kode QR, sesi tersimpan

> Antarmuka aplikasi berbahasa Mandarin; [tutorial](docs/tutorial-en.md) menjelaskan setiap kolom beserta tangkapan layarnya.

## Unduh & jalankan (Windows 10/11)

1. Ambil `multi-platform-publisher-<version>-exe.zip` dari [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Ekstrak ke folder mana pun yang **bisa ditulis** (jangan di Program Files).
3. Klik dua kali **`多平台发布器.exe`** — hanya butuh Chrome atau Edge. Pemakaian pertama: klik “重新登录” (Login ulang) dan pindai kode QR satu kali per platform.

> Exe tidak ditandatangani sehingga beberapa antivirus bisa menandainya — positif palsu yang umum pada PyInstaller; tambahkan ke whitelist. Lebih suka dari kode sumber? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # pemeriksaan mandiri lingkungan
python cli.py login     # login QR, tiga tab
python cli.py publish --video "D:\v\clip.mp4" --title "Judul" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Perilaku bawaan: isi semuanya lalu **berhenti** — Anda periksa halamannya dan menekan Publikasikan sendiri (`--auto` mengaktifkan pengiriman otomatis; `--now` langsung mempublikasikan).

## FAQ

| Gejala | Solusi |
|---|---|
| Tertahan di halaman login | Sesi kedaluwarsa — “重新登录” lalu pindai lagi |
| “profile is busy” | Tutup jendela browser dari sesi sebelumnya |
| Antivirus menandai exe | Positif palsu PyInstaller — masukkan whitelist |
| Tagar tidak jadi “pil” | Topik tidak ada di platform itu — ubah redaksinya |
| CAPTCHA | Selesaikan sekali secara manual; publikasi terlalu sering bisa memicu pemeriksaan |

## Catatan & batasan

- Platform diproses satu per satu; ~3–8 menit per video (tergantung ukuran berkas)
- Sesi login tersimpan di `profile/` — **jangan pernah dibagikan** (itu adalah akun Anda)
- Desain ulang platform bisa merusak selector; perbaikan ada di `platforms/<platform>.py`
- Ini bukan API resmi dan tidak berafiliasi dengan Bilibili, Kuaishou, atau Douyin. Otomatisasi browser dapat melanggar ketentuan platform — uji dengan akun cadangan dan publikasikan secara bertanggung jawab, dengan risiko Anda sendiri.

## Lisensi

[MIT](LICENSE)
