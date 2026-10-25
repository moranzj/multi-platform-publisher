"""快手创作者服务平台适配器。

快手的定时面板是 antd，时间列必须用真实点击（原 PS 版注释里明确记录过
el.click() 对 antd 时间列无效），这里统一用 Playwright 的点击。
"""
from __future__ import annotations

import time

from core import steps
from core.log import RunLog
from .base import Job, Platform, Result

DESC_SELECTORS = (
    "div[contenteditable='true'][data-placeholder*='作品描述']",
    "div[contenteditable='true'][data-placeholder*='描述']",
    "div[contenteditable='true']",
    "textarea[placeholder*='描述']",
)


class Kuaishou(Platform):
    key = "kuaishou"
    name = "快手"
    url = "https://cp.kuaishou.com/article/publish/video"
    success_patterns = ("发布成功", "作品发布成功", "提交成功")

    def fill(self, page, job: Job, log: RunLog) -> Result | None:
        log.stage("快手 开始")
        page.goto(self.url, wait_until="domcontentloaded", timeout=60_000)
        steps.pause(3, 5)
        steps.close_popups(page, log)
        steps.shot(page, log, "kuaishou-01-open")

        blocked = self.guard_login(page, log)
        if blocked:
            return blocked

        # 1) 视频
        if not steps.set_files_by_kind(page, "video", job.video, log, click_target="上传视频"):
            return Result(self.name, False, "找不到视频上传入口")
        steps.pause(2, 3)
        steps.wait_upload(page, log, steps.size_mb(job.video))
        steps.shot(page, log, "kuaishou-02-uploaded")

        # 2) 作品描述 = 标题 + 话题 + 文案（快手只有一个大输入框）
        desc_parts = [job.title]
        ks_tags = steps.normalize_topics(job.kuaishou_topics)
        if ks_tags:
            desc_parts.append(" ".join(ks_tags))
        if job.desc and job.desc != job.title:
            desc_parts.append(job.desc)
        desc = " ".join(p.strip() for p in desc_parts if p.strip())

        if not self._fill_desc(page, desc, log):
            return Result(self.name, False, "作品描述填不进去")
        steps.shot(page, log, "kuaishou-03-text")

        # 3) 封面（没指定就点平台推荐的第一张）
        self._cover(page, job.cover, log)
        steps.shot(page, log, "kuaishou-04-cover")

        # 4) 定时
        self._schedule(page, job, log)
        steps.shot(page, log, "kuaishou-05-scheduled")
        log.ok("快手 填写完成，等待提交")
        return None

    def submit(self, page, job: Job, log: RunLog) -> Result:
        log.stage("快手 提交")
        log.step("点击「发布」")
        if not steps.click_text(page, "发布", timeout=10_000, log=log):
            return Result(self.name, False, "点不到发布按钮")
        steps.pause(2, 3)
        steps.click_text(page, "确认发布", timeout=3000, log=log)

        ok = steps.wait_success(page, self.success_patterns, log=log)
        steps.shot(page, log, "kuaishou-05-result")
        return Result(self.name, True, "已提交" if ok else "已提交（未见成功提示，请核对）")

    # ------------------------------------------------------------------
    def _fill_desc(self, page, value: str, log: RunLog) -> bool:
        # 上传后编辑器是异步挂载的，给它最多 30 秒出现
        for attempt in range(3):
            for sel in DESC_SELECTORS:
                try:
                    if page.locator(sel).count() == 0:
                        continue
                    if steps.fill_editable(page, sel, value, timeout=10_000, log=log):
                        return True
                    if steps.fill_input(page, sel, value, timeout=10_000, log=log):
                        return True
                except Exception:
                    continue
            log.warn(f"描述框第 {attempt + 1} 次没找到，等待后重试")
            page.wait_for_timeout(8000)
        log.warn("所有描述输入框都失效")
        return False

    def _cover(self, page, cover: str, log: RunLog) -> None:
        """快手封面：有图就上传，没图就点「智能推荐封面」里的一张。

        新版弹窗是「封面截取 / 上传封面」两个 tab：
        切到「上传封面」→ 塞图 → 等预览真的渲染出来 → 点底部「确认」。
        只有「弹窗关掉 + 主封面缩略图变了」才算成功。
        """
        log.step("上传封面" if cover else "未指定封面，用快手推荐的封面")
        try:
            if not cover:
                self._pick_recommend(page, log)
                return

            self._wait_cover_ready(page, log)
            before = self._cover_shot(page)
            before_src = self._cover_src(page)
            for attempt in range(2):
                if not self._upload_cover_once(page, cover, log):
                    if attempt == 0:
                        log.warn("封面流程没走通，再试一次")
                        page.wait_for_timeout(1500)
                        continue
                    log.warn("封面没设置成功，请在网页上手动设置")
                    return

                after_src = self._cover_src(page)
                if after_src and after_src != before_src:
                    log.ok("封面已设置")
                    return

                after = self._cover_shot(page)
                if before and after and self._shot_diff(before, after) >= 5:
                    log.ok("封面已设置")
                    return

                if not before and after_src:
                    log.ok("封面已提交（截图核对不可用，请顺手看一眼）")
                    return

                log.warn("封面没生效" + ("，再试一次" if attempt == 0 else ""))
                before = after or before
                before_src = after_src or before_src
            log.warn("封面没设置成功，请在网页上手动设置")
        except Exception as exc:
            log.warn(f"封面流程失败: {type(exc).__name__}，请在网页上手动设置")

    def _upload_cover_once(self, page, cover: str, log: RunLog) -> bool:
        """走一遍「封面截取」弹窗：打开 → 切「上传封面」→ 塞图 → 确认。"""
        modal = self._cover_modal(page)
        if not modal.is_visible():
            slot = page.locator("div[class*='_default-cover']").first
            if not slot.count():
                log.warn("找不到快手封面块")
                return False
            try:
                slot.scroll_into_view_if_needed(timeout=3000)
                slot.click(timeout=8000)
            except Exception as exc:
                log.warn(f"点封面块失败: {type(exc).__name__}")
                # 被遮罩吃掉时，改成 DOM 点击
                try:
                    page.evaluate("""() => {
                        const el = document.querySelector("[class*='_cover-full-editor']");
                        if (el) el.click();
                    }""")
                except Exception:
                    pass
            try:
                modal.wait_for(state="visible", timeout=12000)
            except Exception:
                log.warn("封面弹窗没打开，这次没设置成功")
                return False

        page.wait_for_timeout(800)  # 等 ant-modal 打开动画

        def panel_open() -> bool:
            # 标签切过去后，弹窗里会出现「上传图片」面板；
            # 已经传过图时按钮会变成「清空上传」，同样说明面板开着。
            # 必须看可见性：隐藏副本会一直挂在 DOM 里。
            try:
                for text in ("上传图片", "清空上传"):
                    loc = modal.get_by_text(text, exact=False)
                    if any(loc.nth(i).is_visible() for i in range(min(loc.count(), 10))):
                        return True
                return False
            except Exception:
                return False

        tab = modal.get_by_text("上传封面", exact=True).first
        before_inputs = self._image_input_count(page)
        switched = panel_open()
        for attempt in range(4):
            if switched:
                break
            try:
                tab.click(timeout=6000)
            except Exception as exc:
                log.warn(f"第 {attempt + 1} 次点「上传封面」失败: {type(exc).__name__}")
                page.wait_for_timeout(800)
                continue
            for _ in range(10):
                page.wait_for_timeout(400)
                if self._image_input_count(page) > before_inputs or panel_open():
                    switched = True
                    break
            if switched:
                break
            log.warn("「上传封面」标签没切过去，重试")
            page.wait_for_timeout(800)

        if not switched:
            # 兜底：有些遮罩会拦真实点击，但拦不住 DOM 的 click
            try:
                log.warn("改用 DOM 点击「上传封面」")
                tab.evaluate("el => el.click()")
                page.wait_for_timeout(1200)
                switched = self._image_input_count(page) > before_inputs or panel_open()
            except Exception:
                pass

        if not switched:
            log.warn("「上传封面」标签始终打不开，放弃本次封面")
            self._close_cover_modal(page)
            return False

        log.step("已切到「上传封面」")
        if not steps.set_files_by_kind(page, "image", cover, log, prefer_last=True):
            log.warn("找不到封面文件输入框")
            self._close_cover_modal(page)
            return False

        # 上传成功的标志：「上传图片」变成「清空上传」，再等预览图渲染出来
        accepted = False
        for _ in range(25):
            page.wait_for_timeout(400)
            try:
                clear = modal.get_by_text("清空上传", exact=False)
                if any(clear.nth(i).is_visible() for i in range(min(clear.count(), 10))):
                    accepted = True
                    break
            except Exception:
                pass
        if not accepted:
            log.warn("封面图没传上去（没出现「清空上传」）")
            self._close_cover_modal(page)
            return False

        self._wait_preview(modal, page, log)

        # 只点底部那个「确认」；「去编辑」是主按钮，别点错。
        # 预览还没就绪时点击会被吞掉，所以没关弹窗就再点一次。
        for round_ in range(3):
            clicked = False
            try:
                btn = modal.locator("button", has_text="确认").last
                if btn.count():
                    btn.scroll_into_view_if_needed(timeout=2000)
                    btn.click(timeout=6000)
                    clicked = True
            except Exception as exc:
                log.warn(f"点封面「确认」失败: {type(exc).__name__}")
            if not clicked:
                try:
                    modal.get_by_text("确认", exact=True).last.click(timeout=4000)
                    clicked = True
                except Exception:
                    pass
            if not clicked:
                log.warn("封面弹窗里找不到「确认」")
                break

            for _ in range(20):          # 最多等 10 秒
                page.wait_for_timeout(500)
                if not modal.is_visible():
                    page.wait_for_timeout(1500)
                    return True
            log.warn(f"点了「确认」弹窗没关，再试第 {round_ + 2} 次")

        self._close_cover_modal(page)
        return False

    @staticmethod
    def _wait_preview(modal, page, log: RunLog, timeout: int = 8) -> bool:
        """等上传的封面预览真的渲染出来。

        「清空上传」出现只代表文件选中了，图还在解码/裁切；
        这时候点「确认」经常什么也不发生。预览可能是 img、canvas 或背景图。
        """
        js = """m => {
            if ([...m.querySelectorAll('img')]
                .some(i => i.offsetParent && i.naturalWidth > 100)) return true;
            const cv = m.querySelector('canvas');
            if (cv && cv.width > 100) return true;
            return [...m.querySelectorAll('div,span')].some(d => {
                const s = getComputedStyle(d).backgroundImage || '';
                return s.includes('blob:') || s.includes('data:image');
            });
        }"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if modal.evaluate(js):
                    page.wait_for_timeout(500)
                    return True
            except Exception:
                pass
            page.wait_for_timeout(400)
        log.warn("封面预览没渲染出来，仍然尝试确认")
        return False

    @staticmethod
    def _cover_modal(page):
        """「封面截取」弹窗（antd modal）。"""
        return page.locator(".ant-modal-content").filter(has_text="封面截取").last

    @classmethod
    def _close_cover_modal(cls, page) -> None:
        try:
            modal = cls._cover_modal(page)
            if modal.is_visible():
                close = modal.locator("img[class*='_header-close']").last
                if close.count():
                    close.click(timeout=3000)
                    page.wait_for_timeout(500)
        except Exception:
            pass
        try:
            if cls._cover_modal(page).is_visible():
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception:
            pass

    @staticmethod
    def _wait_cover_ready(page, log: RunLog, timeout: int = 20) -> bool:
        """等封面缩略图真正渲染出来（视频处理中时元素在，但图还是空的）。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ready = page.evaluate("""() => {
                    const box = document.querySelector("[class*='_default-cover']");
                    const img = box && box.querySelector('img');
                    return !!(img && img.src && img.complete && img.naturalWidth > 0);
                }""")
                if ready:
                    return True
            except Exception:
                pass
            page.wait_for_timeout(500)
        log.warn("封面区没准备好，继续尝试")
        return False

    @staticmethod
    def _cover_shot(page) -> bytes:
        """主封面缩略图截图，用来确认封面真的换了。"""
        try:
            loc = page.locator("div[class*='_default-cover']").first
            if not loc.count():
                return b""
            loc.scroll_into_view_if_needed(timeout=2500)
            return loc.screenshot(animations="disabled", timeout=8000)
        except Exception:
            try:
                loc = page.locator("div[class*='_default-cover']").first
                box = loc.bounding_box()
                if box:
                    return page.screenshot(clip=box, animations="disabled", timeout=8000)
            except Exception:
                pass
        return b""

    @classmethod
    def _wait_cover_changed(cls, page, before: bytes, timeout: int = 10) -> bytes:
        """轮询封面缩略图，确认变化稳定后返回新截图；一直没变返回空。"""
        if not before:
            return b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            page.wait_for_timeout(500)
            shot = cls._cover_shot(page)
            if not shot or cls._shot_diff(before, shot) < 5:
                continue
            page.wait_for_timeout(600)
            again = cls._cover_shot(page)
            if again and cls._shot_diff(before, again) >= 5 and cls._shot_diff(shot, again) < 8:
                return again
        return b""

    @staticmethod
    def _shot_diff(a: bytes, b: bytes) -> float:
        """两张截图的平均灰度差（0-255），用来判断封面图有没有换。"""
        if not a or not b:
            return 0.0
        try:
            from io import BytesIO

            from PIL import Image, ImageChops, ImageStat

            ia = Image.open(BytesIO(a)).convert("L").resize((96, 96))
            ib = Image.open(BytesIO(b)).convert("L").resize((96, 96))
            return float(ImageStat.Stat(ImageChops.difference(ia, ib)).mean[0])
        except Exception:
            return 0.0

    @staticmethod
    def _cover_src(page) -> str:
        """主封面缩略图的图片地址（只做兜底判断）。"""
        try:
            return page.evaluate("""() => {
                const box = document.querySelector("[class*='_default-cover']");
                const img = box && box.querySelector('img');
                return img ? (img.currentSrc || img.src || '') : '';
            }""") or ""
        except Exception:
            return ""

    @staticmethod
    def _image_input_count(page) -> int:
        """页面上 image 类型的文件输入框数量（切标签会多一个）。"""
        try:
            return int(page.evaluate(
                """() => [...document.querySelectorAll("input[type=file]")]
                    .filter(i => /image/.test((i.getAttribute('accept') || '').toLowerCase()))
                    .length"""))
        except Exception:
            return 0

    def _pick_recommend(self, page, log: RunLog) -> bool:
        """从「智能推荐封面」里挑最亮的一张。

        推荐位是按顺序给的，第一张经常就是视频开头那帧黑的；直接点第一张
        看起来跟没设置一样，所以按亮度挑一张更像封面的。
        """
        try:
            tiles = page.locator("[class*='_recommend-cover-item']")
            count = tiles.count()
            if count == 0:
                log.warn("找不到快手的推荐封面，保留视频首帧")
                return False
            idx = self._brightest_tile(page, log)
            tiles.nth(idx).scroll_into_view_if_needed(timeout=3000)
            tiles.nth(idx).click(timeout=5000)
            page.wait_for_timeout(2500)
            log.ok(f"已应用快手推荐封面（第 {idx + 1} 张）")
            return True
        except Exception as exc:
            log.warn(f"应用推荐封面失败: {type(exc).__name__}")
            return False

    @staticmethod
    def _brightest_tile(page, log: RunLog) -> int:
        """挑最亮的一张推荐封面。

        推荐图的 CDN 是跨域的，页面里 canvas 读像素会被安全策略拦掉，
        所以把图下载下来用 Pillow 算平均亮度。算不出来就退化为第 2 张
        （第 1 张通常就是当前首帧，常常是黑的）。
        """
        try:
            srcs = page.evaluate(
                """() => [...document.querySelectorAll("[class*='_recommend-cover-item']")]
                    .map(t => {
                        const img = t.querySelector('img');
                        return img ? (img.currentSrc || img.src || '') : '';
                    })"""
            )
        except Exception:
            return 0
        fallback = 1 if len(srcs) > 1 else 0
        try:
            import io

            from PIL import Image
        except Exception:
            return fallback

        best, best_lum = fallback, 0.0
        for i, src in enumerate(srcs):
            if not src:
                continue
            try:
                body = page.request.get(src, timeout=8000).body()
                im = Image.open(io.BytesIO(body)).convert("L").resize((16, 16))
                lum = sum(im.getdata()) / 256
            except Exception:
                continue
            if lum > best_lum:
                best, best_lum = i, lum
        log.step(f"推荐封面按亮度选第 {best + 1} 张（{best_lum:.0f}/255）")
        return best

    def _schedule(self, page, job: Job, log: RunLog) -> None:
        if job.immediate:
            self._set_immediate(page, log)
            return
        log.step(f"设定时发布 {job.date} {job.time}")
        try:
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1200)

            # 选「定时发布」单选
            picked = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('label.ant-radio-wrapper')]
                        .find(e => e.innerText.trim() === '定时发布');
                    if (!el) return false;
                    el.click();
                    return true;
                }"""
            )
            if picked:
                log.step("已选「定时发布」")
            else:
                log.warn("找不到定时发布单选")
                return
            page.wait_for_timeout(2000)

            # 打开日期时间面板
            opened = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('input')]
                        .find(e => e.placeholder && e.placeholder.includes('选择日期时间'));
                    if (!el) return false;
                    el.click();
                    return true;
                }"""
            )
            if not opened:
                log.warn("找不到日期时间输入框")
                return
            page.wait_for_timeout(1200)

            day = str(int(job.date.split("-")[2]))
            if not self._pick_day(page, day):
                log.warn(f"日历里找不到 {day} 号")
            page.wait_for_timeout(900)

            # 选完日期面板会刷新，重新点开
            page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('input')]
                        .find(e => e.placeholder && e.placeholder.includes('选择日期时间'));
                    if (el) el.click();
                }"""
            )
            page.wait_for_timeout(900)

            hh, mm = job.time.split(":")[:2]
            self._pick_time_col(page, int(hh), 1, log)
            page.wait_for_timeout(400)
            self._pick_time_col(page, int(mm), 2, log)
            page.wait_for_timeout(500)

            steps.click_sel(page, "li.ant-picker-ok button", log=log, what="确定")
            page.wait_for_timeout(800)
            log.ok("定时已设置")
        except Exception as exc:
            log.warn(f"定时设置失败: {type(exc).__name__}")

    @staticmethod
    def _set_immediate(page, log: RunLog) -> None:
        """切到「立即发布」：点单选，并确认日期时间框真的消失。"""
        log.step("切换为「立即发布」")
        try:
            clicked = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('label.ant-radio-wrapper')]
                        .find(e => (e.innerText || '').trim() === '立即发布');
                    if (!el) return false;
                    el.click();
                    return true;
                }"""
            )
            if not clicked:
                log.warn("找不到「立即发布」选项，保持平台默认")
                return
            page.wait_for_timeout(1500)
            gone = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('input')]
                        .find(e => e.placeholder && e.placeholder.includes('选择日期时间'));
                    return !(el && el.offsetParent);
                }"""
            )
            if gone:
                log.ok("已切换为立即发布")
            else:
                log.warn("点了「立即发布」但时间框还在，请在网页上确认")
        except Exception as exc:
            log.warn(f"切换立即发布失败: {type(exc).__name__}")

    @staticmethod
    def _pick_day(page, day: str) -> bool:
        try:
            return bool(page.evaluate(
                """(d) => {
                    const cells = [...document.querySelectorAll('div.ant-picker-cell-inner')]
                        .filter(e => e.innerText.trim() === d && e.offsetParent !== null);
                    if (!cells.length) return false;
                    cells[cells.length - 1].click();
                    return true;
                }""",
                day,
            ))
        except Exception:
            return False

    @staticmethod
    def _pick_time_col(page, hour_or_min: int, nth: int, log: RunLog) -> None:
        """antd 时间列：第 nth 列里点第 hour_or_min 个 li（列有占位行，故 +1）。"""
        idx = hour_or_min + 1
        sel = (f"div.ant-picker-time-panel ul.ant-picker-time-panel-column"
               f":nth-of-type({nth}) li:nth-child({idx})")
        try:
            loc = page.locator(sel).first
            if loc.count():
                loc.click(timeout=5000)
                log.step(f"时间列 {nth} 选第 {hour_or_min}")
            else:
                log.warn(f"时间列 {nth} 未命中")
        except Exception as exc:
            log.warn(f"时间列点击失败: {type(exc).__name__}")

