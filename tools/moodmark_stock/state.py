# -*- coding: utf-8 -*-
"""記事URL一覧と最終スナップショットのJSON永続化。"""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

STATE_VERSION = 1

DEFAULT_REL_PATH = os.path.join("data", "article_stock_state.json")


def get_state_path() -> str:
    return os.environ.get("MOODMARK_STOCK_STATE_PATH") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        DEFAULT_REL_PATH,
    )


DEFAULT_STATE_PATH = get_state_path()


def _empty_state() -> Dict[str, Any]:
    return {
        "version": STATE_VERSION,
        "articles": [],
        "last_snapshot": None,
        "updated_at": None,
    }


def load_state(path: Optional[str] = None) -> Dict[str, Any]:
    p = path or get_state_path()
    if not os.path.isfile(p):
        return _empty_state()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()
    if data.get("version") != STATE_VERSION:
        data = migrate_state(data)
    data.setdefault("articles", [])
    data.setdefault("last_snapshot", None)
    return data


def migrate_state(data: Dict[str, Any]) -> Dict[str, Any]:
    """将来バージョンアップ用フック。"""
    data["version"] = STATE_VERSION
    return data


def save_state(state: Dict[str, Any], path: Optional[str] = None) -> str:
    p = path or get_state_path()
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    out = deepcopy(state)
    out["version"] = STATE_VERSION
    out["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return p


def add_article(
    state: Dict[str, Any],
    url: str,
    label: str = "",
) -> Tuple[Dict[str, Any], Optional[str]]:
    """URL正規化して追加。エラー時は (state, error_msg)。"""
    u = _normalize_article_url(url)
    if not u:
        return state, "有効な記事URLを入力してください（isetan.mistore.jp の moodmark 配下推奨）"
    for a in state.get("articles", []):
        if a.get("url") == u:
            return state, "同じURLが既に登録されています"
    aid = str(uuid.uuid4())[:8]
    state.setdefault("articles", []).append(
        {"id": aid, "url": u, "label": (label or "").strip() or u}
    )
    return state, None


def remove_article(state: Dict[str, Any], article_id: str) -> Dict[str, Any]:
    state["articles"] = [a for a in state.get("articles", []) if a.get("id") != article_id]
    return state


def update_article(
    state: Dict[str, Any],
    article_id: str,
    url: Optional[str] = None,
    label: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    for a in state.get("articles", []):
        if a.get("id") != article_id:
            continue
        if url is not None and url.strip():
            nu = _normalize_article_url(url)
            if not nu:
                return state, "URLが無効です"
            a["url"] = nu
        if label is not None:
            a["label"] = label.strip() or a.get("url", "")
        return state, None
    return state, "記事が見つかりません"


def _normalize_article_url(url: str) -> str:
    s = (url or "").strip()
    if not s.startswith("http"):
        s = "https://" + s
    try:
        from urllib.parse import urlparse, urlunparse

        pr = urlparse(s)
        if not pr.netloc:
            return ""
        path = pr.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return urlunparse((pr.scheme, pr.netloc, path or "/", "", "", ""))
    except Exception:
        return ""


def export_state_json(state: Dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2)


def import_state_json(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return None, f"JSON解析エラー: {e}"
    if not isinstance(data, dict):
        return None, "ルートはオブジェクトである必要があります"
    data.setdefault("articles", [])
    data.setdefault("last_snapshot", None)
    data["version"] = STATE_VERSION
    return data, None


def attach_snapshot(state: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
    state["last_snapshot"] = snapshot
    return state
