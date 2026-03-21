# -*- coding: utf-8 -*-
"""snapshot 表示と登録記事の同期（ラベル再計算・atp フィルタ）。"""

import os
import sys
import unittest

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.moodmark_stock.snapshot_display import (  # noqa: E402
    article_url_to_label_map,
    filter_article_to_products_by_registration,
    rehydrate_article_labels_in_df,
    registered_article_urls,
    split_article_urls,
)


class TestSplitArticleUrls(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            split_article_urls("https://a/x; https://b/y"),
            ["https://a/x", "https://b/y"],
        )

    def test_empty(self):
        self.assertEqual(split_article_urls(""), [])
        self.assertEqual(split_article_urls(None), [])


class TestFilterAtp(unittest.TestCase):
    def test_drops_unregistered(self):
        atp = {
            "https://keep.example/a": ["p1"],
            "https://gone.example/b": ["p2"],
        }
        reg = {"https://keep.example/a"}
        out = filter_article_to_products_by_registration(atp, reg)
        self.assertEqual(list(out.keys()), ["https://keep.example/a"])
        self.assertEqual(out["https://keep.example/a"], ["p1"])


class TestRehydrateLabels(unittest.TestCase):
    def test_updates_labels_from_articles(self):
        df = pd.DataFrame(
            [
                {
                    "article_urls": "https://a/x; https://b/y",
                    "article_labels": "OLD1; OLD2",
                }
            ]
        )
        articles = [
            {"url": "https://a/x", "label": "新A"},
            {"url": "https://b/y", "label": ""},
        ]
        out = rehydrate_article_labels_in_df(df, articles)
        self.assertEqual(out["article_labels"].iloc[0], "新A; https://b/y")

    def test_unregistered_url_fallback(self):
        df = pd.DataFrame(
            [{"article_urls": "https://deleted/article", "article_labels": "gone"}]
        )
        out = rehydrate_article_labels_in_df(df, [])
        self.assertEqual(
            out["article_labels"].iloc[0], "https://deleted/article"
        )


class TestArticleUrlToLabelMap(unittest.TestCase):
    def test_registered_urls(self):
        arts = [{"url": " https://x ", "label": " L "}]
        self.assertEqual(registered_article_urls(arts), {"https://x"})
        m = article_url_to_label_map(arts)
        self.assertEqual(m["https://x"], "L")


if __name__ == "__main__":
    unittest.main()
