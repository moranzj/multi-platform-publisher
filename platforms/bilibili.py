"""B站投稿适配器。

选择器来自旧版 PowerShell 实现的实测记录（B站投稿页是 micro-app，
可访问性树不暴露，只能靠 CSS）。这里改成 Playwright 的直连写法。
"""
from __future__ import annotations

from core import steps
from core.log import RunLog
from .base import Job, Platform, Result


class Bilibili(Platform):
    key = "bili"
    name = "B站"
    url = "https://member.bilibili.com/platform/upload/video/frame"
    success_patterns = ("投稿成功", "发布成功", "稿件投递成功")

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
        if not steps.fill_input(page, self.SEL_TITLE, job.title, log=log):
            return Result(self.name, False, "标题填不进去")
        steps.pause(0.5, 1.0)

        if job.bili_tags:
            self._fill_tags(page, job.bili_tags, log)

        if job.bili_topic:
            self._add_topic(page, job.bili_topic, log)

        if job.desc:
            steps.fill_editable(page, self.SEL_DESC, job.desc, log=log)
        steps.shot(page, log, "bili-03-text")

        # 3) 封面（没指定就用「系统推荐封面」第一张）
        if job.cover:
            self._cover(page, job.cover, log)
        else:
            self._pick_recommend(page, log)
        steps.shot(page, log, "bili-04-cover")

        # 4) 定时发布
        self._schedule(page, job, log)
        steps.shot(page, log, "bili-05-scheduled")
        log.ok("B站 填写完成，等待提交")
        return None

    def submit(self, page, job: Job, log: RunLog) -> Result:
        log.stage("B站 提交")
        log.step("点击「立即投稿」")
        if not steps.click_sel(page, self.SEL_SUBMIT, log=log, what="立即投稿"):
            return Result(self.name, False, "点不到投稿按钮")
        steps.pause(2, 3)
        steps.click_text(page, "确认投稿", timeout=4000, log=log)
        steps.click_text(page, "确定", timeout=3000, log=log)

        ok = steps.wait_success(page, self.success_patterns, log=log)
        steps.shot(page, log, "bili-05-result")
        return Result(self.name, True, "已提交" if ok else "已提交（未见成功提示，请核对）")

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

    @staticmethod
    def _pick_recommend(page, log: RunLog) -> bool:
        """用「系统推荐封面」里的第一张。

        B站 封面区下面有一排「以下为系统推荐封面」缩略图，
        点第一张就是 B站 自己推荐的那张（不是视频首帧）。
        """
        try:
            cards = page.locator("div.img-item-box.img-item-cover")
            if cards.count() == 0:
                # 新版页面默认就选中第一张，不需要再点
                if steps.visible(page, "系统默认选中第一张为封面", exact=False):
                    log.ok("B站 已默认选中第一张推荐封面")
                    return True
                log.warn("没找到 B站 系统推荐封面，保留默认")
                return False
            cards.first.scroll_into_view_if_needed(timeout=3000)
            cards.first.click(timeout=5000)
            page.wait_for_timeout(1500)
            log.ok("已用 B站 系统推荐封面")
            return True
        except Exception as exc:
            log.warn(f"选推荐封面失败: {type(exc).__name__}")
            return False

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
            for _ in range(4):
                if not self._cover_editor_open(page):
                    break
                steps.click_modal_done(page, log)
                page.wait_for_timeout(2500)
                if steps.visible(page, "确认同步", exact=False):
                    steps.click_text(page, "确认同步", timeout=2500, log=log)
                page.wait_for_timeout(1500)

            if self._cover_editor_open(page):
                log.warn("封面弹窗仍未关闭，Esc 兜底")
                steps.dismiss_overlays(
                    page, log,
                    hints=("封面制作", "上传封面", "设置封面", "确认同步"))
            else:
                log.ok("封面已设置")
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

    def _schedule(self, page, job: Job, log: RunLog) -> None:
        if job.immediate:
            self._set_immediate(page, log)
            return
        log.step(f"设定时发布 {job.date} {job.time}")
        try:
            steps.dismiss_overlays(page, log)
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1500)

            if not steps.click_sel(page, self.SEL_SCHEDULE_SWITCH, log=log, what="定时发布开关"):
                log.warn("找不到定时开关")
                return
            page.wait_for_timeout(3000)
            if not page.locator(self.SEL_DATE_INPUT).count():
                steps.click_sel(page, self.SEL_SCHEDULE_SWITCH, log=log, what="定时开关(重试)")
                page.wait_for_timeout(3000)

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
            log.ok("定时已设置")
        except Exception as exc:
            log.warn(f"定时设置失败: {type(exc).__name__}")

    @staticmethod
    def _set_immediate(page, log: RunLog) -> None:
        """B站的定时是一个开关：开着就点一下关掉，日期框消失即为立即发布。"""
        log.step("切换为「立即发布」")

        def schedule_on() -> bool:
            loc = page.locator(Bilibili.SEL_DATE_INPUT)
            try:
                for i in range(min(loc.count(), 3)):
                    if loc.nth(i).is_visible():
                        return True
            except Exception:
                pass
            return False

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

