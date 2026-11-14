<div align="center">

# Multi-Platform Video Publisher (멀티 플랫폼 영상 게시기)

[简体中文](README.md) · [English](README.en.md) · [日本語](README.ja.md) · **한국어** · [Español](README.es.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Русский](README.ru.md) · [Português (BR)](README.pt-BR.md) · [Italiano](README.it.md) · [Türkçe](README.tr.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [ไทย](README.th.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md)

영상 1개를 **빌리빌리 · 쿠아이쇼우 · 더우인(중국식 틱톡)** 세 플랫폼에 —— 게시 페이지를 전부 자동으로 작성해 드립니다.

무료 & 오픈소스(MIT) · 설치 없는 포터블 exe · 입력 후 대기: 마지막 "게시" 버튼은 직접 누릅니다

[⬇️ 다운로드(포터블 exe)](https://github.com/moranzj/multi-platform-publisher/releases/latest) · [📖 단계별 튜토리얼(영어)](docs/tutorial-en.md)

</div>

<p align="center">
  <img src="docs/images/app-form.png" width="32%" alt="입력 폼">
  <img src="docs/images/app-run.png" width="32%" alt="실행 로그">
  <img src="docs/images/app-done.png" width="32%" alt="완료">
</p>

## 이 도구의 역할

폼에 **한 번만** 입력하면, 도구가 Chrome/Edge에서 세 플랫폼의 업로드 페이지를 열어 영상 업로드 · 제목 · 설명 · 해시태그 · 커버 · 예약까지 모두 채워 넣습니다. 채우기가 끝나면 페이지는 그대로 유지되고 — 직접 눈으로 확인한 뒤 "게시" 버튼을 누릅니다. 도구가 임의로 제출하지 않습니다.

- **빌리빌리 / 쿠아이쇼우 / 더우인** — 영상 1개를 일괄 게시
- 플랫폼별 제목 · 설명 · 해시태그 · 커버(이미지 지정, 미지정 시 영상 첫 프레임 자동 사용)
- **즉시 게시 / 예약 게시**(플랫폼별 예약 가능 범위 검증: 빌리빌리 +5분~15일, 쿠아이쇼우 +1시간~14일, 더우인 +2시간~14일)
- 더우인 "게임 펜던트" 태그 지원(쿠아이쇼우 웹 버전에는 해당 항목 없음)
- 브라우저를 열기 전 미리보기 & 검사: 제목/설명 길이 · 태그 수 · 커버 비율 · 파일 크기
- 실시간 실행 로그 · 단계별 스크린샷 · 기록 템플릿(최대 50개)
- 브라우저 확장 불필요 — 플랫폼마다 QR 코드로 한 번만 로그인하면 이후 자동 유지

> 앱 UI는 중국어입니다. [튜토리얼(영어)](docs/tutorial-en.md)에서 모든 입력란을 스크린샷과 함께 설명합니다.

## 다운로드 및 실행(Windows 10/11)

1. [Releases](https://github.com/moranzj/multi-platform-publisher/releases/latest)에서 `multi-platform-publisher-<version>-exe.zip`을 내려받습니다.
2. **쓰기 가능**한 폴더에 압축 해제(Program Files 제외).
3. **`多平台发布器.exe`**를 두 번 클릭 — Chrome 또는 Edge만 있으면 됩니다. 최초 실행 시 "重新登录"(재로그인)을 누르고 플랫폼별로 QR 코드를 한 번씩 스캔하세요.

> exe는 서명이 없어 일부 백신이 오탐할 수 있습니다(PyInstaller의 일반적인 현상). 화이트리스트에 추가하세요. 소스로 직접 실행하려면 `git clone` + `setup.bat`(Python 3.9+).

```powershell
python cli.py doctor    # 환경 자가 점검
python cli.py login     # QR 로그인(세 탭)
python cli.py publish --video "D:\v\clip.mp4" --title "제목" --ks-topics "#태그1 #태그2" --date 2026-11-20 --time 06:00
```

기본 동작은 "채우고 정지" — 페이지를 확인한 뒤 직접 게시 버튼을 누릅니다(`--auto`는 자동 제출, `--now`는 즉시 게시).

## FAQ

| 증상 | 해결 |
|---|---|
| 로그인 페이지에서 멈춤 | 세션 만료 — "重新登录" 후 다시 스캔 |
| "profile is busy" | 이전 실행의 브라우저 창을 닫고 재실행 |
| 백신이 exe 탐지 | PyInstaller 오탐 — 화이트리스트 등록 |
| 해시태그가 필(캡슐)로 변하지 않음 | 해당 플랫폼에 없는 토픽 — 표현을 바꾸세요 |
| CAPTCHA 등장 | 수동으로 1회 통과. 고빈도 게시는 플랫폼 점검을 유발할 수 있음 |

## 참고 및 제한

- 세 플랫폼은 순차 처리. 영상 1개당 약 3~8분(용량에 따라 다름)
- 로그인 상태는 `profile/`에 저장 — **절대 공유 금지**(그 자체가 계정입니다)
- 플랫폼 개편으로 셀렉터가 깨질 수 있음. 수정은 `platforms/<platform>.py`에서
- 공식 API가 아니며 빌리빌리 · 쿠아이쇼우 · 더우인과 제휴하지 않았습니다. 브라우저 자동화는 플랫폼 약관에 어긋날 수 있으므로 보조 계정으로 테스트하고 본인 책임하에 사용하세요.

## 라이선스

[MIT](LICENSE)
