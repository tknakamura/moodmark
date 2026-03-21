# -*- coding: utf-8 -*-
"""Streamlit 共通: ページ見出しにロゴ（img-logo.svg）を並べる。"""

from __future__ import annotations

import base64
import html
import logging
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LOGO_PATH = _REPO_ROOT / "img-logo.svg"


def _logo_data_uri() -> str:
    if not _LOGO_PATH.is_file():
        logger.warning("img-logo.svg が見つかりません: %s", _LOGO_PATH)
        return ""
    return "data:image/svg+xml;base64," + base64.standard_b64encode(
        _LOGO_PATH.read_bytes()
    ).decode("ascii")


def render_page_title_with_logo(
    title: str,
    *,
    title_element_id: str = "moodmark-page-title",
) -> None:
    """
    メインのページタイトル。img-logo.svg があれば左に並べ、無ければ st.title にフォールバック。
    """
    logo_src = _logo_data_uri()
    title_html = html.escape(title)
    safe_id = html.escape(title_element_id.strip(), quote=True)
    if logo_src:
        st.markdown(
            f'<div class="moodmark-page-title-row" style="display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;margin:0 0 0.25rem 0;">'
            f'<img src="{logo_src}" alt="MOO:D MARK" style="height:1.75rem;width:auto;max-width:min(45vw,220px);object-fit:contain;flex-shrink:0;" />'
            f'<h1 id="{safe_id}" style="margin:0;padding:0;font-size:calc(1.75rem + 0.5vw);font-weight:600;line-height:1.2;border:none;">{title_html}</h1>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.title(title)
