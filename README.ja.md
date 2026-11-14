<div align="center">

# Multi-Platform Video Publisher（多プラットフォーム投稿ツール）

[简体中文](README.md) · [English](README.en.md) · **日本語** · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

動画 1 本を **ビリビリ（B站）・クアイショウ（快手）・ドウイン（抖音）** の 3 プラットフォームへ —— 投稿ページをすべて自動入力。

無料 & オープンソース（MIT） · インストール不要のポータブル exe · 入力して停止：最後の「投稿」ボタンはあなたが押します

[⬇️ ダウンロード（ポータブル exe）](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 ステップ解説チュートリアル（英語）](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="フォーム">
  <img src="docs/images/app-run.png" width="32%" alt="実行ログ">
  <img src="docs/images/app-done.png" width="32%" alt="完了">
</p>

## できること

フォームに **1 回**入力するだけで、ツールが Chrome/Edge で 3 プラットフォームの投稿ページを開き、動画アップロード・タイトル・説明文・ハッシュタグ・サムネイル・予約投稿まで全部入力します。入力が終わったらページはそのまま —— あなたが目で確認して、自分で「投稿」を押します。ツールが勝手に送信することはありません。

- **ビリビリ / クアイショウ / ドウイン** —— 動画 1 本を一括投稿
- プラットフォーム別のタイトル・説明文・ハッシュタグ・サムネイル（画像を指定、または動画の先頭フレームを自動使用）
- **即時投稿 / 予約投稿**（各プラットフォームの予約可能範囲を検証：ビリビリ +5 分〜15 日、クアイショウ +1 時間〜14 日、ドウイン +2 時間〜14 日）
- ドウインの「ゲームペンダント」タグ対応（クアイショウの Web 版には項目がありません）
- ブラウザを開く前にプレビュー & チェック：文字数・タグ数・サムネイル比率・ファイルサイズ
- リアルタイム実行ログ・各ステップのスクリーンショット・履歴テンプレート（最大 50 件）
- ブラウザ拡張不要 —— 各プラットフォームに QR コードで 1 回ログインすれば、以降はログイン状態を再利用

> アプリの UI は中国語です。[チュートリアル（英語）](docs/tutorial-en.md) で全フィールドをスクリーンショット付きで解説しています。

## ダウンロードと実行（Windows 10/11）

1. [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest) から `multi-platform-publisher-<version>-exe.zip` をダウンロード。
2. **書き込み可能**なフォルダに解凍（Program Files は避ける）。
3. **`多平台发布器.exe`** をダブルクリック —— 必要なのは Chrome か Edge だけ。初回は「重新登录」（再ログイン）を押して、各プラットフォームの QR コードを 1 回ずつスキャン。

> exe は未署名のため、ウイルス対策ソフトが誤検知することがあります（PyInstaller の典型）。ホワイトリストに追加してください。ソースから使う場合は `git clone` + `setup.bat`（Python 3.9+）。

```powershell
python cli.py doctor    # 環境セルフチェック
python cli.py login     # QR ログイン（3 タブ）
python cli.py publish --video "D:\v\clip.mp4" --title "タイトル" --ks-topics "#タグ1 #タグ2" --date 2026-11-20 --time 06:00
```

デフォルトは「入力して停止」—— ページを確認してから自分で投稿を押します（`--auto` で自動送信、`--now` で即時投稿）。

## FAQ

| 症状 | 対処 |
|---|---|
| ログイン画面で止まる | セッション切れ —— 「重新登录」でもう一度スキャン |
| 「profile is busy」 | 前回のブラウザウィンドウを閉じてから実行 |
| ウイルス対策ソフトが exe を検知 | PyInstaller の誤検知 —— ホワイトリストへ |
| ハッシュタグがピル（カプセル）にならない | そのプラットフォームに話題が存在しない —— 表現を変える |
| CAPTCHA が出る | 手動で 1 回通す。高頻度投稿はプラットフォームのチェックを招くことがあります |

## 注意・制限

- 3 プラットフォームは順番に処理。動画 1 本あたり約 3〜8 分（ファイルサイズによる）
- ログイン状態は `profile/` に保存 —— **絶対に共有しないでください**（それ自体がアカウントです）
- プラットフォームの改修でセレクタが壊れることがあります。修正は `platforms/<platform>.py` へ
- 公式 API ではなく、ビリビリ・クアイショウ・ドウインとは無関係です。ブラウザ自動操作は各社の利用規約に抵触する可能性があるため、サブアカウントでテストし、自己責任でご利用ください。

## ライセンス

[MIT](LICENSE)
