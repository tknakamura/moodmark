#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GA4/GSC AI分析チャットページ
Streamlitマルチページ機能を使用
"""

import streamlit as st
import sys
import os
import warnings
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd

# importlib.metadataエラーの警告を抑制
warnings.filterwarnings('ignore', message='.*importlib.metadata.*packages_distributions.*')

# 環境変数の読み込み（オプショナル）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenvがインストールされていない場合は環境変数が既に設定されていると仮定
    pass

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from analytics.ai_analytics_chat import AIAnalyticsChat
from csv_to_html_dashboard import (
    render_dashboard_sidebar_nav,
    render_likepass_footer,
    require_dashboard_login,
)
from tools.streamlit_branding import render_page_title_with_logo

# ページ設定（最初のStreamlitコマンドである必要がある）
st.set_page_config(
    page_title="GA4/GSC AI分析チャット",
    page_icon="📊",
    layout="wide"
)
require_dashboard_login()

# タイトル
render_page_title_with_logo(
    "📊 GA4/GSC AI分析チャット",
    title_element_id="analytics-chat-title",
)
st.markdown("Google Analytics 4とGoogle Search ConsoleのデータをAIが分析し、質問にお答えします。")

# セッション状態の初期化（最初に実行）
from datetime import datetime, timedelta

# 各属性を個別に初期化（順序に依存しない）
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ai_chat" not in st.session_state:
    st.session_state.ai_chat = None
if "model" not in st.session_state:
    st.session_state.model = "gpt-4o-mini"
if "date_range_days" not in st.session_state:
    st.session_state.date_range_days = 30
if "start_date" not in st.session_state:
    st.session_state.start_date = None
if "end_date" not in st.session_state:
    st.session_state.end_date = None
if "keyword" not in st.session_state:
    st.session_state.keyword = ""
if "landing_page" not in st.session_state:
    st.session_state.landing_page = ""
if "comparison_mode" not in st.session_state:
    st.session_state.comparison_mode = "year_over_year"  # デフォルトは前年同時期対比

# 日付範囲選択ボタン
col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
with col1:
    if st.button("直近7日", use_container_width=True):
        st.session_state.date_range_days = 7
        st.session_state.start_date = None
        st.session_state.end_date = None
        st.rerun()
with col2:
    if st.button("直近30日", use_container_width=True):
        st.session_state.date_range_days = 30
        st.session_state.start_date = None
        st.session_state.end_date = None
        st.rerun()
with col3:
    if st.button("直近90日", use_container_width=True):
        st.session_state.date_range_days = 90
        st.session_state.start_date = None
        st.session_state.end_date = None
        st.rerun()

# 日付範囲の表示
if st.session_state.start_date and st.session_state.end_date:
    date_range_text = f"期間: {st.session_state.start_date} 〜 {st.session_state.end_date}"
else:
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=st.session_state.date_range_days - 1)).strftime('%Y-%m-%d')
    date_range_text = f"期間: {start_date} 〜 {end_date} (過去{st.session_state.date_range_days}日間)"
st.caption(date_range_text)
st.markdown("---")

# サイドバー設定
with st.sidebar:
    render_dashboard_sidebar_nav()

    st.header("⚙️ 設定")
    
    # サイト選択
    st.subheader("🌐 サイト選択")
    if 'selected_site' not in st.session_state:
        st.session_state.selected_site = 'moodmark'
    
    site_options = {
        'moodmark': 'MOODMARK (https://isetan.mistore.jp/moodmark/)',
        'moodmarkgift': 'MOODMARK GIFT (https://isetan.mistore.jp/moodmarkgift/)'
    }
    
    selected_site = st.radio(
        "分析するサイトを選択",
        options=list(site_options.keys()),
        format_func=lambda x: site_options[x],
        index=0 if st.session_state.selected_site == 'moodmark' else 1,
        key="site_selector"
    )
    st.session_state.selected_site = selected_site
    st.caption(f"選択中: {site_options[selected_site]}")
    
    st.markdown("---")
    
    # モデル選択
    st.subheader("🤖 AIモデル")
    available_models = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo"
    ]
    selected_model = st.selectbox(
        "使用するAIモデル",
        available_models,
        index=0,
        key="model_selector"
    )
    st.session_state.model = selected_model
    
    st.markdown("---")
    
    # 接続状態の確認
    st.subheader("🔌 接続状態")
    
    # AIチャットの初期化
    if st.session_state.ai_chat is None:
        try:
            with st.spinner("AIチャットを初期化中..."):
                credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'config/google-credentials-474807.json')
                credentials_path = os.path.join(project_root, credentials_file)
                
                openai_api_key = os.getenv('OPENAI_API_KEY')
                if not openai_api_key:
                    st.error("⚠️ OpenAI APIキーが設定されていません")
                    st.info("環境変数OPENAI_API_KEYを設定してください。")
                else:
                    st.session_state.ai_chat = AIAnalyticsChat(
                        credentials_file=credentials_path,
                        openai_api_key=openai_api_key
                    )
                    st.success("✅ AIチャット初期化完了")
        except Exception as e:
            st.error(f"❌ 初期化エラー: {str(e)}")
            st.info("設定を確認してください。")
    else:
        st.success("✅ AIチャット接続済み")
        
        # Google APIs接続状態の確認
        st.markdown("---")
        st.subheader("📊 Google APIs接続状態")
        
        # 認証状態の確認
        auth_status = st.session_state.ai_chat.google_apis.check_authentication_status()
        
        # GA4接続状態
        if auth_status['ga4_service_initialized'] and auth_status['ga4_property_id_set']:
            st.success("✅ GA4: 接続済み")
        else:
            st.error("❌ GA4: 未接続")
            if not auth_status['ga4_service_initialized']:
                st.caption("GA4サービスが初期化されていません")
            if not auth_status['ga4_property_id_set']:
                st.caption("GA4_PROPERTY_IDが設定されていません")
        
        # GSC接続状態
        if auth_status['gsc_service_initialized'] and auth_status['gsc_site_url_set']:
            st.success("✅ GSC: 接続済み")
        else:
            st.error("❌ GSC: 未接続")
            if not auth_status['gsc_service_initialized']:
                st.caption("GSCサービスが初期化されていません")
            if not auth_status['gsc_site_url_set']:
                st.caption("GSC_SITE_URLが設定されていません")
        
        # エラーがある場合の表示
        if auth_status['errors']:
            with st.expander("⚠️ エラー詳細", expanded=True):
                for error in auth_status['errors']:
                    st.error(error)
                
                # 診断情報の表示
                if auth_status.get('diagnostics'):
                    st.markdown("**診断情報:**")
                    diagnostics = auth_status['diagnostics']
                    
                    if diagnostics.get('credentials_type') == 'GOOGLE_CREDENTIALS_JSON':
                        st.info("💡 **推奨**: `GOOGLE_CREDENTIALS_JSON`環境変数が設定されています。")
                        st.info("認証ファイル（JSON）の内容全体を環境変数に貼り付けてください。")
                        if not diagnostics.get('json_valid', True):
                            st.error("JSON形式が不正です。正しいJSON形式であることを確認してください。")
                    elif diagnostics.get('credentials_type') == 'GOOGLE_CREDENTIALS_FILE':
                        st.info("💡 `GOOGLE_CREDENTIALS_FILE`環境変数が設定されています。")
                        
                        # GOOGLE_CREDENTIALS_FILEにJSONが設定されている場合
                        if diagnostics.get('credentials_file_contains_json', False):
                            st.error("⚠️ **問題**: `GOOGLE_CREDENTIALS_FILE`にJSONの内容が設定されています。")
                            st.warning("""
                            **正しい設定方法:**
                            
                            1. Render.comの環境変数から`GOOGLE_CREDENTIALS_FILE`を削除
                            2. 新しい環境変数を追加:
                               - **Key**: `GOOGLE_CREDENTIALS_JSON`
                               - **Value**: `GOOGLE_CREDENTIALS_FILE`に設定されていたJSONの内容をそのまま貼り付け
                            3. デプロイを再実行
                            """)
                        elif not diagnostics.get('file_exists', False):
                            st.error(f"ファイルが見つかりません: {os.getenv('GOOGLE_CREDENTIALS_FILE')}")
                            st.info("Render.comでファイルをアップロードするか、`GOOGLE_CREDENTIALS_JSON`環境変数を使用してください。")
                    else:
                        st.warning("認証情報の設定方法:")
                        st.markdown("""
                        1. **推奨方法**: `GOOGLE_CREDENTIALS_JSON`環境変数を設定
                           - 認証ファイル（JSON）の内容全体をコピー
                           - Render.comの環境変数に貼り付け
                        
                        2. **代替方法**: `GOOGLE_CREDENTIALS_FILE`環境変数を設定
                           - 認証ファイルをRender.comにアップロード
                           - ファイルパスを環境変数に設定
                        """)
        
        # 警告がある場合の表示
        if auth_status['warnings']:
            with st.expander("⚠️ 警告", expanded=False):
                for warning in auth_status['warnings']:
                    st.warning(warning)
        
        # 接続テストボタン
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 GA4接続テスト", use_container_width=True, key="test_ga4_button"):
                with st.spinner("GA4接続をテスト中..."):
                    test_result = st.session_state.ai_chat.google_apis.test_ga4_connection()
                    if test_result['success']:
                        st.success(test_result['message'])
                        if test_result.get('data_sample'):
                            st.caption(f"データサンプル: {test_result['data_sample']['row_count']}件 ({test_result['data_sample']['date_range']})")
                    else:
                        st.error(test_result['message'])
                        if test_result.get('error'):
                            st.caption(f"エラー: {test_result['error']}")
        
        with col2:
            if st.button("🔍 GSC接続テスト", use_container_width=True, key="test_gsc_button"):
                with st.spinner("GSC接続をテスト中..."):
                    test_result = st.session_state.ai_chat.google_apis.test_gsc_connection(site_name=st.session_state.selected_site)
                    if test_result['success']:
                        st.success(test_result['message'])
                        if test_result.get('data_sample'):
                            st.caption(f"データサンプル: {test_result['data_sample']['row_count']}件 ({test_result['data_sample']['date_range']})")
                    else:
                        st.error(test_result['message'])
                        if test_result.get('error'):
                            st.caption(f"エラー: {test_result['error']}")
    
    # 両サイトの接続状態を表示
    st.markdown("---")
    st.subheader("📊 両サイトの接続状態")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**MOODMARK**")
        if st.button("🔍 テスト", key="test_moodmark", use_container_width=True):
            with st.spinner("MOODMARK接続をテスト中..."):
                test_result = st.session_state.ai_chat.google_apis.test_gsc_connection(site_name='moodmark')
                if test_result['success']:
                    st.success("✅ 接続成功")
                else:
                    st.error("❌ 接続失敗")
    
    with col2:
        st.markdown("**MOODMARK GIFT**")
        if st.button("🔍 テスト", key="test_moodmarkgift", use_container_width=True):
            with st.spinner("MOODMARK GIFT接続をテスト中..."):
                test_result = st.session_state.ai_chat.google_apis.test_gsc_connection(site_name='moodmarkgift')
                if test_result['success']:
                    st.success("✅ 接続成功")
                else:
                    st.error("❌ 接続失敗")
    
    st.markdown("---")
    
    # チャット履歴のクリア
    if st.button("🗑️ チャット履歴をクリア"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    
    # キーワード入力フィールド
    st.subheader("🔍 分析対象")
    keyword_input = st.text_input(
        "分析対象キーワード（オプション）",
        value=st.session_state.get('keyword', ''),
        placeholder="例: 結婚祝い お菓子",
        key="keyword_input"
    )
    st.session_state.keyword = keyword_input
    
    # ランディングページ入力フィールド
    landing_page_input = st.text_input(
        "分析対象ランディングページ（オプション）",
        value=st.session_state.get('landing_page', ''),
        placeholder="例: https://isetan.mistore.jp/moodmark/...",
        key="landing_page_input"
    )
    st.session_state.landing_page = landing_page_input
    
    st.markdown("---")
    
    # URL入力（SEO分析用、後方互換性のため残す）
    st.subheader("🔗 ページ分析（旧形式）")
    url_input = st.text_input(
        "分析したいページのURLを入力（オプション）",
        placeholder="https://isetan.mistore.jp/moodmark/...",
        key="url_input"
    )
    if url_input:
        st.info(f"📄 {url_input} を分析対象に含めます")
        # ランディングページにも設定
        if not st.session_state.landing_page:
            st.session_state.landing_page = url_input
    
    st.markdown("---")
    
    # デバッグモード
    st.subheader("🔧 デバッグ設定")
    debug_mode = st.checkbox("デバッグモードを有効化", value=st.session_state.get('debug_mode', False), key="debug_mode_checkbox")
    st.session_state.debug_mode = debug_mode
    if debug_mode:
        st.info("デバッグモードが有効です。エラー時に詳細情報が表示されます。")
    
    st.markdown("---")
    
    # 使用例
    st.subheader("💡 使用例")
    example_questions = [
        "今週のトラフィックは？",
        "SEOの改善点を教えて",
        "人気のページは？",
        "検索流入の状況は？",
        "バウンス率はどう？",
        "CTRを改善するには？"
    ]
    
    for example in example_questions:
        if st.button(f"📌 {example}", key=f"example_{example}", use_container_width=True):
            st.session_state.user_input = example
            st.rerun()
    
    # SEO分析の使用例
    st.markdown("---")
    st.subheader("🔍 SEO分析の使用例")
    seo_examples = [
        "このページのSEO改善点は？",
        "タイトルとディスクリプションを最適化して",
        "見出し構造を分析して",
    ]
    
    for example in seo_examples:
        if st.button(f"📌 {example}", key=f"seo_example_{example}", use_container_width=True):
            if url_input:
                st.session_state.user_input = f"{example} {url_input}"
            else:
                st.session_state.user_input = example
            st.rerun()

# KPIカード表示機能
def get_previous_date_range(date_range_days, start_date=None, end_date=None, comparison_mode='year_over_year'):
    """
    比較期間の日付範囲を計算
    
    Args:
        date_range_days: 日数
        start_date: 開始日（オプション）
        end_date: 終了日（オプション）
        comparison_mode: 比較モード ('year_over_year': 前年同時期, 'previous_period': 前期間)
    
    Returns:
        tuple: (prev_start, prev_end) の文字列タプル
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days_diff = (end - start).days + 1
    else:
        end = datetime.now()
        start = end - timedelta(days=date_range_days - 1)
        days_diff = date_range_days
    
    if comparison_mode == 'year_over_year':
        # 前年同時期対比
        prev_start = start - relativedelta(years=1)
        prev_end = end - relativedelta(years=1)
    else:
        # 前期間対比
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_diff - 1)
    
    return prev_start.strftime('%Y-%m-%d'), prev_end.strftime('%Y-%m-%d')

def fetch_kpi_data(date_range_days, start_date=None, end_date=None, site_name='moodmark'):
    """KPIデータを取得"""
    if st.session_state.ai_chat is None:
        return None
    
    try:
        # 現在期間のデータ取得
        if start_date and end_date:
            ga4_summary = st.session_state.ai_chat._get_ga4_summary(
                date_range_days=(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1,
                start_date=start_date,
                end_date=end_date,
                site_name=site_name
            )
        else:
            ga4_summary = st.session_state.ai_chat._get_ga4_summary(
                date_range_days=date_range_days,
                site_name=site_name
            )
        
        if start_date and end_date:
            gsc_summary = st.session_state.ai_chat._get_gsc_summary(
                date_range_days=(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1,
                start_date=start_date,
                end_date=end_date,
                site_name=site_name
            )
        else:
            gsc_summary = st.session_state.ai_chat._get_gsc_summary(
                date_range_days=date_range_days,
                site_name=site_name
            )
        
        # 比較期間のデータ取得（比較モードに応じて前年同時期または前期間）
        comparison_mode = st.session_state.get('comparison_mode', 'year_over_year')
        prev_start, prev_end = get_previous_date_range(
            date_range_days, 
            start_date, 
            end_date, 
            comparison_mode=comparison_mode
        )
        prev_days = (datetime.strptime(prev_end, '%Y-%m-%d') - datetime.strptime(prev_start, '%Y-%m-%d')).days + 1
        
        prev_ga4_summary = st.session_state.ai_chat._get_ga4_summary(
            date_range_days=prev_days,
            start_date=prev_start,
            end_date=prev_end,
            site_name=site_name
        )
        
        prev_gsc_summary = st.session_state.ai_chat._get_gsc_summary(
            date_range_days=prev_days,
            start_date=prev_start,
            end_date=prev_end,
            site_name=site_name
        )
        
        # 自然検索セッションの取得
        organic_sessions = 0
        prev_organic_sessions = 0
        if 'channel_data' in ga4_summary and ga4_summary.get('channel_data'):
            organic_data = ga4_summary['channel_data'].get('Organic Search', {})
            organic_sessions = organic_data.get('sessions', 0)
        
        if 'channel_data' in prev_ga4_summary and prev_ga4_summary.get('channel_data'):
            prev_organic_data = prev_ga4_summary['channel_data'].get('Organic Search', {})
            prev_organic_sessions = prev_organic_data.get('sessions', 0)
        
        return {
            'current': {
                'sessions': ga4_summary.get('total_sessions', 0),
                'transactions': ga4_summary.get('total_purchases', 0),  # eコマース購入数
                'cvr': ga4_summary.get('cvr', 0.0),
                'organic_sessions': organic_sessions,
                'gsc_clicks': gsc_summary.get('total_clicks', 0),
                'gsc_impressions': gsc_summary.get('total_impressions', 0),
                'gsc_ctr': gsc_summary.get('avg_ctr', 0.0),
                'gsc_position': gsc_summary.get('avg_position', 0.0),
            },
            'previous': {
                'sessions': prev_ga4_summary.get('total_sessions', 0),
                'transactions': prev_ga4_summary.get('total_purchases', 0),  # eコマース購入数
                'cvr': prev_ga4_summary.get('cvr', 0.0),
                'organic_sessions': prev_organic_sessions,
                'gsc_clicks': prev_gsc_summary.get('total_clicks', 0),
                'gsc_impressions': prev_gsc_summary.get('total_impressions', 0),
                'gsc_ctr': prev_gsc_summary.get('avg_ctr', 0.0),
                'gsc_position': prev_gsc_summary.get('avg_position', 0.0),
            }
        }
    except Exception as e:
        st.error(f"KPIデータ取得エラー: {str(e)}")
        return None

def display_kpi_cards(kpi_data):
    """KPIカードを表示"""
    if kpi_data is None:
        return
    
    def calculate_comparison(current, previous, is_lower_better=False):
        """
        比較対比を計算
        
        Args:
            current: 現在の値
            previous: 比較対象の値
            is_lower_better: Trueの場合、数値が低いほど良い指標（例: GSC平均ポジション）
        
        Returns:
            tuple: (diff, percent) - diffは符号そのまま（色はst.metricのdelta_colorで制御）
        """
        if previous == 0:
            return None, None
        diff = current - previous
        percent = (diff / previous) * 100 if previous != 0 else None
        return diff, percent
    
    current = kpi_data['current']
    previous = kpi_data['previous']
    
    # KPIカードを表示
    st.subheader("📊 KPIダッシュボード")
    
    # 比較モード選択
    comparison_mode = st.session_state.get('comparison_mode', 'year_over_year')
    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        new_comparison_mode = st.radio(
            "比較モード",
            options=['year_over_year', 'previous_period'],
            format_func=lambda x: '前年同時期対比' if x == 'year_over_year' else '前期間対比',
            index=0 if comparison_mode == 'year_over_year' else 1,
            horizontal=True,
            key='comparison_mode_radio'
        )
        if new_comparison_mode != comparison_mode:
            st.session_state.comparison_mode = new_comparison_mode
            st.rerun()
    
    # 比較期間の表示
    with col2:
        if comparison_mode == 'year_over_year':
            st.caption("📅 前年同時期と比較")
        else:
            st.caption("📅 前期間と比較")
    
    st.markdown("---")
    
    # 8つのKPIカードを2行4列で表示
    kpi_cols = st.columns(4)
    
    # 1行目
    with kpi_cols[0]:
        sessions_diff, sessions_percent = calculate_comparison(current['sessions'], previous['sessions'])
        st.metric(
            label="セッション",
            value=f"{current['sessions']:,}",
            delta=f"{sessions_diff:+,} ({sessions_percent:+.2f}%)" if sessions_percent is not None else None
        )
    
    with kpi_cols[1]:
        transactions_diff, transactions_percent = calculate_comparison(current['transactions'], previous['transactions'])
        st.metric(
            label="トランザクション",
            value=f"{current['transactions']:,}",
            delta=f"{transactions_diff:+,} ({transactions_percent:+.2f}%)" if transactions_percent is not None else None
        )
    
    with kpi_cols[2]:
        cvr_diff, cvr_percent = calculate_comparison(current['cvr'], previous['cvr'])
        st.metric(
            label="CVR",
            value=f"{current['cvr']:.2f}%",
            delta=f"{cvr_diff:+.2f}%ポイント ({cvr_percent:+.2f}%)" if cvr_percent is not None else None
        )
    
    with kpi_cols[3]:
        organic_diff, organic_percent = calculate_comparison(current['organic_sessions'], previous['organic_sessions'])
        st.metric(
            label="自然検索セッション",
            value=f"{current['organic_sessions']:,}",
            delta=f"{organic_diff:+,} ({organic_percent:+.2f}%)" if organic_percent is not None else None
        )
    
    # 2行目
    kpi_cols2 = st.columns(4)
    
    with kpi_cols2[0]:
        gsc_clicks_diff, gsc_clicks_percent = calculate_comparison(current['gsc_clicks'], previous['gsc_clicks'])
        st.metric(
            label="GSC クリック数",
            value=f"{current['gsc_clicks']:,}",
            delta=f"{gsc_clicks_diff:+,} ({gsc_clicks_percent:+.2f}%)" if gsc_clicks_percent is not None else None
        )
    
    with kpi_cols2[1]:
        gsc_impressions_diff, gsc_impressions_percent = calculate_comparison(current['gsc_impressions'], previous['gsc_impressions'])
        st.metric(
            label="GSC インプレッション数",
            value=f"{current['gsc_impressions']:,}",
            delta=f"{gsc_impressions_diff:+,} ({gsc_impressions_percent:+.2f}%)" if gsc_impressions_percent is not None else None
        )
    
    with kpi_cols2[2]:
        gsc_ctr_diff, gsc_ctr_percent = calculate_comparison(current['gsc_ctr'], previous['gsc_ctr'])
        st.metric(
            label="GSC CTR",
            value=f"{current['gsc_ctr']:.2f}%",
            delta=f"{gsc_ctr_diff:+.2f}%ポイント ({gsc_ctr_percent:+.2f}%)" if gsc_ctr_percent is not None else None
        )
    
    with kpi_cols2[3]:
        gsc_position_diff, gsc_position_percent = calculate_comparison(current['gsc_position'], previous['gsc_position'], is_lower_better=True)
        st.metric(
            label="GSC 平均ポジション",
            value=f"{current['gsc_position']:.1f}",
            delta=f"{gsc_position_diff:+.1f} ({gsc_position_percent:+.2f}%)" if gsc_position_percent is not None else None,
            delta_color="inverse"  # 数値が低いほど良い指標のため、負の値（改善）を緑色で表示
        )
    
    st.markdown("---")

def fetch_traffic_trend_data(date_range_days, start_date=None, end_date=None, site_name='moodmark'):
    """トラフィック推移データを取得（日別）"""
    if st.session_state.ai_chat is None:
        return None
    
    try:
        # GA4から日別データを取得（eコマース購入数を使用）
        if start_date and end_date:
            ga4_data = st.session_state.ai_chat.google_apis.get_ga4_data_custom_range(
                start_date=start_date,
                end_date=end_date,
                metrics=['sessions', 'ecommercePurchases'],
                dimensions=['date'],
                site_name=site_name
            )
        else:
            ga4_data = st.session_state.ai_chat.google_apis.get_ga4_data(
                date_range_days=date_range_days,
                metrics=['sessions', 'ecommercePurchases'],
                dimensions=['date'],
                site_name=site_name
            )
        
        if ga4_data is None or ga4_data.empty:
            return None
        
        # 日付でソート
        if 'date' in ga4_data.columns:
            ga4_data['date'] = pd.to_datetime(ga4_data['date'])
            ga4_data = ga4_data.sort_values('date')
        
        # 日別に集計（同じ日付のデータがある場合に備えて）
        if 'date' in ga4_data.columns:
            ga4_data = ga4_data.groupby('date').agg({
                'sessions': 'sum',
                'ecommercePurchases': 'sum'
            }).reset_index()
        
        return ga4_data
    except Exception as e:
        st.error(f"トラフィック推移データ取得エラー: {str(e)}")
        return None

def display_traffic_trend_chart(traffic_data):
    """トラフィック推移グラフを表示"""
    if traffic_data is None or traffic_data.empty:
        return
    
    st.subheader("📈 トラフィック推移")
    
    # データの準備
    if 'date' not in traffic_data.columns:
        st.warning("日付データが見つかりません")
        return
    
    # セッション数とトランザクション数を取得（数値に変換）
    sessions = []
    transactions = []
    dates = []
    
    for _, row in traffic_data.iterrows():
        date_val = row['date']
        if pd.notna(date_val):
            dates.append(date_val)
            # セッション数を取得（数値に変換）
            session_val = row.get('sessions', 0)
            if pd.notna(session_val):
                sessions.append(float(session_val))
            else:
                sessions.append(0.0)
            
            # eコマース購入数を取得（ecommercePurchasesから、数値に変換）
            transaction_val = row.get('ecommercePurchases', 0)
            if pd.notna(transaction_val):
                transactions.append(float(transaction_val))
            else:
                transactions.append(0.0)
    
    if not dates:
        st.warning("表示するデータがありません")
        return
    
    # Plotlyでグラフを作成
    fig = go.Figure()
    
    # セッションの折れ線（左Y軸）
    fig.add_trace(go.Scatter(
        x=dates,
        y=sessions,
        name='セッション',
        line=dict(color='#8884d8', width=2),
        mode='lines+markers',
        marker=dict(size=4),
        hovertemplate='<b>%{x|%Y年%m月%d日}</b><br>セッション: %{y:,.0f}<extra></extra>'
    ))
    
    # トランザクションの折れ線（右Y軸）
    fig.add_trace(go.Scatter(
        x=dates,
        y=transactions,
        name='トランザクション',
        line=dict(color='#82ca9d', width=2),
        mode='lines+markers',
        marker=dict(size=4),
        yaxis='y2',
        hovertemplate='<b>%{x|%Y年%m月%d日}</b><br>トランザクション: %{y:,.0f}<extra></extra>'
    ))
    
    # X軸の日付フォーマットを設定
    # データ数に応じてtick間隔を調整
    num_dates = len(dates)
    if num_dates <= 7:
        dtick_value = 86400000  # 1日（ミリ秒）
        tickformat = '%m/%d'
    elif num_dates <= 30:
        dtick_value = 86400000 * 2  # 2日間隔
        tickformat = '%m/%d'
    elif num_dates <= 90:
        dtick_value = 86400000 * 7  # 1週間間隔
        tickformat = '%m/%d'
    else:
        dtick_value = 86400000 * 14  # 2週間間隔
        tickformat = '%m/%d'
    
    # レイアウト設定
    fig.update_layout(
        height=400,
        xaxis=dict(
            title='',
            tickangle=-45,
            tickformat=tickformat,
            type='date',
            showgrid=True,
            gridcolor='rgba(204, 204, 204, 0.3)'
        ),
        yaxis=dict(
            title=dict(text='セッション', font=dict(color='#8884d8', size=12)),
            tickfont=dict(color='#8884d8'),
            side='left',
            showgrid=True,
            gridcolor='rgba(204, 204, 204, 0.1)',
            rangemode='tozero'
        ),
        yaxis2=dict(
            title=dict(text='トランザクション', font=dict(color='#82ca9d', size=12)),
            tickfont=dict(color='#82ca9d'),
            overlaying='y',
            side='right',
            showgrid=False,
            rangemode='tozero'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(255, 255, 255, 0.8)'
        ),
        hovermode='x unified',
        margin=dict(l=60, r=60, t=50, b=100),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")

def fetch_keyword_ranking_data(date_range_days, start_date=None, end_date=None, site_name='moodmark'):
    """キーワードランキングデータを取得（現在期間と比較期間）"""
    if st.session_state.ai_chat is None:
        return None, None
    
    try:
        # 現在期間のキーワードデータ取得
        if start_date and end_date:
            current_queries = st.session_state.ai_chat.google_apis.get_top_queries_gsc(
                start_date=start_date,
                end_date=end_date,
                limit=30,
                site_name=site_name
            )
        else:
            current_queries = st.session_state.ai_chat.google_apis.get_top_queries_gsc(
                date_range_days=date_range_days,
                limit=30,
                site_name=site_name
            )
        
        # 比較期間のキーワードデータ取得
        comparison_mode = st.session_state.get('comparison_mode', 'year_over_year')
        prev_start, prev_end = get_previous_date_range(
            date_range_days,
            start_date,
            end_date,
            comparison_mode=comparison_mode
        )
        
        prev_queries = st.session_state.ai_chat.google_apis.get_top_queries_gsc(
            start_date=prev_start,
            end_date=prev_end,
            limit=100,  # 比較用に多めに取得
            site_name=site_name
        )
        
        return current_queries, prev_queries
    except Exception as e:
        st.error(f"キーワードランキングデータ取得エラー: {str(e)}")
        return None, None

def display_keyword_ranking(current_queries, prev_queries):
    """キーワードランキングテーブルを表示"""
    if current_queries is None or current_queries.empty:
        return
    
    st.subheader("🔍 キーワードランキング（上位30件）")
    
    # 比較期間のデータを辞書に変換（高速検索用）
    prev_dict = {}
    if prev_queries is not None and not prev_queries.empty:
        for _, row in prev_queries.iterrows():
            query = row.get('query', '')
            if query:
                prev_dict[query] = {
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr_calculated': row.get('ctr_calculated', 0.0),
                    'avg_position': row.get('avg_position', 0.0)
                }
    
    # テーブルデータの準備
    table_data = []
    for idx, row in current_queries.iterrows():
        query = row.get('query', '')
        current_clicks = int(row.get('clicks', 0))
        current_impressions = int(row.get('impressions', 0))
        current_ctr = float(row.get('ctr_calculated', 0.0))
        current_position = float(row.get('avg_position', 0.0))
        
        # 比較期間のデータを取得
        prev_data = prev_dict.get(query, {})
        prev_clicks = prev_data.get('clicks', 0)
        prev_impressions = prev_data.get('impressions', 0)
        prev_ctr = prev_data.get('ctr_calculated', 0.0)
        prev_position = prev_data.get('avg_position', 0.0)
        
        # 差分とパーセンテージを計算
        clicks_diff = current_clicks - prev_clicks
        clicks_percent = (clicks_diff / prev_clicks * 100) if prev_clicks > 0 else None
        
        impressions_diff = current_impressions - prev_impressions
        impressions_percent = (impressions_diff / prev_impressions * 100) if prev_impressions > 0 else None
        
        ctr_diff = current_ctr - prev_ctr
        ctr_percent = (ctr_diff / prev_ctr * 100) if prev_ctr > 0 else None
        
        position_diff = current_position - prev_position
        position_percent = (position_diff / prev_position * 100) if prev_position > 0 else None
        
        table_data.append({
            '順位': idx + 1,
            'キーワード': query,
            'クリック': {
                'current': current_clicks,
                'diff': clicks_diff,
                'percent': clicks_percent,
                'prev': prev_clicks
            },
            'インプレッション': {
                'current': current_impressions,
                'diff': impressions_diff,
                'percent': impressions_percent,
                'prev': prev_impressions
            },
            'CTR': {
                'current': current_ctr,
                'diff': ctr_diff,
                'percent': ctr_percent,
                'prev': prev_ctr
            },
            'ポジション': {
                'current': current_position,
                'diff': position_diff,
                'percent': position_percent,
                'prev': prev_position
            }
        })
    
    # 色の決定関数
    def get_color(diff, is_lower_better=False):
        if diff is None or diff == 0:
            return "#6b7280"  # gray
        if is_lower_better:
            return "#10b981" if diff < 0 else "#ef4444"  # ポジション: 下がる=緑、上がる=赤
        else:
            return "#10b981" if diff > 0 else "#ef4444"  # その他: 上がる=緑、下がる=赤
    
    # 差分表示の準備関数
    def format_delta(diff, percent, prev_value):
        if diff is None or percent is None or prev_value == 0:
            return ""
        sign = "+" if diff >= 0 else ""
        color = get_color(diff)
        return f'<div style="color: {color}; font-size: 12px;">{sign}{diff:,.0f} ({percent:+.1f}%)</div>'
    
    def format_delta_ctr(diff, percent, prev_value):
        if diff is None or percent is None or prev_value == 0:
            return ""
        sign = "+" if diff >= 0 else ""
        color = get_color(diff)
        return f'<div style="color: {color}; font-size: 12px;">{sign}{diff:.2f}% ({percent:+.1f}%)</div>'
    
    def format_delta_position(diff, percent, prev_value):
        if diff is None or percent is None or prev_value == 0:
            return ""
        sign = "+" if diff >= 0 else ""
        color = get_color(diff, is_lower_better=True)
        return f'<div style="color: {color}; font-size: 12px;">{sign}{diff:.1f} ({percent:+.1f}%)</div>'
    
    # Streamlitのテーブルで表示（カスタムHTMLを使用）
    html_table = """
    <div style="overflow-x: auto;">
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    <thead>
        <tr style="background-color: #f3f4f6;">
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">順位</th>
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">キーワード</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">クリック</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">インプレッション</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">CTR</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">ポジション</th>
        </tr>
    </thead>
    <tbody>
    """
    
    for data in table_data:
        # HTMLエスケープ
        keyword = data['キーワード'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        clicks_delta = format_delta(data['クリック']['diff'], data['クリック']['percent'], data['クリック']['prev'])
        impressions_delta = format_delta(data['インプレッション']['diff'], data['インプレッション']['percent'], data['インプレッション']['prev'])
        ctr_delta = format_delta_ctr(data['CTR']['diff'], data['CTR']['percent'], data['CTR']['prev'])
        position_delta = format_delta_position(data['ポジション']['diff'], data['ポジション']['percent'], data['ポジション']['prev'])
        
        html_table += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px; font-weight: 600;">{data['順位']}</td>
            <td style="padding: 12px;">{keyword}</td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['クリック']['current']:,}</div>
                {clicks_delta}
            </td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['インプレッション']['current']:,}</div>
                {impressions_delta}
            </td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['CTR']['current']:.2f}%</div>
                {ctr_delta}
            </td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['ポジション']['current']:.1f}</div>
                {position_delta}
            </td>
        </tr>
        """
    
    html_table += """
    </tbody>
    </table>
    </div>
    """
    
    # Streamlit Componentsを使用してHTMLを表示
    import streamlit.components.v1 as components
    components.html(html_table, height=1200, scrolling=True)
    st.markdown("---")

def fetch_page_ranking_data(date_range_days, start_date=None, end_date=None, site_name='moodmark'):
    """ページランキングデータを取得（現在期間と比較期間）"""
    if st.session_state.ai_chat is None:
        return None, None
    
    try:
        # 現在期間のページデータ取得
        if start_date and end_date:
            current_pages = st.session_state.ai_chat.google_apis.get_top_pages_gsc(
                start_date=start_date,
                end_date=end_date,
                limit=30,
                site_name=site_name
            )
        else:
            current_pages = st.session_state.ai_chat.google_apis.get_top_pages_gsc(
                date_range_days=date_range_days,
                limit=30,
                site_name=site_name
            )
        
        # 比較期間のページデータ取得
        comparison_mode = st.session_state.get('comparison_mode', 'year_over_year')
        prev_start, prev_end = get_previous_date_range(
            date_range_days,
            start_date,
            end_date,
            comparison_mode=comparison_mode
        )
        
        prev_pages = st.session_state.ai_chat.google_apis.get_top_pages_gsc(
            start_date=prev_start,
            end_date=prev_end,
            limit=100,  # 比較用に多めに取得
            site_name=site_name
        )
        
        return current_pages, prev_pages
    except Exception as e:
        st.error(f"ページランキングデータ取得エラー: {str(e)}")
        return None, None

def display_page_ranking(current_pages, prev_pages, site_name='moodmark'):
    """ページランキングテーブルを表示"""
    if current_pages is None or current_pages.empty:
        return
    
    st.subheader("📄 ページランキング（上位30件）")
    
    # サイトのベースURLを取得
    if site_name == 'moodmarkgift':
        site_base_url = 'https://isetan.mistore.jp'
    else:
        site_base_url = 'https://isetan.mistore.jp'
    
    # 比較期間のデータを辞書に変換（高速検索用）
    prev_dict = {}
    if prev_pages is not None and not prev_pages.empty:
        for _, row in prev_pages.iterrows():
            page = row.get('page', '')
            if page:
                prev_dict[page] = {
                    'clicks': row.get('clicks', 0),
                    'impressions': row.get('impressions', 0),
                    'ctr_calculated': row.get('ctr_calculated', 0.0),
                    'avg_position': row.get('avg_position', 0.0)
                }
    
    # テーブルデータの準備
    table_data = []
    for idx, row in current_pages.iterrows():
        page = row.get('page', '')
        current_clicks = int(row.get('clicks', 0))
        current_impressions = int(row.get('impressions', 0))
        current_ctr = float(row.get('ctr_calculated', 0.0))
        current_position = float(row.get('avg_position', 0.0))
        
        # 比較期間のデータを取得
        prev_data = prev_dict.get(page, {})
        prev_clicks = prev_data.get('clicks', 0)
        prev_impressions = prev_data.get('impressions', 0)
        prev_ctr = prev_data.get('ctr_calculated', 0.0)
        prev_position = prev_data.get('avg_position', 0.0)
        
        # 差分とパーセンテージを計算
        clicks_diff = current_clicks - prev_clicks
        clicks_percent = (clicks_diff / prev_clicks * 100) if prev_clicks > 0 else None
        
        impressions_diff = current_impressions - prev_impressions
        impressions_percent = (impressions_diff / prev_impressions * 100) if prev_impressions > 0 else None
        
        ctr_diff = current_ctr - prev_ctr
        ctr_percent = (ctr_diff / prev_ctr * 100) if prev_ctr > 0 else None
        
        position_diff = current_position - prev_position
        position_percent = (position_diff / prev_position * 100) if prev_position > 0 else None
        
        table_data.append({
            '順位': idx + 1,
            'ページ': page,
            'クリック': {
                'current': current_clicks,
                'diff': clicks_diff,
                'percent': clicks_percent,
                'prev': prev_clicks
            },
            'インプレッション': {
                'current': current_impressions,
                'diff': impressions_diff,
                'percent': impressions_percent,
                'prev': prev_impressions
            },
            'CTR': {
                'current': current_ctr,
                'diff': ctr_diff,
                'percent': ctr_percent,
                'prev': prev_ctr
            },
            'ポジション': {
                'current': current_position,
                'diff': position_diff,
                'percent': position_percent,
                'prev': prev_position
            }
        })
    
    # 色の決定関数
    def get_color(diff, is_lower_better=False):
        if diff is None or diff == 0:
            return "#6b7280"  # gray
        if is_lower_better:
            return "#10b981" if diff < 0 else "#ef4444"  # ポジション: 下がる=緑、上がる=赤
        else:
            return "#10b981" if diff > 0 else "#ef4444"  # その他: 上がる=緑、下がる=赤
    
    # 差分表示の準備関数
    def format_delta(diff, percent, prev_value):
        if diff is None or percent is None or prev_value == 0:
            return ""
        sign = "+" if diff >= 0 else ""
        color = get_color(diff)
        return f'<div style="color: {color}; font-size: 12px;">{sign}{diff:,.0f} ({percent:+.1f}%)</div>'
    
    def format_delta_ctr(diff, percent, prev_value):
        if diff is None or percent is None or prev_value == 0:
            return ""
        sign = "+" if diff >= 0 else ""
        color = get_color(diff)
        return f'<div style="color: {color}; font-size: 12px;">{sign}{diff:.2f}% ({percent:+.1f}%)</div>'
    
    def format_delta_position(diff, percent, prev_value):
        if diff is None or percent is None or prev_value == 0:
            return ""
        sign = "+" if diff >= 0 else ""
        color = get_color(diff, is_lower_better=True)
        return f'<div style="color: {color}; font-size: 12px;">{sign}{diff:.1f} ({percent:+.1f}%)</div>'
    
    # Streamlitのテーブルで表示（カスタムHTMLを使用）
    html_table = """
    <div style="overflow-x: auto;">
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    <thead>
        <tr style="background-color: #f3f4f6;">
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">順位</th>
            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">ページ</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">クリック</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">インプレッション</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">CTR</th>
            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">ポジション</th>
        </tr>
    </thead>
    <tbody>
    """
    
    for data in table_data:
        # HTMLエスケープとハイパーリンク作成
        page_url_raw = data['ページ']
        # URLが完全なURLでない場合（パスのみの場合）、サイトURLを追加
        if not page_url_raw.startswith('http://') and not page_url_raw.startswith('https://'):
            full_url = site_base_url + page_url_raw
        else:
            full_url = page_url_raw
        
        # HTMLエスケープ
        page_url_escaped = page_url_raw.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        full_url_escaped = full_url.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # ハイパーリンク作成
        page_link = f'<a href="{full_url_escaped}" target="_blank" rel="noopener noreferrer" style="color: #1f77b4; text-decoration: underline;">{page_url_escaped}</a>'
        
        clicks_delta = format_delta(data['クリック']['diff'], data['クリック']['percent'], data['クリック']['prev'])
        impressions_delta = format_delta(data['インプレッション']['diff'], data['インプレッション']['percent'], data['インプレッション']['prev'])
        ctr_delta = format_delta_ctr(data['CTR']['diff'], data['CTR']['percent'], data['CTR']['prev'])
        position_delta = format_delta_position(data['ポジション']['diff'], data['ポジション']['percent'], data['ポジション']['prev'])
        
        html_table += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px; font-weight: 600;">{data['順位']}</td>
            <td style="padding: 12px; word-break: break-all; max-width: 400px;">{page_link}</td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['クリック']['current']:,}</div>
                {clicks_delta}
            </td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['インプレッション']['current']:,}</div>
                {impressions_delta}
            </td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['CTR']['current']:.2f}%</div>
                {ctr_delta}
            </td>
            <td style="padding: 12px; text-align: right;">
                <div>{data['ポジション']['current']:.1f}</div>
                {position_delta}
            </td>
        </tr>
        """
    
    html_table += """
    </tbody>
    </table>
    </div>
    """
    
    # Streamlit Componentsを使用してHTMLを表示
    import streamlit.components.v1 as components
    components.html(html_table, height=1200, scrolling=True)
    st.markdown("---")

# KPIカードの表示（AIチャットが初期化されている場合のみ）
if st.session_state.ai_chat is not None:
    with st.spinner("KPIデータを取得中..."):
        kpi_data = fetch_kpi_data(
            date_range_days=st.session_state.date_range_days,
            start_date=st.session_state.start_date,
            end_date=st.session_state.end_date,
            site_name=st.session_state.selected_site
        )
        if kpi_data:
            display_kpi_cards(kpi_data)
    
    # トラフィック推移グラフの表示
    with st.spinner("トラフィック推移データを取得中..."):
        traffic_data = fetch_traffic_trend_data(
            date_range_days=st.session_state.date_range_days,
            start_date=st.session_state.start_date,
            end_date=st.session_state.end_date,
            site_name=st.session_state.selected_site
        )
        if traffic_data is not None and not traffic_data.empty:
            display_traffic_trend_chart(traffic_data)
    
    # キーワードランキングの表示
    with st.spinner("キーワードランキングデータを取得中..."):
        current_queries, prev_queries = fetch_keyword_ranking_data(
            date_range_days=st.session_state.date_range_days,
            start_date=st.session_state.start_date,
            end_date=st.session_state.end_date,
            site_name=st.session_state.selected_site
        )
        if current_queries is not None and not current_queries.empty:
            display_keyword_ranking(current_queries, prev_queries)
    
    # ページランキングの表示
    with st.spinner("ページランキングデータを取得中..."):
        current_pages, prev_pages = fetch_page_ranking_data(
            date_range_days=st.session_state.date_range_days,
            start_date=st.session_state.start_date,
            end_date=st.session_state.end_date,
            site_name=st.session_state.selected_site
        )
        if current_pages is not None and not current_pages.empty:
            display_page_ranking(current_pages, prev_pages, site_name=st.session_state.selected_site)

# メインエリア
# チャット履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "timestamp" in message:
            st.caption(f"🕐 {message['timestamp']}")

# ユーザー入力
chat_placeholder = "GA4やGSCについて質問してください...（URLを含めるとページ分析も実行されます）"
if prompt := st.chat_input(chat_placeholder):
    # URLがサイドバーに入力されている場合は質問に追加
    if 'url_input' in st.session_state and st.session_state.url_input and st.session_state.url_input.strip():
        # サイドバーのURLを追加（既に質問に含まれていない場合）
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls_in_prompt = re.findall(url_pattern, prompt)
        if st.session_state.url_input not in urls_in_prompt:
            prompt_with_url = f"{prompt} {st.session_state.url_input}"
        else:
            prompt_with_url = prompt
    else:
        prompt_with_url = prompt
    
    # ユーザーメッセージを追加
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.messages.append({
        "role": "user",
        "content": prompt_with_url if prompt_with_url != prompt else prompt,
        "timestamp": timestamp
    })
    
    # ユーザーメッセージを表示
    with st.chat_message("user"):
        display_prompt = prompt
        if prompt_with_url != prompt:
            display_prompt = f"{prompt}\n\n🔗 分析URL: {st.session_state.url_input}"
        st.markdown(display_prompt)
        st.caption(f"🕐 {timestamp}")
    
    # AI回答を生成
    if st.session_state.ai_chat is None:
        with st.chat_message("assistant"):
            st.error("AIチャットが初期化されていません。サイドバーで設定を確認してください。")
    else:
        with st.chat_message("assistant"):
            # URLが含まれている場合はそれを使用、そうでなければサイドバーのURLを使用
            question = prompt_with_url if 'prompt_with_url' in locals() else prompt
            
            # URLが含まれている場合は分析ステップを表示
            urls_in_question = []
            if 'url_input' in st.session_state and st.session_state.url_input:
                urls_in_question.append(st.session_state.url_input)
            # 質問内のURLも抽出
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls_in_question.extend(re.findall(url_pattern, question))
            
            if urls_in_question:
                # SEO分析実行中のステップ表示（シンプル版）
                status_placeholder = st.empty()
                
                try:
                    # ストリーミング応答を取得
                    # ステップメッセージとAI応答を分けて処理
                    step_messages = []
                    ai_response_parts = []
                    in_ai_response = False
                    answer_placeholder = st.empty()  # AI応答用のプレースホルダー
                    
                    # ストリーミング応答を処理
                    try:
                        # 会話履歴を取得（直前の2-3件）
                        conversation_history = st.session_state.messages[-3:] if len(st.session_state.messages) > 0 else []
                        
                        for chunk in st.session_state.ai_chat.ask_stream(
                            question,
                            model=st.session_state.model,
                            site_name=st.session_state.selected_site,
                            conversation_history=conversation_history,
                            keyword=st.session_state.get('keyword', ''),
                            landing_page=st.session_state.get('landing_page', '')
                        ):
                            # ステップメッセージかAI応答かを判定
                            if chunk.startswith("[STEP]"):
                                step_messages.append(chunk)
                                # ステップメッセージをリアルタイム表示
                                with status_placeholder.container():
                                    st.info("".join(step_messages))
                            else:
                                # AI応答の開始
                                if not in_ai_response:
                                    in_ai_response = True
                                    status_placeholder.empty()  # ステップメッセージをクリア
                                
                                ai_response_parts.append(chunk)
                                # AI応答をリアルタイム表示（プレースホルダー内で更新）
                                answer_placeholder.markdown("".join(ai_response_parts))
                        
                        # 完全な応答を取得
                        full_answer = "".join(ai_response_parts)
                    except AttributeError:
                        # Streamlit 1.28.0未満の場合の代替実装
                        answer_placeholder = st.empty()
                        full_answer = ""
                        # 会話履歴を取得（直前の2-3件）
                        conversation_history = st.session_state.messages[-3:] if len(st.session_state.messages) > 0 else []
                        
                        for chunk in st.session_state.ai_chat.ask_stream(
                            question,
                            model=st.session_state.model,
                            site_name=st.session_state.selected_site,
                            conversation_history=conversation_history,
                            keyword=st.session_state.get('keyword', ''),
                            landing_page=st.session_state.get('landing_page', '')
                        ):
                            if chunk.startswith("[STEP]"):
                                step_messages.append(chunk)
                                with status_placeholder.container():
                                    st.info("".join(step_messages))
                            else:
                                if not in_ai_response:
                                    in_ai_response = True
                                    status_placeholder.empty()
                                full_answer += chunk
                                answer_placeholder.markdown(full_answer)
                    
                    # メッセージ履歴に追加
                    answer_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_answer,
                        "timestamp": answer_timestamp
                    })
                    st.caption(f"🕐 {answer_timestamp}")
                    
                except TimeoutError as e:
                    # タイムアウトエラーの処理
                    status_placeholder.empty()
                    error_message = f"⏱️ タイムアウトエラー\n\n**エラー内容**: {str(e)}\n\n"
                    error_message += "**考えられる原因**:\n"
                    error_message += "- データ取得に時間がかかりすぎています\n"
                    error_message += "- ネットワーク接続が遅い可能性があります\n\n"
                    error_message += "**対処方法**:\n"
                    error_message += "- しばらく待ってから再度お試しください\n"
                    error_message += "- より短い期間のデータを指定してください\n"
                    st.error(error_message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    # ステータス表示をクリア
                    status_placeholder.empty()
                    
                    import traceback
                    error_details = traceback.format_exc()
                    
                    # エラーメッセージを詳細に表示
                    error_message = f"❌ エラーが発生しました\n\n**エラー内容**: {str(e)}\n\n"
                    
                    # よくあるエラーの解決方法を提示
                    if "ページの取得に失敗" in str(e) or "Connection" in str(e):
                        error_message += "**考えられる原因**:\n"
                        error_message += "- URLが正しくない\n"
                        error_message += "- ページがアクセスできない（認証が必要、存在しないなど）\n"
                        error_message += "- ネットワーク接続の問題\n\n"
                        error_message += "**対処方法**:\n"
                        error_message += "- URLが正しいか確認してください\n"
                        error_message += "- ページが公開されているか確認してください\n"
                    elif "OpenAI" in str(e) or "API" in str(e):
                        error_message += "**考えられる原因**:\n"
                        error_message += "- OpenAI APIキーが正しく設定されていない\n"
                        error_message += "- APIの利用制限に達している\n\n"
                        error_message += "**対処方法**:\n"
                        error_message += "- 環境変数OPENAI_API_KEYを確認してください\n"
                        error_message += "- APIの利用状況を確認してください\n"
                    
                    st.error(error_message)
                    
                    # デバッグ情報（開発環境用）
                    if st.session_state.get('debug_mode', False):
                        with st.expander("🔧 デバッグ情報"):
                            st.code(error_details)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            else:
                # 通常の分析（シンプル版）
                status_placeholder = st.empty()
                
                try:
                    # ストリーミング応答を取得
                    # ステップメッセージとAI応答を分けて処理
                    step_messages = []
                    ai_response_parts = []
                    in_ai_response = False
                    answer_placeholder = st.empty()  # AI応答用のプレースホルダー
                    
                    # ストリーミング応答を処理
                    try:
                        # 会話履歴を取得（直前の2-3件）
                        conversation_history = st.session_state.messages[-3:] if len(st.session_state.messages) > 0 else []
                        
                        for chunk in st.session_state.ai_chat.ask_stream(
                            question,
                            model=st.session_state.model,
                            site_name=st.session_state.selected_site,
                            conversation_history=conversation_history,
                            keyword=st.session_state.get('keyword', ''),
                            landing_page=st.session_state.get('landing_page', '')
                        ):
                            # ステップメッセージかAI応答かを判定
                            if chunk.startswith("[STEP]"):
                                step_messages.append(chunk)
                                # ステップメッセージをリアルタイム表示
                                with status_placeholder.container():
                                    st.info("".join(step_messages))
                            else:
                                # AI応答の開始
                                if not in_ai_response:
                                    in_ai_response = True
                                    status_placeholder.empty()  # ステップメッセージをクリア
                                
                                ai_response_parts.append(chunk)
                                # AI応答をリアルタイム表示（プレースホルダー内で更新）
                                answer_placeholder.markdown("".join(ai_response_parts))
                        
                        # 完全な応答を取得
                        full_answer = "".join(ai_response_parts)
                    except AttributeError:
                        # Streamlit 1.28.0未満の場合の代替実装
                        answer_placeholder = st.empty()
                        full_answer = ""
                        # 会話履歴を取得（直前の2-3件）
                        conversation_history = st.session_state.messages[-3:] if len(st.session_state.messages) > 0 else []
                        
                        for chunk in st.session_state.ai_chat.ask_stream(
                            question,
                            model=st.session_state.model,
                            site_name=st.session_state.selected_site,
                            conversation_history=conversation_history,
                            keyword=st.session_state.get('keyword', ''),
                            landing_page=st.session_state.get('landing_page', '')
                        ):
                            if chunk.startswith("[STEP]"):
                                step_messages.append(chunk)
                                with status_placeholder.container():
                                    st.info("".join(step_messages))
                            else:
                                if not in_ai_response:
                                    in_ai_response = True
                                    status_placeholder.empty()
                                full_answer += chunk
                                answer_placeholder.markdown(full_answer)
                    
                    # メッセージ履歴に追加
                    answer_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_answer,
                        "timestamp": answer_timestamp
                    })
                    st.caption(f"🕐 {answer_timestamp}")
                    
                except TimeoutError as e:
                    # タイムアウトエラーの処理
                    status_placeholder.empty()
                    error_message = f"⏱️ タイムアウトエラー\n\n**エラー内容**: {str(e)}\n\n"
                    error_message += "**考えられる原因**:\n"
                    error_message += "- データ取得に時間がかかりすぎています\n"
                    error_message += "- ネットワーク接続が遅い可能性があります\n\n"
                    error_message += "**対処方法**:\n"
                    error_message += "- しばらく待ってから再度お試しください\n"
                    error_message += "- より短い期間のデータを指定してください\n"
                    st.error(error_message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    # ステータス表示をクリア
                    status_placeholder.empty()
                    
                    import traceback
                    error_details = traceback.format_exc()
                    
                    # エラーメッセージを詳細に表示
                    error_message = f"❌ エラーが発生しました\n\n**エラー内容**: {str(e)}\n\n"
                    
                    # よくあるエラーの解決方法を提示
                    if "ページの取得に失敗" in str(e) or "Connection" in str(e):
                        error_message += "**考えられる原因**:\n"
                        error_message += "- URLが正しくない\n"
                        error_message += "- ページがアクセスできない（認証が必要、存在しないなど）\n"
                        error_message += "- ネットワーク接続の問題\n\n"
                        error_message += "**対処方法**:\n"
                        error_message += "- URLが正しいか確認してください\n"
                        error_message += "- ページが公開されているか確認してください\n"
                    elif "OpenAI" in str(e) or "API" in str(e):
                        error_message += "**考えられる原因**:\n"
                        error_message += "- OpenAI APIキーが正しく設定されていない\n"
                        error_message += "- APIの利用制限に達している\n\n"
                        error_message += "**対処方法**:\n"
                        error_message += "- 環境変数OPENAI_API_KEYを確認してください\n"
                        error_message += "- APIの利用状況を確認してください\n"
                    
                    st.error(error_message)
                    
                    # デバッグ情報（開発環境用）
                    if st.session_state.get('debug_mode', False):
                        with st.expander("🔧 デバッグ情報"):
                            st.code(error_details)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

# フッター
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>💡 ヒント: 「今週のトラフィックは？」「SEOの改善点は？」などの質問ができます</p>
        <p>📊 データはGoogle Analytics 4とGoogle Search Consoleから取得されます</p>
        <p>🔍 URLを含めると、ページのHTML/CSS解析とSEO分析も実行されます</p>
        <p>📄 分析内容: タイトル、ディスクリプション、見出し構造、画像alt属性、構造化データ、リンク構造など</p>
    </div>
    """,
    unsafe_allow_html=True,
)
render_likepass_footer()

