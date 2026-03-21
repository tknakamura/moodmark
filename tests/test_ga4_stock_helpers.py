# -*- coding: utf-8 -*-
"""GA4 日付窓・商品URLスラッグ抽出のユニットテスト。"""

import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import unittest

from analytics.google_apis_integration import GoogleAPIsIntegration  # noqa: E402
from tools.moodmark_stock.scraper import product_slug_for_ga4_item_id  # noqa: E402


class TestGa4ReportDateStrings(unittest.TestCase):
    def test_lag3_window7(self):
        start, end = GoogleAPIsIntegration.ga4_report_date_strings(
            3, 7, reference_date=date(2026, 3, 21)
        )
        self.assertEqual(end, "2026-03-18")
        self.assertEqual(start, "2026-03-12")


class TestProductSlugForGa4(unittest.TestCase):
    def test_mm_numeric(self):
        u = "https://isetan.mistore.jp/moodmark/product/MM-12345.html"
        self.assertEqual(product_slug_for_ga4_item_id(u), "MM-12345")

    def test_mmv_slug(self):
        u = "https://isetan.mistore.jp/moodmark/product/MMV-0415385006491.html?cgid=I010201"
        self.assertEqual(product_slug_for_ga4_item_id(u), "MMV-0415385006491")


if __name__ == "__main__":
    unittest.main()
