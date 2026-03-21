# -*- coding: utf-8 -*-
"""
MOO:D MARK 記事・商品ページのスクレイピング。

在庫判定:
  div.btn.red.btn-cart.soldout 内の span.main テキストで
  「入荷待ち」「SOLD OUT」を区別。無ければ在庫あり想定。

高速化:
  - 記事GET / 商品GET をそれぞれ ThreadPoolExecutor で並列（同時数上限）
  - cache_meta: 24h以内（TTL可変）の記事は掲載URL一覧を再利用、商品は在庫結果を再利用
"""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Collection, Dict, List, Optional, Tuple

from tools.moodmark_stock.state import _normalize_article_url
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# MM-123（従来）および MMV-0415385006491 形式など
_PRODUCT_SLUG = r"(?:MM-\d+|MMV-[A-Za-z0-9]+)"
PRODUCT_PATH_RE = re.compile(
    rf"/moodmark/product/({_PRODUCT_SLUG})\.html",
    re.IGNORECASE,
)
ABS_PRODUCT_RE = re.compile(
    rf"https://isetan\.mistore\.jp/moodmark/product/({_PRODUCT_SLUG})\.html",
    re.IGNORECASE,
)


def canonical_product_url(url_or_path: str) -> Optional[str]:
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


def product_slug_for_ga4_item_id(url_or_path: str) -> Optional[str]:
    """
    商品URLから GA4 の itemId 候補（パス上のファイル名ベース、拡張子なし）を返す。
    canonical に載らない相対パスでも path 正規表現で拾う。
    """
    if not (url_or_path or "").strip():
        return None
    s = url_or_path.strip()
    c = canonical_product_url(s)
    if c:
        m = ABS_PRODUCT_RE.search(c)
        if m:
            return m.group(1)
    try:
        path = urlparse(s).path if s.startswith("http") else s
    except Exception:
        path = s
    m = PRODUCT_PATH_RE.search(path or "")
    return m.group(1) if m else None


def extract_product_urls_from_html(html: str, base_url: str = "") -> List[str]:
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


def fetch_article_html(
    url: str,
    session: Optional[requests.Session] = None,
    delay_s: float = 0,
) -> Tuple[Optional[str], Optional[str]]:
    """記事URLをGET。delay_s は互換用。"""
    if delay_s > 0:
        time.sleep(delay_s)
    return fetch_url(url, session=session)


def fetch_url(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: int = 25,
) -> Tuple[Optional[str], Optional[str]]:
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


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_product_name_from_html(html: str) -> str:
    """
    商品ページHTMLから商品名を推定。
    h1.name 直下の span（brand / keyword 以外）→ og:title → twitter:title → h1 全文 → title。
    """
    if not html:
        return ""

    def strip_site_suffix(t: str) -> str:
        t = (t or "").strip()
        for sep in (" | ", " ｜ ", "|", "｜", " - ", " – "):
            if sep in t:
                left = t.split(sep, 1)[0].strip()
                if len(left) >= 2:
                    return left[:500]
        return t[:500] if t else ""

    soup = BeautifulSoup(html, "lxml")
    # 画面表示の商品名（例: <h1 class="name"><span class="brand">…</span><span>商品名</span><span class="keyword">…</span>）
    h1_name = soup.find("h1", class_="name")
    if h1_name:
        for span in h1_name.find_all("span", recursive=False):
            classes = span.get("class") or []
            if "brand" in classes or "keyword" in classes:
                continue
            t = span.get_text(" ", strip=True)
            if t and len(t) >= 2:
                return t[:500]

    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        c = strip_site_suffix(str(og["content"]))
        if c:
            return c
    tw = soup.find("meta", attrs={"name": "twitter:title"})
    if tw and tw.get("content"):
        c = strip_site_suffix(str(tw["content"]))
        if c:
            return c
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)[:500]
    title = soup.find("title")
    if title:
        return strip_site_suffix(title.get_text(strip=True))
    return ""


def _is_within_ttl(checked_at: str, ttl_hours: float, now: datetime) -> bool:
    t = _parse_iso(checked_at)
    if not t:
        return False
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (now - t).total_seconds() < ttl_hours * 3600


def parse_stock_from_html(html: str) -> Dict[str, Any]:
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
    return {
        "status": "unavailable_other",
        "label": raw_main or "在庫なし（要確認）",
        "raw_main": raw_main,
        "raw_sub": raw_sub,
    }


def _fetch_one_article(aurl: str, delay_s: float):
    if delay_s > 0:
        time.sleep(delay_s)
    sess = requests.Session()
    html, err = fetch_url(aurl, session=sess)
    if err:
        return aurl, [], err
    base = f"{urlparse(aurl).scheme}://{urlparse(aurl).netloc}"
    products = extract_product_urls_from_html(html or "", base_url=base)
    return aurl, products, None


def fetch_product_stock(
    product_url: str,
    session: Optional[requests.Session] = None,
    delay_s: float = 0,
) -> Dict[str, Any]:
    """単一商品URLの在庫取得（互換・単体利用用）。"""
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
            "product_name": "",
        }
    info = parse_stock_from_html(html or "")
    info["product_name"] = parse_product_name_from_html(html or "")
    info["error"] = info.get("error")
    return info


def _fetch_one_product(purl: str, delay_s: float):
    if delay_s > 0:
        time.sleep(delay_s)
    sess = requests.Session()
    html, err = fetch_url(purl, session=sess)
    if err:
        return purl, {
            "status": "fetch_error",
            "label": f"取得エラー: {err[:80]}",
            "raw_main": "",
            "raw_sub": "",
            "error": err,
            "product_name": "",
        }
    info = parse_stock_from_html(html or "")
    info["product_name"] = parse_product_name_from_html(html or "")
    info["error"] = info.get("error")
    return purl, info


def run_stock_check(
    articles: List[Dict[str, Any]],
    request_delay_s: float = 0.0,
    max_article_workers: int = 4,
    max_product_workers: int = 12,
    previous_snapshot: Optional[Dict[str, Any]] = None,
    cache_ttl_hours: float = 24.0,
    force_full_refresh: bool = False,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    only_check_article_urls: Optional[Collection[str]] = None,
) -> Dict[str, Any]:
    """
    登録記事を巡回し商品URLを集め、各商品の在庫を取得する。

    previous_snapshot: 直前の実行結果（cache_meta を含む）。TTL内スキップに使用。
    force_full_refresh: True ならキャッシュを使わず全GET（only_check_article_urls で選ばれた記事のみ対象）。
    only_check_article_urls: 指定時はその記事URLだけ記事ページをTTL判定・再取得する。
        それ以外の登録記事は previous_snapshot の article_to_products / cache_meta を引き継ぐ。
        前回スナップショットがない場合、対象外記事は商品0件扱い。
    """
    now = datetime.now(timezone.utc)
    run_at = now.isoformat()

    cm_prev: Dict[str, Any] = {}
    if previous_snapshot and not force_full_refresh:
        cm_prev = deepcopy(previous_snapshot.get("cache_meta") or {})
    articles_cached = cm_prev.get("articles") or {}
    products_cached = cm_prev.get("products") or {}

    all_article_urls = [
        (art.get("url") or "").strip() for art in articles if (art.get("url") or "").strip()
    ]

    check_set: Optional[set] = None
    if only_check_article_urls is not None:
        check_set = set()
        for u in only_check_article_urls:
            raw = (u or "").strip()
            if not raw:
                continue
            nu = _normalize_article_url(raw)
            if nu:
                check_set.add(nu)

    prev_atp: Dict[str, Any] = {}
    if previous_snapshot and isinstance(previous_snapshot.get("article_to_products"), dict):
        prev_atp = previous_snapshot["article_to_products"]

    def _article_in_refresh_scope(aurl: str) -> bool:
        if check_set is None:
            return True
        key = _normalize_article_url(aurl) or aurl
        return key in check_set

    article_to_products: Dict[str, List[str]] = {}
    article_warnings: List[Dict[str, str]] = []
    need_article_fetch: List[str] = []

    for aurl in all_article_urls:
        if not _article_in_refresh_scope(aurl):
            prods = prev_atp.get(aurl)
            if isinstance(prods, list):
                article_to_products[aurl] = [p for p in prods if isinstance(p, str)]
            else:
                article_to_products[aurl] = []
            if not previous_snapshot:
                article_warnings.append(
                    {
                        "article_url": aurl,
                        "message": (
                            "前回スナップショットがないため、部分チェック対象外の記事は商品0件として扱いました"
                        ),
                    }
                )
            continue

        if force_full_refresh:
            need_article_fetch.append(aurl)
            continue
        ent = articles_cached.get(aurl)
        if ent and isinstance(ent, dict) and _is_within_ttl(
            str(ent.get("fetched_at") or ""), cache_ttl_hours, now
        ):
            prods = ent.get("products")
            if isinstance(prods, list):
                article_to_products[aurl] = [p for p in prods if isinstance(p, str)]
            else:
                article_to_products[aurl] = []
            if not article_to_products[aurl]:
                article_warnings.append(
                    {
                        "article_url": aurl,
                        "message": "（キャッシュ）商品URLが0件でした",
                    }
                )
        else:
            need_article_fetch.append(aurl)

    na = len(need_article_fetch)
    article_fetch_errors: set = set()
    ai = [0]

    def prog_article(msg: str):
        if progress_callback and na > 0:
            progress_callback(msg, ai[0], na)
            ai[0] += 1

    ma = max(1, min(max_article_workers, 32))
    if need_article_fetch:
        with ThreadPoolExecutor(max_workers=ma) as ex:
            futs = {
                ex.submit(_fetch_one_article, u, request_delay_s): u
                for u in need_article_fetch
            }
            for fut in as_completed(futs):
                aurl, products, err = fut.result()
                if err:
                    article_fetch_errors.add(aurl)
                    article_warnings.append(
                        {"article_url": aurl, "message": f"記事の取得に失敗: {err}"}
                    )
                    article_to_products[aurl] = []
                else:
                    article_to_products[aurl] = products
                    if not products:
                        article_warnings.append(
                            {
                                "article_url": aurl,
                                "message": "商品URLが0件です（JS描画の可能性。Playwrightが必要な場合あり）",
                            }
                        )
                prog_article(f"記事: {aurl}")

    all_products_order: List[str] = []
    seen_p: set = set()
    for aurl in all_article_urls:
        for p in article_to_products.get(aurl, []):
            if p not in seen_p:
                seen_p.add(p)
                all_products_order.append(p)

    product_stock: Dict[str, Dict[str, Any]] = {}
    need_product_fetch: List[str] = []

    for purl in all_products_order:
        if force_full_refresh:
            need_product_fetch.append(purl)
            continue
        pent = products_cached.get(purl)
        if pent and isinstance(pent, dict) and _is_within_ttl(
            str(pent.get("checked_at") or ""), cache_ttl_hours, now
        ):
            stock = {
                k: v
                for k, v in pent.items()
                if k not in ("checked_at",)
            }
            stock.setdefault("product_name", "")
            product_stock[purl] = stock
        else:
            need_product_fetch.append(purl)

    np = len(need_product_fetch)
    total_steps = na + np
    pj = [0]
    product_fetch_errors: set = set()

    def prog_product(msg: str):
        if progress_callback and total_steps > 0:
            progress_callback(msg, na + pj[0], total_steps)
            pj[0] += 1

    mp = max(1, min(max_product_workers, 48))
    if need_product_fetch:
        with ThreadPoolExecutor(max_workers=mp) as ex:
            futs = {
                ex.submit(_fetch_one_product, u, request_delay_s): u
                for u in need_product_fetch
            }
            for fut in as_completed(futs):
                purl, info = fut.result()
                product_stock[purl] = info
                if info.get("status") == "fetch_error":
                    product_fetch_errors.add(purl)
                prog_product(f"在庫: {purl}")

    art_by_url = {a.get("url", "").strip(): a for a in articles}
    product_to_articles: Dict[str, List[Dict[str, str]]] = {
        p: [] for p in all_products_order
    }
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
                "product_name": (st.get("product_name") or "").strip(),
                "stock_status": st.get("status", "unknown"),
                "stock_label": st.get("label", ""),
                "raw_main": st.get("raw_main", ""),
                "raw_sub": st.get("raw_sub", ""),
                "error": st.get("error"),
                "article_urls": "; ".join(a["url"] for a in arts),
                "article_labels": "; ".join(a["label"] for a in arts),
            }
        )

    # cache_meta 更新
    cache_articles: Dict[str, Any] = {}
    for aurl in all_article_urls:
        if not _article_in_refresh_scope(aurl):
            if aurl in articles_cached and isinstance(articles_cached[aurl], dict):
                cache_articles[aurl] = deepcopy(articles_cached[aurl])
            else:
                cache_articles[aurl] = {
                    "fetched_at": str((previous_snapshot or {}).get("run_at") or run_at),
                    "products": list(article_to_products.get(aurl, [])),
                }
            continue

        if aurl in need_article_fetch:
            if aurl in article_fetch_errors:
                if aurl in articles_cached:
                    cache_articles[aurl] = deepcopy(articles_cached[aurl])
            else:
                cache_articles[aurl] = {
                    "fetched_at": run_at,
                    "products": list(article_to_products.get(aurl, [])),
                }
        else:
            prev = articles_cached.get(aurl, {})
            cache_articles[aurl] = {
                "fetched_at": prev.get("fetched_at") or run_at,
                "products": list(article_to_products.get(aurl, [])),
            }

    cache_products: Dict[str, Any] = {}
    for purl in all_products_order:
        st = product_stock.get(purl, {})
        if purl in need_product_fetch:
            if purl in product_fetch_errors:
                if purl in products_cached:
                    cache_products[purl] = deepcopy(products_cached[purl])
            else:
                cache_products[purl] = {
                    "checked_at": run_at,
                    "status": st.get("status"),
                    "label": st.get("label", ""),
                    "raw_main": st.get("raw_main", ""),
                    "raw_sub": st.get("raw_sub", ""),
                    "error": st.get("error"),
                    "product_name": (st.get("product_name") or "").strip(),
                }
        else:
            prev = products_cached.get(purl, {})
            cache_products[purl] = {
                "checked_at": prev.get("checked_at") or run_at,
                "status": st.get("status"),
                "label": st.get("label", ""),
                "raw_main": st.get("raw_main", ""),
                "raw_sub": st.get("raw_sub", ""),
                "error": st.get("error"),
                "product_name": (st.get("product_name") or prev.get("product_name") or "").strip(),
            }

    return {
        "run_at": run_at,
        "article_to_products": article_to_products,
        "article_warnings": article_warnings,
        "product_stock": product_stock,
        "rows": rows,
        "cache_meta": {"articles": cache_articles, "products": cache_products},
        "run_stats": {
            "articles_fetched": len(need_article_fetch),
            "articles_cached": len(all_article_urls) - len(need_article_fetch),
            "products_fetched": len(need_product_fetch),
            "products_cached": len(all_products_order) - len(need_product_fetch),
            "cache_ttl_hours": cache_ttl_hours,
            "force_full_refresh": force_full_refresh,
            "articles_refresh_target": sum(
                1 for u in all_article_urls if _article_in_refresh_scope(u)
            ),
            "articles_preserved_without_fetch": sum(
                1 for u in all_article_urls if not _article_in_refresh_scope(u)
            ),
        },
    }
