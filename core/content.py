"""发布前的文案组装、长度检查和封面/视频体检。

三个平台对文案的用法不一样：

- B站：标题、简介、标签、参与话题是四个独立字段
- 快手：标题 + 话题 + 文案会拼成同一个「作品描述」
- 抖音：标题独立，话题和文案进「作品描述」

这里把最终会填进页面的内容先拼出来，让用户在点「开始填表」之前就能看到
每个平台实际会收到什么，并把超长、标签过多、封面比例不合适之类的问题
提前暴露出来。检查结果只做提示，不强行修改用户文案。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from core import steps

if TYPE_CHECKING:  # 避免 core -> platforms 的运行时循环依赖
    from platforms.base import Job

# 平台建议上限（超过只警告，不截断）
LIMITS: dict[str, dict[str, object]] = {
    "bili": {"name": "B站", "title": 80, "desc": 2000, "tags": 10},
    "kuaishou": {"name": "快手", "title": 0, "desc": 500, "tags": 0},
    "douyin": {"name": "抖音", "title": 30, "desc": 1000, "tags": 5},
}

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".flv", ".avi", ".wmv", ".webm", ".m4v"}


def bili_tags(text: str) -> list[str]:
    """B站标签按逗号拆；和 platforms/bilibili.py 的填写逻辑保持一致。"""
    return [t.strip().lstrip("#") for t in re.split(r"[,，]", text or "") if t.strip()]


def compose(key: str, job: "Job") -> dict[str, str]:
    """返回某个平台最终会填进页面的文案。"""
    spec = LIMITS.get(key, {"name": key})
    title = job.title_for(key)
    desc = job.desc_for(key)

    if key == "bili":
        tags = bili_tags(job.bili_tags)
        topics = [t.lstrip("#") for t in steps.normalize_topics(job.bili_topic)]
        extra: list[str] = []
        if tags:
            extra.append("标签：" + "、".join(tags))
        if topics:
            extra.append("参与话题：" + "、".join(topics))
        return {
            "name": str(spec["name"]),
            "title": title,
            "body": desc,
            "extra": "\n".join(extra),
        }

    if key == "kuaishou":
        # 快手只有一个大输入框：标题 + 话题 + 文案
        topics = steps.normalize_topics(job.kuaishou_topics)
        parts = [title, *topics]
        if desc and desc != title:
            parts.append(desc)
    else:
        # 抖音标题是独立字段，作品描述里只有文案和话题，且文案在前
        topics = steps.normalize_topics(job.douyin_topics)
        parts = []
        if desc and desc != title:
            parts.append(desc)
        parts.extend(topics)
    return {
        "name": str(spec["name"]),
        "title": title,
        "body": " ".join(p.strip() for p in parts if p.strip()),
        # 抖音挂了游戏手柄时把游戏名亮出来，用户好核对
        "extra": (f"游戏手柄：{(job.dy_game or '').strip()}（快手网页端无此入口，不挂）"
                  if key == "douyin" and (job.dy_game or "").strip() else ""),
    }


def preview_text(key: str, job: "Job") -> str:
    """给 GUI/CLI 看的多行预览。"""
    data = compose(key, job)
    lines = [f"【{data['name']}】", f"标题（{len(data['title'])} 字）：{data['title'] or '（空）'}"]
    if key == "bili":
        lines += ["", f"简介（{len(data['body'])} 字）：{data['body'] or '（空）'}"]
    else:
        lines += ["", f"作品描述（{len(data['body'])} 字）：{data['body'] or '（空）'}"]
    if data["extra"]:
        lines += ["", data["extra"]]
    return "\n".join(lines)


def check_cover(path: str, platforms: list[str]) -> tuple[list[str], list[str]]:
    """封面尺寸/比例检查。没有封面、没装 Pillow 时安静跳过。"""
    if not path:
        return [], []
    file = Path(path)
    if not file.is_file():
        return [f"封面文件不存在：{path}"], []
    try:
        from PIL import Image
    except Exception:
        return [], ["Pillow 未安装，跳过封面尺寸检查"]

    try:
        with Image.open(file) as im:
            width, height = im.size
    except Exception as exc:
        return [f"封面读不出来：{type(exc).__name__}"], []

    warnings: list[str] = []
    if width < 400 or height < 400:
        warnings.append(f"封面 {width}x{height} 偏小，快手建议至少 400x400")
    ratio = width / height if height else 0
    targets = (16 / 9, 9 / 16, 1.0)
    if ratio and min(abs(ratio - t) for t in targets) > 0.08:
        warnings.append(
            f"封面 {width}x{height} 不是常见比例（16:9 / 9:16 / 1:1），"
            "平台会自动裁剪，注意主体别被切掉")
    return [], warnings


def check_video(path: str) -> tuple[list[str], list[str]]:
    if not path:
        return [], []
    file = Path(path)
    if not file.is_file():
        return [f"视频不存在：{path}"], []
    warnings: list[str] = []
    try:
        size_mb = file.stat().st_size / 1024 / 1024
    except Exception:
        size_mb = 0
    if size_mb > 4096:
        warnings.append(f"视频 {size_mb:.0f}MB，超过 4GB，部分平台可能拒收")
    if file.suffix.lower() not in VIDEO_EXTS:
        warnings.append(f"视频格式 {file.suffix or '（无扩展名）'} 不常见，平台可能不支持")
    return [], warnings


def check(job: "Job", platforms: list[str]) -> tuple[list[str], list[str]]:
    """检查所有选中平台，返回 (errors, warnings)。

    errors 只包含一定发不出去的问题；长度/比例这类只给 warnings，
    由调用方决定是否继续。
    """
    errors: list[str] = []
    warnings: list[str] = []

    for key in dict.fromkeys(platforms):
        spec = LIMITS.get(key)
        if not spec:
            continue
        name = str(spec["name"])
        title = job.title_for(key).strip()
        desc = job.desc_for(key)
        if not title:
            errors.append(f"{name}标题是空的")
            continue

        title_limit = int(spec["title"])
        if title_limit and len(title) > title_limit:
            warnings.append(
                f"{name}标题 {len(title)} 字，超过建议上限 {title_limit} 字")

        if key == "bili":
            if len(desc) > int(spec["desc"]):
                warnings.append(
                    f"B站简介 {len(desc)} 字，超过上限 {spec['desc']} 字")
            tags = bili_tags(job.bili_tags)
            if len(tags) > int(spec["tags"]):
                warnings.append(
                    f"B站标签 {len(tags)} 个，超过上限 {spec['tags']} 个")
            long_tags = [t for t in tags if len(t) > 20]
            if long_tags:
                warnings.append("B站标签超过 20 字：" + "、".join(long_tags[:3]))
        elif key == "kuaishou":
            combined = compose(key, job)["body"]
            if len(combined) > int(spec["desc"]):
                warnings.append(
                    f"快手作品描述共 {len(combined)} 字，超过 {spec['desc']} 字上限")
        elif key == "douyin":
            combined = compose(key, job)["body"]
            if len(combined) > int(spec["desc"]):
                warnings.append(
                    f"抖音作品描述共 {len(combined)} 字，超过 {spec['desc']} 字上限")
            topics = steps.normalize_topics(job.douyin_topics)
            if len(topics) > int(spec["tags"]):
                warnings.append(
                    f"抖音话题 {len(topics)} 个，超过建议上限 {spec['tags']} 个")

    video_errors, video_warnings = check_video(job.video)
    cover_errors, cover_warnings = check_cover(job.cover, platforms)
    errors += video_errors + cover_errors
    warnings += video_warnings + cover_warnings
    return errors, warnings
