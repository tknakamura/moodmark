#!/usr/bin/env python3
"""
Google APIs連携テストスクリプト
"""

import os
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_google_apis_integration():
    """Google APIs統合のテスト"""
    print("=== Google APIs統合テスト ===")
    
    try:
        from google_apis_integration import GoogleAPIsIntegration
        
        # API統合インスタンス作成
        api = GoogleAPIsIntegration()
        
        if not api.credentials:
            print("❌ 認証に失敗しました。認証ファイルを確認してください。")
            return False
        
        print("✅ Google APIs認証成功")
        
        # 環境変数の確認
        if not api.ga4_property_id:
            print("⚠️  GA4_PROPERTY_IDが設定されていません")
        
        if not api.gsc_site_url:
            print("⚠️  GSC_SITE_URLが設定されていません")
        
        print("✅ Google APIs統合テスト完了")
        return True
        
    except ImportError as e:
        print(f"❌ モジュールのインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ Google APIs統合テストエラー: {e}")
        return False

def test_looker_studio_connector():
    """Looker Studio コネクタのテスト"""
    print("\n=== Looker Studio コネクタテスト ===")
    
    try:
        from looker_studio_connector import LookerStudioConnector
        
        # コネクタ初期化
        connector = LookerStudioConnector()
        
        if not connector.credentials:
            print("❌ Looker Studio認証に失敗しました。")
            return False
        
        print("✅ Looker Studio コネクタ認証成功")
        print("✅ Looker Studio コネクタテスト完了")
        return True
        
    except ImportError as e:
        print(f"❌ モジュールのインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ Looker Studio コネクタテストエラー: {e}")
        return False

def test_integrated_analytics_system():
    """統合分析システムのテスト"""
    print("\n=== 統合分析システムテスト ===")
    
    try:
        from integrated_analytics_system import IntegratedAnalyticsSystem
        
        # システム初期化
        system = IntegratedAnalyticsSystem()
        
        print("✅ 統合分析システム初期化成功")
        
        # 設定確認
        print(f"設定ファイル: {system.config}")
        
        print("✅ 統合分析システムテスト完了")
        return True
        
    except ImportError as e:
        print(f"❌ モジュールのインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 統合分析システムテストエラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("Google APIs連携システムテスト開始")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 環境変数の確認
    print("\n=== 環境変数確認 ===")
    required_vars = [
        'GOOGLE_CREDENTIALS_FILE',
        'GA4_PROPERTY_ID', 
        'GSC_SITE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: 設定済み")
        else:
            print(f"❌ {var}: 未設定")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        print("設定例:")
        print("export GOOGLE_CREDENTIALS_FILE='config/google-credentials.json'")
        print("export GA4_PROPERTY_ID='your-ga4-property-id'")
        print("export GSC_SITE_URL='https://isetan.mistore.jp/moodmarkgift/'")
        print("\n環境変数を設定してから再実行してください。")
        return
    
    # テスト実行
    tests = [
        test_google_apis_integration,
        test_looker_studio_connector,
        test_integrated_analytics_system
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ テスト実行エラー: {e}")
            results.append(False)
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("=== テスト結果サマリー ===")
    
    passed = sum(results)
    total = len(results)
    
    print(f"合格: {passed}/{total}")
    
    if passed == total:
        print("🎉 すべてのテストが合格しました！")
        print("\n次のステップ:")
        print("1. 実際のGA4プロパティIDとGSCサイトURLを設定")
        print("2. python analytics/google_apis_integration.py でデータ取得テスト")
        print("3. python analytics/integrated_analytics_system.py once で統合テスト")
    else:
        print("⚠️  一部のテストが失敗しました。")
        print("エラーメッセージを確認して設定を修正してください。")

if __name__ == "__main__":
    main()
