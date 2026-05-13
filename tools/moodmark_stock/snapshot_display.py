# -*- coding: utf-8 -*-
"""last_snapshot 表示を現在の登録記事一覧と揃える（Streamlit 非依存）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    """ISO 文字列を timezone 付き datetime に（失敗時 None）。"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def article_cache_meta_utc_times(
    snap: Optional[Dict[str, Any]],
    article_url: str,
    product_urls: List[str],
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    last_snapshot.cache_meta から、記事ページ取得時刻と掲載商品の在庫取得の最新時刻を返す。
    いずれも UTC 想定。snap が無い・メタが無い場合は None。
    """
    if not snap or not isinstance(snap, dict):
        return None, None
    cm = snap.get("cache_meta") or {}
    if not isinstance(cm, dict):
        return None, None
    arts = cm.get("articles") or {}
    prods = cm.get("products") or {}
    if not isinstance(arts, dict) or not isinstance(prods, dict):
        return None, None
    aurl = (article_url or "").strip()
    ent_a = arts.get(aurl)
    if ent_a is None and aurl.endswith("/"):
        ent_a = arts.get(aurl.rstrip("/"))
    elif ent_a is None and aurl and not aurl.endswith("/"):
        ent_a = arts.get(aurl + "/")
    article_dt: Optional[datetime] = None
    if isinstance(ent_a, dict):
        article_dt = _parse_iso_datetime(ent_a.get("fetched_at"))

    latest: Optional[datetime] = None
    for p in product_urls or []:
        if not isinstance(p, str) or not p.strip():
            continue
        ent_p = prods.get(p.strip())
        if not isinstance(ent_p, dict):
            continue
        ct = _parse_iso_datetime(ent_p.get("checked_at"))
        if ct is not None and (latest is None or ct > latest):
            latest = ct
    return article_dt, latest


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
