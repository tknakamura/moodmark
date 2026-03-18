# -*- coding: utf-8 -*-
"""
MOO:D MARK 記事・商品ページのスクレイピング。

在庫判定:
  div.btn.red.btn-cart.soldout 内の span.main テキストで
  「入荷待ち」「SOLD OUT」を区別。無ければ在庫あり想定。
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 商品URL（正規化後のベース）
PRODUCT_PATH_RE = re.compile(
    r"/moodmark/product/(MM-\d+)\.html",
    re.IGNORECASE,
)
ABS_PRODUCT_RE = re.compile(
    r"https://isetan\.mistore\.jp/moodmark/product/(MM-\d+)\.html",
    re.IGNORECASE,
)


def canonical_product_url(url_or_path: str) -> Optional[str]:
    """一意の商品ページURL（クエリ除去）を返す。"""
    if not url_or_path:
        return None
    s = url_or_path.strip()
    m = ABS_PRODUCT_RE.search(s)
    if m:
        return f"https://isetan.mistore.jp/moodmark/product/{m.group(1)}.html"
    m = PRODUCT_PATH_RE.search(s)
    if m:
        return f"https://isetan.mistore.jp/moodmark/product/{m.group(1)}.html"
    return None


def extract_product_urls_from_html(html: str, base_url: str = "") -> List[str]:
    """
    HTML から moodmark 商品URLを抽出し、正規化・重複除去（順序維持）。
    """
    seen: set = set()
    out: List[str] = []

    def add(u: Optional[str]) -> None:
        if not u:
            return
        c = canonical_product_url(u)
        if c and c not in seen:
            seen.add(c)
            out.append(c)

    for m in ABS_PRODUCT_RE.finditer(html or ""):
        add(m.group(0))

    for m in PRODUCT_PATH_RE.finditer(html or ""):
        path = m.group(0)
        if base_url:
            add(urljoin(base_url, path))
        else:
            add(f"https://isetan.mistore.jp{path}")

    return out


def fetch_url(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: int = 25,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (html, error_message).
    """
    sess = session or requests.Session()
    try:
        r = sess.get(
            url,
            headers={"User-Agent": DEFAULT_UA, "Accept-Language": "ja,en;q=0.9"},
            timeout=timeout,
        )
        r.raise_for_status()
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text, None
    except requests.RequestException as e:
        return None, str(e)


def fetch_article_html(
    url: str,
    session: Optional[requests.Session] = None,
    delay_s: float = 0,
) -> Tuple[Optional[str], Optional[str]]:
    if delay_s > 0:
        time.sleep(delay_s)
    return fetch_url(url, session=session)


def parse_stock_from_html(html: str) -> Dict[str, Any]:
    """
    商品ページHTMLから在庫状態を返す。

    Returns:
      status: in_stock | restock_wait | sold_out | parse_error
      label: 画面表示用ラベル（日本語）
      raw_main: span.main の生テキスト（デバッグ用）
      raw_sub: span.sub があれば
    """
    if not html:
        return {
            "status": "parse_error",
            "label": "取得失敗",
            "raw_main": "",
            "raw_sub": "",
        }
    soup = BeautifulSoup(html, "lxml")
    sold = soup.select_one("div.btn-cart.soldout")
    if not sold:
        sold = soup.select_one("div.soldout.btn-cart")
    if not sold:
        # クラス順不同対応
        for div in soup.find_all("div", class_=True):
            cls = " ".join(div.get("class", []))
            if "btn-cart" in cls and "soldout" in cls:
                sold = div
                break

    if not sold:
        return {
            "status": "in_stock",
            "label": "在庫あり",
            "raw_main": "",
            "raw_sub": "",
        }

    main = sold.select_one("span.main")
    sub = sold.select_one("span.sub")
    raw_main = main.get_text(strip=True) if main else ""
    raw_sub = sub.get_text(strip=True) if sub else ""
    combined = f"{raw_main} {raw_sub}".upper()

    if "入荷待ち" in raw_main or "入荷待ち" in raw_sub:
        return {
            "status": "restock_wait",
            "label": "入荷待ち",
            "raw_main": raw_main,
            "raw_sub": raw_sub,
        }
    if "SOLD OUT" in combined or "SOLDOUT" in combined.replace(" ", ""):
        return {
            "status": "sold_out",
            "label": "SOLD OUT",
            "raw_main": raw_main,
            "raw_sub": raw_sub,
        }
    # soldout だが文言不明
    return {
        "status": "unavailable_other",
        "label": raw_main or "在庫なし（要確認）",
        "raw_main": raw_main,
        "raw_sub": raw_sub,
    }


def fetch_product_stock(
    product_url: str,
    session: Optional[requests.Session] = None,
    delay_s: float = 0,
) -> Dict[str, Any]:
    """商品URLをGETし在庫情報dictを返す。"""
    if delay_s > 0:
        time.sleep(delay_s)
    html, err = fetch_url(product_url, session=session)
    if err:
        return {
            "status": "fetch_error",
            "label": f"取得エラー: {err[:80]}",
            "raw_main": "",
            "raw_sub": "",
            "error": err,
        }
    info = parse_stock_from_html(html or "")
    info["error"] = info.get("error")
    return info


def run_stock_check(
    articles: List[Dict[str, Any]],
    request_delay_s: float = 0.75,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Dict[str, Any]:
    """
    登録記事を巡回し商品URLを集め、各商品の在庫を取得する。

    articles: [{"id": str, "url": str, "label": str}, ...]

    Returns:
      run_at (ISO)
      article_to_products: {article_url: [product_url, ...]}
      article_warnings: [{article_url, message}]
      product_stock: {product_url: {status, label, raw_main, raw_sub, error?}}
      rows: 一覧用の行のリスト
    """
    from datetime import datetime, timezone

    session = requests.Session()
    run_at = datetime.now(timezone.utc).isoformat()

    article_to_products: Dict[str, List[str]] = {}
    article_warnings: List[Dict[str, str]] = []
    all_products_order: List[str] = []
    seen_p: set = set()

    total_articles = len(articles)
    for i, art in enumerate(articles):
        aurl = (art.get("url") or "").strip()
        if not aurl:
            continue
        if progress_callback:
            progress_callback(f"記事取得: {aurl}", i, total_articles)
        html, err = fetch_article_html(aurl, session=session, delay_s=request_delay_s)
        if err:
            article_warnings.append(
                {"article_url": aurl, "message": f"記事の取得に失敗: {err}"}
            )
            article_to_products[aurl] = []
            continue
        base = f"{urlparse(aurl).scheme}://{urlparse(aurl).netloc}"
        products = extract_product_urls_from_html(html or "", base_url=base)
        article_to_products[aurl] = products
        if not products:
            article_warnings.append(
                {
                    "article_url": aurl,
                    "message": "商品URLが0件です（JS描画の可能性。Playwrightが必要な場合あり）",
                }
            )
        for p in products:
            if p not in seen_p:
                seen_p.add(p)
                all_products_order.append(p)

    product_stock: Dict[str, Dict[str, Any]] = {}
    n = len(all_products_order)
    for j, purl in enumerate(all_products_order):
        if progress_callback:
            progress_callback(f"在庫確認: {purl}", j, n)
        product_stock[purl] = fetch_product_stock(
            purl, session=session, delay_s=request_delay_s
        )

    # product -> which articles (labels)
    product_to_articles: Dict[str, List[Dict[str, str]]] = {p: [] for p in all_products_order}
    art_by_url = {a.get("url", "").strip(): a for a in articles}
    for aurl, plist in article_to_products.items():
        art = art_by_url.get(aurl, {})
        label = art.get("label") or aurl
        for p in plist:
            if p in product_to_articles:
                product_to_articles[p].append({"url": aurl, "label": label})

    rows: List[Dict[str, Any]] = []
    for purl in all_products_order:
        st = product_stock.get(purl, {})
        arts = product_to_articles.get(purl, [])
        rows.append(
            {
                "product_url": purl,
                "stock_status": st.get("status", "unknown"),
                "stock_label": st.get("label", ""),
                "raw_main": st.get("raw_main", ""),
                "raw_sub": st.get("raw_sub", ""),
                "error": st.get("error"),
                "article_urls": "; ".join(a["url"] for a in arts),
                "article_labels": "; ".join(a["label"] for a in arts),
            }
        )

    return {
        "run_at": run_at,
        "article_to_products": article_to_products,
        "article_warnings": article_warnings,
        "product_stock": product_stock,
        "rows": rows,
    }
