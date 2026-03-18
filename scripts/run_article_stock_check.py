#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事掲載商品の在庫チェックをCLIで実行（GitHub Actions / Render Cron 等）。

  MOODMARK_STOCK_STATE_PATH … 読み書きするJSON（未設定時はプロジェクトの data/article_stock_state.json）
  MOODMARK_STOCK_DELAY      … リクエスト間隔（秒）デフォルト 0.75

例:
  cd /path/to/moodmark && python scripts/run_article_stock_check.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.moodmark_stock.scraper import run_stock_check  # noqa: E402
from tools.moodmark_stock.state import (  # noqa: E402
    attach_snapshot,
    load_state,
    save_state,
)


def main() -> int:
    state = load_state()
    arts = state.get("articles") or []
    if not arts:
        print("No articles registered in state JSON.", file=sys.stderr)
        return 1
    delay = float(os.environ.get("MOODMARK_STOCK_DELAY", "0.75"))
    print(f"Checking {len(arts)} article(s), delay={delay}s …")
    snap = run_stock_check(arts, request_delay_s=delay)
    attach_snapshot(state, snap)
    path = save_state(state)
    n = len(snap.get("rows") or [])
    print(f"Done. {n} unique products. Saved: {path}")
    print(f"Run at: {snap.get('run_at')}")
    for w in snap.get("article_warnings") or []:
        print(f"  WARN {w.get('article_url')}: {w.get('message')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
