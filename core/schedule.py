"""定时发布的时间解析与平台窗口规则。

三个平台对定时时间的限制不一样，而且会调整：

    B站  ：5 分钟后 ~ 15 天内
    快手 ：1 小时后 ~ 14 天内
    抖音 ：2 小时后 ~ 14 天内

三者同时勾选时，实际可用窗口是 2 小时 ~ 14 天。这里只负责提示，
真正的兜底是提交时识别平台的报错（见 platforms/bilibili.py）。
"""
from __future__ import annotations

import datetime as dt
import re

# key -> (最短小时数, 最长天数, 平台名)
WINDOWS: dict[str, tuple[float, int, str]] = {
    "bili": (5 / 60, 15, "B站"),
    "kuaishou": (1, 14, "快手"),
    "douyin": (2, 14, "抖音"),
}

# 6 / 6:00 / 6：00 / 6点 / 6点30 / 06:00
_TIME_RE = re.compile(r"^(\d{1,2})\s*(?:[:：点时]\s*(\d{1,2})?\s*分?)?$")


def normalize_time(value: str, default: str = "06:00") -> str:
    """把 6、6:0、6：30、6点 统一成 HH:MM。"""
    text = (value or "").strip()
    if not text:
        return default
    match = _TIME_RE.match(text)
    if not match:
        raise ValueError(f"时间格式不对：{value}（要 06:00 这种，也可以直接写 6）")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"时间超出范围：{value}（小时 0-23，分钟 0-59）")
    return f"{hour:02d}:{minute:02d}"


def normalize_date(value: str) -> str:
    """接受 2026-11-05 / 2026/11/5 / 2026.11.5 / 2026年11月5日。"""
    text = (value or "").strip()
    for old, new in (("/", "-"), (".", "-"), ("年", "-"), ("月", "-"), ("日", "")):
        text = text.replace(old, new)
    text = text.strip("-")
    if not text:
        return (dt.date.today() + dt.timedelta(days=1)).isoformat()
    try:
        return dt.datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"日期格式不对：{value}（要 2026-11-05 这种）") from exc


def parse(date_text: str, time_text: str) -> dt.datetime:
    """把日期 + 时间解析成 datetime，出错时给一句人话。"""
    day = dt.date.fromisoformat(normalize_date(date_text))
    hour, minute = (int(x) for x in normalize_time(time_text).split(":"))
    return dt.datetime(day.year, day.month, day.day, hour, minute)


def _num(value: float) -> str:
    """1.0 -> 1，1.5 -> 1.5。"""
    return f"{value:.1f}".rstrip("0").rstrip(".")


def human_hours(hours: float) -> str:
    """1.5 -> 1.5 小时；0.4 -> 24 分钟；72 -> 3 天。"""
    if hours < 0:
        return f"{_num(-hours * 60)} 分钟前"
    if hours < 1:
        return f"{_num(hours * 60)} 分钟"
    if hours < 48:
        return f"{_num(hours)} 小时"
    return f"{_num(hours / 24)} 天"


def check_window(at: dt.datetime, platforms: list[str],
                 now: dt.datetime | None = None) -> tuple[list[str], list[str]]:
    """检查定时时间是否落在平台窗口内。

    返回 (errors, warnings)：
    - errors：一定发不出去（时间已经过去）
    - warnings：平台可能拒收，交给调用方决定是否继续
    """
    now = now or dt.datetime.now()
    hours = (at - now).total_seconds() / 3600
    errors: list[str] = []
    warnings: list[str] = []

    if hours < 0:
        errors.append(f"定时时间已经过去了（{human_hours(hours)}）")
        return errors, warnings

    for key in dict.fromkeys(platforms):
        spec = WINDOWS.get(key)
        if not spec:
            continue
        min_hours, max_days, name = spec
        if hours < min_hours:
            warnings.append(
                f"{name}要求至少 {human_hours(min_hours)}后，"
                f"现在只差 {human_hours(hours)}")
        if hours > max_days * 24:
            warnings.append(
                f"{name}最晚只能约 {max_days} 天，现在是 {human_hours(hours)}后")

    return errors, warnings


def describe(platforms: list[str]) -> str:
    """一句话说明所选平台的时间窗口，用于界面提示和日志。"""
    keys = [k for k in dict.fromkeys(platforms) if k in WINDOWS]
    if not keys:
        return ""
    parts = [f"{WINDOWS[k][2]} {human_hours(WINDOWS[k][0])}后" for k in keys]
    max_days = min(WINDOWS[k][1] for k in keys)
    return "；".join(parts) + f"，最晚 {max_days} 天"


def bump(at: dt.datetime, hours: float) -> dt.datetime:
    """往后挪几个小时，用于平台拒绝定时时间后的重试。"""
    return at + dt.timedelta(hours=hours)
