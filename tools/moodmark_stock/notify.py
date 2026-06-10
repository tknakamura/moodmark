# -*- coding: utf-8 -*-
"""在庫チェック完了の Slack 通知（Bot API / Incoming Webhook）。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
SLACK_API_POST_MESSAGE = "https://slack.com/api/chat.postMessage"


def _parse_run_at(run_at: Any) -> Optional[datetime]:
    if not run_at:
        return None
    s = str(run_at).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def _format_run_times(run_at: Any) -> str:
    dt = _parse_run_at(run_at)
    if not dt:
        return str(run_at or "—")
    utc_s = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    jst_s = dt.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")
    return f"{utc_s} / {jst_s}"


def _format_run_date_jst(run_at: Any) -> str:
    dt = _parse_run_at(run_at)
    if not dt:
        return "—"
    return dt.astimezone(JST).strftime("%m/%d")


def _summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    n = len(rows)
    in_stock = 0
    restock = 0
    sold_out = 0
    fetch_err = 0
    other_oos = 0
    for r in rows:
        st = (r.get("stock_status") or "unknown").strip()
        if st == "in_stock":
            in_stock += 1
        elif st == "restock_wait":
            restock += 1
        elif st == "fetch_error":
            fetch_err += 1
        elif st in ("sold_out", "out_of_stock"):
            sold_out += 1
        elif st != "in_stock":
            other_oos += 1
    oos = n - in_stock
    return {
        "total": n,
        "in_stock": in_stock,
        "oos": oos,
        "restock": restock,
        "sold_out": sold_out,
        "fetch_error": fetch_err,
        "other_oos": other_oos,
    }


def _summary_one_liner(stats: Dict[str, int]) -> str:
    if stats["oos"] == 0:
        return f"ユニーク商品 {stats['total']} 件 / *すべて在庫あり*"
    return f"ユニーク商品 {stats['total']} 件 / 在庫注意 *{stats['oos']}* 件"


def _alert_line_items(rows: List[Dict[str, Any]], limit: int = 5) -> List[str]:
    items: List[str] = []
    for r in rows:
        st = (r.get("stock_status") or "").strip()
        if st == "in_stock":
            continue
        name = (r.get("product_name") or r.get("product_name_display") or "").strip()
        url = (r.get("product_url") or "").strip()
        label = (r.get("stock_label") or st or "在庫注意").strip()
        if name:
            items.append(f"• {name} — {label}")
        elif url:
            items.append(f"• {url} — {label}")
        else:
            items.append(f"• {label}")
        if len(items) >= limit:
            break
    return items


def build_parent_text(snap: Dict[str, Any]) -> str:
    """スレッド親メッセージ: タイトル（mm/dd）+ 主要サマリ1行。"""
    rows = snap.get("rows") or []
    stats = _summarize_rows(rows)
    date_s = _format_run_date_jst(snap.get("run_at"))
    title = f"*MOO:D MARK 在庫チェック完了（{date_s}）*"
    return f"{title}\n{_summary_one_liner(stats)}"


def build_thread_detail_text(
    snap: Dict[str, Any],
    articles: List[Dict[str, Any]],
    *,
    run_url: Optional[str] = None,
) -> str:
    """スレッド返信用の詳細テキスト。"""
    rows = snap.get("rows") or []
    stats = _summarize_rows(rows)
    warnings = snap.get("article_warnings") or []
    w_count = len(warnings) if isinstance(warnings, list) else 0
    art_count = len(articles) if articles else 0

    lines = [
        f"実行時刻: {_format_run_times(snap.get('run_at'))}",
        f"登録記事: {art_count} 件 / ユニーク商品: {stats['total']} 件",
    ]

    if stats["oos"] == 0:
        lines.append("*すべて在庫あり*（在庫注意 0 件）")
    else:
        lines.append(
            f"在庫注意 *{stats['oos']}* 件 "
            f"（入荷待ち {stats['restock']}, SOLD OUT等 {stats['sold_out'] + stats['other_oos']}, "
            f"取得エラー {stats['fetch_error']}）"
        )
        alert_items = _alert_line_items(rows)
        if alert_items:
            lines.append("")
            lines.append("在庫注意（最大5件）:")
            lines.extend(alert_items)

    if w_count:
        lines.append("")
        lines.append(f"記事警告: {w_count} 件")
        for w in warnings[:3]:
            if isinstance(w, dict):
                lines.append(
                    f"• {w.get('article_url', '')}: {w.get('message', '')}"
                )

    rs = snap.get("run_stats") or {}
    if rs:
        lines.append("")
        lines.append(
            f"取得: 記事 新規 {rs.get('articles_fetched', 0)} / キャッシュ {rs.get('articles_cached', 0)}"
            f" · 商品 新規 {rs.get('products_fetched', 0)} / キャッシュ {rs.get('products_cached', 0)}"
        )

    if run_url:
        lines.append("")
        lines.append(f"<{run_url}|GitHub Actions の実行ログ>")

    return "\n".join(lines)


def build_slack_summary_text(
    snap: Dict[str, Any],
    articles: List[Dict[str, Any]],
    *,
    run_url: Optional[str] = None,
) -> str:
    """Slack 用プレーンテキスト（Incoming Webhook の text フィールド）。"""
    parent = build_parent_text(snap)
    detail = build_thread_detail_text(snap, articles, run_url=run_url)
    return f"{parent}\n\n{detail}"


def _chat_post_message(
    bot_token: str,
    channel: str,
    text: str,
    *,
    thread_ts: Optional[str] = None,
    timeout_s: float = 15.0,
) -> str:
    """Slack chat.postMessage を呼び出し、投稿の ts を返す。"""
    payload: Dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    resp = requests.post(
        SLACK_API_POST_MESSAGE,
        json=payload,
        timeout=timeout_s,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")
    ts = data.get("ts")
    if not ts:
        raise RuntimeError("Slack API did not return ts")
    return str(ts)


def post_slack_thread(
    snap: Dict[str, Any],
    articles: List[Dict[str, Any]],
    *,
    bot_token: str,
    channel: str,
    run_url: Optional[str] = None,
    timeout_s: float = 15.0,
) -> None:
    """Bot API で親メッセージを投稿し、スレッドに詳細を返信。失敗時は例外を送出。"""
    token = (bot_token or "").strip()
    ch = (channel or "").strip()
    if not token or not ch:
        return
    parent_ts = _chat_post_message(
        token,
        ch,
        build_parent_text(snap),
        timeout_s=timeout_s,
    )
    detail = build_thread_detail_text(snap, articles, run_url=run_url)
    if detail.strip():
        _chat_post_message(
            token,
            ch,
            detail,
            thread_ts=parent_ts,
            timeout_s=timeout_s,
        )


def post_slack_summary(
    snap: Dict[str, Any],
    articles: List[Dict[str, Any]],
    webhook_url: str,
    *,
    run_url: Optional[str] = None,
    timeout_s: float = 15.0,
) -> None:
    """Incoming Webhook にサマリを投稿。失敗時は例外を送出。"""
    url = (webhook_url or "").strip()
    if not url:
        return
    text = build_slack_summary_text(snap, articles, run_url=run_url)
    resp = requests.post(
        url,
        json={"text": text},
        timeout=timeout_s,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
