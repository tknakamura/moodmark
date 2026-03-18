#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事掲載商品の在庫可視化（MOO:D MARK）
"""

import html as html_escape
import os
import sys

import pandas as pd
import streamlit.components.v1 as components
import streamlit as st

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from csv_to_html_dashboard import check_authentication, login_page

from tools.moodmark_stock.scraper import run_stock_check
from tools.moodmark_stock.state import import_state_json
from tools.moodmark_stock.store import get_store

RESULT_TABLE_HEADERS = {
    "product_url": "商品ページ",
    "product_name": "商品名",
    "article_count": "掲載記事数",
    "stock_label": "在庫表示",
    "error": "エラー",
    "article_urls": "掲載記事URL",
    "article_labels": "掲載記事ラベル",
}

# 結果表に出す列の順（在庫コード・ボタン文言・サブ文言は非表示）
RESULT_TABLE_COLUMN_ORDER = [
    "product_url",
    "product_name",
    "article_count",
    "stock_label",
    "error",
    "article_urls",
    "article_labels",
]


def _count_articles_from_urls(article_urls) -> int:
    """article_urls の ; 区切り非空要素数 = 掲載記事数。"""
    if article_urls is None or (isinstance(article_urls, float) and pd.isna(article_urls)):
        return 0
    s = str(article_urls).strip()
    if not s:
        return 0
    return len([p for p in s.split(";") if p.strip()])


def _result_df_to_clickable_html(df: pd.DataFrame) -> str:
    """商品URL・記事URLをクリックで開けるHTMLテーブル。"""
    cols = [c for c in RESULT_TABLE_COLUMN_ORDER if c in df.columns]
    th = "".join(
        f"<th>{html_escape.escape(RESULT_TABLE_HEADERS.get(c, c))}</th>" for c in cols
    )
    rows = []
    for _, row in df.iterrows():
        tds = []
        for c in cols:
            v = row[c]
            s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
            if c == "product_url" and s.startswith("http"):
                esc = html_escape.escape(s)
                cell = f'<a href="{esc}" target="_blank" rel="noopener noreferrer">{esc}</a>'
            elif c == "article_count":
                cell = html_escape.escape(s) if s else "0"
            elif c == "article_urls" and s:
                parts = [p.strip() for p in s.split(";") if p.strip()]
                links = []
                for p in parts:
                    if p.startswith("http"):
                        e = html_escape.escape(p)
                        links.append(
                            f'<a href="{e}" target="_blank" rel="noopener noreferrer">{e}</a>'
                        )
                    else:
                        links.append(html_escape.escape(p))
                cell = "<br>".join(links) if links else html_escape.escape(s)
            else:
                cell = html_escape.escape(s)
            tds.append(f"<td>{cell}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return (
        "<style>.article-stock-result-table a{color:#1976d2;text-decoration:underline;}"
        ".article-stock-result-table td{vertical-align:top;word-break:break-all;}"
        ".article-stock-result-table th,.article-stock-result-table td{padding:8px;border:1px solid #ddd;}"
        ".article-stock-result-table th{background:#f5f5f5;}</style>"
        '<table class="article-stock-result-table" style="border-collapse:collapse;width:100%;font-size:14px;">'
        f"<thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


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
    st.caption(
        "記事・商品は並列取得。前回実行から指定時間以内のデータは再GETしません（強制フルで無効化）。"
    )
    c1, c2 = st.columns(2)
    with c1:
        ttl_h = st.selectbox(
            "スキップするキャッシュの有効期間",
            [12, 24, 48],
            index=1,
            format_func=lambda x: f"{x} 時間以内なら記事・在庫をスキップ",
            key="ams_ttl",
        )
        force_full = st.checkbox(
            "強制フルチェック（キャッシュを使わず全件GET）", key="ams_force"
        )
    with c2:
        w_art = st.slider("記事ページ取得の同時接続数", 1, 16, 4, key="ams_wa")
        w_prd = st.slider("商品ページ取得の同時接続数", 1, 32, 12, key="ams_wp")
    delay = st.slider(
        "各ワーカーのリクエスト前待機（秒）",
        0.0,
        1.5,
        0.5,
        0.05,
        help="サイト負荷配慮のため **0.3〜0.5秒を推奨**。0にすると並列時の負荷が上がります。",
        key="ams_delay",
    )
    st.caption(
        "**推奨**: 待機 **0.3〜0.5秒**（既定 0.5秒）。短すぎると相手サーバへの負荷・ブロックのリスクが上がります。"
    )
    arts = _get_state().get("articles") or []
    if not arts:
        st.warning("先に「記事URLの管理」で記事を登録してください。")
    else:
        st.write(f"対象記事: **{len(arts)}** 件")
        if st.button("実行", type="primary", key="ams_run"):
            arts_now = get_store().load_state().get("articles") or []
            prev_snap = get_store().load_state().get("last_snapshot")
            prog = st.progress(0.0)
            status = st.empty()

            def cb(msg, cur, tot):
                if tot:
                    prog.progress(min(1.0, (cur + 1) / max(tot, 1)))
                status.text(msg[-120:] if msg else "")

            try:
                snap = run_stock_check(
                    arts_now,
                    request_delay_s=delay,
                    max_article_workers=int(w_art),
                    max_product_workers=int(w_prd),
                    previous_snapshot=prev_snap,
                    cache_ttl_hours=float(ttl_h),
                    force_full_refresh=force_full,
                    progress_callback=cb,
                )
            except Exception as e:
                st.error(f"実行エラー: {e}")
            else:
                get_store().record_snapshot(snap)
                _invalidate_state_cache()
                prog.progress(1.0)
                status.text("完了")
                rs = snap.get("run_stats") or {}
                st.info(
                    f"記事: 新規取得 {rs.get('articles_fetched', 0)} / キャッシュ利用 {rs.get('articles_cached', 0)} ・ "
                    f"商品: 新規取得 {rs.get('products_fetched', 0)} / キャッシュ利用 {rs.get('products_cached', 0)}"
                )
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
            if "product_name" not in df.columns:
                df["product_name"] = ""
            else:
                df["product_name"] = df["product_name"].fillna("").astype(str)
                df.loc[df["product_name"] == "nan", "product_name"] = ""
            order_front = ["product_url", "product_name"]
            order_mid = [
                "stock_status",
                "stock_label",
                "raw_main",
                "raw_sub",
                "error",
                "article_urls",
                "article_labels",
            ]
            cols = [c for c in order_front if c in df.columns]
            cols += [c for c in order_mid if c in df.columns]
            cols += [c for c in df.columns if c not in cols]
            df = df[cols]
            df["_oos"] = df["stock_status"].apply(lambda x: x != "in_stock")
            df["article_count"] = df["article_urls"].apply(_count_articles_from_urls)

            atp = snap.get("article_to_products") or {}
            total_slots = sum(len(plist) for plist in atp.values())
            slots_unknown = total_slots == 0 and len(df) > 0

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("ユニークSKU数", len(df))
            k2.metric(
                "記事上の掲載枠（合計）",
                "—" if slots_unknown else str(total_slots),
                help=None
                if not slots_unknown
                else "article_to_products が無い古いスナップショットの可能性があります。在庫チェックを再実行してください。",
            )
            k3.metric("在庫あり", int((df["stock_status"] == "in_stock").sum()))
            k4.metric("入荷待ち", int((df["stock_status"] == "restock_wait").sum()))
            k5.metric("SOLD OUT等", int(df["_oos"].sum()))
            st.caption(
                "掲載枠の合計は、記事をまたいだ同一商品の重複や、同一記事内の複数リンクを含みます。"
                " ユニークSKU数とは一致しません。"
            )

            st.subheader("記事別サマリ")
            st.caption(
                "掲載リンク数は当該記事内の商品URL数です。"
                " 記事間の合計はユニークSKU数と一致しません（同一商品の複数掲載など）。"
            )
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
            if not summary_rows:
                st.info("記事別の集計データがありません。")
            else:
                table_rows = []
                for r in summary_rows:
                    n = int(r["掲載数"])
                    bad = int(r["在庫注意"])
                    ok = n - bad
                    rate = f"{bad / n * 100:.1f}%" if n else "—"
                    u = str(r.get("article_url") or "").strip()
                    if u and not u.startswith(("http://", "https://")):
                        u = "https://" + u.lstrip("/")
                    table_rows.append(
                        {
                            "記事": r["記事"],
                            "掲載リンク数": n,
                            "在庫あり": ok,
                            "在庫注意": bad,
                            "在庫注意率": rate,
                            "記事URL": u,
                        }
                    )
                article_table = pd.DataFrame(table_rows)
                article_table = article_table.sort_values(
                    ["在庫注意", "掲載リンク数"],
                    ascending=[False, False],
                    kind="mergesort",
                )
                st.dataframe(
                    article_table,
                    column_config={
                        "記事URL": st.column_config.LinkColumn(
                            "記事を開く",
                            display_text="開く",
                        ),
                        "掲載リンク数": st.column_config.NumberColumn(
                            "掲載リンク数", format="%d", help="記事HTML内の商品URL数"
                        ),
                        "在庫あり": st.column_config.NumberColumn(
                            "在庫あり", format="%d", help="在庫OKと判定されたリンク数"
                        ),
                        "在庫注意": st.column_config.NumberColumn(
                            "在庫注意",
                            format="%d",
                            help="入荷待ち・SOLD OUT・取得エラー等",
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

            st.subheader("商品一覧")
            show = st.radio(
                "表示",
                ("すべて", "在庫注意のみ", "在庫ありのみ"),
                horizontal=True,
            )
            multi_article_only = st.checkbox(
                "2記事以上に掲載されている商品のみ",
                value=False,
                help="掲載記事数が2以上のSKUに絞り込みます。",
            )
            art_filter = st.selectbox(
                "記事で絞り込み",
                ["（すべて）"]
                + [a.get("label") or a.get("url") for a in state.get("articles", [])],
            )
            view = df.copy()
            if show == "在庫注意のみ":
                view = view[view["_oos"]]
            elif show == "在庫ありのみ":
                view = view[view["stock_status"] == "in_stock"]
            if multi_article_only:
                view = view[view["article_count"] >= 2]
            if show == "在庫注意のみ":
                view = view.sort_values(
                    "article_count", ascending=False, kind="mergesort"
                )
            view = view.drop(columns=["_oos"], errors="ignore")
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
            if view.empty:
                st.info("条件に一致する行がありません。")
            else:
                table_html = _result_df_to_clickable_html(view)
                h = min(720, 140 + len(view) * 36)
                components.html(
                    f'<div style="overflow:auto;max-height:680px;">{table_html}</div>',
                    height=h,
                    scrolling=True,
                )

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
