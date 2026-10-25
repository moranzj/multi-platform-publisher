"""抖音创作者中心适配器。

抖音的 DOM 改版频率最高，因此这里所有字段都走「多选择器兜底」策略，
任一关键步骤失败会立即返回并留下截图，而不是带着错误配置硬提交。
"""
from __future__ import annotations

from core import steps
from core.log import RunLog
from .base import Job, Platform, Result

TITLE_SELECTORS = (
    "input[placeholder*='作品标题']",
    "textarea[placeholder*='作品标题']",
    "input[placeholder*='标题']",
)
DESC_SELECTORS = (
    "div[contenteditable='true'][data-placeholder*='话题']",
    "div[contenteditable='true']",
)
PUBLISH_BUTTONS = (
    "button:has-text('发布')",
    "div[role='button']:has-text('发布')",
)


class Douyin(Platform):
    key = "douyin"
    name = "抖音"
    url = "https://creator.douyin.com/creator-micro/content/post/video"
    success_patterns = ("发布成功", "作品发布成功", "提交成功")

    def fill(self, page, job: Job, log: RunLog) -> Result | None:
        log.stage("抖音 开始")
        page.goto(self.url, wait_until="domcontentloaded", timeout=60_000)
        steps.pause(3, 5)
        steps.close_popups(page, log)
        steps.shot(page, log, "douyin-01-open")

        blocked = self.guard_login(page, log)
        if blocked:
            return blocked

        # 1) 视频
        if not steps.set_files_by_kind(page, "video", job.video, log, click_target="上传视频"):
            return Result(self.name, False, "找不到视频上传入口")
        steps.pause(2, 3)
        steps.wait_upload(page, log, steps.size_mb(job.video))
        steps.shot(page, log, "douyin-02-uploaded")

        # 2) 标题
        if not self._fill_first(page, TITLE_SELECTORS, job.title, log, "标题"):
            return Result(self.name, False, "标题填不进去")
        steps.pause(0.5, 1.0)

        # 3) 话题（必须走真实键盘输入，否则不会生成话题胶囊）
        #    文案和标题不同时，也写进作品描述，别让用户填的文案白填
        if job.douyin_topics or (job.desc and job.desc != job.title):
            self._fill_topics(page, job, log)
        steps.shot(page, log, "douyin-03-text")

        # 4) 封面（没指定就点平台推荐的第一张）
        self._cover(page, job.cover, log)
        steps.shot(page, log, "douyin-04-cover")

        # 5) 定时
        self._schedule(page, job, log)
        steps.shot(page, log, "douyin-05-scheduled")
        log.ok("抖音 填写完成，等待提交")
        return None

    def submit(self, page, job: Job, log: RunLog) -> Result:
        log.stage("抖音 提交")
        log.step("点击「发布」")
        if not self._click_publish(page, log):
            return Result(self.name, False, "点不到发布按钮")
        steps.pause(2, 3)
        steps.click_text(page, "确认发布", timeout=3000, log=log)

        ok = steps.wait_success(page, self.success_patterns, log=log)
        steps.shot(page, log, "douyin-05-result")
        return Result(self.name, True, "已提交" if ok else "已提交（未见成功提示，请核对）")

    # ------------------------------------------------------------------
    def _fill_first(self, page, selectors, value: str, log: RunLog, what: str) -> bool:
        for sel in selectors:
            try:
                if page.locator(sel).count() == 0:
                    continue
                if steps.fill_input(page, sel, value, timeout=6000, log=log):
                    return True
            except Exception:
                continue
        log.warn(f"{what}：所有选择器都失效")
        return False

    def _fill_topics(self, page, job: Job, log: RunLog) -> None:
        tags = steps.normalize_topics(job.douyin_topics)
        desc = job.desc if job.desc and job.desc != job.title else ""
        if not tags and not desc:
            return
        target = None
        for sel in DESC_SELECTORS:
            if page.locator(sel).count():
                target = page.locator(sel).last
                break
        if target is None:
            log.warn("找不到描述编辑器，文案/话题跳过")
            return
        try:
            target.click()
            steps.pause(0.4, 0.8)
            # 抖音会恢复上次没发出去的草稿，描述里可能已经有同样的话题。
            # 先清空编辑器，否则会变成两遍话题。
            page.keyboard.press("Control+A")
            page.keyboard.press("Delete")
            steps.pause(0.3, 0.6)
            if desc:
                page.keyboard.type(desc)
                steps.pause(0.3, 0.6)
                page.keyboard.press("Space")
                steps.pause(0.3, 0.6)
                log.step("文案已写入作品描述")
            good, bad = [], []
            for tag in tags:
                page.keyboard.type(tag)
                steps.pause(0.4, 0.9)
                page.keyboard.press("Space")
                steps.pause(0.5, 0.9)
                if self._is_chip(page, tag):
                    good.append(tag)
                    continue
                # 没变成胶囊，多半平台里没有同名话题，试试推荐位里的那个
                if self._pick_suggestion(page, tag) and self._is_chip(page, tag):
                    good.append(tag)
                else:
                    bad.append(tag)
            if good:
                log.ok("话题已生效：" + " ".join(good))
            if bad:
                log.warn("没被识别成话题（平台里可能没有同名话题）：" + " ".join(bad))
        except Exception as exc:
            log.warn(f"描述/话题输入失败: {type(exc).__name__}")

    @staticmethod
    def _is_chip(page, tag: str) -> bool:
        """话题胶囊是 contenteditable=false 的 span，普通文字不算。"""
        try:
            return bool(page.evaluate(
                """(t) => {
                    const want = [t, t.replace(/^#/, '')];
                    return [...document.querySelectorAll("span[contenteditable='false']")]
                        .some(e => e.offsetParent
                                   && want.includes((e.innerText || '').trim()));
                }""",
                tag,
            ))
        except Exception:
            return False

    @staticmethod
    def _pick_suggestion(page, tag: str) -> bool:
        """在平台给的推荐话题里点同名的那个。"""
        try:
            return bool(page.evaluate(
                """(t) => {
                    const want = [t, t.replace(/^#/, '')];
                    const el = [...document.querySelectorAll('span,div,a,button')]
                        .filter(e => e.offsetParent && e.children.length === 0
                                     && want.includes((e.innerText || '').trim())
                                     && (e.innerText || '').trim().length < 24)
                        .pop();
                    if (!el) return false;
                    el.click();
                    return true;
                }""",
                tag,
            ))
        except Exception:
            return False

    def _cover(self, page, cover: str, log: RunLog) -> None:
        """抖音封面：没指定就用「Ai智能推荐封面」第一张，指定了才走上传。

        上传的坑：编辑器默认用视频首帧，直接塞页面顶部的 input 不生效；
        必须点「选择封面」打开面板，再塞 selectArea 里的 semi-upload input。
        """
        log.step("上传封面" if cover else "未指定封面，用抖音推荐的封面")
        try:
            if not cover:
                self._pick_recommend(page, log)
                return

            if not steps.visible(page, "设置横封面", exact=False):
                self._open_cover_editor(page, log)
                for _ in range(6):
                    if steps.visible(page, "设置横封面", exact=False):
                        break
                    page.wait_for_timeout(1000)

            if not steps.visible(page, "设置横封面", exact=False):
                self._log_cover_texts(page, log)
                log.warn("封面编辑器没打开，跳过封面")
                return
            log.step("封面编辑器已打开")

            # 竖封面引导弹窗，有就跳过（大多数时候没有，别白等）
            if steps.visible(page, "暂不设置", exact=True):
                steps.click_text(page, "暂不设置", timeout=2500, log=log)
                page.wait_for_timeout(600)

            if not self._pick_new_cover(page, cover, log):
                log.warn("封面没传上，抖音会沿用视频首帧")
            page.wait_for_timeout(3000)

            # 完成可能被引导弹窗挡住，循环点直到编辑器消失
            for _ in range(4):
                if not steps.visible(page, "设置横封面", exact=False):
                    break
                steps.click_modal_done(page, log)
                page.wait_for_timeout(2000)
                if steps.visible(page, "暂不设置", exact=True):
                    steps.click_text(page, "暂不设置", timeout=1200, log=log)
                page.wait_for_timeout(700)

            if steps.visible(page, "设置横封面", exact=False):
                log.warn("封面编辑器未关闭，Esc 兜底")
                steps.dismiss_overlays(page, log, hints=("设置横封面", "设置竖封面"))
            else:
                log.ok("封面已设置")
        except Exception as exc:
            log.warn(f"封面流程失败: {type(exc).__name__}")

    @staticmethod
    def _pick_recommend(page, log: RunLog) -> bool:
        """「Ai智能推荐封面」点第一张，弹窗里确认应用。"""
        try:
            clicked = page.evaluate("""() => {
                const box = document.querySelector("[class*='recommendContainer']");
                if (!box) return false;
                const imgs = [...box.querySelectorAll('img')]
                    .filter(e => e.offsetParent && e.getBoundingClientRect().width > 40);
                if (!imgs.length) return false;
                imgs[0].click();
                return true;
            }""")
            if not clicked:
                log.warn("找不到抖音的推荐封面，保留视频首帧")
                return False
            page.wait_for_timeout(1200)
            if steps.visible(page, "是否确认应用此封面", exact=False):
                steps.click_text(page, "确定", timeout=3000, log=log)
                page.wait_for_timeout(1500)
            log.ok("已应用抖音推荐封面")
            return True
        except Exception as exc:
            log.warn(f"应用推荐封面失败: {type(exc).__name__}")
            return False

    @staticmethod
    def _open_cover_editor(page, log: RunLog) -> bool:
        """打开封面编辑器。

        入口平时藏着：hover 封面块才浮出「编辑封面」，直接点缩略图不一定有反应。
        """
        try:
            ctrl = page.locator("div[class*='coverControl']").first
            if ctrl.count():
                try:
                    ctrl.scroll_into_view_if_needed(timeout=3000)
                    ctrl.hover(timeout=4000)
                    page.wait_for_timeout(800)
                except Exception:
                    pass
                if steps.click_text(page, "编辑封面", timeout=2500, log=log):
                    return True
                try:
                    ctrl.click(timeout=6000)
                    log.step("点击封面控件")
                    return True
                except Exception as exc:
                    log.warn(f"点封面控件失败: {type(exc).__name__}")
        except Exception:
            pass
        return steps.click_text(page, "选择封面", timeout=6000, exact=False, log=log)

    @staticmethod
    def _log_cover_texts(page, log: RunLog) -> None:
        """编辑器没打开时，把可见的「封面/上传」相关文本记下来，方便下次对准。"""
        try:
            texts = page.evaluate(
                """() => [...document.querySelectorAll('button,span,div,label')]
                    .filter(e => e.offsetParent && /封面|上传|编辑/.test(e.innerText || ''))
                    .map(e => (e.innerText || '').trim())
                    .filter(t => t && t.length < 16)"""
            )
            uniq = list(dict.fromkeys(texts))[:12]
            log.info("可见封面相关文本：" + " | ".join(uniq))
        except Exception:
            pass

    def _pick_new_cover(self, page, cover: str, log: RunLog) -> bool:
        """抖音封面：点横封面的「选择封面」→ 面板里的上传区 → 塞图 → 完成。

        页面顶部那个 upload-btn-input 是「头像/背景」一类的入口，塞了没用；
        真正生效的是面板里 selectArea 下的 semi-upload-hidden-input。
        """
        if self._click_horizontal_pick(page):
            log.step("打开「选择封面」面板")
        else:
            log.warn("没点到横封面的「选择封面」")

        for _ in range(6):
            if steps.visible(page, "点击上传文件或拖拽文件到这里", exact=False):
                break
            page.wait_for_timeout(800)

        if not steps.visible(page, "点击上传文件或拖拽文件到这里", exact=False):
            self._log_cover_texts(page, log)
            log.warn("封面面板没打开，跳过上传")
            return False

        if not self._set_cover_file(page, cover, log):
            log.warn("找不到封面面板里的文件输入框")
            return False

        log.step("封面图已注入上传区")
        page.wait_for_timeout(3000)
        return True

    @staticmethod
    def _set_cover_file(page, cover: str, log: RunLog) -> bool:
        """只认「上传区」里的那个 input，别碰顶部和 AI 推荐列表里的。"""
        try:
            handles = page.query_selector_all("input[type=file]")
            for h in handles:
                cls = h.get_attribute("class") or ""
                if "semi-upload" not in cls:
                    continue
                try:
                    inside = page.evaluate(
                        "(el) => !!el.closest(\"[class*='selectArea']\")", h)
                except Exception:
                    continue
                if inside:
                    h.set_input_files(cover)
                    return True
        except Exception as exc:
            log.warn(f"注入封面失败: {type(exc).__name__}")
        return False

    @staticmethod
    def _click_horizontal_pick(page) -> bool:
        """只在「横封面4:3」那个槽位里点「选择封面」，别点到竖封面的。"""
        try:
            return bool(page.evaluate(
                """() => {
                    const nodes = [...document.querySelectorAll('div')]
                        .filter(e => e.offsetParent && /横封面/.test(e.innerText || ''));
                    for (const n of nodes.reverse()) {
                        const btn = [...n.querySelectorAll('*')]
                            .find(e => (e.innerText || '').trim() === '选择封面' && e.offsetParent);
                        if (btn) { btn.click(); return true; }
                    }
                    return false;
                }"""
            ))
        except Exception:
            return False

    def _schedule(self, page, job: Job, log: RunLog) -> None:
        if job.immediate:
            self._set_immediate(page, log)
            return
        log.step(f"设定时发布 {job.date} {job.time}")
        try:
            steps.dismiss_overlays(page, log, hints=("上传新封面", "封面制作"))
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1200)

            clicked = page.evaluate("""() => {
              const lab = [...document.querySelectorAll('label')]
                  .find(e => (e.innerText || '').trim() === '定时发布');
              if (lab) { lab.click(); return true; }
              const span = [...document.querySelectorAll('span')]
                  .find(e => (e.innerText || '').trim() === '定时发布');
              if (span) { span.click(); return true; }
              return false;
            }""")
            if clicked:
                log.step("已选「定时发布」")
            else:
                log.warn("找不到定时发布选项")
                return
            page.wait_for_timeout(2000)

            # 面板有时要等两三秒才挂出来；等不到就再点一次（可能刚才点空了）
            date_sels = (
                "input[placeholder*='日期和时间']",
                "input[placeholder*='选择日期']",
                "input[placeholder*='日期']",
            )

            def find_input():
                for sel in date_sels:
                    loc = page.locator(sel).last
                    try:
                        if loc.count() and loc.is_visible():
                            return loc
                    except Exception:
                        continue
                return None

            inp = None
            for round_ in range(3):
                for _ in range(10):          # 每轮最多等 5 秒
                    inp = find_input()
                    if inp is not None:
                        break
                    page.wait_for_timeout(500)
                if inp is not None:
                    break
                if round_ == 0:
                    log.warn("定时面板没出来，再点一次「定时发布」")
                    page.evaluate("""() => {
                      const lab = [...document.querySelectorAll('label')]
                          .find(e => (e.innerText || '').trim() === '定时发布');
                      if (lab) lab.click();
                    }""")
                page.wait_for_timeout(1000)

            if inp is None:
                log.warn("日期时间输入框没找到，定时没设上，请在网页上手动确认")
                return

            # 抖音用的是 Semi Design 日期选择器，`input.value = ...` 只改显示值，
            # 表单状态根本没变（发出去还是「立即发布」）。必须用真实键盘输入 + 回车，
            # 让组件自己解析并提交。
            try:
                hh, mm = (int(x) for x in job.time.split(":")[:2])
            except Exception:
                hh, mm = 6, 0
            target = f"{job.date} {hh:02d}:{mm:02d}"

            filled = False
            for _attempt in range(2):
                try:
                    inp.scroll_into_view_if_needed(timeout=3000)
                    inp.click(timeout=5000)
                    page.wait_for_timeout(700)
                    page.keyboard.press("Control+A")
                    page.keyboard.type(target, delay=35)
                    page.wait_for_timeout(300)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1200)
                except Exception as exc:
                    log.warn(f"写日期时间失败: {type(exc).__name__}")
                    inp = find_input() or inp
                    continue
                cur = (inp.input_value() or "").strip()
                if cur == target:
                    filled = True
                    break
                log.warn(f"写入后是「{cur}」，重试")
                inp = find_input() or inp

            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            try:
                cur = (page.evaluate(
                    """() => {
                        const i = [...document.querySelectorAll('input')]
                            .find(e => /日期/.test(e.placeholder || ''));
                        return i ? i.value : '';
                    }""") or "").strip()
            except Exception:
                cur = ""
            if filled and cur == target:
                log.ok(f"定时已设置（{target}）")
            else:
                log.warn(
                    f"定时没写进去，当前显示「{cur or '（读不到）'}」，"
                    "请在网页上手动确认")
        except Exception as exc:
            log.warn(f"定时设置失败: {type(exc).__name__}")

    @staticmethod
    def _set_immediate(page, log: RunLog) -> None:
        """切到「立即发布」，并确认日期时间框真的收起来了。"""
        log.step("切换为「立即发布」")
        try:
            clicked = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('label,span,div')]
                        .filter(e => e.offsetParent && (e.innerText || '').trim() === '立即发布')
                        .pop();
                    if (!el) return false;
                    el.click();
                    return true;
                }"""
            )
            if not clicked:
                log.warn("找不到「立即发布」选项，保持平台默认")
                return
            page.wait_for_timeout(1200)
            gone = page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('input')]
                        .find(e => (e.placeholder || '').includes('日期和时间'));
                    return !(el && el.offsetParent);
                }"""
            )
            if gone:
                log.ok("已切换为立即发布")
            else:
                log.warn("点了「立即发布」但时间框还在，请在网页上确认")
        except Exception as exc:
            log.warn(f"切换立即发布失败: {type(exc).__name__}")

    def _click_publish(self, page, log: RunLog) -> bool:
        for sel in PUBLISH_BUTTONS:
            try:
                loc = page.locator(sel).last
                if not loc.count():
                    continue
                loc.scroll_into_view_if_needed(timeout=3000)
                loc.click(timeout=8000)
                log.step("点击「发布」")
                return True
            except Exception:
                continue
        # 最后兜底：按文本点
        return steps.click_text(page, "发布", timeout=5000, log=log)

