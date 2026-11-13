"""分平台文案组装与发布前检查的单元测试（不依赖 Playwright）。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core import content
from platforms.base import Job


class JobFallbackTests(unittest.TestCase):
    def test_title_override_and_fallback(self):
        job = Job(video="x.mp4", title="通用标题", bili_title="B站标题")
        self.assertEqual(job.title_for("bili"), "B站标题")
        self.assertEqual(job.title_for("kuaishou"), "通用标题")

    def test_desc_override_and_fallback(self):
        job = Job(video="x.mp4", title="通用标题", desc="通用文案",
                  ks_title="快手标题", ks_desc="快手文案")
        self.assertEqual(job.desc_for("kuaishou"), "快手文案")
        self.assertEqual(job.desc_for("douyin"), "通用文案")

    def test_desc_follows_platform_title_when_general_desc_is_empty(self):
        # 只改平台标题、没单独写通用文案时，别把通用标题重复拼进描述
        job = Job(video="x.mp4", title="通用标题", ks_title="快手标题")
        self.assertEqual(job.desc_for("kuaishou"), "快手标题")


class ComposeTests(unittest.TestCase):
    def test_bili_fields(self):
        job = Job(
            video="x.mp4", title="通用标题", desc="通用简介",
            bili_title="B站标题", bili_desc="B站简介",
            bili_tags="三国杀, #桌游棋牌，复盘", bili_topic="卡牌 复盘",
        )
        data = content.compose("bili", job)
        self.assertEqual(data["name"], "B站")
        self.assertEqual(data["title"], "B站标题")
        self.assertEqual(data["body"], "B站简介")
        self.assertIn("标签：三国杀、桌游棋牌、复盘", data["extra"])
        self.assertIn("参与话题：卡牌、复盘", data["extra"])

    def test_kuaishou_merges_title_topics_and_desc(self):
        job = Job(
            video="x.mp4", title="通用标题", desc="通用文案",
            ks_title="快手标题", ks_desc="快手文案",
            kuaishou_topics="三国杀 桌游",
        )
        data = content.compose("kuaishou", job)
        self.assertEqual(data["body"], "快手标题 #三国杀 #桌游 快手文案")

    def test_douyin_uses_own_title_and_desc(self):
        job = Job(
            video="x.mp4", title="通用标题", desc="通用文案",
            dy_title="抖音标题", dy_desc="抖音文案",
            douyin_topics="#三国杀 #随时随地杀一下",
        )
        data = content.compose("douyin", job)
        self.assertEqual(data["title"], "抖音标题")
        # 抖音标题是独立字段，作品描述里只有文案和话题
        self.assertEqual(
            data["body"], "抖音文案 #三国杀 #随时随地杀一下")
        self.assertNotIn("抖音标题", data["body"])

    def test_bili_tags_split_and_strip_hash(self):
        self.assertEqual(
            content.bili_tags("三国杀, #桌游棋牌，复盘"),
            ["三国杀", "桌游棋牌", "复盘"])

    def test_douyin_game_shown_in_extra_only_for_douyin(self):
        job = Job(video="x.mp4", title="通用标题", dy_game="三国杀")
        self.assertIn("游戏手柄：三国杀", content.compose("douyin", job)["extra"])
        self.assertEqual(content.compose("kuaishou", job)["extra"], "")

    def test_douyin_game_empty_extra(self):
        job = Job(video="x.mp4", title="通用标题")
        self.assertEqual(content.compose("douyin", job)["extra"], "")


class PreviewTests(unittest.TestCase):
    def test_preview_contains_platform_and_counts(self):
        job = Job(video="x.mp4", title="通用标题", bili_title="B站标题")
        text = content.preview_text("bili", job)
        self.assertIn("【B站】", text)
        self.assertIn("标题（4 字）：B站标题", text)
        self.assertIn("简介", text)


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.video = self.dir / "video.mp4"
        self.video.write_bytes(b"not really a video")

    def job(self, **kwargs) -> Job:
        base = {"video": str(self.video), "title": "正常标题", "desc": "正常文案"}
        base.update(kwargs)
        return Job(**base)

    def test_valid_job_has_no_errors(self):
        errors, _warnings = content.check(
            self.job(), ["bili", "kuaishou", "douyin"])
        self.assertEqual(errors, [])

    def test_empty_title_is_error(self):
        errors, _warnings = content.check(self.job(title=""), ["bili"])
        self.assertTrue(any("B站标题是空的" in e for e in errors))

    def test_missing_video_is_error(self):
        missing = self.dir / "missing.mp4"
        errors, _warnings = content.check(
            self.job(video=str(missing)), ["bili"])
        self.assertTrue(any("视频不存在" in e for e in errors))

    def test_missing_cover_is_error(self):
        errors, _warnings = content.check(
            self.job(cover=str(self.dir / "missing.jpg")), ["bili"])
        self.assertTrue(any("封面文件不存在" in e for e in errors))

    def test_long_bili_title_warns(self):
        errors, warnings = content.check(
            self.job(title="长" * 81), ["bili"])
        self.assertEqual(errors, [])
        self.assertTrue(any("B站标题 81 字" in w for w in warnings))

    def test_too_many_bili_tags_warns(self):
        tags = ",".join(f"标签{i}" for i in range(11))
        _errors, warnings = content.check(
            self.job(bili_tags=tags), ["bili"])
        self.assertTrue(any("B站标签 11 个" in w for w in warnings))

    def test_long_kuaishou_combined_desc_warns(self):
        _errors, warnings = content.check(
            self.job(desc="长" * 500), ["kuaishou"])
        self.assertTrue(any("快手作品描述共" in w for w in warnings))

    def test_too_many_douyin_topics_warns(self):
        topics = " ".join(f"话题{i}" for i in range(6))
        _errors, warnings = content.check(
            self.job(douyin_topics=topics), ["douyin"])
        self.assertTrue(any("抖音话题 6 个" in w for w in warnings))

    def test_small_cover_warns(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow 未安装")
        cover = self.dir / "cover.png"
        Image.new("RGB", (200, 200), "white").save(cover)
        errors, warnings = content.check_cover(str(cover), ["kuaishou"])
        self.assertEqual(errors, [])
        self.assertTrue(any("偏小" in w for w in warnings))

    def test_normal_cover_is_quiet(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow 未安装")
        cover = self.dir / "cover.png"
        Image.new("RGB", (1280, 720), "white").save(cover)
        errors, warnings = content.check_cover(str(cover), ["kuaishou"])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
