"""提交成功判定的单元测试（用假页面，不启动浏览器）。"""
from __future__ import annotations

import unittest

from core import steps


class FakeBody:
    def __init__(self, text: str):
        self.text = text

    def inner_text(self, timeout: int = 0) -> str:
        return self.text


class FakePage:
    def __init__(self, url: str = "", text: str = ""):
        self.url = url
        self._body = FakeBody(text)

    def locator(self, _selector: str):
        return self._body


class WaitSuccessTests(unittest.TestCase):
    def test_landing_on_manage_page_is_success(self):
        page = FakePage("https://cp.kuaishou.com/article/manage/video?status=1")
        self.assertTrue(steps.wait_success(
            page, ("发布成功",), timeout=100, url_hints=("article/manage",)))

    def test_success_banner_is_success(self):
        page = FakePage("https://example.com/upload", "发布成功，正在跳转")
        self.assertTrue(steps.wait_success(page, ("发布成功",), timeout=100))

    def test_failure_toast_wins(self):
        page = FakePage("https://example.com/upload", "投稿失败：内容不合规")
        self.assertFalse(steps.wait_success(
            page, ("投稿成功",), timeout=100, fail_patterns=("投稿失败",)))

    def test_nothing_happens(self):
        page = FakePage("https://example.com/upload", "还在上传")
        self.assertFalse(steps.wait_success(page, ("发布成功",), timeout=100))


if __name__ == "__main__":
    unittest.main()
