"""浏览器生命周期：用独立 profile 持久化登录态，优先系统 Chrome，回退 Edge。"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright

# 隐藏自动化指纹，降低风控概率
LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--start-maximized",
]

# navigator.webdriver 是最常见的检测点，抹掉
INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
"""


class BrowserUnavailable(RuntimeError):
    pass


def open_context(
    pw: Playwright,
    profile_dir: Path,
    headless: bool = False,
    slow_mo: int = 60,
) -> tuple[BrowserContext, str]:
    """打开持久化上下文。返回 (context, 实际使用的浏览器通道名)。"""
    profile_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    for channel in ("chrome", "msedge"):
        try:
            ctx = pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                channel=channel,
                headless=headless,
                slow_mo=slow_mo,
                viewport={"width": 1440, "height": 900},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                args=LAUNCH_ARGS,
                ignore_default_args=["--enable-automation"],
                accept_downloads=True,
            )
            ctx.add_init_script(INIT_SCRIPT)
            # 上传大文件时默认 30s 不够，页面操作超时放宽
            ctx.set_default_timeout(20_000)
            return ctx, channel
        except Exception as exc:
            errors.append(f"{channel}: {exc}")

    raise BrowserUnavailable(
        "无法启动浏览器（Chrome / Edge 都不可用）。\n"
        "  1. 确认本机装了 Chrome 或 Edge\n"
        "  2. 如果 profile 目录被占用，先关掉所有由本工具打开的窗口\n"
        "  3. 报错详情：\n    " + "\n    ".join(errors)
    )


def first_page(ctx: BrowserContext):
    """持久化上下文启动时自带一个 about:blank 标签页，直接复用，避免多开。"""
    pages = [p for p in ctx.pages if not p.is_closed()]
    return pages[0] if pages else ctx.new_page()
