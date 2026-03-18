#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON の article_stock_state を PostgreSQL に取り込む（初回移行用）。

前提:
  - 環境変数 DATABASE_URL（External 推奨: ローカル実行時）
  - 取り込み元: 第1引数のパス、または MOODMARK_STOCK_STATE_PATH、
    未指定時は tools.moodmark_stock.state の既定 JSON パス

注意: DB 上の moodmark_stock_* テーブルは上書き（全消去後に投入）されます。

例:
  export DATABASE_URL='postgresql://...'
  python scripts/migrate_article_stock_json_to_db.py ./article_stock_state.json
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.moodmark_stock.state import get_state_path, load_state  # noqa: E402
from tools.moodmark_stock.store import get_store  # noqa: E402


def main() -> int:
    if not os.environ.get("DATABASE_URL", "").strip():
        print("DATABASE_URL が必要です。", file=sys.stderr)
        return 1
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.environ.get("MOODMARK_STOCK_STATE_PATH", "").strip() or get_state_path()
    if not os.path.isfile(path):
        print(f"ファイルがありません: {path}", file=sys.stderr)
        return 1
    data = load_state(path)
    arts = data.get("articles") or []
    snap = data.get("last_snapshot")
    if not arts and not snap:
        print("記事も最終スナップショットも空です。中止します。", file=sys.stderr)
        return 1
    store = get_store()
    if store.backend_label != "postgresql":
        print("PostgreSQL ストアではありません（DATABASE_URL を確認）。", file=sys.stderr)
        return 1
    err = store.import_full_state(data)
    if err:
        print(err, file=sys.stderr)
        return 1
    print(f"取り込み完了: 記事 {len(arts)} 件", end="")
    if snap:
        print(f" / スナップショット 1 件", end="")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
