# -*- coding: utf-8 -*-
"""moodmarkgift 記事の data-moodmark-product-id から商品URLを拾うテスト。"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.moodmark_stock.scraper import extract_product_urls_from_html  # noqa: E402


class TestExtractProductUrlsMoodmarkgift(unittest.TestCase):
    def test_data_moodmark_product_id_mm_and_mmv(self):
        html = """
        <p><a data-moodmark-product-id="MM-4903357600021">x</a></p>
        <p><a data-moodmark-product-id="MMV-4582417683534">y</a></p>
        """
        urls = extract_product_urls_from_html(html)
        self.assertEqual(
            urls,
            [
                "https://isetan.mistore.jp/moodmark/product/MM-4903357600021.html",
                "https://isetan.mistore.jp/moodmark/product/MMV-4582417683534.html",
            ],
        )

    def test_combined_with_href_moodmark_product(self):
        html = """
        <a href="/moodmark/product/MM-111.html">a</a>
        <span data-moodmark-product-id='MM-222'>b</span>
        """
        urls = extract_product_urls_from_html(html, base_url="https://isetan.mistore.jp")
        self.assertEqual(len(urls), 2)
        self.assertIn("https://isetan.mistore.jp/moodmark/product/MM-111.html", urls)
        self.assertIn("https://isetan.mistore.jp/moodmark/product/MM-222.html", urls)


if __name__ == "__main__":
    unittest.main()
