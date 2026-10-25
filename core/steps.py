"""页面操作的通用动作层。

设计原则：
- 每个动作失败都抛异常或返回 False，由平台层决定"必做"还是"尽力而为"
- 所有定位优先用可见文本 / placeholder，比 class 名抗改版
- 关键节点留截图，出问题能直接看出卡在哪一屏
"""
from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path

from .log import RunLog


def pause(a: float = 0.6, b: float = 1.4) -> None:
    time.sleep(random.uniform(a, b))


def size_mb(path: str | Path) -> float:
    """文件体积（MB）。读不到时给一个保守值，别让日志流程因此中断。"""
    try:
        return Path(path).stat().st_size / 1024 / 1024
    except Exception:
        return 50.0


def detect_login_wall(page) -> bool:
    """判断当前是否停在登录页 / 登录弹窗。

    比"找不到上传入口"更早、更准确地暴露登录态失效。
    """
    url = (page.url or "").lower()
    if any(k in url for k in ("login", "passport", "signin", "sso")):
        return True
    try:
        txt = page.locator("body").inner_text(timeout=3000)
    except Exception:
        return False
    return any(h in txt for h in ("扫码登录", "密码登录", "短信登录", "立即登录", "登录后即可"))


def shot(page, log: RunLog, tag: str) -> None:
    """截图统一走日志对象，保证落在本次运行的日志目录里。"""
    log.shot(page, tag)


# ---------------------------------------------------------------- 点击
def click_text(page, text: str, timeout: int = 8000, exact: bool = True,
               log: RunLog | None = None) -> bool:
    """按可见文本点击。同名元素取最后一个**可见的**（弹窗通常在 DOM 末尾）。

    注意：不能直接等最后一个——页面上常有同名但隐藏的副本，
    等它会白白等到超时（快手的「上传封面」就是这样）。
    """
    try:
        loc = page.get_by_text(text, exact=exact)
        deadline = time.time() + timeout / 1000
        target = None
        while target is None and time.time() < deadline:
            count = loc.count()
            for i in range(count - 1, -1, -1):
                try:
                    cand = loc.nth(i)
                    if cand.is_visible():
                        target = cand
                        break
                except Exception:
                    continue
            if target is None:
                time.sleep(0.3)
        if target is None:
            raise TimeoutError(text)
        target.scroll_into_view_if_needed(timeout=3000)
        target.click(timeout=timeout)
        if log:
            log.step(f"点击「{text}」")
        return True
    except Exception as exc:
        if log:
            log.warn(f"点不到「{text}」: {type(exc).__name__}")
        return False


def click_sel(page, selector: str, timeout: int = 8000,
              log: RunLog | None = None, what: str = "") -> bool:
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout)
        loc.scroll_into_view_if_needed(timeout=3000)
        loc.click(timeout=timeout)
        if log:
            log.step(f"点击 {what or selector}")
        return True
    except Exception as exc:
        if log:
            log.warn(f"点不到 {what or selector}: {type(exc).__name__}")
        return False


# ---------------------------------------------------------------- 填字
def fill_input(page, selector: str, value: str, timeout: int = 10000,
               log: RunLog | None = None) -> bool:
    """input/textarea 填值。先点一下让 React 收到 focus 事件。"""
    if not value:
        return True
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout)
        loc.click(timeout=timeout)
        loc.fill("")
        loc.fill(value)
        pause(0.3, 0.6)
        if log:
            log.step(f"填 {selector} ← {value[:24]}{'…' if len(value) > 24 else ''}")
        return True
    except Exception as exc:
        if log:
            log.warn(f"填不进去 {selector}: {type(exc).__name__}")
        return False


def normalize_topics(text: str) -> list[str]:
    """把用户写的话题串拆成一个个话题，并保证每个都带 #。

    抖音/快手都认「#话题」这种写法，没 # 就是普通文字。
    分隔符认空格、逗号、顿号、分号，中英文都算；
    连着写「#三国杀#桌游」也能拆开（很多人会这么打）。
    """
    if not text:
        return []
    out: list[str] = []
    for chunk in re.split(r"[\s,，、;；]+", text.strip()):
        for part in chunk.split("#"):
            part = part.strip()
            if not part:
                continue
            tag = "#" + part
            if tag not in out:
                out.append(tag)
    return out


def fill_editable(page, selector: str, value: str, timeout: int = 10000,
                  log: RunLog | None = None) -> bool:
    """contenteditable 编辑器（B站简介、抖音描述）。"""
    if not value:
        return True
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout)
        loc.click(timeout=timeout)
        page.keyboard.press("Control+A")
        page.keyboard.press("Delete")
        page.keyboard.insert_text(value)
        pause(0.4, 0.8)
        if log:
            log.step(f"填 {selector} ← {value[:24]}{'…' if len(value) > 24 else ''}")
        return True
    except Exception as exc:
        if log:
            log.warn(f"填不进去 {selector}: {type(exc).__name__}")
        return False


# ---------------------------------------------------------------- 传文件
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".flv", ".avi", ".wmv", ".webm", ".m4v")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def set_files_by_kind(page, kind: str, path: str | Path,
                      log: RunLog | None = None,
                      click_target: str | None = None,
                      prefer_last: bool = False) -> bool:
    """绕过拖拽，直接往 <input type=file> 塞文件。

    kind: 'video' | 'image' —— 按 accept 属性匹配，避免把封面塞进视频框。
    accept 有时只写扩展名（.jpg,.png）而不是 MIME，所以两种都要认。
    prefer_last: 页面同时有多个同类输入框时，取最后挂载的那个（弹窗里的）。
    找不到输入框时，退化为「点击触发文件选择器」。
    """
    path = str(path)
    handles = page.query_selector_all("input[type=file]")
    candidate = None
    matches = []
    exts = VIDEO_EXTS if kind == "video" else IMAGE_EXTS
    for h in handles:
        accept = (h.get_attribute("accept") or "").lower()
        if kind in accept or any(ext in accept for ext in exts):
            matches.append(h)
    if matches:
        candidate = matches[-1] if prefer_last else matches[0]
    elif handles:
        # 没有 accept 声明时，按顺序猜：视频在前，图片在后
        candidate = handles[-1] if prefer_last else handles[0 if kind == "video" else -1]

    if candidate is not None:
        try:
            candidate.set_input_files(path)
            if log:
                log.step(f"注入{'视频' if kind == 'video' else '封面'}文件（input 直塞）")
            return True
        except Exception as exc:
            if log:
                log.warn(f"input 直塞失败: {type(exc).__name__}，改用选择器")

    if click_target:
        try:
            loc = page.get_by_text(click_target, exact=False)
            target = None
            for i in range(loc.count() - 1, -1, -1):
                el = loc.nth(i)
                if el.is_visible():
                    target = el
                    break
            if target is None:
                raise TimeoutError(click_target)
            with page.expect_file_chooser(timeout=8000) as fc:
                target.click(timeout=8000)
            fc.value.set_files(path)
            if log:
                log.step(f"通过文件选择器上传 {Path(path).name}")
            return True
        except Exception as exc:
            if log:
                log.warn(f"文件选择器也失败: {type(exc).__name__}")
    return False


# ---------------------------------------------------------------- 等待
def wait_upload(page, log: RunLog, file_mb: float, timeout_min: float = 25) -> None:
    """等待视频上传完成。

    没有通用信号，所以采用「经验等待」：按文件体积估算，再留余量。
    真正的完成判断交给平台层按钮可用性检测。
    """
    est = min(timeout_min * 60, max(45, file_mb * 3.5))
    log.step(f"视频 {file_mb:.1f}MB，预计等待 {est:.0f}s")
    deadline = time.time() + est
    while time.time() < deadline:
        time.sleep(5)
        try:
            txt = page.locator("body").inner_text(timeout=3000)
        except Exception:
            continue
        for kw in ("上传失败", "上传出错", "视频处理失败"):
            if kw in txt:
                log.err(f"检测到「{kw}」")
                raise RuntimeError(f"视频上传失败：{kw}")
        for kw in ("上传成功", "上传完成", "100%"):
            if kw in txt:
                log.ok(f"检测到「{kw}」")
                return
    log.warn("未捕获到上传完成提示，按超时继续（后面靠按钮状态兜底）")


# ---------------------------------------------------------------- 收尾
def wait_success(page, patterns: tuple[str, ...], timeout: int = 25_000,
                 log: RunLog | None = None) -> bool:
    """提交后确认成功提示。"""
    deadline = time.time() + timeout / 1000
    while time.time() < deadline:
        try:
            txt = page.locator("body").inner_text(timeout=3000)
        except Exception:
            txt = ""
        for p in patterns:
            if p in txt:
                if log:
                    log.ok(f"页面确认「{p}」")
                return True
        time.sleep(1.5)
    if log:
        log.warn("未见成功提示，请到内容管理页确认")
    return False


def close_popups(page, log: RunLog | None = None) -> None:
    """关掉残留草稿/引导弹窗，避免挡住后续操作。

    不点泛化的「取消」：快手的发布页底部就有「取消」按钮，误点会把整张
    表单关掉。这里只处理语义明确的弹窗按钮，其余交给 Esc 兜底。
    """
    for text in ("不用了", "放弃", "以后再说", "我知道了"):
        try:
            loc = page.get_by_text(text, exact=True)
            for i in range(loc.count() - 1, -1, -1):
                el = loc.nth(i)
                if not el.is_visible():
                    continue
                el.click(timeout=2500)
                if log:
                    log.step(f"关闭弹窗「{text}」")
                pause(0.4, 0.8)
                break
        except Exception:
            pass
    # 只靠文字不一定能关掉所有引导层；Esc 是最后的兜底。
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def visible(page, text: str, exact: bool = True) -> bool:
    try:
        loc = page.get_by_text(text, exact=exact)
        return any(loc.nth(i).is_visible() for i in range(min(loc.count(), 10)))
    except Exception:
        return False


def click_modal_done(page, log: RunLog, timeout: int = 8000) -> bool:
    """点弹窗里的「完成」：只点可见的那个，隐藏副本会点不动。"""
    try:
        loc = page.get_by_text("完成", exact=True)
        for i in range(loc.count() - 1, -1, -1):
            el = loc.nth(i)
            if el.is_visible():
                el.click(timeout=timeout)
                log.step("点击弹窗「完成」")
                return True
    except Exception as exc:
        log.warn(f"点「完成」失败：{type(exc).__name__}")
    return False


def dismiss_overlays(page, log: RunLog,
                     hints: tuple[str, ...] = ("封面制作", "上传封面", "设置封面"),
                     tries: int = 3) -> bool:
    """用 Esc 清掉挡住页面的弹窗，否则后面的开关全点不到。"""
    cleared = False
    for _ in range(tries):
        if not any(visible(page, h, exact=False) for h in hints):
            break
        try:
            page.keyboard.press("Escape")
            cleared = True
            log.step("Esc 关闭遮挡弹窗")
            pause(0.6, 1.2)
        except Exception:
            break
    return cleared


def dump(page, log: RunLog, tag: str) -> None:
    """把关键元素导成 JSON，页面结构不明时用来定位真实选择器。"""
    js = """() => {
      const out = [];
      const seen = new Set();
      const push = (el) => {
        if (out.length > 400 || !el.tagName) return;
        const tag = el.tagName.toLowerCase();
        const cls = String(el.className || '').slice(0, 100);
        const txt = (el.innerText || '').trim().slice(0, 40);
        const ph = (el.getAttribute && el.getAttribute('placeholder')) || '';
        const ce = (el.getAttribute && el.getAttribute('contenteditable')) || '';
        const ty = (el.getAttribute && el.getAttribute('type')) || '';
        const ac = (el.getAttribute && el.getAttribute('accept')) || '';
        const key = [tag, cls, txt, ph, ce, ty, ac].join('|');
        if (seen.has(key)) return;
        const relevant = ce || ty === 'file' ||
          /switch|radio|picker|editor|input|textarea/i.test(cls) ||
          (/定时|发布|封面|描述|作品|上传/.test(txt) && txt.length < 20);
        if (!relevant) return;
        seen.add(key);
        out.push({tag, cls, txt, ph, ce, ty, ac,
                  vis: !!(el.offsetParent || (el.getClientRects && el.getClientRects().length))});
      };
      const walk = (root) => {
        for (const el of root.querySelectorAll('*')) {
          push(el);
          if (el.shadowRoot) walk(el.shadowRoot);
        }
      };
      walk(document);
      return out;
    }"""
    try:
        data = page.evaluate(js)
        path = log.dir / f"{tag}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info(f"DOM 转储 {path.name}（{len(data)} 条）")
    except Exception as exc:
        log.warn(f"DOM 转储失败：{type(exc).__name__}")
