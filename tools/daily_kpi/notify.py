# -*- coding: utf-8 -*-
"""Daily KPI Bot の Slack 通知（親 + 複数スレッド返信）。"""

from __future__ import annotations

from typing import List, Optional

import requests

from tools.slack_client import chat_post_message

SLACK_MAX_TEXT = 5000


def _split_text(text: str, limit: int = SLACK_MAX_TEXT) -> List[str]:
    """Slack 文字数制限を超える場合に分割。"""
    body = (text or "").strip()
    if not body:
        return []
    if len(body) <= limit:
        return [body]
    chunks: List[str] = []
    while body:
        if len(body) <= limit:
            chunks.append(body)
            break
        split_at = body.rfind("\n", 0, limit)
        if split_at <= 0:
            split_at = limit
        chunks.append(body[:split_at].strip())
        body = body[split_at:].strip()
    return [c for c in chunks if c]


def post_slack_kpi_thread(
    parent: str,
    replies: List[str],
    *,
    bot_token: str,
    channel: str,
    timeout_s: float = 15.0,
) -> None:
    """Bot API で親メッセージを投稿し、スレッドに複数返信を順次投稿。"""
    token = (bot_token or "").strip()
    ch = (channel or "").strip()
    if not token or not ch:
        return
    parent_ts = chat_post_message(
        token,
        ch,
        parent.strip(),
        timeout_s=timeout_s,
    )
    for reply in replies:
        for chunk in _split_text(reply):
            chat_post_message(
                token,
                ch,
                chunk,
                thread_ts=parent_ts,
                timeout_s=timeout_s,
            )


def post_slack_kpi_webhook(
    parent: str,
    replies: List[str],
    webhook_url: str,
    *,
    timeout_s: float = 15.0,
) -> None:
    """Incoming Webhook に全メッセージを1通で投稿（スレッド不可）。"""
    url = (webhook_url or "").strip()
    if not url:
        return
    parts = [parent.strip()] + [r.strip() for r in replies if (r or "").strip()]
    text = "\n\n---\n\n".join(parts)
    resp = requests.post(
        url,
        json={"text": text[:SLACK_MAX_TEXT]},
        timeout=timeout_s,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
