# -*- coding: utf-8 -*-
"""部分在庫チェック: 未選択記事は前回スナップショットを維持する。"""

import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.moodmark_stock.scraper import run_stock_check  # noqa: E402

_UA = "https://example.invalid/article-a"
_UB = "https://example.invalid/article-b"
_MU1 = "https://isetan.mistore.jp/moodmark/product/MM-90001.html"
_MU2 = "https://isetan.mistore.jp/moodmark/product/MM-90002.html"


def _mock_fetch_article(aurl, delay_s):
    if "article-a" in aurl:
        return aurl, [_MU1], None
    return aurl, [], "should_not_fetch_b"


def _mock_fetch_product(purl, delay_s):
    info = {
        "status": "in_stock",
        "label": "ok",
        "raw_main": "",
        "raw_sub": "",
        "error": None,
        "product_name": "n",
    }
    return purl, info


class TestPartialStockCheck(unittest.TestCase):
    @patch(
        "tools.moodmark_stock.scraper._fetch_one_product",
        side_effect=_mock_fetch_product,
    )
    @patch(
        "tools.moodmark_stock.scraper._fetch_one_article",
        side_effect=_mock_fetch_article,
    )
    def test_partial_preserves_unselected_article_products(
        self, mock_article, _mock_product
    ):
        prev = {
            "run_at": "2020-01-01T00:00:00+00:00",
            "article_to_products": {
                _UA: [_MU1],
                _UB: [_MU2],
            },
            "cache_meta": {
                "articles": {
                    _UA: {
                        "fetched_at": "2020-01-01T00:00:00+00:00",
                        "products": [_MU1],
                    },
                    _UB: {
                        "fetched_at": "2020-01-01T00:00:00+00:00",
                        "products": [_MU2],
                    },
                },
                "products": {
                    _MU1: {
                        "checked_at": "2020-01-01T00:00:00+00:00",
                        "status": "in_stock",
                        "label": "",
                        "raw_main": "",
                        "raw_sub": "",
                        "error": None,
                        "product_name": "",
                    },
                    _MU2: {
                        "checked_at": "2020-01-01T00:00:00+00:00",
                        "status": "restock_wait",
                        "label": "待ち",
                        "raw_main": "",
                        "raw_sub": "",
                        "error": None,
                        "product_name": "B",
                    },
                },
            },
        }
        articles = [
            {"url": _UA, "label": "A"},
            {"url": _UB, "label": "B"},
        ]
        snap = run_stock_check(
            articles,
            previous_snapshot=prev,
            only_check_article_urls=[_UA],
            force_full_refresh=True,
            cache_ttl_hours=8760.0,
            request_delay_s=0.0,
        )
        self.assertEqual(snap["article_to_products"][_UB], [_MU2])
        self.assertEqual(snap["run_stats"].get("articles_preserved_without_fetch"), 1)
        fetched_urls = [c.args[0] for c in mock_article.call_args_list]
        self.assertTrue(all("article-a" in u for u in fetched_urls))
        self.assertFalse(any("article-b" in u for u in fetched_urls))


if __name__ == "__main__":
    unittest.main()
