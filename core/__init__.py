"""多平台视频发布器核心包。"""
import os
import sys
from pathlib import Path

__version__ = "1.3.0"


def _relocate_temp_for_frozen() -> None:
    """打包成 exe 后：把 TEMP/TMP 挪到程序目录里。

    有安全软件/沙箱按「进程来源目录」限制写权限：放在受监视目录里的
    node.exe 等运行时往系统 TEMP 写文件会报 EPERM（python 本体反而不受限，
    所以不能用 python 自己探测试水），往自己目录里写则不受影响。Playwright
    的 node 驱动必须在 TEMP 里建 playwright-artifacts-*，不改就起不了浏览器。
    程序目录本身不可写（如放在 Program Files）时维持系统 TEMP 不动。
    """
    if not getattr(sys, "frozen", False):
        return
    try:
        tmp = Path(sys.executable).resolve().parent / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        probe = tmp / ".write-probe"
        probe.write_bytes(b"")
        probe.unlink()
    except Exception:
        return
    os.environ["TEMP"] = str(tmp)
    os.environ["TMP"] = str(tmp)


_relocate_temp_for_frozen()
