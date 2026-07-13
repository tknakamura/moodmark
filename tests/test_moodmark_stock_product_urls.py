# -*- coding: utf-8 -*-
"""商品URL抽出・正規化（旧 isetan / 新 moodmark ホスト）。"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.moodmark_stock.scraper import (  # noqa: E402
    canonical_product_url,
    extract_product_urls_from_html,
    product_slug_for_ga4_item_id,
)

_OLD = "https://isetan.mistore.jp/moodmark/product/MM-0411775000902.html"
_NEW = "https://moodmark.mistore.jp/product/MM-3614229833805.html"
_NEW_MMV = "https://moodmark.mistore.jp/product/MMV-690251019090.html"
_CANON_NEW = "https://isetan.mistore.jp/moodmark/product/MM-3614229833805.html"
_CANON_MMV = "https://isetan.mistore.jp/moodmark/product/MMV-690251019090.html"


class TestCanonicalProductUrl(unittest.TestCase):
    def test_old_absolute(self):
        self.assertEqual(canonical_product_url(_OLD), _OLD)

    def test_new_moodmark_host(self):
        self.assertEqual(canonical_product_url(_NEW), _CANON_NEW)
        self.assertEqual(canonical_product_url(_NEW_MMV), _CANON_MMV)

    def test_short_relative_path(self):
        self.assertEqual(
            canonical_product_url("/product/MM-3614229833805.html"),
            _CANON_NEW,
        )

    def test_old_relative_path(self):
        self.assertEqual(
            canonical_product_url("/moodmark/product/MM-0411775000902.html"),
            _OLD,
        )

    def test_unknown(self):
        self.assertIsNone(canonical_product_url("https://example.com/foo"))
        self.assertIsNone(canonical_product_url(""))


class TestExtractProductUrls(unittest.TestCase):
    def test_mixed_old_and_new(self):
        html = f"""
        <a href="{_OLD}">old</a>
        <a href="{_NEW}">new</a>
        <a href="{_NEW_MMV}">mmv</a>
        <div data-moodmark-product-id="MM-0421794000234"></div>
        """
        got = extract_product_urls_from_html(
            html, base_url="https://www.mistore.jp"
        )
        self.assertEqual(
            got,
            [
                _OLD,
                _CANON_NEW,
                _CANON_MMV,
                "https://isetan.mistore.jp/moodmark/product/MM-0421794000234.html",
            ],
        )

    def test_new_host_only_like_moodmarkgift_article(self):
        html = """
        <a href="https://moodmark.mistore.jp/product/MM-3614229833805.html">a</a>
        <a href="https://moodmark.mistore.jp/product/MMV-690251019090.html">b</a>
        <a href="https://isetan.mistore.jp/moodmark/birthday/">nav</a>
        """
        got = extract_product_urls_from_html(
            html, base_url="https://www.mistore.jp"
        )
        self.assertEqual(got, [_CANON_NEW, _CANON_MMV])

    def test_short_path_not_double_counted_with_moodmark_prefix(self):
        html = '<a href="/moodmark/product/MM-0411775000902.html">x</a>'
        got = extract_product_urls_from_html(
            html, base_url="https://isetan.mistore.jp"
        )
        self.assertEqual(got, [_OLD])


class TestProductSlugForGa4(unittest.TestCase):
    def test_new_host_slug(self):
        self.assertEqual(
            product_slug_for_ga4_item_id(_NEW), "MM-3614229833805"
        )
        self.assertEqual(
            product_slug_for_ga4_item_id(_NEW_MMV), "MMV-690251019090"
        )


if __name__ == "__main__":
    unittest.main()
