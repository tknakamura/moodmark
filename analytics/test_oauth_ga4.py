#!/usr/bin/env python3
"""
OAuth 2.0 GA4 API連携テストスクリプト
"""

import sys
import os
from datetime import datetime
from oauth_google_apis import OAuthGoogleAPIsIntegration

def print_separator(title=""):
    """セパレーター表示"""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print('=' * 60)
    else:
        print('=' * 60)

def test_authentication():
    """認証テスト"""
    print_separator("OAuth 2.0 認証テスト")
    
    try:
        api = OAuthGoogleAPIsIntegration()
        
        if api.credentials:
            print("✅ 認証成功")
            print(f"   GA4プロパティID: {api.ga4_property_id}")
            print(f"   GSCサイトURL: {api.gsc_site_url}")
            return api
        else:
            print("❌ 認証失敗")
            return None
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        return None

def test_ga4_connection(api):
    """GA4接続テスト"""
    print_separator("GA4 API接続テスト")
    
    try:
        # 過去7日間のデータを取得（少量のデータでテスト）
        print("📊 過去7日間のデータを取得中...")
        
        ga4_data = api.get_ga4_data(
            date_range_days=7,
            metrics=['sessions', 'totalUsers'],
            dimensions=['date']
        )
        
        if not ga4_data.empty:
            print(f"✅ データ取得成功: {len(ga4_data)}行")
            print("\n--- データプレビュー ---")
            print(ga4_data.head(10).to_string(index=False))
            
            # 統計情報
            if 'sessions' in ga4_data.columns:
                total_sessions = ga4_data['sessions'].sum()
                print(f"\n📈 合計セッション数: {total_sessions:,.0f}")
            
            if 'totalUsers' in ga4_data.columns:
                total_users = ga4_data['totalUsers'].sum()
                print(f"👥 合計ユーザー数: {total_users:,.0f}")
            
            return True
        else:
            print("⚠️  データが取得できませんでした")
            print("   以下を確認してください：")
            print("   1. GA4プロパティIDが正しいか")
            print("   2. 過去7日間にデータがあるか")
            print("   3. GA4プロパティへのアクセス権限があるか")
            return False
            
    except Exception as e:
        print(f"❌ GA4データ取得エラー: {e}")
        return False

def test_gsc_connection(api):
    """GSC接続テスト"""
    print_separator("Google Search Console API接続テスト")
    
    try:
        # 過去7日間のデータを取得
        print("📊 過去7日間の検索データを取得中...")
        
        gsc_data = api.get_gsc_data(
            date_range_days=7,
            dimensions=['date', 'query']
        )
        
        if not gsc_data.empty:
            print(f"✅ データ取得成功: {len(gsc_data)}行")
            print("\n--- データプレビュー（上位10件）---")
            top_queries = gsc_data.nlargest(10, 'clicks')[['query', 'clicks', 'impressions', 'position']]
            print(top_queries.to_string(index=False))
            
            # 統計情報
            total_clicks = gsc_data['clicks'].sum()
            total_impressions = gsc_data['impressions'].sum()
            avg_position = gsc_data['position'].mean()
            
            print(f"\n📈 合計クリック数: {total_clicks:,.0f}")
            print(f"👀 合計表示回数: {total_impressions:,.0f}")
            print(f"📊 平均検索順位: {avg_position:.1f}位")
            
            return True
        else:
            print("⚠️  データが取得できませんでした")
            print("   以下を確認してください：")
            print("   1. GSCサイトURLが正しいか")
            print("   2. Search Consoleプロパティへのアクセス権限があるか")
            print("   3. 過去にデータがあるか（GSCは3日前までのデータ）")
            return False
            
    except Exception as e:
        print(f"❌ GSCデータ取得エラー: {e}")
        return False

def test_summary_report(api):
    """サマリーレポート生成テスト"""
    print_separator("サマリーレポート生成テスト")
    
    try:
        print("📊 30日間のサマリーレポートを生成中...")
        
        summary = api.get_summary_report(date_range_days=30)
        
        print("✅ レポート生成成功")
        print(f"\n--- レポート情報 ---")
        print(f"レポート日時: {summary['report_date']}")
        print(f"分析期間: {summary['date_range_days']}日")
        print(f"サイトURL: {summary['site_url']}")
        print(f"GA4プロパティID: {summary['ga4_property_id']}")
        
        print("\n--- GA4サマリー ---")
        if summary['ga4_summary']:
            for key, value in summary['ga4_summary'].items():
                if isinstance(value, float):
                    print(f"  {key}: {value:,.2f}")
                else:
                    print(f"  {key}: {value:,}")
        else:
            print("  データなし")
        
        print("\n--- GSCサマリー ---")
        if summary['gsc_summary']:
            for key, value in summary['gsc_summary'].items():
                if isinstance(value, float):
                    print(f"  {key}: {value:,.2f}")
                else:
                    print(f"  {key}: {value:,}")
        else:
            print("  データなし")
        
        # レポート保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'data/processed/test_report_{timestamp}.json'
        
        import json
        os.makedirs('data/processed', exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 レポートを保存しました: {report_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ サマリーレポート生成エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("\n" + "=" * 60)
    print("  OAuth 2.0 GA4 API連携テストスクリプト")
    print("=" * 60)
    print("\n🔐 このスクリプトは以下のテストを実行します：")
    print("  1. OAuth 2.0認証")
    print("  2. GA4 API接続とデータ取得")
    print("  3. Google Search Console API接続とデータ取得")
    print("  4. サマリーレポート生成")
    print("\n初回実行時はブラウザが開き、Googleログインが必要です。")
    
    input("\n続行するにはEnterキーを押してください...")
    
    # テスト1: 認証
    api = test_authentication()
    if not api:
        print("\n❌ 認証に失敗したため、テストを中止します。")
        print("\n📝 トラブルシューティング：")
        print("  1. config/oauth_credentials.json が存在することを確認")
        print("  2. Google Cloud ConsoleでOAuth 2.0クライアントIDを作成")
        print("  3. クライアントIDのJSONファイルをダウンロードして配置")
        print("  4. ドキュメントを参照: docs/analytics/oauth_setup_guide.md")
        sys.exit(1)
    
    # テスト結果を記録
    results = {
        'authentication': True,
        'ga4_connection': False,
        'gsc_connection': False,
        'summary_report': False
    }
    
    # テスト2: GA4接続
    results['ga4_connection'] = test_ga4_connection(api)
    
    # テスト3: GSC接続
    results['gsc_connection'] = test_gsc_connection(api)
    
    # テスト4: サマリーレポート
    results['summary_report'] = test_summary_report(api)
    
    # 最終結果
    print_separator("テスト結果サマリー")
    
    all_passed = all(results.values())
    
    print(f"\n{'✅' if results['authentication'] else '❌'} OAuth 2.0認証")
    print(f"{'✅' if results['ga4_connection'] else '❌'} GA4 API接続")
    print(f"{'✅' if results['gsc_connection'] else '❌'} Google Search Console API接続")
    print(f"{'✅' if results['summary_report'] else '❌'} サマリーレポート生成")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 すべてのテストが成功しました！")
        print("\n次のステップ：")
        print("  • analytics/oauth_google_apis.py を使用してデータ分析を実行")
        print("  • 定期的なデータ収集の自動化を検討")
    else:
        print("⚠️  一部のテストが失敗しました")
        print("\n失敗したテストの確認とトラブルシューティングが必要です。")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()


