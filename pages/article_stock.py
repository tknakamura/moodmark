#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事掲載商品の在庫可視化（MOO:D MARK）
"""

import html as html_escape
import logging
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from csv_to_html_dashboard import (
    check_authentication,
    login_page,
    render_likepass_footer,
)

from tools.moodmark_stock.scraper import (
    product_slug_for_ga4_item_id,
    run_stock_check,
)
from tools.moodmark_stock import state as moodmark_state
from tools.moodmark_stock.store import get_store

logger = logging.getLogger(__name__)

RESULT_TABLE_HEADERS = {
    "product_url": "商品ページ",
    "product_name_display": "商品名",
    "ga4_items_purchased": "GA4購入数(7日)",
    "ga4_item_revenue": "GA4収益(7日)",
    "article_count": "記事",
    "stock_label": "在庫表示",
    "article_urls": "掲載記事URL",
    "article_labels": "掲載記事ラベル",
}

# 結果表に出す列の順（在庫コード・ボタン文言・サブ文言は非表示）
RESULT_TABLE_COLUMN_ORDER = [
    "product_url",
    "product_name_display",
    "ga4_items_purchased",
    "ga4_item_revenue",
    "article_count",
    "stock_label",
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
            elif c == "article_labels" and s:
                parts = [p.strip() for p in s.split(";") if p.strip()]
                cell = (
                    "<br>".join(html_escape.escape(p) for p in parts)
                    if parts
                    else html_escape.escape(s)
                )
            elif c == "ga4_items_purchased":
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    cell = "—"
                else:
                    try:
                        cell = html_escape.escape(str(int(v)))
                    except (TypeError, ValueError):
                        cell = html_escape.escape(str(v))
            elif c == "ga4_item_revenue":
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    cell = "—"
                else:
                    try:
                        cell = html_escape.escape(f"{float(v):,.2f}")
                    except (TypeError, ValueError):
                        cell = html_escape.escape(str(v))
            else:
                cell = html_escape.escape(s)
            tds.append(f"<td>{cell}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    # 在庫表示: 適切な幅 / 掲載記事ラベル: 2倍幅
    colgroup = ""
    for i, c in enumerate(cols):
        if c == "stock_label":
            colgroup += '<col style="width:9em">'
        elif c == "article_labels":
            colgroup += '<col style="min-width:18em;width:28%">'
        else:
            colgroup += "<col>"
    return (
        '<table class="article-stock-result-table">'
        f"<colgroup>{colgroup}</colgroup>"
        f"<thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _ensure_product_display_and_ga4_columns(df: pd.DataFrame) -> pd.DataFrame:
    """古いスナップショット互換: 表示用商品名と GA4 列を揃える。"""
    df = df.copy()
    if "product_name" not in df.columns:
        df["product_name"] = ""
    else:
        df["product_name"] = df["product_name"].fillna("").astype(str)
        df.loc[df["product_name"] == "nan", "product_name"] = ""
    if "product_name_display" not in df.columns:
        if "ga4_item_name" in df.columns:
            gn = df["ga4_item_name"].fillna("").astype(str)
            df["product_name_display"] = gn.where(gn.str.strip() != "", df["product_name"])
        else:
            df["product_name_display"] = df["product_name"]
    else:
        df["product_name_display"] = df["product_name_display"].fillna("").astype(str)
        df.loc[df["product_name_display"] == "nan", "product_name_display"] = ""
        empty = df["product_name_display"].str.strip() == ""
        df.loc[empty, "product_name_display"] = df.loc[empty, "product_name"]
    for c, default in (
        ("ga4_items_purchased", None),
        ("ga4_item_revenue", None),
    ):
        if c not in df.columns:
            df[c] = default
    return df


def _enrich_snapshot_rows_ga4_commerce(snap: dict, *, lag_days: int = 3, window_days: int = 7) -> None:
    """snap['rows'] を in-place で GA4 itemName / 購入数 / 収益で拡張。失敗時はログのみ。"""
    rows = snap.get("rows") or []
    if not rows:
        return
    try:
        from analytics.google_apis_integration import GoogleAPIsIntegration
    except ImportError:
        logger.warning("GoogleAPIsIntegration をインポートできません")
        return
    api = GoogleAPIsIntegration()
    if not api.ga4_service or not api.ga4_property_id:
        return

    url_to_slug: dict = {}
    slugs_ordered: list = []
    for r in rows:
        url = (r.get("product_url") or "").strip()
        if not url:
            continue
        sid = product_slug_for_ga4_item_id(url)
        if sid:
            url_to_slug[url] = sid
            slugs_ordered.append(sid)
    unique_slugs = list(dict.fromkeys(slugs_ordered))
    if not unique_slugs:
        for r in rows:
            scraped = (r.get("product_name") or "").strip()
            r["product_name_display"] = scraped
        return

    try:
        commerce = api.get_item_commerce_by_item_ids(
            unique_slugs, lag_days=lag_days, window_days=window_days
        )
    except Exception as e:
        logger.warning("GA4 商品コマース取得エラー: %s", e)
        for r in rows:
            scraped = (r.get("product_name") or "").strip()
            r["product_name_display"] = scraped
        return

    for r in rows:
        url = (r.get("product_url") or "").strip()
        sid = url_to_slug.get(url)
        scraped = (r.get("product_name") or "").strip()
        if not sid:
            r["ga4_item_id"] = None
            r["ga4_item_name"] = ""
            r["ga4_items_purchased"] = None
            r["ga4_item_revenue"] = None
            r["product_name_display"] = scraped
            continue
        info = commerce.get(sid)
        if not info:
            r["ga4_item_id"] = sid
            r["ga4_item_name"] = ""
            r["ga4_items_purchased"] = 0
            r["ga4_item_revenue"] = 0.0
            r["product_name_display"] = scraped
            continue
        name = (info.get("item_name") or "").strip()
        ip = info.get("items_purchased")
        ir = info.get("item_revenue")
        r["ga4_item_id"] = sid
        r["ga4_item_name"] = name
        try:
            r["ga4_items_purchased"] = int(round(float(ip))) if ip is not None else 0
        except (TypeError, ValueError):
            r["ga4_items_purchased"] = 0
        try:
            r["ga4_item_revenue"] = float(ir) if ir is not None else 0.0
        except (TypeError, ValueError):
            r["ga4_item_revenue"] = 0.0
        r["product_name_display"] = name or scraped


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


def _sync_article_ga4_pageviews(store, article_id: str, article_url: str) -> None:
    try:
        from analytics.google_apis_integration import GoogleAPIsIntegration
    except ImportError:
        logger.warning("GoogleAPIsIntegration をインポートできません")
        return
    api = GoogleAPIsIntegration()
    if not api.ga4_service or not api.ga4_property_id:
        return
    path = (urlparse(article_url).path or "").strip() or "/"
    fetched_at = datetime.now(timezone.utc)
    try:
        pv = api.get_screen_page_views_for_path(path)
        store.set_article_ga4_pageviews(
            article_id,
            fetched_at,
            pageviews=pv,
        )
    except Exception as e:
        logger.warning("記事GA4 PV取得エラー (%s): %s", article_url, e)
        store.set_article_ga4_pageviews(
            article_id,
            fetched_at,
            error=str(e)[:512],
        )


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

# タブを横幅均等・切り替えやすく
st.markdown(
    """
<style>
.stTabs [data-baseweb="tab-list"] { width: 100%; display: flex; }
.stTabs [data-baseweb="tab-list"] [data-baseweb="tab"] {
  flex: 1; justify-content: center; min-width: 0;
  padding: 12px 16px; min-height: 48px;
}
/* 商品一覧: 記事別サマリ（st.dataframe）に近い本文スケール */
.article-stock-result-table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  font-size: 0.875rem;
  line-height: 1.375;
  font-family: inherit;
}
.article-stock-result-table a {
  color: #1976d2;
  text-decoration: underline;
  font-size: inherit;
}
.article-stock-result-table td { vertical-align: top; word-break: break-all; }
.article-stock-result-table th,
.article-stock-result-table td { padding: 8px; border: 1px solid #ddd; }
.article-stock-result-table th { background: #f5f5f5; }
</style>""",
    unsafe_allow_html=True,
)
# 結果の表示をデフォルトにするため先頭に配置
tab_view, tab_manage, tab_run, tab_backup = st.tabs(
    ["結果の表示", "記事URLの管理", "在庫チェック実行", "バックアップ / 復元"]
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
            nu = moodmark_state._normalize_article_url(new_url)
            fresh = get_store().load_state()
            art = next(
                (a for a in fresh.get("articles", []) if a.get("url") == nu),
                None,
            )
            if art:
                with st.spinner("GA4から表示回数を取得中…"):
                    _sync_article_ga4_pageviews(store, art["id"], art["url"])
            _invalidate_state_cache()
            st.success("追加しました")
            st.rerun()

    st.subheader("登録一覧")
    arts = _get_state().get("articles") or []
    if not arts:
        st.warning("記事が未登録です。上でURLを追加してください。")
    else:
        df_reg = pd.DataFrame(arts)
        reg_cols = ["label", "url", "id"]
        for c in ("ga4_pageviews_7d", "ga4_pv_fetched_at"):
            if c in df_reg.columns:
                reg_cols.append(c)
        st.dataframe(
            df_reg[[c for c in reg_cols if c in df_reg.columns]],
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
                    fresh = get_store().load_state()
                    art = next(
                        (a for a in fresh.get("articles", []) if a.get("id") == aid),
                        None,
                    )
                    if art:
                        with st.spinner("GA4から表示回数を取得中…"):
                            _sync_article_ga4_pageviews(
                                store, aid, art.get("url", "")
                            )
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
        fetch_ga4_commerce = st.checkbox(
            "GA4で商品名（itemName）・購入数・収益を取得",
            value=True,
            key="ams_ga4_commerce",
            help="期間は記事のPV(7日)と同じ（終端3日前から遡る7日）。purchase 由来の指標です。",
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
    st.caption(
        "**記事の絞り込み**: 下で選んだ記事だけ記事ページを再取得します。"
        " 選んでいない記事は**前回の実行結果**をそのまま表示用データに使います（初回のみ前回がないため未選択は商品0件になります）。"
    )
    arts = _get_state().get("articles") or []
    if not arts:
        st.warning("先に「記事URLの管理」で記事を登録してください。")
    else:
        article_url_options = []
        url_labels = {}
        for a in arts:
            u = (a.get("url") or "").strip()
            if not u:
                continue
            article_url_options.append(u)
            url_labels[u] = f"{a.get('label') or u} ({a.get('id', '')})"
        selected_urls = st.multiselect(
            "在庫チェックする記事",
            options=article_url_options,
            default=article_url_options,
            format_func=lambda u: url_labels.get(u, u),
            key="ams_article_scope",
            help="すべて選択＝従来どおり全記事が対象。一部だけ選ぶと部分チェックになります。",
        )
        st.write(f"登録記事: **{len(article_url_options)}** 件 / 今回チェック: **{len(selected_urls)}** 件")
        if st.button("実行", type="primary", key="ams_run"):
            if not selected_urls:
                st.warning("1件以上選んでください。")
            else:
                arts_now = get_store().load_state().get("articles") or []
                prev_snap = get_store().load_state().get("last_snapshot")
                all_set = set(article_url_options)
                sel_set = set(selected_urls)
                only_urls = None
                if sel_set != all_set or len(selected_urls) != len(article_url_options):
                    only_urls = list(selected_urls)
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
                        only_check_article_urls=only_urls,
                    )
                except Exception as e:
                    st.error(f"実行エラー: {e}")
                else:
                    if fetch_ga4_commerce:
                        with st.spinner(
                            "GA4から商品の itemName・購入数・収益を取得中…"
                        ):
                            _enrich_snapshot_rows_ga4_commerce(snap)
                    get_store().record_snapshot(snap)
                    _invalidate_state_cache()
                    prog.progress(1.0)
                    status.text("完了")
                    rs = snap.get("run_stats") or {}
                    extra = ""
                    if rs.get("articles_preserved_without_fetch"):
                        extra = (
                            f" ・ 前回結果を維持した記事 {rs.get('articles_preserved_without_fetch', 0)} 件"
                        )
                    st.info(
                        f"記事: 新規取得 {rs.get('articles_fetched', 0)} / キャッシュ利用 {rs.get('articles_cached', 0)}"
                        f"{extra} ・ "
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
            df = _ensure_product_display_and_ga4_columns(df)
            order_front = ["product_url", "product_name_display"]
            order_ga4 = ["ga4_items_purchased", "ga4_item_revenue"]
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
            cols += [c for c in order_ga4 if c in df.columns]
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
            k4.metric("在庫注意", int(df["_oos"].sum()))
            k5.metric("入荷待ち", int((df["stock_status"] == "restock_wait").sum()))
            st.caption(
                "掲載枠の合計は、記事をまたいだ同一商品の重複や、同一記事内の複数リンクを含みます。"
                " ユニークSKU数とは一致しません。"
            )

            st.subheader("記事別サマリ")
            st.caption(
                "掲載リンク数は当該記事内の商品URL数です。"
                " 記事間の合計はユニークSKU数と一致しません（同一商品の複数掲載など）。"
            )
            st.caption(
                "PV(7日): GA4の画面表示回数（screenPageViews）。"
                " 期間の終端は本日から3日前、そこからさかのぼる7日間（処理遅延を避けるため）。"
                " 記事の登録・更新時に取得します。"
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
                pv7 = None
                if art is not None and art.get("ga4_pageviews_7d") is not None:
                    try:
                        pv7 = int(art["ga4_pageviews_7d"])
                    except (TypeError, ValueError):
                        pv7 = None
                summary_rows.append(
                    {
                        "記事": label,
                        "掲載数": n,
                        "在庫注意": bad,
                        "article_url": aurl,
                        "PV(7日)": pv7,
                    }
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
                    pv_cell = r.get("PV(7日)")
                    table_rows.append(
                        {
                            "記事": r["記事"],
                            "掲載リンク数": n,
                            "在庫あり": ok,
                            "在庫注意": bad,
                            "在庫注意率": rate,
                            "PV(7日)": pv_cell,
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
                        # display_text は Streamlit 1.29+ のみ（requirements は 1.28.1）
                        "記事URL": st.column_config.LinkColumn(
                            "記事URL",
                            help="クリックで記事ページを開きます",
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
                        "PV(7日)": st.column_config.NumberColumn(
                            "PV(7日)",
                            format="%d",
                            help="GA4 screenPageViews（終端3日前から遡る7日間）。未取得は空欄。",
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

            st.subheader("商品一覧")
            st.caption(
                "商品名は GA4 の itemName が取得できていればそれを表示し、なければページから取得した名称です。"
                " GA4購入数・収益は purchase 由来で、記事PV(7日)と同じ期間（終端＝本日から3日前、そこから遡る7日間）。"
                " 通貨は GA4 プロパティの設定に依存します。"
            )
            show = st.radio(
                "表示",
                ("すべて", "在庫注意のみ", "在庫ありのみ"),
                index=1,
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
                # メイン DOM で描画（st.dataframe と同じフォント階層を継承）。iframe の components.html は避ける。
                st.markdown(
                    f'<div style="overflow:auto;max-height:920px;">{table_html}</div>',
                    unsafe_allow_html=True,
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
        data, err = moodmark_state.import_state_json(raw)
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

render_likepass_footer()
