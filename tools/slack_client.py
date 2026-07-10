# -*- coding: utf-8 -*-
"""Slack Web API 共通クライアント。"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

SLACK_API_POST_MESSAGE = "https://slack.com/api/chat.postMessage"


def chat_post_message(
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
