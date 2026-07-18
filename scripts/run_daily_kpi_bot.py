#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily KPI Bot — GA4 前々日 KPI を Slack に配信（GitHub Actions / 手動実行）。

毎朝 09:00 JST に前々日（JST）の確定データをレポートします。

環境変数:
  GOOGLE_CREDENTIALS_JSON   … サービスアカウント JSON（必須）
  GA4_PROPERTY_ID           … GA4 プロパティ ID（デフォルト 316302380）
  SLACK_BOT_TOKEN           … Slack Bot Token（推奨）
  SLACK_KPI_CHANNEL_ID      … 通知先チャンネル ID（例: C011BDFHN7N）
  SLACK_WEBHOOK_URL         … Bot 未設定時のフォールバック
  MOODMARK_KPI_NOTIFY_RUN_URL … Actions 実行ログ URL（任意）
  MOODMARK_KPI_DRY_RUN      … 1/true なら Slack 投稿せず stdout に出力
  MOODMARK_KPI_OFFSET_DAYS  … 対象日を N 日さらに過去へずらす（テスト用）

例:
  cd /path/to/moodmark && python scripts/run_daily_kpi_bot.py
  MOODMARK_KPI_DRY_RUN=1 python scripts/run_daily_kpi_bot.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.daily_kpi.format_slack import build_slack_messages  # noqa: E402
from tools.daily_kpi.ga4_collector import collect_daily_kpi, get_report_dates  # noqa: E402
from tools.daily_kpi.notify import post_slack_kpi_thread, post_slack_kpi_webhook  # noqa: E402


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def main() -> int:
    offset = int(os.environ.get("MOODMARK_KPI_OFFSET_DAYS", "0") or "0")
    report_date, compare_date = get_report_dates(offset_days=offset)

    print(f"Collecting Daily KPI: {report_date} vs {compare_date} (YoY, 364 days)")
    report = collect_daily_kpi(report_date=report_date, compare_date=compare_date)

    if report.errors:
        for err in report.errors:
            print(f"WARN: {err}", file=sys.stderr)

    run_url = (os.environ.get("MOODMARK_KPI_NOTIFY_RUN_URL") or "").strip() or None
    parent, replies = build_slack_messages(report, run_url=run_url)

    if _env_truthy("MOODMARK_KPI_DRY_RUN"):
        print("\n=== PARENT ===")
        print(parent)
        for i, reply in enumerate(replies, 1):
            print(f"\n=== REPLY {i} ===")
            print(reply)
        return 0 if not report.errors else 1

    bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel = (
        os.environ.get("SLACK_KPI_CHANNEL_ID", "").strip()
        or os.environ.get("SLACK_CHANNEL_ID", "").strip()
        or os.environ.get("SLACK_CHANNEL", "").strip()
    )
    hook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()

    if bot_token and channel:
        try:
            post_slack_kpi_thread(
                parent,
                replies,
                bot_token=bot_token,
                channel=channel,
            )
            print("Slack KPI thread notification sent.")
        except Exception as exc:
            print(f"Slack notify error: {exc}", file=sys.stderr)
            return 1
    elif hook:
        try:
            post_slack_kpi_webhook(parent, replies, hook)
            print("Slack KPI webhook notification sent.")
        except Exception as exc:
            print(f"Slack notify error: {exc}", file=sys.stderr)
            return 1
    else:
        print(
            "Slack not configured (set SLACK_BOT_TOKEN + SLACK_KPI_CHANNEL_ID or SLACK_WEBHOOK_URL).",
            file=sys.stderr,
        )
        return 1

    return 0 if not report.errors else 1


if __name__ == "__main__":
    sys.exit(main())
