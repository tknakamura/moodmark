#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事掲載商品の在庫可視化（MOO:D MARK）
"""

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from csv_to_html_dashboard import check_authentication, login_page

from tools.moodmark_stock.scraper import run_stock_check
from tools.moodmark_stock.state import import_state_json
from tools.moodmark_stock.store import get_store

st.set_page_config(
    page_title="記事掲載商品・在庫",
    page_icon="📦",
    layout="wide",
)

if not check_authentication():
    login_page()
    st.stop()

with st.sidebar:
    st.markdown("### 🔗 ダッシュボード")
    st.markdown("---")
    st.markdown("**📦 記事掲載商品・在庫**")
    st.markdown("（現在のページ）")
    st.markdown("")
    st.markdown(
        '[<div style="text-align: center;"><button style="background-color: #4CAF50; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%; margin-bottom: 0.5rem;">📄 CSV to HTML</button></div>](/)',
        unsafe_allow_html=True,
    )
    st.markdown(
        '[<div style="text-align: center;"><button style="background-color: #2196F3; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%; margin-bottom: 0.5rem;">📄 コミュニティコンバーター</button></div>](converter_community)',
        unsafe_allow_html=True,
    )
    st.markdown(
        '[<div style="text-align: center;"><button style="background-color: #FF4B4B; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%; margin-bottom: 0.5rem;">📊 GA4/GSC AI分析</button></div>](analytics_chat)',
        unsafe_allow_html=True,
    )
    st.markdown(
        '[<div style="text-align: center;"><button style="background-color: #9C27B0; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%;">🖼️ 画像クロップ</button></div>](image_resize)',
        unsafe_allow_html=True,
    )
    st.markdown("---")


def _invalidate_state_cache():
    st.session_state.pop("ams_state", None)


def _get_state():
    if "ams_state" not in st.session_state:
        st.session_state.ams_state = get_store().load_state()
    return st.session_state.ams_state


st.title("📦 記事掲載商品の在庫")
st.caption("登録した特集記事から商品URLを抽出し、在庫状態をまとめて表示します。")

store = get_store()
if os.environ.get("DATABASE_URL", "").strip():
    st.success(
        "データ保存先: **PostgreSQL**（`DATABASE_URL`）。記事一覧と実行履歴（最新結果）がDBに保存されます。"
    )
else:
    st.info(
        f"データ保存先: **JSON** `{store.backend_label.split(':', 1)[-1]}` 。"
        "PostgreSQL を使う場合は環境変数 **`DATABASE_URL`** を設定してください（Render でDBとWebを紐づけ）。"
    )

state = _get_state()

tab_manage, tab_run, tab_view, tab_backup = st.tabs(
    ["記事URLの管理", "在庫チェック実行", "結果の表示", "バックアップ / 復元"]
)

with tab_manage:
    st.subheader("記事URLの登録")
    c1, c2 = st.columns([3, 1])
    with c1:
        new_url = st.text_input(
            "記事URL",
            placeholder="https://isetan.mistore.jp/moodmark/birthday",
            key="ams_new_url",
        )
    with c2:
        new_label = st.text_input("表示ラベル（任意）", placeholder="誕生日特集", key="ams_new_label")

    if st.button("追加", type="primary", key="ams_add"):
        err = store.add_article(new_url, new_label)
        if err:
            st.error(err)
        else:
            _invalidate_state_cache()
            st.success("追加しました")
            st.rerun()

    st.subheader("登録一覧")
    arts = _get_state().get("articles") or []
    if not arts:
        st.warning("記事が未登録です。上でURLを追加してください。")
    else:
        st.dataframe(
            pd.DataFrame(arts)[["label", "url", "id"]],
            use_container_width=True,
            hide_index=True,
        )
        opts = {f"{a.get('label') or a.get('url')} ({a.get('id')})": a["id"] for a in arts}
        pick = st.selectbox("編集・削除する記事を選択", list(opts.keys()))
        aid = opts[pick]
        cur = next(x for x in arts if x["id"] == aid)
        eu = st.text_input("URL", value=cur.get("url", ""), key="ams_edit_url")
        el = st.text_input("ラベル", value=cur.get("label", ""), key="ams_edit_label")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("更新", key="ams_upd"):
                err = store.update_article(aid, url=eu, label=el)
                if err:
                    st.error(err)
                else:
                    _invalidate_state_cache()
                    st.success("更新しました")
                    st.rerun()
        with c2:
            if st.button("削除", key="ams_rm"):
                store.remove_article(aid)
                _invalidate_state_cache()
                st.success("削除しました")
                st.rerun()

with tab_run:
    st.subheader("今すぐ在庫チェック")
    delay = st.slider("リクエスト間隔（秒）", 0.3, 2.0, 0.75, 0.05)
    arts = _get_state().get("articles") or []
    if not arts:
        st.warning("先に「記事URLの管理」で記事を登録してください。")
    else:
        st.write(f"対象記事: **{len(arts)}** 件")
        if st.button("実行", type="primary", key="ams_run"):
            arts_now = get_store().load_state().get("articles") or []
            prog = st.progress(0.0)
            status = st.empty()

            def cb(msg, cur, tot):
                if tot:
                    prog.progress(min(1.0, (cur + 1) / max(tot, 1)))
                status.text(msg[-120:] if msg else "")

            try:
                snap = run_stock_check(
                    arts_now, request_delay_s=delay, progress_callback=cb
                )
            except Exception as e:
                st.error(f"実行エラー: {e}")
            else:
                get_store().record_snapshot(snap)
                _invalidate_state_cache()
                prog.progress(1.0)
                status.text("完了")
                w = snap.get("article_warnings") or []
                if w:
                    st.warning("警告（記事ごと）:")
                    for x in w:
                        st.write(f"- `{x.get('article_url')}`: {x.get('message')}")
                st.success(
                    f"完了: 商品 {len(snap.get('rows') or [])} 件（実行時刻: {snap.get('run_at', '')}）"
                )
                st.balloons()

with tab_view:
    state = _get_state()
    snap = state.get("last_snapshot")
    if not snap:
        st.info("まだ実行されていません。「在庫チェック実行」タブから実行してください。")
    else:
        st.subheader("サマリ")
        st.caption(f"最終実行（UTC）: `{snap.get('run_at', '')}`")
        rows = snap.get("rows") or []
        if not rows:
            st.warning("商品0件でした。")
        else:
            df = pd.DataFrame(rows)
            df["_oos"] = df["stock_status"].apply(lambda x: x != "in_stock")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("掲載商品数（ユニーク）", len(df))
            c2.metric("在庫あり", int((df["stock_status"] == "in_stock").sum()))
            c3.metric("入荷待ち", int((df["stock_status"] == "restock_wait").sum()))
            c4.metric("SOLD OUT等", int(df["_oos"].sum()))

            st.subheader("記事別: 掲載数 vs 在庫注意")
            article_to_products = snap.get("article_to_products") or {}
            product_stock = snap.get("product_stock") or {}
            summary_rows = []
            for aurl, plist in article_to_products.items():
                art = next(
                    (x for x in state.get("articles", []) if x.get("url") == aurl),
                    None,
                )
                label = (art or {}).get("label") or aurl
                n = len(plist)
                bad = sum(
                    1
                    for p in plist
                    if product_stock.get(p, {}).get("status") != "in_stock"
                )
                summary_rows.append(
                    {"記事": label, "掲載数": n, "在庫注意": bad, "article_url": aurl}
                )
            if summary_rows:
                sdf = pd.DataFrame(summary_rows)
                fig = go.Figure()
                fig.add_bar(
                    name="掲載数",
                    x=sdf["記事"],
                    y=sdf["掲載数"],
                    marker_color="rgb(100, 149, 237)",
                )
                fig.add_bar(
                    name="在庫注意（入荷待ち・SOLD OUT・エラー等）",
                    x=sdf["記事"],
                    y=sdf["在庫注意"],
                    marker_color="rgb(220, 80, 80)",
                )
                fig.update_layout(
                    barmode="group",
                    height=400,
                    xaxis_title="記事",
                    yaxis_title="件数",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                )
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("商品一覧")
            show = st.radio(
                "表示",
                ("すべて", "在庫注意のみ", "在庫ありのみ"),
                horizontal=True,
            )
            art_filter = st.selectbox(
                "記事で絞り込み",
                ["（すべて）"]
                + [a.get("label") or a.get("url") for a in state.get("articles", [])],
            )
            view = df.drop(columns=["_oos"], errors="ignore")
            if show == "在庫注意のみ":
                view = df[df["_oos"]].drop(columns=["_oos"], errors="ignore")
            elif show == "在庫ありのみ":
                view = df[df["stock_status"] == "in_stock"].drop(
                    columns=["_oos"], errors="ignore"
                )
            if art_filter != "（すべて）":
                art = next(
                    (
                        x
                        for x in state.get("articles", [])
                        if (x.get("label") or x.get("url")) == art_filter
                    ),
                    None,
                )
                if art:
                    u = art.get("url", "")
                    view = view[view["article_urls"].str.contains(u, na=False)]
            try:
                st.dataframe(
                    view,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "product_url": st.column_config.LinkColumn("商品ページ"),
                    },
                )
            except Exception:
                st.dataframe(view, use_container_width=True, hide_index=True)

with tab_backup:
    st.subheader("JSON ダウンロード")
    st.download_button(
        "現在の設定・最終結果をダウンロード",
        data=get_store().export_state_json(),
        file_name="article_stock_state.json",
        mime="application/json",
    )
    st.subheader("JSON アップロードで復元")
    up = st.file_uploader("article_stock_state.json", type=["json"])
    if up is not None:
        raw = up.read().decode("utf-8", errors="replace")
        data, err = import_state_json(raw)
        if err:
            st.error(err)
        else:
            if st.button("この内容で上書き保存", type="primary"):
                imp_err = get_store().import_full_state(data)
                if imp_err:
                    st.error(imp_err)
                else:
                    _invalidate_state_cache()
                    st.success("復元しました")
                    st.rerun()
