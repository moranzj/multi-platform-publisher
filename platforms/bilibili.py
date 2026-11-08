"""B站投稿适配器。

选择器来自旧版 PowerShell 实现的实测记录（B站投稿页是 micro-app，
可访问性树不暴露，只能靠 CSS）。这里改成 Playwright 的直连写法。
"""
from __future__ import annotations

import base64
from dataclasses import replace

from core import schedule as sched
from core import steps
from core.log import RunLog
from .base import Job, Platform, Result


class Bilibili(Platform):
    key = "bili"
    name = "B站"
    url = "https://member.bilibili.com/platform/upload/video/frame"
    success_patterns = ("投稿成功", "发布成功", "稿件投递成功")
    # 提交成功后 B站会跳到稿件管理；只等横幅会误判成「没提交上」
    success_urls = ("upload-manager", "content/manage")
    fail_patterns = ("投稿失败", "提交失败", "定时发布时间不可用")

    # ---- 选择器常量（改版时集中改这里）----
    SEL_TITLE = "input[placeholder='请输入稿件标题']"
    SEL_TAG = "input[placeholder='按回车键Enter创建标签']"
    SEL_DESC = "div.ql-editor"
    SEL_SUBMIT = "span.submit-add"
    SEL_SCHEDULE_SWITCH = "div.switch-container"
    SEL_DATE_INPUT = "div.date-picker-date"
    SEL_TIME_INPUT = "div.date-picker-timer"

    def fill(self, page, job: Job, log: RunLog) -> Result | None:
        log.stage("B站 开始")
        page.goto(self.url, wait_until="domcontentloaded", timeout=60_000)
        steps.pause(3, 5)
        steps.close_popups(page, log)
        steps.shot(page, log, "bili-01-open")

        blocked = self.guard_login(page, log)
        if blocked:
            return blocked

        # 1) 上传视频
        if not steps.set_files_by_kind(page, "video", job.video, log, click_target="上传视频"):
            return Result(self.name, False, "找不到视频上传入口")
        steps.pause(2, 3)

        size_mb = steps.size_mb(job.video)
        steps.wait_upload(page, log, size_mb)
        steps.shot(page, log, "bili-02-uploaded")

        # 2) 标题 / 标签 / 简介
        if not steps.fill_input(page, self.SEL_TITLE, job.title_for("bili"), log=log):
            return Result(self.name, False, "标题填不进去")
        steps.pause(0.5, 1.0)

        if job.bili_tags:
            self._fill_tags(page, job.bili_tags, log)

        if job.bili_topic:
            self._add_topic(page, job.bili_topic, log)

        bili_desc = job.desc_for("bili")
        if bili_desc:
            steps.fill_editable(page, self.SEL_DESC, bili_desc, log=log)
        steps.shot(page, log, "bili-03-text")

        # 3) 封面（没指定就用「系统推荐封面」第一张）
        if job.cover:
            self._cover(page, job.cover, log)
        else:
            self._pick_recommend(page, job.video, log)
        steps.shot(page, log, "bili-04-cover")

        # 4) 定时发布
        if not self._schedule(page, job, log):
            steps.shot(page, log, "bili-05-scheduled")
            return Result(self.name, False, "定时没设上（已停下，避免误发立即发布）")
        steps.shot(page, log, "bili-05-scheduled")
        log.ok("B站 填写完成，等待提交")
        return None

    def submit(self, page, job: Job, log: RunLog) -> Result:
        log.stage("B站 提交")
        original = job
        for attempt in range(1, 4):
            if not steps.click_sel(page, self.SEL_SUBMIT, log=log, what="立即投稿"):
                return Result(self.name, False, "点不到投稿按钮")
            steps.pause(2, 3)
            steps.click_text(page, "确认投稿", timeout=4000, log=log, optional=True)
            steps.pause(1.5, 2.5)

            reason = self._schedule_rejected(page)
            if not reason:
                steps.click_text(page, "确定", timeout=2500, log=log, optional=True)
                ok = steps.wait_success(
                    page, self.success_patterns, log=log,
                    url_hints=self.success_urls,
                    fail_patterns=self.fail_patterns)
                steps.shot(page, log, "bili-05-result")
                return Result(self.name, True,
                              "已提交" if ok else "已提交（未见成功提示，请核对）")

            log.warn(f"B站拒绝定时时间：{reason}")
            if attempt >= 3:
                break
            self._close_dialog(page, log)
            # 第一次往后挪 2 小时，第二次挪到第二天同一时间：
            # 既覆盖「离现在太近」，也覆盖「当天不让约」两种情况
            later = sched.bump(original.publish_at(), 2 if attempt == 1 else 24)
            job = replace(original, date=f"{later:%Y-%m-%d}", time=f"{later:%H:%M}")
            log.step(f"改用 {job.date} {job.time} 重新设定时（第 {attempt + 1} 次）")
            if not self._schedule(page, job, log):
                log.warn("重新设置定时失败，停止重试")
                break
            steps.pause(1.0, 1.5)

        steps.shot(page, log, "bili-05-rejected")
        return Result(self.name, False,
                      f"定时时间被 B站拒绝（原定 {original.date} {original.time}，"
                      "已试 +2h / +24h），请换个时间或改用立即发布")

    @staticmethod
    def _schedule_rejected(page) -> str:
        """提交后 B站会用弹窗拦下不可用的定时时间（只认可见的，避免旧 DOM 误报）。"""
        for phrase in ("定时发布时间不可用", "定时时间不可用",
                       "发布时间不可用", "定时发布时间不合法"):
            try:
                loc = page.get_by_text(phrase, exact=False)
                if any(loc.nth(i).is_visible() for i in range(min(loc.count(), 5))):
                    return phrase
            except Exception:
                continue
        return ""

    @staticmethod
    def _close_dialog(page, log: RunLog) -> None:
        """Esc 关掉报错弹窗；之后重新设时间比找「确定」更稳。"""
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        steps.pause(0.8, 1.2)
        steps.dismiss_overlays(page, log)

    # ------------------------------------------------------------------
    def _fill_tags(self, page, tags: str, log: RunLog) -> None:
        """B站标签必须逐个回车生成，逗号分隔的整串会被当成一个标签。"""
        items = [t.strip().lstrip("#") for t in tags.replace("，", ",").split(",") if t.strip()]
        for item in items:
            try:
                box = page.locator(self.SEL_TAG).first
                box.click(timeout=8000)
                box.fill(item)
                steps.pause(0.3, 0.6)
                page.keyboard.press("Enter")
                steps.pause(0.4, 0.8)
                log.step(f"标签「{item}」")
            except Exception as exc:
                log.warn(f"标签「{item}」失败: {type(exc).__name__}")

    def _add_topic(self, page, topic: str, log: RunLog) -> None:
        """参与话题：点「搜索更多话题」→ 搜关键词 → 勾选 → 确定。

        弹窗结构（2026-10 实测）：
            div.dialog-item
              └ span.check-radio-v2-box   ← 单选圈，点这个才选中
              └ div.topic-card
                  ├ div.topic-tag-name    ← 话题名
                  └ div.topic-vv          ← 播放量
        「确定」是 button.submit-add（点它里面的 span 会点不动）。
        """
        tags = steps.normalize_topics(topic)
        if not tags:
            return
        for tag in tags:
            name = tag.lstrip("#")
            try:
                if not self._open_topic_dialog(page, log):
                    log.warn("找不到「搜索更多话题」入口")
                    return
                box = page.locator("input.bcc-search-input").last
                box.click(timeout=6000)
                box.fill(name)
                steps.pause(1.8, 2.8)

                idx = page.evaluate(
                    """(kw) => {
                        const all = [...document.querySelectorAll('div.dialog-item')];
                        const rows = all.filter(r => r.offsetParent);
                        const parse = (t) => {
                            const m = (t || '').match(/([\\d.]+)\\s*(万|亿)?/);
                            if (!m) return 0;
                            const n = parseFloat(m[1]);
                            return m[2] === '万' ? n * 1e4 : (m[2] === '亿' ? n * 1e8 : n);
                        };
                        let best = -1, bestScore = -1;
                        rows.forEach((r, i) => {
                            const nameEl = r.querySelector('div.topic-tag-name');
                            const nm = ((nameEl || r).innerText || '').trim();
                            if (!nm.includes(kw)) return;
                            const vvEl = r.querySelector('div.topic-vv');
                            const plays = parse((vvEl || r).innerText || '');
                            const score = plays + (nm === kw ? 1e12 : 0);
                            if (score > bestScore) { bestScore = score; best = i; }
                        });
                        // 返回在「全部节点」里的下标，和 Playwright 的 nth() 对齐；
                        // 只返回可见行下标会错位到隐藏节点。
                        return best >= 0 ? all.indexOf(rows[best]) : -1;
                    }""",
                    name,
                )
                if idx is None or idx < 0:
                    log.warn(f"话题「{name}」在 B站 搜不到")
                    self._close_topic_dialog(page, log)
                    continue

                row = page.locator("div.dialog-item").nth(idx)
                radio = row.locator("span.check-radio-v2-box")
                if radio.count():
                    radio.first.click(timeout=5000)
                else:
                    row.locator("div.topic-card").first.click(timeout=5000)
                steps.pause(0.4, 0.9)

                nm = row.locator("div.topic-tag-name")
                picked = nm.first.inner_text().strip()[:24] if nm.count() else name
                vv = row.locator("div.topic-vv")
                plays = vv.first.inner_text().strip() if vv.count() else ""
                log.step(f"话题选「{picked}」{plays}")

                page.locator("button.submit-add").last.click(timeout=6000)
                steps.pause(1.2, 2.0)

                if self._topic_dialog_open(page):
                    log.warn(f"话题「{picked}」没能确定")
                    self._close_topic_dialog(page, log)
            except Exception as exc:
                log.warn(f"话题「{name}」失败: {type(exc).__name__}")
                self._close_topic_dialog(page, log)

    @staticmethod
    def _topic_dialog_open(page) -> bool:
        try:
            box = page.locator("input.bcc-search-input")
            return bool(box.count()) and box.last.is_visible()
        except Exception:
            return False

    @staticmethod
    def _open_topic_dialog(page, log: RunLog) -> bool:
        """打开「参与话题」弹窗（已经开着就直接用）。"""
        if Bilibili._topic_dialog_open(page):
            return True
        try:
            more = page.locator("div.tag-more")
            if more.count():
                more.first.scroll_into_view_if_needed(timeout=4000)
                more.first.click(timeout=6000)
            else:
                # 文字带个箭头「搜索更多话题 >」，精确匹配找不到，用模糊匹配
                steps.click_text(page, "搜索更多话题", timeout=4000, exact=False, log=log)
            page.wait_for_timeout(1500)
        except Exception as exc:
            log.warn(f"打开话题弹窗失败: {type(exc).__name__}")
            return False
        return Bilibili._topic_dialog_open(page)

    @staticmethod
    def _close_topic_dialog(page, log: RunLog) -> None:
        """把话题弹窗关掉，别挡着后面的表单。"""
        try:
            cancel = page.locator("button.submit-cancel")
            if cancel.count():
                cancel.last.click(timeout=3000)
            else:
                steps.click_text(page, "取消", timeout=2000, log=log)
            page.wait_for_timeout(800)
        except Exception:
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            except Exception:
                pass

    def _pick_recommend(self, page, video: str, log: RunLog) -> bool:
        """没有指定封面时，用视频第一帧当封面。

        新旧两套投稿页都走同一条路：从本地视频抓第 0 秒的画面，
        打开「封面制作」弹窗注入图片，再点「完成」。即使旧版页面
        已经自动选了推荐封面，也会用第一帧替换掉，保证默认行为一致。
        """
        frame = self._video_frame(page, video, log)
        if not frame:
            log.warn("没能从视频里取到第一帧")
            return self._keep_auto_cover(page, log)

        try:
            if not self._open_cover_editor(page, log):
                log.warn("找不到 B站 封面入口，保留默认")
                return self._keep_auto_cover(page, log)
            if not self._wait_cover_editor(page):
                log.warn("B站 封面弹窗没打开，保留默认")
                self._close_cover_editor(page, log)
                return self._keep_auto_cover(page, log)

            if not self._set_cover_frame(page, frame, log):
                log.warn("视频首帧没能塞进 B站 封面弹窗")
                self._close_cover_editor(page, log)
                return self._keep_auto_cover(page, log)

            if not self._finish_cover_editor(page, log):
                log.warn("B站 封面弹窗没关掉，保留默认")
                self._close_cover_editor(page, log)
                return self._keep_auto_cover(page, log)

            for _ in range(5):
                if self._cover_selected(page):
                    log.ok("B站 已用视频第一帧作为封面")
                    return True
                page.wait_for_timeout(1000)
            log.warn("B站 封面弹窗完成了，但封面区仍显示未设置")
            return False
        except Exception as exc:
            log.warn(f"B站 自动封面失败: {type(exc).__name__}")
            try:
                self._close_cover_editor(page, log)
            except Exception:
                pass
            return self._keep_auto_cover(page, log)

    @staticmethod
    def _keep_auto_cover(page, log: RunLog) -> bool:
        """首帧设置失败时，如果 B站 自己选了封面就保留。"""
        if Bilibili._cover_selected(page):
            log.ok("保留 B站 自动选中的封面")
            return True
        log.warn("B站 封面仍未设置，保留默认")
        return False

    @staticmethod
    def _cover_empty_visible(page) -> bool:
        """新版封面区是不是「添加封面」的空状态。"""
        try:
            empty = page.locator("div.cover-empty")
            return any(empty.nth(i).is_visible()
                       for i in range(min(empty.count(), 4)))
        except Exception:
            return False

    @staticmethod
    def _cover_selected(page) -> bool:
        """回读封面区：新旧版都确认真的有一张封面。"""
        try:
            if Bilibili._cover_empty_visible(page):
                return False
            img = page.locator("div.cover-img")
            for i in range(min(img.count(), 4)):
                el = img.nth(i)
                if not el.is_visible():
                    continue
                style = (el.get_attribute("style") or "").lower()
                if "background-image" in style and "url(" in style:
                    return True
            selected = page.locator("div.img-item-box.img-item-cover-selected")
            return any(selected.nth(i).is_visible()
                       for i in range(min(selected.count(), 4)))
        except Exception:
            return False

    @staticmethod
    def _wait_cover_editor(page, tries: int = 6) -> bool:
        for _ in range(tries):
            if Bilibili._cover_editor_open(page):
                return True
            page.wait_for_timeout(1000)
        return False

    @staticmethod
    def _video_frame(page, video: str, log: RunLog) -> bytes | None:
        """用浏览器自己解码本地视频，抓第一帧当封面（不依赖 ffmpeg）。

        做法：往页面里塞一个隐藏 file input，把本地视频文件放进去，
        再用 <video> + <canvas> 取第 0 秒的画面。这样不用额外装
        ffmpeg/opencv，也能处理常见 MP4/MOV。
        """
        input_id = "__bili_cover_frame_input"
        try:
            page.evaluate(
                """(id) => {
                    const old = document.getElementById(id);
                    if (old) old.remove();
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.id = id;
                    input.style.display = 'none';
                    document.body.appendChild(input);
                }""",
                input_id,
            )
            page.locator(f"#{input_id}").set_input_files(video)
            result = page.evaluate(
                r"""async (id) => {
                    const input = document.getElementById(id);
                    const file = input && input.files && input.files[0];
                    if (!file) return {ok: false, why: 'no file'};
                    const url = URL.createObjectURL(file);
                    const v = document.createElement('video');
                    v.muted = true;
                    v.playsInline = true;
                    v.preload = 'auto';
                    v.src = url;
                    v.style.position = 'fixed';
                    v.style.left = '-9999px';
                    document.body.appendChild(v);
                    try {
                        await new Promise((resolve, reject) => {
                            const t = setTimeout(
                                () => reject(new Error('metadata timeout')), 15000);
                            v.addEventListener('loadedmetadata', () => {
                                clearTimeout(t); resolve();
                            }, {once: true});
                            v.addEventListener('error', () => {
                                clearTimeout(t);
                                reject(new Error('video error ' +
                                    (v.error && v.error.code)));
                            }, {once: true});
                        });
                        // 等第一帧真正解码出来，再画到 canvas
                        if (v.readyState < 2) {
                            await new Promise((resolve) => {
                                const timer = setTimeout(resolve, 8000);
                                v.addEventListener('loadeddata', () => {
                                    clearTimeout(timer); resolve();
                                }, {once: true});
                                v.addEventListener('canplay', () => {
                                    clearTimeout(timer); resolve();
                                }, {once: true});
                            });
                        }
                        // 确保停在 0 秒；已经是 0 就不重复 seek
                        if (Math.abs(v.currentTime) > 0.001) {
                            await new Promise((resolve) => {
                                const timer = setTimeout(resolve, 5000);
                                v.addEventListener('seeked', () => {
                                    clearTimeout(timer); resolve();
                                }, {once: true});
                                try { v.currentTime = 0; }
                                catch (e) { clearTimeout(timer); resolve(); }
                            });
                        }
                        if (!v.videoWidth || !v.videoHeight) {
                            return {ok: false, why: 'no video size'};
                        }
                        const c = document.createElement('canvas');
                        const maxW = 1920;
                        const scale = Math.min(1, maxW / v.videoWidth);
                        c.width = Math.max(1, Math.round(v.videoWidth * scale));
                        c.height = Math.max(1, Math.round(v.videoHeight * scale));
                        c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
                        return {
                            ok: true, w: c.width, h: c.height, t: v.currentTime,
                            data: c.toDataURL('image/jpeg', 0.92),
                        };
                    } catch (e) {
                        return {ok: false, why: String(e && e.name) + ': ' +
                                String(e && e.message)};
                    } finally {
                        URL.revokeObjectURL(url);
                        v.remove();
                    }
                }""",
                input_id,
            )
            if not result.get("ok"):
                log.warn(f"视频取帧失败: {result.get('why')}")
                return None
            data = result["data"].split(",", 1)[1]
            frame = base64.b64decode(data)
            log.step(f"视频首帧 {result['w']}x{result['h']}")
            return frame
        except Exception as exc:
            log.warn(f"视频取帧失败: {type(exc).__name__}")
            return None
        finally:
            try:
                page.evaluate(
                    "(id) => { const el = document.getElementById(id);"
                    " if (el) el.remove(); }",
                    input_id,
                )
            except Exception:
                pass

    @staticmethod
    def _set_cover_frame(page, frame: bytes, log: RunLog) -> bool:
        """把视频帧塞进封面制作弹窗的 4:3 图片输入框。"""
        try:
            target = page.locator(
                "div.cover-editor div.cover-editor-panel-canvas-empty"
                ".ratio_4_3 input[type=file][accept*='image']")
            if target.count() == 0:
                target = page.locator(
                    "div.cover-editor input[type=file][accept*='image']")
            if target.count() == 0:
                target = page.locator("input[type=file][accept*='image']")
            if target.count() == 0:
                return False
            target.first.set_input_files({
                "name": "bili-cover.jpg",
                "mimeType": "image/jpeg",
                "buffer": frame,
            })
            log.step("注入视频帧到 B站 封面弹窗")
            page.wait_for_timeout(3000)
            # 等 4:3 画布真正出现图片；最多再等 8 秒
            for _ in range(8):
                filled = page.locator(
                    "div.cover-editor div.cover-editor-panel-canvas-image")
                if any(filled.nth(i).is_visible()
                       for i in range(min(filled.count(), 3))):
                    break
                page.wait_for_timeout(1000)
            return True
        except Exception as exc:
            log.warn(f"注入封面帧失败: {type(exc).__name__}")
            return False

    @classmethod
    def _finish_cover_editor(cls, page, log: RunLog) -> bool:
        """点「完成」/「确认同步」，直到封面弹窗关闭。"""
        page.wait_for_timeout(2000)
        for _ in range(5):
            if not cls._cover_editor_open(page):
                return True
            steps.click_modal_done(page, log)
            page.wait_for_timeout(2500)
            if steps.visible(page, "确认同步", exact=False):
                steps.click_text(page, "确认同步", timeout=2500, log=log)
            page.wait_for_timeout(1500)
        if cls._cover_editor_open(page):
            steps.dismiss_overlays(
                page, log,
                hints=("封面制作", "上传封面", "设置封面", "确认同步"))
        return not cls._cover_editor_open(page)

    @staticmethod
    def _close_cover_editor(page, log: RunLog) -> None:
        """放弃编辑时关掉封面弹窗，别挡着后面的定时设置。"""
        try:
            if not Bilibili._cover_editor_open(page):
                return
            close = page.locator("div.cover-editor-head-close")
            for i in range(min(close.count(), 3)):
                el = close.nth(i)
                if el.is_visible():
                    el.click(timeout=3000)
                    break
            page.wait_for_timeout(1000)
            if not Bilibili._cover_editor_open(page):
                return
            for text in ("放弃", "确定", "确认"):
                if steps.click_text(page, text, timeout=1200, exact=False,
                                    log=log, optional=True):
                    page.wait_for_timeout(800)
                    if not Bilibili._cover_editor_open(page):
                        return
            if Bilibili._cover_editor_open(page):
                steps.dismiss_overlays(
                    page, log,
                    hints=("封面制作", "上传封面", "设置封面", "确认同步"))
        except Exception:
            pass

    @staticmethod
    def _cover_editor_open(page) -> bool:
        """封面编辑弹窗是否还开着（新旧版标题/按钮不一样）。"""
        for text in ("封面制作", "确认同步"):
            if steps.visible(page, text, exact=False):
                return True
        # 新版弹窗可能只剩一个「完成」按钮；主页面上的「上传完成」不是精确匹配。
        # 不把「上传封面」单独当信号：它可能是主页面 hover 后才出现的旧按钮。
        if steps.visible(page, "完成", exact=True):
            return True
        # 最后看弹窗容器：有些新版弹窗的标题/按钮文案会换，但容器类名仍含 dialog/modal
        try:
            return bool(page.evaluate("""() => {
                const nodes = [...document.querySelectorAll('[class*="dialog"], [class*="modal"]')];
                return nodes.some(n => {
                    const s = getComputedStyle(n);
                    if (s.display === 'none' || s.visibility === 'hidden') return false;
                    const r = n.getBoundingClientRect();
                    if (r.width < 2 || r.height < 2) return false;
                    const t = n.innerText || '';
                    return t.includes('封面') && /上传|制作|同步|完成/.test(t);
                });
            }"""))
        except Exception:
            return False

    @classmethod
    def _open_cover_editor(cls, page, log: RunLog) -> bool:
        """打开封面编辑弹窗。

        旧版入口是「添加封面」（span.add-text）；新版改成 hover 封面区后
        出现的「封面设置」，而且默认藏在 DOM 里，所以先 hover 再点，
        最后用 DOM 点击兜底。
        """
        cls._reveal_cover_edit(page, log)

        # 旧版入口在新版页面已经不存在，不必为它等满 8 秒；
        # 这里不打 warn，否则新版每次成功走兜底都会留下一条吓人的假警告。
        if steps.click_sel(page, "span.add-text", timeout=2500,
                           what="添加封面"):
            log.step("点击「添加封面」")
            return True

        try:
            edit = page.get_by_text("封面设置", exact=True)
            for i in range(edit.count() - 1, -1, -1):
                el = edit.nth(i)
                if el.is_visible():
                    el.click(timeout=5000)
                    log.step("点击「封面设置」")
                    return True
        except Exception:
            pass

        try:
            clicked = page.evaluate("""() => {
                const el = [...document.querySelectorAll('span.edit-text')]
                    .find(e => (e.innerText || '').trim() === '封面设置');
                if (!el) return false;
                el.click();
                return true;
            }""")
            if clicked:
                page.wait_for_timeout(1500)
                log.step("通过 DOM 点击「封面设置」")
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _reveal_cover_edit(page, log: RunLog) -> bool:
        """把鼠标移到封面区，让隐藏的「封面设置」入口显形。

        新版 B 站把入口放在 hover 才出现的 span.edit-text 里；不 hover
        直接 get_by_text 永远等不到可见元素。失败也不影响后面的 DOM 兜底。
        """
        targets = [
            page.locator("div.img-item-box.img-item-cover"),
            page.locator("div.section-title-container", has_text="封面"),
        ]
        hovered = False
        for loc in targets:
            try:
                if not loc.count():
                    continue
                first = loc.first
                first.scroll_into_view_if_needed(timeout=3000)
                first.hover(timeout=3000)
                page.wait_for_timeout(600)
                hovered = True
            except Exception:
                continue
        return hovered

    def _cover(self, page, cover: str, log: RunLog) -> None:
        log.step("上传封面")
        try:
            page.mouse.wheel(0, -600)
            steps.pause(0.5, 1.0)
            if not self._open_cover_editor(page, log):
                log.warn("找不到封面入口，跳过封面")
                return
            # 等弹窗真正挂载出来；新版页面有时比旧版慢
            opened = False
            for _ in range(6):
                if self._cover_editor_open(page):
                    opened = True
                    break
                page.wait_for_timeout(1000)
            if not opened:
                log.warn("封面弹窗没打开，跳过封面")
                return
            if not self._set_cover_file(page, cover, log):
                log.warn("封面文件注入失败")
                steps.dismiss_overlays(
                    page, log,
                    hints=("封面制作", "上传封面", "设置封面", "确认同步"))
                return
            page.wait_for_timeout(4000)
            # 完成 → 确认同步，可能要点多次；以封面编辑弹窗消失为准
            if self._finish_cover_editor(page, log):
                log.ok("封面已设置")
            else:
                log.warn("封面弹窗仍未关闭")
        except Exception as exc:
            log.warn(f"封面流程失败: {type(exc).__name__}")

    @staticmethod
    def _set_cover_file(page, cover: str, log: RunLog) -> bool:
        """塞封面图；新版弹窗若停在「封面截取」，先切到「上传封面」。"""
        if steps.set_files_by_kind(page, "image", cover, log):
            return True
        if steps.click_text(page, "上传封面", timeout=2500, exact=True, log=log):
            page.wait_for_timeout(1200)
            return steps.set_files_by_kind(page, "image", cover, log)
        return False

    def _schedule(self, page, job: Job, log: RunLog) -> bool:
        if job.immediate:
            self._set_immediate(page, log)
            return True
        log.step(f"设定时发布 {job.date} {job.time}")
        try:
            steps.dismiss_overlays(page, log)
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1500)

            # 重试时开关可能已经开着，再点一下会把它关掉
            if not self._date_visible(page):
                if not steps.click_sel(page, self.SEL_SCHEDULE_SWITCH,
                                       log=log, what="定时发布开关"):
                    log.warn("找不到定时开关")
                    return False
                page.wait_for_timeout(3000)
            if not self._date_visible(page):
                steps.click_sel(page, self.SEL_SCHEDULE_SWITCH,
                                log=log, what="定时开关(重试)")
                page.wait_for_timeout(3000)
            if not self._date_visible(page):
                log.warn("定时面板没打开")
                return False

            # 日期
            steps.click_sel(page, self.SEL_DATE_INPUT, log=log, what="日期框")
            page.wait_for_timeout(1200)
            day = str(int(job.date.split("-")[2]))
            if not self._pick_day(page, day):
                log.warn(f"日历里找不到 {day} 号，尝试翻到下月")
                steps.click_sel(page, "button.date-picker-next, div.date-picker-next", log=log, what="下月")
                page.wait_for_timeout(800)
                self._pick_day(page, day)
            page.wait_for_timeout(1000)

            # 时分
            steps.click_sel(page, self.SEL_TIME_INPUT, log=log, what="时间框")
            page.wait_for_timeout(1000)
            hh, mm = job.time.split(":")[:2]
            self._pick_time(page, f"{int(hh):02d}", 0, log)
            page.wait_for_timeout(600)
            self._pick_time(page, f"{int(mm):02d}", 1, log)
            page.wait_for_timeout(800)

            # 面板显示值必须和表单目标一致：显示对了，提交时才不会被拦
            shown_date = self._read_text(page, self.SEL_DATE_INPUT)
            shown_time = self._read_text(page, self.SEL_TIME_INPUT)
            want_time = f"{int(hh):02d}:{int(mm):02d}"
            if shown_date and shown_date != job.date:
                log.warn(f"日期框显示「{shown_date}」，目标「{job.date}」，没设上")
                return False
            if shown_time and shown_time != want_time:
                log.warn(f"时间框显示「{shown_time}」，目标「{want_time}」，没设上")
                return False
            log.ok(f"定时已设置（{shown_date or job.date} {shown_time or want_time}）")
            return True
        except Exception as exc:
            log.warn(f"定时设置失败: {type(exc).__name__}")
            return False

    @staticmethod
    def _read_text(page, selector: str) -> str:
        try:
            return (page.locator(selector).first.inner_text(timeout=2000) or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _date_visible(page) -> bool:
        loc = page.locator(Bilibili.SEL_DATE_INPUT)
        try:
            return any(loc.nth(i).is_visible() for i in range(min(loc.count(), 3)))
        except Exception:
            return False

    @staticmethod
    def _set_immediate(page, log: RunLog) -> None:
        """B站的定时是一个开关：开着就点一下关掉，日期框消失即为立即发布。"""
        log.step("切换为「立即发布」")

        def schedule_on() -> bool:
            return Bilibili._date_visible(page)

        try:
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1200)
            if schedule_on():
                steps.click_sel(page, Bilibili.SEL_SCHEDULE_SWITCH,
                                log=log, what="关闭定时开关")
                page.wait_for_timeout(1500)
            if not schedule_on():
                log.ok("已切换为立即发布")
            else:
                log.warn("定时开关没关掉，请在网页上确认")
        except Exception as exc:
            log.warn(f"切换立即发布失败: {type(exc).__name__}")

    @staticmethod
    def _pick_day(page, day: str) -> bool:
        try:
            return bool(page.evaluate(
                """(d) => {
                    const cells = [...document.querySelectorAll('div.date-picker-body-item')]
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
    def _pick_time(page, value: str, col: int, log: RunLog) -> None:
        try:
            ok = page.evaluate(
                """({v, c}) => {
                    const wraps = document.querySelectorAll('div.time-picker-panel-select-wrp');
                    const wrap = wraps[c];
                    if (!wrap) return false;
                    const el = [...wrap.querySelectorAll('span.time-picker-panel-select-item')]
                        .find(e => e.innerText.trim() === v);
                    if (!el) return false;
                    el.click();
                    return true;
                }""",
                {"v": value, "c": col},
            )
            if not ok:
                log.warn(f"时间选项 {value} 未找到")
        except Exception as exc:
            log.warn(f"选时间失败: {type(exc).__name__}")

