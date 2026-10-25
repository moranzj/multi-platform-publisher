"""多平台视频发布器 —— 命令行入口。

用法：
    python cli.py doctor
    python cli.py login
    python cli.py publish --video "D:\\v.mp4" --title "标题"
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROFILE_DIR = ROOT / "profile"
CONFIG_PATH = ROOT / "config.json"

sys.path.insert(0, str(ROOT))

from core import __version__, steps  # noqa: E402
from core.browser import BrowserUnavailable, first_page, open_context  # noqa: E402
from core.log import RunLog  # noqa: E402
from platforms.base import Job, Result  # noqa: E402
from platforms.bilibili import Bilibili  # noqa: E402
from platforms.douyin import Douyin  # noqa: E402
from platforms.kuaishou import Kuaishou  # noqa: E402

REGISTRY = {p.key: p for p in (Bilibili(), Kuaishou(), Douyin())}
ALL_KEYS = ["bili", "kuaishou", "douyin"]

# 只在该平台登录成功后才会出现的会话 cookie（游客态实测均不存在）
LOGIN_COOKIES: dict[str, tuple[set[str], str]] = {
    "bili": ({"SESSDATA"}, "bilibili.com"),
    "kuaishou": ({"userId"}, "kuaishou.com"),
    "douyin": ({"sessionid"}, "douyin.com"),
}


def login_cookie_ok(ctx, key: str) -> bool:
    need, domain = LOGIN_COOKIES[key]
    try:
        names = {c["name"] for c in ctx.cookies() if domain in (c.get("domain") or "")}
    except Exception:
        return False
    return bool(need & names)


def cookie_names(ctx, key: str) -> list[str]:
    _need, domain = LOGIN_COOKIES[key]
    try:
        return sorted({c["name"] for c in ctx.cookies()
                       if domain in (c.get("domain") or "")})
    except Exception:
        return []


# ---------------------------------------------------------------- 配置
def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(cfg, dict):
                return cfg
            print("[!!] config.json 顶层不是对象，使用空配置")
        except Exception as exc:
            print(f"[!!] config.json 解析失败，使用空配置：{exc}")
    return {}


def cfg_default(cfg: dict, key: str, fallback: str = "") -> str:
    defaults = cfg.get("defaults")
    if not isinstance(defaults, dict):
        return fallback
    value = defaults.get(key)
    return value if isinstance(value, str) and value.strip() else fallback


def say(msg: str = "") -> None:
    """控制台输出。GUI 被关掉后 stdout 管道会断，不能让它把后台任务带崩。"""
    try:
        print(msg, flush=True)
    except Exception:
        pass


# ---------------------------------------------------------------- doctor
def cmd_doctor(_args) -> int:
    print("=== 环境自检 ===")
    ok = True
    gui_ok = True

    print(f"版本        : {__version__}")
    print(f"Python      : {sys.version.split()[0]}")
    if sys.version_info < (3, 9):
        print("[XX] Python 版本过低，需要 3.9+（推荐 3.11）")
        ok = False

    try:
        import tkinter  # noqa: F401
        print("tkinter     : ✓")
    except Exception as exc:
        print(f"[!!] tkinter 不可用，图形界面无法启动：{exc}")
        gui_ok = False

    try:
        import playwright
        from playwright.sync_api import sync_playwright
        print(f"Playwright  : {playwright.__file__}")
    except Exception as exc:
        print(f"[XX] Playwright 未安装：{exc}")
        print("     修复：pip install -r requirements.txt")
        return 1

    try:
        import PIL
        print(f"Pillow      : {PIL.__version__} ✓")
    except Exception:
        print("Pillow      : 未安装（可选，但快手封面亮度/封面校验会退化）")

    # 浏览器可用性
    with sync_playwright() as pw:
        for channel in ("chrome", "msedge"):
            try:
                b = pw.chromium.launch(channel=channel, headless=True)
                print(f"浏览器      : {channel} {b.version} ✓")
                b.close()
                break
            except Exception:
                print(f"浏览器      : {channel} 不可用")
        else:
            print("[XX] Chrome / Edge 都启动不了")
            ok = False

    print(f"profile 目录: {PROFILE_DIR} {'✓' if (PROFILE_DIR / 'Default').exists() else '（尚未初始化，先跑 login）'}")

    cfg = load_config()
    defaults = cfg.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
    if defaults:
        print("默认预设    :")
        for k, v in defaults.items():
            print(f"  {k} = {v}")
    else:
        print("默认预设    : 无（可在 config.json 里配置）")

    if ok:
        tail = "自检通过，可以运行 python cli.py login"
        if not gui_ok:
            tail += "（图形界面不可用，CLI 仍可使用）"
    else:
        tail = "存在阻断项，先按上面提示修复"
    print("\n" + tail)
    return 0 if ok else 1


# ---------------------------------------------------------------- login
def cmd_login(args) -> int:
    from playwright.sync_api import sync_playwright

    if profile_in_use(PROFILE_DIR):
        say("[XX] 上一次打开的浏览器还开着，profile 被占用。先关掉它再登录。")
        return 1

    log = RunLog(ROOT, "login")
    with sync_playwright() as pw:
        try:
            ctx, channel = open_context(pw, PROFILE_DIR, headless=False, slow_mo=40)
        except BrowserUnavailable as exc:
            say(exc)
            log.close()
            return 1
        log.ok(f"浏览器已启动（{channel}）")
        log.info(f"profile: {PROFILE_DIR}")

        # 三个平台各开一个标签页，否则后一个会覆盖前一个，没法同时登录
        first = first_page(ctx)
        pages = [first]
        for _ in range(len(ALL_KEYS) - 1):
            pages.append(ctx.new_page())

        for page, key in zip(pages, ALL_KEYS):
            plat = REGISTRY[key]
            log.step(f"打开 {plat.name}")
            try:
                page.goto(plat.url, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(2000)
            except Exception as exc:
                log.warn(f"{plat.name} 打开失败：{type(exc).__name__}")

        say("""
────────────────────────────────────────────────
 浏览器里已经开好三个标签页，就在这个窗口里扫码登录：

   [1] B站    https://member.bilibili.com
   [2] 快手   https://cp.kuaishou.com
   [3] 抖音   https://creator.douyin.com

 用手机对应的 App 扫码即可，顺序随意。
 三个都登好后本窗口会自动结束，不用按回车。
────────────────────────────────────────────────
""")

        # 三个平台并行轮询，谁先登好先记谁，避免串行等待
        remaining = {key: page for key, page in zip(ALL_KEYS, pages)}
        hits: dict[str, int] = {k: 0 for k in ALL_KEYS}
        deadline = time.time() + args.timeout
        last_notice = time.time()

        while remaining and time.time() < deadline:
            for key, page in list(remaining.items()):
                plat = REGISTRY[key]
                try:
                    host = urlparse(page.url or "").netloc.lower()
                except Exception:
                    host = ""
                expected = urlparse(plat.url).netloc.lower()
                # 会话 cookie 是唯一可靠信号：快手游客态页面也停在原 URL
                if not login_cookie_ok(ctx, key) or host != expected:
                    hits[key] = 0
                    continue
                # 连续两次确认，避开页面加载过程中的误判
                hits[key] += 1
                if hits[key] >= 2:
                    say(f"  ✓ {plat.name} 已登录")
                    log.ok(f"{plat.name} 登录成功")
                    del remaining[key]
            time.sleep(2)

            # 用户直接关掉浏览器时，不用继续空等十分钟
            try:
                if not [p for p in ctx.pages if not p.is_closed()]:
                    say("浏览器已关闭，停止等待登录")
                    break
            except Exception:
                break

            if remaining and time.time() - last_notice > 30:
                left = int(deadline - time.time())
                say(f"  等待中：{'、'.join(REGISTRY[k].name for k in remaining)}"
                    f"  （剩余 {left // 60} 分 {left % 60} 秒）")
                last_notice = time.time()

        if remaining:
            for key in remaining:
                log.warn(f"{REGISTRY[key].name} 超时未检测到登录")
                log.info(f"  现有 cookie：{', '.join(cookie_names(ctx, key)) or '(空)'}")
                say(f"  ✗ {REGISTRY[key].name} 仍未登录")
            say("\n可以重新运行本命令，已登录的平台不需要再扫。")

        try:
            ctx.close()
        except Exception:
            pass

    ok_count = len(ALL_KEYS) - len(remaining)
    log.ok(f"登录态已保存（{ok_count}/{len(ALL_KEYS)}）")
    log.close()
    return 0 if not remaining else 1


# ---------------------------------------------------------------- 预检
def _profile_pids(profile: Path) -> list[str] | None:
    """返回用这个 profile 启动的 Chrome/Edge 进程号；查询失败返回 None。

    持久化上下文没有 ctx.browser 句柄；浏览器被直接关掉时，
    Playwright 有时既不给 close 事件也不断开连接，只能从系统层面看一眼。
    Chrome 和 Edge 都要查：登录时用哪个浏览器，后面就可能用哪个。
    """
    try:
        path = str(profile).replace("'", "''").lower()
        ps = ("Get-CimInstance Win32_Process -Filter \"name='chrome.exe' OR name='msedge.exe'\" "
              f"| Where-Object {{ $_.CommandLine -and $_.CommandLine.ToLower().Contains('{path}') }} "
              "| Select-Object -ExpandProperty ProcessId")
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=25,
            creationflags=subprocess.CREATE_NO_WINDOW)
        if out.returncode != 0:
            return None
        return [x.strip() for x in out.stdout.splitlines() if x.strip()]
    except Exception:
        return None


def browser_alive(profile: Path) -> bool:
    pids = _profile_pids(profile)
    return True if pids is None else bool(pids)   # 查不到就当还活着，宁可多等也别误关


def profile_in_use(profile: Path) -> bool:
    """开跑前检查：上一次的浏览器还开着吗？

    Chromium 的 profile 是独占的，第二个实例会卡在启动阶段（不报错也不退出），
    所以必须提前拦住，给一句人能看懂的话。
    """
    return bool(_profile_pids(profile))


def preflight(job: Job, log: RunLog) -> bool:
    """开浏览器之前能发现的问题，别让它白跑六分钟。"""
    if not job.title.strip():
        log.err("标题是空的")
        return False

    if job.immediate:
        log.info("发布方式: 立即发布（不设定时）")
    else:
        try:
            at = job.publish_at()
        except ValueError:
            log.err(f"定时格式不对：{job.date} {job.time}（要 YYYY-MM-DD 和 HH:MM）")
            return False

        hours = (at - datetime.datetime.now()).total_seconds() / 3600
        log.info("发布方式: 定时发布")
        log.info(f"距今  : {hours:.1f} 小时")
        if hours < 2:
            log.warn("定时距现在不足 2 小时，抖音会拒绝（要求 2 小时后、14 天内）")
        if hours > 14 * 24:
            log.warn("定时超过 14 天，抖音/快手会拒绝")
        if hours < 0:
            log.err("定时时间已经过去了")
            return False

    title_len = len(job.title.strip())
    if title_len > 80:
        log.warn(f"标题 {title_len} 字，B站上限 80 字，可能被截断")
    if title_len > 30:
        log.warn(f"标题 {title_len} 字，抖音标题上限约 30 字，可能被截断")

    if job.bili_tags:
        tags = [t.strip() for t in job.bili_tags.replace("，", ",").split(",") if t.strip()]
        if len(tags) > 10:
            log.warn(f"B站标签 {len(tags)} 个，上限 10 个，超出部分可能被丢弃")
        long_tags = [t for t in tags if len(t) > 20]
        if long_tags:
            log.warn("B站标签超过 20 字：" + "、".join(long_tags[:3]))

    video = Path(job.video)
    ext = video.suffix.lower()
    if ext not in steps.VIDEO_EXTS:
        log.warn(f"视频格式 {ext or '(无扩展名)'}，平台可能不支持")
    try:
        size_mb = video.stat().st_size / 1024 / 1024
    except OSError:
        log.err(f"读不到视频文件：{job.video}")
        return False
    if size_mb > 4096:
        log.warn(f"视频 {size_mb:.0f}MB，超过 4GB 平台可能拒收")

    if job.cover:
        cover = Path(job.cover)
        cext = cover.suffix.lower()
        if cext not in (".jpg", ".jpeg", ".png", ".webp"):
            log.warn(f"封面格式 {cext or '(无扩展名)'}，平台一般只认 jpg/png")
        try:
            cover_mb = cover.stat().st_size / 1024 / 1024
            if cover_mb > 10:
                log.warn(f"封面 {cover_mb:.1f}MB，过大可能上传失败")
        except OSError:
            log.warn(f"读不到封面文件：{job.cover}")
    return True


# ---------------------------------------------------------------- publish
def cmd_publish(args) -> int:
    from playwright.sync_api import sync_playwright

    cfg = load_config()
    platforms = list(dict.fromkeys(
        p.strip() for p in args.platforms.split(",") if p.strip()))
    if not platforms:
        say("[XX] 至少选一个平台（bili / kuaishou / douyin）")
        return 2
    bad = [p for p in platforms if p not in REGISTRY]
    if bad:
        say(f"[XX] 未知平台：{', '.join(bad)}（可选 bili / kuaishou / douyin）")
        return 2

    video = Path(args.video)
    if not video.is_file():
        say(f"[XX] 视频不存在或不是文件：{video}")
        return 2
    if args.cover and not Path(args.cover).is_file():
        say(f"[XX] 封面不存在或不是文件：{args.cover}")
        return 2

    job = Job(
        video=str(video),
        title=args.title.strip(),
        cover=args.cover or "",
        desc=args.desc.strip() or "",
        bili_tags=args.bili_tags.strip() or cfg_default(cfg, "bili_tags"),
        bili_topic=args.bili_topic.strip() or cfg_default(cfg, "bili_topic"),
        kuaishou_topics=args.ks_topics.strip() or cfg_default(cfg, "kuaishou_topics"),
        douyin_topics=args.dy_topics.strip() or cfg_default(cfg, "douyin_topics"),
        date=(args.date or "").strip(),
        time=(args.time or "06:00").strip() or "06:00",
        immediate=bool(getattr(args, "now", False)),
    )

    log = RunLog(ROOT, "publish")
    log.stage("发布任务")
    log.info(f"视频  : {job.video}  ({steps.size_mb(job.video):.1f}MB)")
    log.info(f"标题  : {job.title}")
    log.info(f"封面  : {job.cover or '（未指定，用平台推荐封面）'}")
    if job.immediate:
        log.info("定时  : 立即发布")
    else:
        log.info(f"定时  : {job.date} {job.time}")
    log.info(f"平台  : {'、'.join(REGISTRY[k].name for k in platforms)}")
    keep = not args.auto
    mode_text = "保持页面，等你手动发布" if keep else "填完自动提交"
    log.info(f"模式  : {mode_text}")
    if args.headless and keep:
        log.warn("无头模式下看不到页面，保持模式无法手动发布；建议改用 --auto 或去掉 --headless")
    if not preflight(job, log):
        log.close()
        return 2

    if profile_in_use(PROFILE_DIR):
        log.err("上一次打开的浏览器还开着，profile 被占用，这次启动会卡住。")
        log.info("请先关掉那个发布器窗口（或任务管理器里的 Chrome/Edge），再重新运行。")
        log.close()
        return 1

    results: list[Result] = []
    with sync_playwright() as pw:
        try:
            ctx, channel = open_context(pw, PROFILE_DIR, headless=args.headless)
            log.ok(f"浏览器就绪（{channel}）")
        except BrowserUnavailable as exc:
            say(exc)
            log.close()
            return 1

        # 每个平台独立标签页：填完的表单都留着，方便逐个检查
        first = first_page(ctx)
        pages = {key: (first if i == 0 else ctx.new_page())
                 for i, key in enumerate(platforms)}

        def run_fill(key: str):
            plat = REGISTRY[key]
            try:
                return plat.fill(pages[key], job, log)
            except Exception as exc:
                log.err(f"{plat.name} 异常：{type(exc).__name__}: {exc}")
                log.shot(pages[key], f"{key}-crashed")
                return Result(plat.name, False, f"{type(exc).__name__}: {exc}")
            finally:
                if args.dump:
                    steps.dump(pages[key], log, f"{key}-dump")

        if keep:
            # 填完就停，页面无限期保持，由用户自己在网页上点发布
            for key in platforms:
                r = run_fill(key)
                if r is not None:
                    results.append(r)
                log.info("")

            failed = [r for r in results if not r.ok]
            failed_names = {r.platform for r in failed}
            filled = [REGISTRY[k].name for k in platforms
                      if REGISTRY[k].name not in failed_names]
            if failed:
                say("\n以下平台没填成功，页面上可能不完整：")
                for r in failed:
                    say(f"  ✗ {r.platform}：{r.detail}")

            say(f"""
────────────────────────────────────────────────
 已填好：{'、'.join(filled) or '（无）'}
 页面保持打开，不会自动提交，也不会计时关闭。

 请直接在网页上检查，然后自己点「发布 / 立即投稿」。
 关掉浏览器后，本程序自动退出。
────────────────────────────────────────────────
""")
            last_probe = time.time()
            while True:
                try:
                    if not [p for p in ctx.pages if not p.is_closed()]:
                        break
                except Exception:
                    break
                now = time.time()
                if now - last_probe > 30:
                    last_probe = now
                    if not browser_alive(PROFILE_DIR):
                        log.warn("浏览器已经关掉了")
                        break
                time.sleep(3)

            log.warn("浏览器已关闭；程序未自动提交（如果你已在网页上发布，以平台为准）")
            log.stage("汇总")
            for r in results:
                mark = "OK " if r.ok else "FAIL"
                log.line(f"[{mark}]", f"{r.platform:<4} {r.detail}")
            log.info(f"日志与截图：{log.dir}")
            log.close()
            return 0 if not failed else 1

        # 自动提交
        for key in platforms:
            try:
                results.append(REGISTRY[key].publish(pages[key], job, log))
            except Exception as exc:
                log.err(f"{REGISTRY[key].name} 异常：{type(exc).__name__}: {exc}")
                log.shot(pages[key], f"{key}-crashed")
                results.append(Result(REGISTRY[key].name, False,
                                      f"{type(exc).__name__}: {exc}"))
            finally:
                if args.dump:
                    steps.dump(pages[key], log, f"{key}-dump")
                log.info("")

        try:
            ctx.close()
        except Exception:
            pass

    # 汇总
    log.stage("结果汇总")
    for r in results:
        mark = "OK " if r.ok else "FAIL"
        log.line(f"[{mark}]", f"{r.platform:<4} {r.detail}")
    failed = [r for r in results if not r.ok]
    log.info(f"日志与截图：{log.dir}")
    log.close()
    return 0 if not failed else 1


# ---------------------------------------------------------------- 入口
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="多平台视频发布器（Playwright 直连，不依赖浏览器扩展）",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="检查环境").set_defaults(func=cmd_doctor)

    login = sub.add_parser("login", help="首次登录，保存三个平台的登录态")
    login.add_argument("--timeout", type=int, default=600, help="等待扫码的秒数，默认 600")
    login.set_defaults(func=cmd_login)

    pub = sub.add_parser("publish", help="发布一条视频")
    pub.add_argument("--video", required=True, help="视频文件路径")
    pub.add_argument("--title", required=True, help="标题")
    pub.add_argument("--cover", default="", help="封面图片路径（不填则用平台推荐封面）")
    pub.add_argument("--desc", default="",
                     help="文案（默认同标题；B站简介/快手描述/抖音作品描述）")
    pub.add_argument("--date", default="", help="发布日期 YYYY-MM-DD（默认明天）")
    pub.add_argument("--time", default="06:00", help="发布时间 HH:MM")
    pub.add_argument("--now", action="store_true",
                     help="立即发布：不设定时，忽略 --date/--time")
    pub.add_argument("--platforms", default="bili,kuaishou,douyin", help="逗号分隔")
    pub.add_argument("--bili-tags", default="", help="B站标签，逗号分隔")
    pub.add_argument("--bili-topic", default="", help="B站参与话题，逗号分隔")
    pub.add_argument("--ks-topics", default="", help="快手话题，# 开头空格分隔")
    pub.add_argument("--dy-topics", default="", help="抖音话题，# 开头空格分隔")
    pub.add_argument("--auto", action="store_true",
                     help="填完直接自动提交（默认不提交，填完保持页面等你手动发布）")
    pub.add_argument("--hold", action="store_true",
                     help="填完就停，页面一直开着（默认行为，写不写都一样）")
    pub.add_argument("--headless", action="store_true", help="无头运行（不建议）")
    pub.add_argument("--dump", action="store_true",
                     help="填完后把页面关键元素导出成 JSON，用于排查选择器")
    pub.set_defaults(func=cmd_publish)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    try:
        code = args.func(args)
    except BrokenPipeError:
        # 图形界面关掉后 stdout 管道会断；任务本身已经跑完，按成功退出
        code = 0
    raise SystemExit(code)
