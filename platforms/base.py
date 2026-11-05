"""发布任务的数据结构与平台基类。"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from core import steps


@dataclass
class Job:
    video: str
    title: str
    cover: str = ""
    desc: str = ""
    # 各平台话题独立配置
    bili_tags: str = ""
    bili_topic: str = ""
    kuaishou_topics: str = ""
    douyin_topics: str = ""
    # 分平台文案覆盖；留空则回退到上面的通用标题/文案
    bili_title: str = ""
    bili_desc: str = ""
    ks_title: str = ""
    ks_desc: str = ""
    dy_title: str = ""
    dy_desc: str = ""
    # 定时发布
    date: str = ""          # YYYY-MM-DD，空则用明天
    time: str = "06:00"     # HH:MM
    immediate: bool = False  # True = 立即发布，忽略 date/time

    _SHORT = {"bili": "bili", "kuaishou": "ks", "douyin": "dy"}

    def __post_init__(self) -> None:
        if not self.date:
            self.date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        if not self.desc:
            self.desc = self.title

    def title_for(self, key: str) -> str:
        """某个平台实际使用的标题；没单独设置就用通用标题。"""
        short = self._SHORT.get(key, key)
        return getattr(self, f"{short}_title", "") or self.title

    def desc_for(self, key: str) -> str:
        """某个平台实际使用的文案；没单独设置就用通用文案。

        如果只给某个平台单独写了标题、通用文案又没单独填（等于通用标题），
        简介/描述就跟着这个平台的标题走，避免把通用标题重复拼进描述。
        """
        short = self._SHORT.get(key, key)
        override = getattr(self, f"{short}_desc", "")
        if override:
            return override
        platform_title = getattr(self, f"{short}_title", "")
        if platform_title and self.desc == self.title:
            return platform_title
        return self.desc

    def publish_at(self) -> datetime.datetime:
        return datetime.datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")


@dataclass
class Result:
    platform: str
    ok: bool
    detail: str = ""


class Platform:
    key = ""
    name = ""
    url = ""
    success_patterns: tuple[str, ...] = ("发布成功", "投稿成功", "提交成功")

    def guard_login(self, page, log) -> "Result | None":
        """停在登录页时直接返回失败结果，避免后面报一堆误导性的选择器错误。"""
        if steps.detect_login_wall(page):
            log.err(f"{self.name} 登录态失效，停在登录页")
            steps.shot(page, log, f"{self.key}-login-wall")
            return Result(self.name, False, "登录态失效，请先运行 python cli.py login")
        return None

    def fill(self, page, job: Job, log) -> "Result | None":
        """填完所有字段，停在提交前。成功返回 None，失败返回 Result。"""
        raise NotImplementedError

    def submit(self, page, job: Job, log) -> Result:
        """在已填好的页面上点提交。"""
        raise NotImplementedError

    def publish(self, page, job: Job, log) -> Result:
        """一步到位：填表 → 提交。"""
        blocked = self.fill(page, job, log)
        if blocked is not None:
            return blocked
        return self.submit(page, job, log)
