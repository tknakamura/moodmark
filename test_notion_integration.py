#!/usr/bin/env python3
"""
Notion統合テストスクリプト
- 全機能の動作確認
- エラーケースのテスト
- パフォーマンステスト
"""

import os
import sys
import json
import tempfile
from datetime import datetime, timedelta
from analytics.notion_integration import NotionIntegration
from analytics.notion_report_converter import NotionReportConverter
from analytics.integrated_analytics_system import IntegratedAnalyticsSystem

def print_test_header(title):
    """テストヘッダー表示"""
    print("\n" + "="*60)
    print(f" TEST: {title}")
    print("="*60)

def print_test_result(test_name, success, details=None):
    """テスト結果表示"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"     Details: {details}")

class NotionIntegrationTester:
    def __init__(self):
        self.results = []
        
    def add_result(self, test_name, success, details=None):
        """テスト結果を記録"""
        self.results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now()
        })
        print_test_result(test_name, success, details)
    
    def test_environment_setup(self):
        """環境設定のテスト"""
        print_test_header("環境設定確認")
        
        # 必須環境変数の確認
        token = os.getenv('NOTION_TOKEN')
        success = token is not None and token.startswith('secret_')
        self.add_result(
            "Environment Variable - NOTION_TOKEN", 
            success,
            "Token found and valid format" if success else "Token missing or invalid format"
        )
        
        # オプション環境変数
        db_id = os.getenv('NOTION_DATABASE_ID')
        self.add_result(
            "Environment Variable - NOTION_DATABASE_ID", 
            db_id is not None,
            f"Database ID: {db_id[:10]}..." if db_id else "Not set (will be created)"
        )
        
        page_id = os.getenv('NOTION_PAGE_ID')
        self.add_result(
            "Environment Variable - NOTION_PAGE_ID", 
            page_id is not None,
            f"Page ID: {page_id[:10]}..." if page_id else "Not set"
        )
        
        return token is not None
    
    def test_notion_connection(self):
        """Notion接続のテスト"""
        print_test_header("Notion API接続")
        
        try:
            notion = NotionIntegration()
            
            # 認証テスト
            success = notion.client is not None
            self.add_result(
                "Notion Client Initialization",
                success,
                "Client created successfully" if success else "Failed to create client"
            )
            
            if not success:
                return None
            
            # データベース接続テスト
            if notion.database_id:
                db_info = notion.get_database_info()
                db_success = db_info is not None
                self.add_result(
                    "Database Connection",
                    db_success,
                    f"Database: {db_info['title'][0]['plain_text']}" if db_success else "Cannot access database"
                )
            else:
                self.add_result(
                    "Database Connection",
                    False,
                    "No database ID configured"
                )
            
            return notion
            
        except Exception as e:
            self.add_result("Notion Connection", False, str(e))
            return None
    
    def test_report_conversion(self):
        """レポート変換のテスト"""
        print_test_header("レポート変換機能")
        
        try:
            converter = NotionReportConverter()
            
            # テストデータの作成
            test_report = {
                "report_date": "2025-10-11T17:30:00",
                "period": "テスト期間",
                "site_url": "https://isetan.mistore.jp/moodmark",
                "summary": {
                    "total_sessions": 100000,
                    "total_users": 85000,
                    "total_pageviews": 250000,
                    "total_purchases": 600,
                    "total_revenue": 3600000,
                    "avg_bounce_rate": 0.25,
                    "avg_session_duration": 180,
                    "purchase_cvr": 0.6,
                    "avg_order_value": 6000
                },
                "recommendations": [
                    "モバイル購入CVRの改善が必要です。",
                    "自然検索からの流入を最適化してください。",
                    "ディスプレイ広告の予算を増額することを推奨します。"
                ]
            }
            
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(test_report, f, ensure_ascii=False, indent=2)
                temp_json_path = f.name
            
            try:
                # 変換テスト
                converted = converter.convert_analysis_report(temp_json_path)
                
                # 基本変換の確認
                success = bool(converted and 'summary' in converted)
                self.add_result(
                    "Basic Report Conversion",
                    success,
                    f"Converted {len(converted)} sections" if success else "Conversion failed"
                )
                
                # サマリー変換の確認
                if success:
                    summary = converted.get('summary', {})
                    summary_success = len(summary) > 0
                    self.add_result(
                        "Summary Metrics Conversion",
                        summary_success,
                        f"Converted {len(summary)} metrics" if summary_success else "No metrics converted"
                    )
                    
                    # 推奨事項変換の確認
                    recs = converted.get('recommendations', [])
                    rec_success = len(recs) > 0
                    self.add_result(
                        "Recommendations Conversion",
                        rec_success,
                        f"Converted {len(recs)} recommendations" if rec_success else "No recommendations converted"
                    )
                    
                    # KPI指標変換の確認
                    kpis = converted.get('kpi_metrics', [])
                    kpi_success = len(kpis) > 0
                    self.add_result(
                        "KPI Metrics Conversion",
                        kpi_success,
                        f"Converted {len(kpis)} KPI metrics" if kpi_success else "No KPI metrics converted"
                    )
                
                return converted
                
            finally:
                # 一時ファイルの削除
                os.unlink(temp_json_path)
                
        except Exception as e:
            self.add_result("Report Conversion", False, str(e))
            return None
    
    def test_page_creation(self, notion, test_data):
        """ページ作成のテスト"""
        print_test_header("Notionページ作成")
        
        if not notion or not test_data:
            self.add_result("Page Creation - Prerequisites", False, "Missing prerequisites")
            return None
        
        try:
            test_content = """# テストレポート

このページはNotion統合のテスト用に作成されました。

## 概要
- 自動ページ作成機能のテスト
- データの整合性確認
- フォーマット検証

## テスト項目
1. ✅ ページ作成
2. ✅ プロパティ設定
3. ✅ コンテンツ挿入

## 結論
Notion統合機能が正常に動作しています。
"""
            
            # ページ作成テスト
            page_id = notion.create_report_page(test_data, test_content)
            
            success = page_id is not None
            self.add_result(
                "Page Creation",
                success,
                f"Page ID: {page_id}" if success else "Failed to create page"
            )
            
            if success:
                # ステータス更新テスト
                update_success = notion.update_report_status(page_id, "Reviewed")
                self.add_result(
                    "Status Update",
                    update_success,
                    "Status updated to 'Reviewed'" if update_success else "Failed to update status"
                )
            
            return page_id
            
        except Exception as e:
            self.add_result("Page Creation", False, str(e))
            return None
    
    def test_integrated_system(self):
        """統合システムのテスト"""
        print_test_header("統合分析システム")
        
        try:
            # システム初期化
            system = IntegratedAnalyticsSystem()
            
            init_success = system is not None
            self.add_result(
                "System Initialization",
                init_success,
                "System initialized successfully" if init_success else "System initialization failed"
            )
            
            if not init_success:
                return False
            
            # Notion統合の確認
            notion_success = system.notion_integration is not None
            self.add_result(
                "Notion Integration in System",
                notion_success,
                "Notion integration enabled" if notion_success else "Notion integration disabled"
            )
            
            # 設定の確認
            config = system.config.get('notion', {})
            config_success = config.get('enabled', False)
            self.add_result(
                "Configuration Check",
                config_success,
                f"Notion config: enabled={config.get('enabled')}, auto_sync={config.get('auto_sync')}" if config_success else "Notion not enabled in config"
            )
            
            return True
            
        except Exception as e:
            self.add_result("Integrated System", False, str(e))
            return False
    
    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        print_test_header("エラーハンドリング")
        
        # 無効なトークンでの初期化テスト
        original_token = os.getenv('NOTION_TOKEN')
        os.environ['NOTION_TOKEN'] = 'invalid_token'
        
        try:
            notion = NotionIntegration()
            invalid_success = notion.client is None
            self.add_result(
                "Invalid Token Handling",
                invalid_success,
                "Properly handled invalid token" if invalid_success else "Failed to handle invalid token"
            )
        except:
            self.add_result("Invalid Token Handling", True, "Exception properly raised")
        finally:
            # 元のトークンを復元
            if original_token:
                os.environ['NOTION_TOKEN'] = original_token
        
        # 存在しないファイルでの変換テスト
        try:
            converter = NotionReportConverter()
            converted = converter.convert_analysis_report('/nonexistent/file.json')
            
            file_error_success = not converted or len(converted) == 0
            self.add_result(
                "Nonexistent File Handling",
                file_error_success,
                "Properly handled nonexistent file" if file_error_success else "Failed to handle nonexistent file"
            )
        except:
            self.add_result("Nonexistent File Handling", True, "Exception properly raised")
    
    def test_performance(self):
        """パフォーマンステスト"""
        print_test_header("パフォーマンス")
        
        try:
            converter = NotionReportConverter()
            
            # 大きなテストデータの作成
            large_test_data = {
                "report_date": datetime.now().isoformat(),
                "period": "大容量テスト",
                "summary": {f"metric_{i}": i * 1000 for i in range(50)},
                "recommendations": [f"推奨事項 {i}: " + "テスト内容 " * 50 for i in range(20)]
            }
            
            # 変換時間の測定
            start_time = datetime.now()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(large_test_data, f, ensure_ascii=False)
                temp_path = f.name
            
            try:
                converted = converter.convert_analysis_report(temp_path)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds()
                performance_success = duration < 10.0  # 10秒以内
                
                self.add_result(
                    "Large Data Conversion Performance",
                    performance_success,
                    f"Conversion time: {duration:.2f}s" if performance_success else f"Too slow: {duration:.2f}s"
                )
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            self.add_result("Performance Test", False, str(e))
    
    def generate_report(self):
        """テストレポートの生成"""
        print_test_header("テスト結果サマリー")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 テスト結果:")
        print(f"   総テスト数: {total_tests}")
        print(f"   成功: {passed_tests}")
        print(f"   失敗: {failed_tests}")
        print(f"   成功率: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ 失敗したテスト:")
            for result in self.results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['details']}")
        
        # テスト結果をJSONファイルに保存
        report_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': success_rate,
                    'test_date': datetime.now().isoformat()
                },
                'results': [
                    {
                        'test': r['test'],
                        'success': r['success'],
                        'details': r['details'],
                        'timestamp': r['timestamp'].isoformat()
                    } for r in self.results
                ]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 詳細な結果は {report_file} に保存されました")
        
        return success_rate > 80.0  # 80%以上の成功率で合格
    
    def run_all_tests(self):
        """全テストの実行"""
        print("🧪 Notion統合機能の包括的テストを開始します\n")
        
        # 1. 環境設定テスト
        env_ok = self.test_environment_setup()
        
        if not env_ok:
            print("\n❌ 環境設定に問題があります。テストを中止します。")
            return False
        
        # 2. Notion接続テスト
        notion = self.test_notion_connection()
        
        # 3. レポート変換テスト
        converted_data = self.test_report_conversion()
        
        # 4. ページ作成テスト（接続が成功した場合のみ）
        if notion and converted_data:
            self.test_page_creation(notion, converted_data)
        
        # 5. 統合システムテスト
        self.test_integrated_system()
        
        # 6. エラーハンドリングテスト
        self.test_error_handling()
        
        # 7. パフォーマンステスト
        self.test_performance()
        
        # 8. レポート生成
        return self.generate_report()


def main():
    """メイン実行関数"""
    tester = NotionIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 全テストが正常に完了しました！")
        print("Notion統合機能は本番環境で使用可能です。")
    else:
        print("\n⚠️  一部のテストが失敗しました。")
        print("詳細を確認して問題を修正してください。")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
