#!/usr/bin/env python3
"""
API連携テストスクリプト
指定されたURLに対して、GA4・GSC・Page Speed Insightsの各APIが正しく連携して数値を取得できるかを確認します。
"""

import os
import sys
from datetime import datetime, timedelta

# 環境変数の読み込み（オプション）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analytics.google_apis_integration import GoogleAPIsIntegration
from analytics.ai_analytics_chat import AIAnalyticsChat

def test_api_integration(url: str):
    """
    指定されたURLに対して、GA4・GSC・Page Speed Insightsの各APIが正しく連携して数値を取得できるかを確認
    
    Args:
        url (str): テストするURL
    """
    print("=" * 80)
    print("API連携テスト開始")
    print("=" * 80)
    print(f"テストURL: {url}")
    print(f"テスト日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Google APIs統合の初期化
    print("【ステップ1】Google APIs統合の初期化")
    print("-" * 80)
    google_apis = GoogleAPIsIntegration()
    
    # 認証状態の確認
    auth_status = google_apis.check_authentication_status()
    print(f"認証状態: {'✓ 認証済み' if auth_status.get('authenticated') else '✗ 未認証'}")
    print(f"GA4サービス: {'✓ 初期化済み' if auth_status.get('ga4_service_initialized') else '✗ 未初期化'}")
    print(f"GSCサービス: {'✓ 初期化済み' if auth_status.get('gsc_service_initialized') else '✗ 未初期化'}")
    print(f"Page Speed Insights APIキー: {'✓ 設定済み' if google_apis.pagespeed_api_key else '✗ 未設定'}")
    print()
    
    if not auth_status.get('authenticated'):
        print("❌ エラー: 認証が完了していません。環境変数を確認してください。")
        if auth_status.get('errors'):
            for error in auth_status['errors']:
                print(f"  - {error}")
        return
    
    # サイト名の判定（URLから）
    # moodmarkgiftが含まれている場合はmoodmarkgift、それ以外のmoodmarkが含まれている場合はmoodmark
    if 'moodmarkgift' in url:
        site_name = 'moodmarkgift'
    elif 'moodmark' in url:
        site_name = 'moodmark'
    else:
        site_name = 'moodmark'  # デフォルト
    print(f"検出されたサイト: {site_name}")
    print(f"使用するGSCサイトURL: {google_apis.gsc_site_urls.get(site_name, 'N/A')}")
    print()
    
    # GA4データの取得テスト
    print("【ステップ2】GA4データの取得テスト")
    print("-" * 80)
    try:
        # GA4プロパティIDの確認
        ga4_property_id = google_apis.ga4_property_id
        if not ga4_property_id or ga4_property_id == 'your-ga4-property-id':
            print("✗ GA4プロパティIDが設定されていません")
            print("  環境変数 GA4_PROPERTY_ID を設定してください")
            print("  現在の値: " + (ga4_property_id or '未設定'))
        else:
            print(f"  GA4プロパティID: {ga4_property_id}")
            
            # 過去30日間のデータを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            ga4_data = google_apis.get_ga4_data_custom_range(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if not ga4_data.empty:
                print("✓ GA4データ取得成功")
                print(f"  データ行数: {len(ga4_data)}")
                print(f"  カラム: {', '.join(ga4_data.columns.tolist()[:5])}...")
                
                # サマリー統計
                if 'sessions' in ga4_data.columns:
                    total_sessions = ga4_data['sessions'].sum()
                    print(f"  総セッション数: {total_sessions:,.0f}")
                if 'totalUsers' in ga4_data.columns:
                    total_users = ga4_data['totalUsers'].sum()
                    print(f"  総ユーザー数: {total_users:,.0f}")
            else:
                print("✗ GA4データが空です")
                print("  考えられる原因:")
                print("    - 指定された期間にデータが存在しない")
                print("    - GA4プロパティIDが正しく設定されていない")
                print("    - サービスアカウントにGA4へのアクセス権限がない")
    except Exception as e:
        print(f"✗ GA4データ取得エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # GSCデータの取得テスト（特定ページ）
    print("【ステップ3】GSCデータの取得テスト（特定ページ）")
    print("-" * 80)
    try:
        # GSCサイトURLの確認
        gsc_site_url = google_apis.gsc_site_urls.get(site_name)
        if not gsc_site_url:
            print(f"✗ GSCサイトURLが設定されていません（サイト: {site_name}）")
            print(f"  環境変数 GSC_SITE_URL_MOODMARK または GSC_SITE_URL_MOODMARKGIFT を設定してください")
        else:
            print(f"  使用するGSCサイトURL: {gsc_site_url}")
            
            # 過去30日間のデータを取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            gsc_data = google_apis.get_page_specific_gsc_data(
                page_url=url,
                date_range_days=30,
                site_name=site_name,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if 'error' not in gsc_data:
                print("✓ GSCデータ取得成功")
                print(f"  ページURL: {gsc_data.get('page_url', 'N/A')}")
                print(f"  ページパス: {gsc_data.get('page_path', 'N/A')}")
                print(f"  クリック数: {gsc_data.get('clicks', 0):,}")
                print(f"  インプレッション数: {gsc_data.get('impressions', 0):,}")
                print(f"  CTR: {gsc_data.get('ctr', 0):.2f}%")
                print(f"  平均順位: {gsc_data.get('avg_position', 0):.2f}")
            else:
                error_msg = gsc_data.get('error', 'Unknown error')
                print(f"✗ GSCデータ取得エラー: {error_msg}")
                print("  考えられる原因:")
                if '403' in str(error_msg) or 'permission' in str(error_msg).lower():
                    print("    - サービスアカウントにGSCへのアクセス権限がない（最重要）")
                    print("    - GSCサイトURLが間違っている可能性があります")
                elif '404' in str(error_msg) or 'not found' in str(error_msg).lower():
                    print("    - 指定されたページのデータが存在しない")
                    print("    - ページがまだGSCに登録されていない")
                else:
                    print("    - 指定されたページのデータが存在しない")
                    print("    - GSCサイトURLが正しく設定されていない")
                    print("    - サービスアカウントにGSCへのアクセス権限がない")
    except Exception as e:
        print(f"✗ GSCデータ取得エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Page Speed Insightsデータの取得テスト
    print("【ステップ4】Page Speed Insightsデータの取得テスト")
    print("-" * 80)
    try:
        # APIキーの確認
        if not google_apis.pagespeed_api_key:
            print("✗ Page Speed Insights APIキーが設定されていません")
            print("  環境変数 PAGESPEED_INSIGHTS_API_KEY を設定してください")
        else:
            print(f"  APIキー: {google_apis.pagespeed_api_key[:10]}...（一部のみ表示）")
            
            # モバイル
            print("  モバイル分析中...")
            psi_mobile = google_apis.get_pagespeed_insights(url, strategy='mobile')
            
            if 'error' not in psi_mobile:
                print("  ✓ モバイルデータ取得成功")
                lhr = psi_mobile.get('lighthouseResult', {})
                categories = lhr.get('categories', {})
                
                if 'performance' in categories:
                    perf_score = categories['performance'].get('score', 0) * 100
                    print(f"    パフォーマンススコア: {perf_score:.0f}/100")
                if 'seo' in categories:
                    seo_score = categories['seo'].get('score', 0) * 100
                    print(f"    SEOスコア: {seo_score:.0f}/100")
            else:
                print(f"  ✗ モバイルデータ取得エラー: {psi_mobile.get('error', 'Unknown error')}")
            
            # デスクトップ
            print("  デスクトップ分析中...")
            psi_desktop = google_apis.get_pagespeed_insights(url, strategy='desktop')
            
            if 'error' not in psi_desktop:
                print("  ✓ デスクトップデータ取得成功")
                lhr = psi_desktop.get('lighthouseResult', {})
                categories = lhr.get('categories', {})
                
                if 'performance' in categories:
                    perf_score = categories['performance'].get('score', 0) * 100
                    print(f"    パフォーマンススコア: {perf_score:.0f}/100")
                if 'seo' in categories:
                    seo_score = categories['seo'].get('score', 0) * 100
                    print(f"    SEOスコア: {seo_score:.0f}/100")
            else:
                print(f"  ✗ デスクトップデータ取得エラー: {psi_desktop.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ Page Speed Insightsデータ取得エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # AI Analytics Chatでの統合テスト
    print("【ステップ5】AI Analytics Chatでの統合テスト")
    print("-" * 80)
    try:
        ai_chat = AIAnalyticsChat()
        
        # テスト質問
        test_question = f"このページのSEO改善点は？ {url}"
        print(f"テスト質問: {test_question}")
        print("分析中...")
        print()
        
        # 分析実行（実際のAI呼び出しは行わず、データ取得のみ確認）
        # 実際のAI呼び出しは時間がかかるため、ここではデータ取得の確認のみ
        
        print("✓ AI Analytics Chatの初期化成功")
        print("  注意: 実際のAI分析は実行していません（時間がかかるため）")
        print("  ダッシュボードで実際の分析を実行して、各APIが正しく連携されているか確認してください")
        
    except Exception as e:
        print(f"✗ AI Analytics Chat初期化エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # 結果サマリー
    print("=" * 80)
    print("テスト結果サマリー")
    print("=" * 80)
    print("各APIの連携状態を確認しました。")
    print("エラーが表示された場合は、環境変数や認証情報を確認してください。")
    print()
    print("確認項目:")
    print("  1. GOOGLE_CREDENTIALS_JSON または GOOGLE_CREDENTIALS_FILE が設定されているか")
    print("  2. GA4_PROPERTY_ID が設定されているか")
    print("  3. GSC_SITE_URL_MOODMARK または GSC_SITE_URL_MOODMARKGIFT が設定されているか")
    print("  4. PAGESPEED_INSIGHTS_API_KEY が設定されているか")
    print("  5. サービスアカウントに各APIへのアクセス権限があるか")
    print()

if __name__ == "__main__":
    # テストURL
    test_url = "https://isetan.mistore.jp/moodmark/guide/guide_05_13.html"
    
    # コマンドライン引数でURLを指定可能
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    test_api_integration(test_url)

