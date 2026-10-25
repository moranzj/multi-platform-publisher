"""图形界面：填参数 → 填好三个平台 → 页面保持打开，由你在网页上提交。

默认「填好并保持页面」，不会自动提交；需要自动提交时切换到另一个选项。
"""
from __future__ import annotations

import datetime
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import __version__

ROOT = Path(__file__).resolve().parent
CLI = ROOT / "cli.py"
CONFIG = ROOT / "config.json"
STATE = ROOT / "gui-state.json"
HISTORY = ROOT / "history.json"
HISTORY_MAX = 50
TIME_PRESETS = ["06:00", "07:00", "08:00", "09:00", "10:00", "12:00",
                "16:00", "17:00", "18:00", "19:00", "20:00", "21:00",
                "22:00", "23:00"]


def child_exe() -> str:
    """pythonw 下 sys.executable 没有控制台，子进程改用 python.exe 才拿得到输出。"""
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        candidate = exe[:-len("pythonw.exe")] + "python.exe"
        if Path(candidate).exists():
            return candidate
    return exe


def load_json(path: Path, default: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def as_text(value, default: str = "") -> str:
    """配置/状态是用户可编辑的，非字符串值不能让 Tk 或 Path 崩掉。"""
    return value if isinstance(value, str) else default


def load_history() -> list[dict]:
    data = load_json(HISTORY, {})
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


def save_history(entries: list[dict]) -> None:
    try:
        HISTORY.write_text(
            json.dumps({"entries": entries[:HISTORY_MAX]}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    except Exception:
        # 历史记录写不进去不影响本次发布，别让 GUI 回调崩掉
        pass


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.q: queue.Queue[str] = queue.Queue()
        self.proc: subprocess.Popen | None = None
        self._closing = False

        root.title(f"多平台视频发布器 v{__version__}")
        # 小屏笔记本（1366x768）放不下 820 高，按屏幕高度自适应
        screen_h = root.winfo_screenheight()
        height = min(820, max(640, screen_h - 90))
        root.geometry(f"860x{height}")
        root.minsize(760, min(700, height))
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass
        ttk.Style().configure(".", font=("Microsoft YaHei UI", 10))

        defaults = load_json(CONFIG, {}).get("defaults")
        if not isinstance(defaults, dict):
            defaults = {}
        state = load_json(STATE, {})

        def state_text(key: str, fallback: str = "") -> str:
            return as_text(state.get(key), as_text(fallback))

        self.v_video = tk.StringVar(value=state_text("video"))
        self.v_cover = tk.StringVar(value=state_text("cover"))
        self.v_title = tk.StringVar(value=state_text("title"))
        self.v_bili_tags = tk.StringVar(
            value=state_text("bili_tags", as_text(defaults.get("bili_tags"))))
        self.v_bili_topic = tk.StringVar(
            value=state_text("bili_topic", as_text(defaults.get("bili_topic"))))
        self.v_ks = tk.StringVar(
            value=state_text("ks_topics", as_text(defaults.get("kuaishou_topics"))))
        self.v_dy = tk.StringVar(
            value=state_text("dy_topics", as_text(defaults.get("douyin_topics"))))
        self.v_desc = tk.StringVar(value=state_text("desc"))
        # 日期永远默认明天：沿用上次的日期会变成过去时间，平台直接拒收
        self.v_date = tk.StringVar(
            value=(datetime.date.today() + datetime.timedelta(days=1)).isoformat())
        when = state_text("when", "schedule")
        self.v_time = tk.StringVar(value=state_text("time") or "06:00")
        self.v_when = tk.StringVar(value=when if when in ("now", "schedule") else "schedule")
        self.c_bili = tk.BooleanVar(value=True)
        self.c_ks = tk.BooleanVar(value=True)
        self.c_dy = tk.BooleanVar(value=True)
        self.mode = tk.StringVar(value="hold")

        self.hist = load_history()
        if self.hist and not self.v_title.get():
            self._fill_from(self.hist[0])

        self._build()
        self._center()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------ 布局
    def _build(self) -> None:
        frm = ttk.Frame(self.root, padding=14)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        def row(r: int, label: str, var: tk.StringVar, hint: str = "", browse: str = "") -> int:
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="e", pady=3, padx=(0, 8))
            ttk.Entry(frm, textvariable=var).grid(row=r, column=1, sticky="ew", pady=3)
            if browse:
                ttk.Button(frm, text="浏览…", width=7,
                           command=lambda: self._browse(var, browse)
                           ).grid(row=r, column=2, padx=(6, 0), pady=3)
            if hint:
                ttk.Label(frm, text=hint, foreground="#888").grid(row=r + 1, column=1, sticky="w")
                return r + 2
            return r + 1

        r = 0
        ttk.Label(frm, text="默认只填表、不提交；填好后页面保持打开，你自己点发布。也可以在下面切换为自动提交。",
                  foreground="#0a7c5a",
                  font=("Microsoft YaHei UI", 10, "bold")
                  ).grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 10))
        r += 1

        hist = ttk.Frame(frm)
        hist.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        ttk.Label(hist, text="历史记录").pack(side="left")
        self.hist_box = ttk.Combobox(hist, state="readonly", width=46)
        self.hist_box.pack(side="left", padx=8)
        self.hist_box.bind("<<ComboboxSelected>>", self._apply_hist)
        ttk.Button(hist, text="存为模板", width=9,
                   command=self._record_hist_now).pack(side="left")
        ttk.Button(hist, text="删除", width=6,
                   command=self._del_hist).pack(side="left", padx=6)
        self._refresh_hist()
        r += 1

        r = row(r, "视频文件", self.v_video, browse="video")
        r = row(r, "封面图片", self.v_cover, "留空则用平台推荐封面", browse="image")
        r = row(r, "标题", self.v_title)
        r = row(r, "B站标签", self.v_bili_tags, "逗号分隔，如 三国杀,桌游棋牌")
        r = row(r, "B站话题", self.v_bili_topic, "参与话题：搜平台现有的话题，逗号/空格分隔")
        r = row(r, "快手话题", self.v_ks, "空格分隔，#可以不写，会自动补：如 三国杀 三国杀锦囊妙会")
        r = row(r, "抖音话题", self.v_dy, "空格分隔，#可以不写，会自动补：如 三国杀 随时随地杀一下")
        r = row(r, "文案", self.v_desc, "留空则用标题（B站简介 / 快手描述 / 抖音作品描述）")

        ttk.Label(frm, text="发布方式").grid(row=r, column=0, sticky="e", pady=3, padx=(0, 8))
        when = ttk.Frame(frm)
        when.grid(row=r, column=1, columnspan=2, sticky="w", pady=3)
        ttk.Radiobutton(when, text="立即发布", value="now", variable=self.v_when,
                        command=self._sync_when).pack(side="left")
        ttk.Radiobutton(when, text="定时发布", value="schedule", variable=self.v_when,
                        command=self._sync_when).pack(side="left", padx=(14, 0))
        r += 1

        ttk.Label(frm, text="定时时间").grid(row=r, column=0, sticky="e", pady=3, padx=(0, 8))
        when2 = ttk.Frame(frm)
        when2.grid(row=r, column=1, columnspan=2, sticky="w", pady=3)
        self.date_entry = ttk.Entry(when2, textvariable=self.v_date, width=13)
        self.date_entry.pack(side="left")
        self.btn_today = ttk.Button(when2, text="今天", width=5,
                                    command=lambda: self._set_day(0))
        self.btn_today.pack(side="left", padx=(5, 0))
        self.btn_tomorrow = ttk.Button(when2, text="明天", width=5,
                                       command=lambda: self._set_day(1))
        self.btn_tomorrow.pack(side="left", padx=(5, 12))
        ttk.Label(when2, text="时间").pack(side="left")
        self.time_box = ttk.Combobox(when2, textvariable=self.v_time, width=8,
                                     values=TIME_PRESETS, state="normal")
        self.time_box.pack(side="left", padx=4)
        ttk.Label(when2, text="（下拉选，也可直接改）", foreground="#888").pack(side="left", padx=4)
        self._when_widgets = [self.date_entry, self.btn_today,
                              self.btn_tomorrow, self.time_box]
        self._sync_when()
        r += 1

        plat = ttk.LabelFrame(frm, text="发布到", padding=(12, 8))
        plat.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        ttk.Checkbutton(plat, text="B站", variable=self.c_bili).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(plat, text="快手", variable=self.c_ks).pack(side="left", padx=(0, 18))
        ttk.Checkbutton(plat, text="抖音", variable=self.c_dy).pack(side="left")
        r += 1

        mode = ttk.LabelFrame(frm, text="跑完之后", padding=(12, 8))
        mode.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        ttk.Radiobutton(mode, text="填好就停，页面保持打开，我自己点发布（推荐）",
                        variable=self.mode, value="hold").pack(anchor="w")
        ttk.Radiobutton(mode, text="填好并自动提交",
                        variable=self.mode, value="auto").pack(anchor="w", pady=(4, 0))
        r += 1

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=3, sticky="ew", pady=(2, 8))
        self.btn_run = ttk.Button(btns, text="开始填表", command=self.run)
        self.btn_run.pack(side="left")
        self.btn_stop = ttk.Button(btns, text="停止", width=6, state="disabled",
                                   command=self.stop)
        self.btn_stop.pack(side="left", padx=8)
        ttk.Button(btns, text="清空日志", command=self.clear_log).pack(side="left")
        ttk.Button(btns, text="打开日志目录", command=self.open_logs).pack(side="left", padx=8)
        ttk.Button(btns, text="重新登录", command=self.relogin).pack(side="left")
        self.v_status = tk.StringVar(value="就绪")
        ttk.Label(btns, textvariable=self.v_status, foreground="#666").pack(side="right")
        r += 1

        frm.rowconfigure(r, weight=1)
        box = ttk.Frame(frm)
        box.grid(row=r, column=0, columnspan=3, sticky="nsew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        self.log = tk.Text(box, wrap="word", bg="#1e1e1e", fg="#7CFC00",
                           insertbackground="#7CFC00", font=("Consolas", 9),
                           relief="flat", padx=8, pady=6)
        self.log.grid(row=0, column=0, sticky="nsew")
        for tag, color in (("ok", "#7CFC00"), ("warn", "#FFC857"),
                           ("err", "#FF6B6B"), ("stage", "#5CC8FF"),
                           ("step", "#9FB0B8")):
            self.log.tag_configure(tag, foreground=color)
        sb = ttk.Scrollbar(box, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=sb.set)

    def _center(self) -> None:
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2 - 20
        self.root.geometry(f"+{x}+{y}")

    def _sync_when(self) -> None:
        """立即发布时，把日期/时间控件灰掉，避免误填。"""
        widgets = getattr(self, "_when_widgets", None)
        if not widgets:
            return
        state = "normal" if self.v_when.get() == "schedule" else "disabled"
        for w in widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _set_day(self, offset: int) -> None:
        self.v_date.set(
            (datetime.date.today() + datetime.timedelta(days=offset)).isoformat())

    # ------------------------------------------------------------ 动作
    def _browse(self, var: tk.StringVar, kind: str) -> None:
        if kind == "video":
            types = [("视频", "*.mp4 *.mov *.mkv *.flv *.avi *.wmv *.webm *.m4v"),
                     ("全部", "*.*")]
        else:
            types = [("图片", "*.jpg *.jpeg *.png *.webp *.bmp"), ("全部", "*.*")]
        path = filedialog.askopenfilename(filetypes=types)
        if path:
            var.set(path)

    def clear_log(self) -> None:
        self.log.delete("1.0", "end")

    def open_logs(self) -> None:
        try:
            d = ROOT / "logs"
            d.mkdir(exist_ok=True)
            os.startfile(d)  # noqa: S606
        except Exception as exc:
            messagebox.showerror("打开失败", f"无法打开日志目录：\n{exc}")

    def relogin(self) -> None:
        try:
            subprocess.Popen([child_exe(), str(CLI), "login"], cwd=str(ROOT),
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
        except Exception as exc:
            messagebox.showerror("启动失败", f"无法启动登录窗口：\n{exc}")

    def append(self, text: str) -> None:
        tag = ""
        if "[OK]" in text:
            tag = "ok"
        elif "[!!]" in text:
            tag = "warn"
        elif "[XX]" in text:
            tag = "err"
        elif "====" in text:
            tag = "stage"
        elif "[..]" in text:
            tag = "step"
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")

    def _save_state(self) -> None:
        try:
            STATE.write_text(json.dumps({
                "video": self.v_video.get().strip(),
                "cover": self.v_cover.get().strip(),
                "title": self.v_title.get().strip(),
                "bili_tags": self.v_bili_tags.get().strip(),
                "bili_topic": self.v_bili_topic.get().strip(),
                "ks_topics": self.v_ks.get().strip(),
                "dy_topics": self.v_dy.get().strip(),
                "desc": self.v_desc.get().strip(),
                "time": self.v_time.get().strip(),
                "when": self.v_when.get(),
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            # 状态保存失败不影响本次任务
            pass

    # ------------------------------------------------------------ 历史模板
    def _snapshot(self) -> dict:
        from datetime import datetime
        return {
            "saved": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "video": self.v_video.get().strip(),
            "cover": self.v_cover.get().strip(),
            "title": self.v_title.get().strip(),
            "desc": self.v_desc.get().strip(),
            "bili_tags": self.v_bili_tags.get().strip(),
            "bili_topic": self.v_bili_topic.get().strip(),
            "ks_topics": self.v_ks.get().strip(),
            "dy_topics": self.v_dy.get().strip(),
            "time": self.v_time.get().strip(),
            "when": self.v_when.get(),
        }

    @staticmethod
    def _hist_key(entry: dict) -> tuple:
        return (entry.get("title", ""), entry.get("desc", ""),
                entry.get("bili_tags", ""), entry.get("bili_topic", ""),
                entry.get("ks_topics", ""), entry.get("dy_topics", ""))

    def _fill_from(self, entry: dict) -> None:
        self.v_title.set(as_text(entry.get("title")))
        self.v_desc.set(as_text(entry.get("desc")))
        self.v_bili_tags.set(as_text(entry.get("bili_tags")))
        self.v_bili_topic.set(as_text(entry.get("bili_topic")))
        self.v_ks.set(as_text(entry.get("ks_topics")))
        self.v_dy.set(as_text(entry.get("dy_topics")))
        time_value = as_text(entry.get("time"))
        if time_value:
            self.v_time.set(time_value)
        when = as_text(entry.get("when"), "schedule")
        self.v_when.set(when if when in ("now", "schedule") else "schedule")
        if hasattr(self, "_when_widgets"):
            self._sync_when()
        # 视频和封面只有文件还在时才覆盖，避免选一堆失效路径
        for field, var in (("video", self.v_video), ("cover", self.v_cover)):
            path = as_text(entry.get(field))
            try:
                if path and Path(path).is_file():
                    var.set(path)
            except Exception:
                pass

    def _refresh_hist(self) -> None:
        self.hist_box.configure(
            values=[f"{e.get('saved', '')} · {e.get('title', '(无标题)')}"
                    for e in self.hist])
        self.hist_box.set("")

    def _record_hist(self) -> None:
        entry = self._snapshot()
        if not entry["title"]:
            return
        key = self._hist_key(entry)
        self.hist = [e for e in self.hist if self._hist_key(e) != key]
        self.hist.insert(0, entry)
        self.hist = self.hist[:HISTORY_MAX]
        save_history(self.hist)
        self._refresh_hist()

    def _record_hist_now(self) -> None:
        if not self.v_title.get().strip():
            messagebox.showwarning("提示", "标题是空的，没存")
            return
        self._record_hist()
        messagebox.showinfo("已保存", "已存为模板，下次从「历史记录」下拉里选")

    def _apply_hist(self, _event=None) -> None:
        i = self.hist_box.current()
        if 0 <= i < len(self.hist):
            self._fill_from(self.hist[i])

    def _del_hist(self) -> None:
        i = self.hist_box.current()
        if not (0 <= i < len(self.hist)):
            messagebox.showinfo("提示", "先在下拉列表里选中一条")
            return
        if not messagebox.askyesno("删除", f"删除这条模板？\n{self.hist[i].get('title', '')}"):
            return
        del self.hist[i]
        save_history(self.hist)
        self._refresh_hist()

    def _cmd(self, video: str, title: str, plats: list[str]) -> list[str]:
        cmd = [child_exe(), str(CLI), "publish",
               "--video", video, "--title", title,
               "--platforms", ",".join(plats)]
        if self.v_when.get() == "now":
            cmd.append("--now")
        else:
            cmd += ["--time", self.v_time.get().strip() or "06:00"]
            date = self.v_date.get().strip()
            if date:
                cmd += ["--date", date]
        for flag, value in [
            ("--cover", self.v_cover.get().strip()),
            ("--desc", self.v_desc.get().strip()),
            ("--bili-tags", self.v_bili_tags.get().strip()),
            ("--bili-topic", self.v_bili_topic.get().strip()),
            ("--ks-topics", self.v_ks.get().strip()),
            ("--dy-topics", self.v_dy.get().strip()),
        ]:
            if value:
                cmd += [flag, value]
        cmd.append("--hold" if self.mode.get() == "hold" else "--auto")
        cmd.append("--dump")          # 留一份 DOM 快照，改版时好定位选择器
        return cmd

    def run(self) -> None:
        if self.proc and self.proc.poll() is None:
            messagebox.showinfo("提示", "上一轮还在跑，等它结束")
            return

        video = self.v_video.get().strip()
        title = self.v_title.get().strip()
        if not video or not Path(video).is_file():
            messagebox.showwarning("提示", "请选择存在的视频文件")
            return
        if not title:
            messagebox.showwarning("提示", "请填写标题")
            return
        cover = self.v_cover.get().strip()
        if cover and not Path(cover).is_file():
            messagebox.showwarning("提示", "封面文件不存在，请重新选择")
            return
        if self.v_when.get() == "schedule":
            try:
                datetime.datetime.strptime(
                    f"{self.v_date.get().strip()} {self.v_time.get().strip()}",
                    "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showwarning(
                    "提示", "日期或时间格式不对。\n日期写 2026-10-22，时间写 06:00")
                return
        plats = [k for k, v in (("bili", self.c_bili), ("kuaishou", self.c_ks),
                                ("douyin", self.c_dy)) if v.get()]
        if not plats:
            messagebox.showwarning("提示", "至少勾选一个平台")
            return

        if self.mode.get() == "auto":
            if not messagebox.askyesno(
                    "自动提交",
                    "填完会直接提交，不再给你逐个平台核对的机会。\n\n"
                    "确定要自动提交吗？"):
                return

        self._save_state()
        self._record_hist()

        cmd = self._cmd(video, title, plats)

        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

        self.clear_log()
        self.append(">>> " + " ".join(cmd[1:]))
        self.append("")
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._t0 = time.time()
        self.v_status.set("启动中…")

        try:
            self.proc = subprocess.Popen(
                cmd, cwd=str(ROOT), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as exc:
            self.btn_run.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.v_status.set("启动失败")
            messagebox.showerror("启动失败", f"无法启动发布进程：\n{exc}")
            return
        threading.Thread(target=self._pump, daemon=True).start()
        self.root.after(150, self._drain)
        self._tick()

    def _tick(self) -> None:
        if self._closing or not (self.proc and self.proc.poll() is None):
            return
        sec = int(time.time() - self._t0)
        self.v_status.set(f"运行中  {sec // 60:02d}:{sec % 60:02d}")
        try:
            self.root.after(1000, self._tick)
        except tk.TclError:
            pass

    def stop(self) -> None:
        if not (self.proc and self.proc.poll() is None):
            return
        if not messagebox.askyesno(
                "停止",
                "停止会连浏览器一起关掉，页面上已经填好的内容会丢失。\n\n确定停止吗？"):
            return
        self.v_status.set("正在停止…")
        subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       capture_output=True)

    def _pump(self) -> None:
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            self.q.put(line.rstrip("\n"))
        self.q.put("__DONE__")

    def _drain(self) -> None:
        if self._closing:
            return
        try:
            while True:
                line = self.q.get_nowait()
                if line == "__DONE__":
                    code = self.proc.poll() if self.proc else None
                    sec = int(time.time() - self._t0) if hasattr(self, "_t0") else 0
                    spent = f"{sec // 60:02d}:{sec % 60:02d}"
                    self.append("")
                    self.append(f">>> 结束，退出码 {code}，用时 {spent}")
                    self.btn_run.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                    self.v_status.set(f"已结束  用时 {spent}")
                    self.proc = None
                    return
                self.append(line)
        except queue.Empty:
            pass
        try:
            self.root.after(150, self._drain)
        except tk.TclError:
            pass

    def _on_close(self) -> None:
        if self.proc and self.proc.poll() is None:
            ok = messagebox.askyesno(
                "任务还在跑",
                "发布任务还没结束。关掉这个窗口不会停止它，"
                "浏览器和后台进程会继续运行。\n\n确定关闭吗？")
            if not ok:
                return
        self._closing = True
        self.root.destroy()


def main() -> None:
    try:
        root = tk.Tk()
        App(root)
        root.mainloop()
    except Exception:
        import traceback

        crash = ROOT / "logs" / "gui-crash.log"
        try:
            crash.parent.mkdir(parents=True, exist_ok=True)
            crash.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                f"图形界面启动失败。\n\n详情见：\n{crash}",
                "多平台发布器",
                0x10,
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
