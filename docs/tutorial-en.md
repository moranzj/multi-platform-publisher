# Multi-Platform Video Publisher · Step-by-Step Tutorial

> From zero to published: download → log in → fill the form once → press “Publish” yourself. About 10 minutes in total.
>
> Other languages: [简体中文](tutorial-zh.md)

---

## What does this tool do?

One video, three platforms — Bilibili, Kuaishou, Douyin (Chinese TikTok). On each one you have to: open the web upload page → log in → upload the video → type the title → type the description → add hashtags → set the cover → (maybe schedule it). **The same information, three times, dozens of clicks.**

This tool automates all of it: **you fill the form once, and it fills in all three publishing pages for you** — video upload, title, description, hashtags, cover, scheduling, everything in place. The final “Publish” button is left to you, which keeps your account safer.

![Main window](images/app-form.png)

---

## Step 1: Download

**Option A: portable exe (recommended, no Python needed)**

1. Open the [Releases page](https://github.com/moranzj/multi-platform-publisher/releases/latest) and download `multi-platform-publisher-<version>-exe.zip`.
2. Unzip it into any **writable** folder (e.g. `D:\multi-platform-publisher`). Do not put it in Program Files (the app writes its config and logs inside its own folder).
3. Double-click **`多平台发布器.exe`**. Requirement: Chrome or Edge installed (Windows 10/11 usually ships with Edge).

> The exe is not code-signed, so some antivirus tools may flag it — a common false positive for PyInstaller builds. Just add it to the whitelist.

**Option B: from source (needs Python 3.9+)**

```powershell
git clone https://github.com/moranzj/multi-platform-publisher.git
cd multi-platform-publisher
setup.bat          # one-click setup: venv, dependencies, desktop shortcut
```

Then double-click the “多平台视频发布器” desktop shortcut, or `启动.bat` in the project folder.

---

## Step 2: First login (scan a QR code once per platform)

Click **“重新登录” (Re-login)** at the bottom right of the window (or double-click `登录.bat` for the source version):

1. A browser window opens with three tabs: **Bilibili / Kuaishou / Douyin**.
2. Log in on each tab by scanning the QR code with the mobile app.
3. When all three are logged in, the window closes by itself — no need to press Enter.

The login state is stored in the `profile\` folder inside the app directory, so every later run is already logged in.

> ⚠️ `profile\` contains your login cookies. **Never share it with anyone** — it is equivalent to handing over your accounts.
>
> ⚠️ If a browser window from the previous run is still open, the new run reports “profile is busy” — close the old window first.

---

## Step 3: Fill the form once

Following the screenshot above, top to bottom:

| Field | What to put | Notes |
|---|---|---|
| **视频文件 (Video)** | click “浏览…” and pick an mp4 | Fills the title from the file name and looks for a matching cover (`video-cover.jpg` etc.) in the same folder |
| **封面图片 (Cover)** | can be empty | Empty = all three platforms use the **first frame of the video**; if set, the image is uploaded everywhere |
| **标题 (Title)** | video title | Auto-filled from the file name, editable |
| **文案 (Description)** | description | Shared by all three platforms; for per-platform text click “分平台文案…” |
| **B站标签/话题 (Bilibili tags/topics)** | comma-separated | e.g. `三国杀,桌游棋牌` |
| **快手/抖音话题 (Kuaishou/Douyin topics)** | `#`-prefixed, space-separated | The `#` is optional (added automatically); commas also work as separators |
| **抖音游戏 (Douyin game)** | game name, optional | Fills the “game pendant” tag on Douyin (the Kuaishou web page has no such entry) |
| **历史 (History)** | dropdown | Every run is saved as a template (up to 50); pick one to refill everything |

**Topic syntax** — both lines below produce the same 4 topics:

```
三国杀 三国杀锦囊妙会 随时随地杀一下 三国将星筑梦
#三国杀 #三国杀锦囊妙会 #随时随地杀一下 #三国杀将星筑梦
```

> Bilibili topics go through the platform's topic search: it first looks for an exact name match, otherwise picks the one with the most plays (the log says which one was picked). Douyin/Kuaishou verify that each topic really became a hashtag pill and call out the ones that didn't (usually the topic does not exist on the platform).

---

## Step 4: Preview & checks

Click **“预览 / 检查…” (Preview/Check)** — nothing opens in a browser. It lists:

- The **final** title, description, tags and topics each platform will receive
- Length/tag warnings (Bilibili title 80 chars, Douyin title 30 chars, etc.)
- Whether the video exists and is under 4 GB; whether the cover size/ratio is common

Fix anything flagged — the checks only warn, they never cut your text.

---

## Step 5: Choose how to publish

| Option | Behavior |
|---|---|
| **立即发布 (Publish now)** | No date is set; publishing happens the moment you click “Publish” on the page |
| **定时发布 (Schedule)** | Pick a date & time (defaults to tomorrow 06:00; shortcuts for today/tomorrow and 06:00/18:00) and all three platforms queue up |

Scheduling windows differ per platform and are validated: **Bilibili +5 min ~ 15 days, Kuaishou +1 h ~ 14 days, Douyin +2 h ~ 14 days** (when all three are selected, the strictest window applies).

---

## Step 6: Start → review → press Publish yourself

1. Tick the platforms (all three by default).
2. Leave “跑完之后” on the first option: **stop when filled, keep pages open**.
3. Click **“开始填表” (Start)** — the log on the right scrolls line by line so you always see what is happening:

![Run log](images/app-run.png)

4. When it finishes, switch to the browser and **review every tab with your own eyes** — title, topics, cover, schedule.
5. If everything looks right, **click “发布 / 立即投稿” yourself**.

> Why not auto-submit? The tool only fills the form; the publish button always stays in your hands. If anything was mis-detected, you see a filled page — not an already-published video. There is also a “fill and auto-submit” option (with an extra confirmation), recommended only after you have verified it works for your pages.

---

## Step 7: See the result

When done, the right panel shows “已结束” (finished) with the total time:

![Finished](images/app-done.png)

- Success is detected by landing on the platform's content-management page or a “published” banner (the log says “已跳转到管理页”).
- Full logs and per-step screenshots of every run are kept in `logs\<timestamp>\`. If something goes wrong, the last lines of `run.log` plus the last screenshot pinpoint the issue.

---

## FAQ

| Symptom | Fix |
|---|---|
| Stuck on the login page | Login expired — click “重新登录” and scan again |
| “profile is busy” | Close the browser window left over from the last run |
| Antivirus flags the exe | Common PyInstaller false positive — whitelist it |
| A topic didn't become a pill | The topic doesn't exist on that platform — change the wording or create it first |
| Schedule didn't stick | The tool stops and reports it — it never falls back to “publish now” by accident |
| Slow upload | The three platforms run one after another; ~3–8 minutes per video depending on size — normal |
| CAPTCHA appears | Solve it once manually; very frequent publishing can trigger platform checks |
| Want to tweak the auto-filling | Edit the selector constants at the top of `platforms/<platform>.py` |

---

## In one sentence

**You fill the form once → the tool fills all three platforms → you review → you press Publish.**

This tool drives the platforms' web pages with browser automation — it is not an official API and is not affiliated with Bilibili, Kuaishou or Douyin. Follow each platform's rules, publish responsibly, at your own risk. See the [MIT License](../LICENSE).
