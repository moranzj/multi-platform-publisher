"""定时时间解析与平台窗口的单元测试（不依赖 Playwright）。"""
from __future__ import annotations

import datetime as dt
import unittest

from core import schedule as s


class NormalizeTimeTests(unittest.TestCase):
    def test_accepts_common_forms(self):
        cases = {
            "6": "06:00",
            "06:00": "06:00",
            "6:5": "06:05",
            "6：30": "06:30",
            "6点": "06:00",
            "6点30": "06:30",
            "23:59": "23:59",
            "0:00": "00:00",
            "": "06:00",
        }
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(s.normalize_time(raw), want)

    def test_rejects_out_of_range(self):
        for raw in ("24:00", "12:60", "abc", "12:345"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    s.normalize_time(raw)


class NormalizeDateTests(unittest.TestCase):
    def test_accepts_common_forms(self):
        for raw in ("2026-11-05", "2026/11/5", "2026.11.5", "2026年11月5日"):
            with self.subTest(raw=raw):
                self.assertEqual(s.normalize_date(raw), "2026-11-05")

    def test_rejects_bad_date(self):
        with self.assertRaises(ValueError):
            s.normalize_date("2026-13-01")


class WindowTests(unittest.TestCase):
    now = dt.datetime(2026, 11, 4, 10, 0)

    def test_past_is_error(self):
        errors, warnings = s.check_window(
            dt.datetime(2026, 11, 4, 9, 0), ["bili"], now=self.now)
        self.assertTrue(errors)
        self.assertFalse(warnings)

    def test_two_hours_is_ok_for_all(self):
        errors, warnings = s.check_window(
            dt.datetime(2026, 11, 4, 12, 0),
            ["bili", "kuaishou", "douyin"], now=self.now)
        self.assertFalse(errors)
        self.assertFalse(warnings)

    def test_too_soon_warns_for_douyin(self):
        errors, warnings = s.check_window(
            dt.datetime(2026, 11, 4, 11, 0), ["douyin"], now=self.now)
        self.assertFalse(errors)
        self.assertTrue(any("抖音" in w for w in warnings))

    def test_too_far_warns(self):
        errors, warnings = s.check_window(
            dt.datetime(2026, 12, 1, 10, 0), ["bili"], now=self.now)
        self.assertFalse(errors)
        self.assertTrue(any("15 天" in w for w in warnings))


class HumanHoursTests(unittest.TestCase):
    def test_format(self):
        self.assertEqual(s.human_hours(0.5), "30 分钟")
        self.assertEqual(s.human_hours(1), "1 小时")
        self.assertEqual(s.human_hours(1.5), "1.5 小时")
        self.assertEqual(s.human_hours(72), "3 天")


if __name__ == "__main__":
    unittest.main()
