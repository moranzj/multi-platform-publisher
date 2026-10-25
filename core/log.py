"""运行日志：控制台 + 文件双写，每步可截图/存 HTML 便于排错。"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path


def _utf8_stdout() -> None:
    """Windows 控制台默认 GBK，中文会炸。

    做法：真实控制台先把代码页切到 65001，再让 Python 按 UTF-8 输出；
    被管道/GUI 接管时（isatty 为 False）直接输出 UTF-8，由调用方解码。
    """
    try:
        import ctypes

        if sys.stdout is not None and sys.stdout.isatty():
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_utf8_stdout()


class RunLog:
    def __init__(self, root: Path, name: str):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = root / "logs" / f"{stamp}-{name}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.dir / "run.log", "a", encoding="utf-8")
        # 同一页面连续截图失败后不再重试，避免卡在渲染异常的页面上反复等超时
        self._shot_failures: dict[int, int] = {}

    # ---------- 基础输出 ----------
    def _write(self, tag: str, msg: str) -> None:
        line = f"[{datetime.datetime.now():%H:%M:%S}] {tag} {msg}"
        try:
            print(line, flush=True)
        except Exception:
            # 图形界面被关掉后 stdout 管道会断开；日志仍要写文件，任务不能跟着崩
            pass
        try:
            self._fh.write(line + "\n")
            self._fh.flush()
        except Exception:
            # 磁盘满/日志文件被占用时，也不能让发布流程崩掉
            pass

    def info(self, msg: str) -> None:
        self._write("    ", msg)

    def line(self, tag: str, msg: str) -> None:
        """自定义标记的一行输出（用于结果汇总）。"""
        self._write(tag, msg)

    def stage(self, msg: str) -> None:
        self._write("====", msg)

    def step(self, msg: str) -> None:
        self._write("[..]", msg)

    def ok(self, msg: str) -> None:
        self._write("[OK]", msg)

    def warn(self, msg: str) -> None:
        self._write("[!!]", msg)

    def err(self, msg: str) -> None:
        self._write("[XX]", msg)

    # ---------- 排错物料 ----------
    def shot(self, page, tag: str) -> None:
        """截图尽量快，但不能卡住主流程。

        试过用 CDP 的 Page.captureScreenshot 绕过「等字体加载」，速度确实快，
        但在 B 站上传完成后的页面上会永久不返回（渲染进程不给帧），
        所以还是用 Playwright 自带截图，超时 10 秒；
        同一页面连续失败 3 次后跳过后续截图，避免把整轮任务拖慢。
        """
        key = id(page)
        if self._shot_failures.get(key, 0) >= 3:
            return

        path = self.dir / f"{tag}.png"
        try:
            page.screenshot(path=str(path), timeout=10000, animations="disabled")
            self._shot_failures[key] = 0
        except Exception as exc:  # 页面已关/崩溃时不影响主流程
            fails = self._shot_failures.get(key, 0) + 1
            self._shot_failures[key] = fails
            if fails >= 3:
                self.warn(f"截图连续失败 {fails} 次，本页后续截图跳过（{tag}: {type(exc).__name__}）")
            else:
                self.warn(f"截图失败 {tag}: {type(exc).__name__}")

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass
