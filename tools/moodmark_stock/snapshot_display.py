# -*- coding: utf-8 -*-
"""last_snapshot 表示を現在の登録記事一覧と揃える（Streamlit 非依存）。"""

from __future__ import annotations

from typing import Any, Dict, List, Set

import pandas as pd


def split_article_urls(article_urls) -> List[str]:
    """article_urls 文字列の ; 区切りを正規化したリストに。"""
    if article_urls is None or (isinstance(article_urls, float) and pd.isna(article_urls)):
        return []
    s = str(article_urls).strip()
    if not s:
        return []
    return [p.strip() for p in s.split(";") if p.strip()]


def registered_article_urls(articles: List[Dict[str, Any]]) -> Set[str]:
    """登録記事の URL 集合（strip 済み）。"""
    out: Set[str] = set()
    for a in articles or []:
        u = (a.get("url") or "").strip()
        if u:
            out.add(u)
    return out


def article_url_to_label_map(articles: List[Dict[str, Any]]) -> Dict[str, str]:
    """url -> 表示ラベル（ラベル空なら URL）。"""
    m: Dict[str, str] = {}
    for a in articles or []:
        u = (a.get("url") or "").strip()
        if not u:
            continue
        lab = (a.get("label") or "").strip()
        m[u] = lab if lab else u
    return m


def filter_article_to_products_by_registration(
    article_to_products: Dict[str, Any],
    registered_urls: Set[str],
) -> Dict[str, List[str]]:
    """スナップショットの article_to_products から、登録中の記事URLのエントリだけ残す。"""
    if not article_to_products:
        return {}
    out: Dict[str, List[str]] = {}
    for u, plist in article_to_products.items():
        if u not in registered_urls:
            continue
        if isinstance(plist, list):
            out[u] = [p for p in plist if isinstance(p, str)]
        else:
            out[u] = []
    return out


def rehydrate_article_labels_in_df(
    df: pd.DataFrame, articles: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    行の article_urls を元に、現在の articles から article_labels を再構築。
    登録に無い URL はその URL文字列をラベルとして使う（削除・URL変更後の旧URL）。
    """
    if df.empty or "article_urls" not in df.columns:
        return df
    df = df.copy()
    m = article_url_to_label_map(articles)

    def relabel(row: pd.Series) -> str:
        urls = split_article_urls(row.get("article_urls"))
        if not urls:
            v = row.get("article_labels")
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return ""
            return str(v)
        return "; ".join(m.get(u, u) for u in urls)

    df["article_labels"] = df.apply(relabel, axis=1)
    return df
