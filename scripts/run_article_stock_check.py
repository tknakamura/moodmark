#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事掲載商品の在庫チェックをCLIで実行（GitHub Actions / Render Cron 等）。

  DATABASE_URL              … 設定時は PostgreSQL に読み書き
  MOODMARK_STOCK_STATE_PATH … JSON モード時のファイルパス（任意）
  MOODMARK_STOCK_DELAY      … 各ワーカーのリクエスト前待機（秒）デフォルト 0.5（推奨 0.3〜0.5）
  MOODMARK_STOCK_ARTICLE_WORKERS … 記事並列数 デフォルト 4
  MOODMARK_STOCK_PRODUCT_WORKERS … 商品並列数 デフォルト 12
  MOODMARK_STOCK_CACHE_HOURS … キャッシュTTL（時間）デフォルト 24
  MOODMARK_STOCK_FORCE_FULL … 1 ならキャッシュ無視
  MOODMARK_STOCK_ONLY_URLS … カンマ区切りの記事URL（指定時はその記事だけ再取得。他は前回スナップショットを継承）

例:
  cd /path/to/moodmark && python scripts/run_article_stock_check.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.moodmark_stock.scraper import run_stock_check  # noqa: E402
from tools.moodmark_stock.store import get_store  # noqa: E402


def main() -> int:
    store = get_store()
    state = store.load_state()
    arts = state.get("articles") or []
    if not arts:
        print("No articles registered.", file=sys.stderr)
        return 1
    delay = float(os.environ.get("MOODMARK_STOCK_DELAY", "0.5"))
    wa = int(os.environ.get("MOODMARK_STOCK_ARTICLE_WORKERS", "4"))
    wp = int(os.environ.get("MOODMARK_STOCK_PRODUCT_WORKERS", "12"))
    ttl = float(os.environ.get("MOODMARK_STOCK_CACHE_HOURS", "24"))
    force = os.environ.get("MOODMARK_STOCK_FORCE_FULL", "").strip() in (
        "1",
        "true",
        "yes",
    )
    prev = state.get("last_snapshot")
    only_raw = os.environ.get("MOODMARK_STOCK_ONLY_URLS", "").strip()
    only_urls = None
    if only_raw:
        parsed = [u.strip() for u in only_raw.split(",") if u.strip()]
        only_urls = parsed if parsed else None
    print(f"Backend: {store.backend_label}")
    print(
        f"Articles={len(arts)} workers=({wa},{wp}) delay={delay}s "
        f"cache_ttl={ttl}h force_full={force}"
        + (f" only_urls={len(only_urls)}" if only_urls else "")
    )
    snap = run_stock_check(
        arts,
        request_delay_s=delay,
        max_article_workers=wa,
        max_product_workers=wp,
        previous_snapshot=prev,
        cache_ttl_hours=ttl,
        force_full_refresh=force,
        only_check_article_urls=only_urls,
    )
    store.record_snapshot(snap)
    rs = snap.get("run_stats") or {}
    print(
        f"Articles fetched/cached: {rs.get('articles_fetched')}/{rs.get('articles_cached')}"
    )
    print(
        f"Products fetched/cached: {rs.get('products_fetched')}/{rs.get('products_cached')}"
    )
    n = len(snap.get("rows") or [])
    print(f"Done. {n} unique products. Run at: {snap.get('run_at')}")
    for w in snap.get("article_warnings") or []:
        print(f"  WARN {w.get('article_url')}: {w.get('message')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
