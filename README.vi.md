<div align="center">

# Multi-Platform Video Publisher (Công cụ đăng video đa nền tảng)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · **Tiếng Việt** · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

Một video → **Bilibili · Kuaishou · Douyin** — cả ba trang đăng tải được điền sẵn cho bạn.

Miễn phí & mã nguồn mở (MIT) · Exe di động, không cần cài đặt · Điền xong rồi dừng: nút “Đăng” do bạn tự bấm

[⬇️ Tải xuống (exe di động)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 Hướng dẫn từng bước (tiếng Anh)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="biểu mẫu">
  <img src="docs/images/app-run.png" width="32%" alt="nhật ký">
  <img src="docs/images/app-done.png" width="32%" alt="xong">
</p>

## Công cụ này làm gì

Điền biểu mẫu **một lần** — công cụ mở ba trang đăng tải trên Chrome/Edge của bạn và điền đầy đủ: tải video lên, tiêu đề, mô tả, hashtag, ảnh bìa và lịch đăng. Khi xong, các trang vẫn mở — bạn soát lại và tự bấm “Đăng”. Công cụ không bao giờ tự gửi khi chưa có lệnh của bạn.

- **Bilibili / Kuaishou / Douyin** — một video, đăng hàng loạt
- Tiêu đề & mô tả riêng cho từng nền tảng, hashtag, ảnh bìa (tải ảnh lên hoặc tự dùng khung hình đầu tiên của video)
- **Đăng ngay hoặc hẹn giờ** (kiểm tra khung thời gian theo từng nền tảng: Bilibili +5 phút–15 ngày, Kuaishou +1 giờ–14 ngày, Douyin +2 giờ–14 ngày)
- Thẻ “móc xỏ game” cho Douyin (trang web của Kuaishou không có mục này)
- Xem trước & kiểm tra trước khi mở bất cứ gì: độ dài tiêu đề/mô tả, số thẻ, tỉ lệ ảnh bìa, dung lượng tệp
- Nhật ký chạy trực tiếp, ảnh chụp từng bước, mẫu lịch sử (tối đa 50)
- Không cần tiện ích trình duyệt — đăng nhập mỗi nền tảng một lần bằng mã QR rồi giữ phiên đăng nhập

> Giao diện của ứng dụng là tiếng Trung; [hướng dẫn](docs/tutorial-en.md) giải thích từng mục kèm ảnh chụp màn hình.

## Tải xuống & chạy (Windows 10/11)

1. Tải `multi-platform-publisher-<version>-exe.zip` từ [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest).
2. Giải nén vào thư mục bất kỳ **có thể ghi** (không để trong Program Files).
3. Nhấp đôi **`多平台发布器.exe`** — chỉ cần Chrome hoặc Edge. Lần đầu: bấm “重新登录” (Đăng nhập lại) và quét mã QR một lần cho từng nền tảng.

> Exe không có chữ ký số nên một số phần mềm diệt virus có thể báo nhầm — hiện tượng phổ biến với PyInstaller; đưa vào danh sách loại trừ. Muốn chạy từ mã nguồn? `git clone` + `setup.bat` (Python 3.9+).

```powershell
python cli.py doctor    # tự kiểm tra môi trường
python cli.py login     # đăng nhập QR, ba thẻ
python cli.py publish --video "D:\v\clip.mp4" --title "Tiêu đề" --ks-topics "#tag1 #tag2" --date 2026-11-20 --time 06:00
```

Hành vi mặc định: điền xong hết rồi **dừng lại** — bạn soát các trang và tự bấm Đăng (`--auto` bật gửi tự động; `--now` đăng ngay lập tức).

## Hỏi đáp nhanh

| Hiện tượng | Cách xử lý |
|---|---|
| Kẹt ở trang đăng nhập | Phiên hết hạn — “重新登录” rồi quét lại |
| “profile is busy” | Đóng cửa sổ trình duyệt của lần chạy trước |
| Phần mềm diệt virus báo exe | Báo nhầm của PyInstaller — đưa vào danh sách loại trừ |
| Hashtag không biến thành “viên thuốc” | Chủ đề không tồn tại trên nền tảng — đổi cách viết |
| CAPTCHA | Tự giải một lần; đăng quá dày có thể kích hoạt kiểm tra của nền tảng |

## Ghi chú & giới hạn

- Ba nền tảng chạy tuần tự; ~3–8 phút mỗi video (tùy dung lượng tệp)
- Phiên đăng nhập nằm trong `profile/` — **tuyệt đối không chia sẻ** (chính là tài khoản của bạn)
- Nền tảng đổi giao diện có thể làm hỏng bộ chọn; sửa trong `platforms/<nền tảng>.py`
- Đây không phải API chính thức và không liên kết với Bilibili, Kuaishou hay Douyin. Tự động hóa trình duyệt có thể vi phạm điều khoản của nền tảng — hãy thử nghiệm bằng tài khoản phụ và đăng tải có trách nhiệm, tự chịu rủi ro.

## Giấy phép

[MIT](LICENSE)
