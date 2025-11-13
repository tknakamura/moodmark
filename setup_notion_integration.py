#!/usr/bin/env python3
"""
Notion統合セットアップスクリプト
- 環境変数の設定確認
- Notion認証のテスト
- データベースの作成・設定
- 初期設定ファイルの生成
"""

import os
import json
import sys
from datetime import datetime
from analytics.notion_integration import NotionIntegration
from analytics.notion_report_converter import NotionReportConverter
from analytics.integrated_analytics_system import IntegratedAnalyticsSystem

def print_header(title):
    """ヘッダー表示"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_step(step, description):
    """ステップ表示"""
    print(f"\n[Step {step}] {description}")
    print("-" * 40)

def check_environment_variables():
    """環境変数の確認"""
    print_step(1, "環境変数の確認")
    
    required_vars = [
        ('NOTION_TOKEN', 'Notion Integration Token'),
        ('NOTION_DATABASE_ID', 'Analytics Database ID (オプション)'),
        ('NOTION_PAGE_ID', 'Parent Page ID (オプション)')
    ]
    
    missing_vars = []
    
    for var_name, description in required_vars:
        value = os.getenv(var_name)
        if value:
            print(f"✅ {var_name}: 設定済み")
            if var_name == 'NOTION_TOKEN':
                print(f"   → Token: {value[:10]}...")
        else:
            print(f"❌ {var_name}: 未設定")
            if 'オプション' not in description:
                missing_vars.append((var_name, description))
    
    if missing_vars:
        print(f"\n⚠️  必須の環境変数が未設定です:")
        for var_name, description in missing_vars:
            print(f"   - {var_name}: {description}")
        
        print(f"\n📖 設定方法:")
        print(f"   export NOTION_TOKEN='your_notion_integration_token'")
        print(f"   export NOTION_DATABASE_ID='your_database_id'  # オプション")
        print(f"   export NOTION_PAGE_ID='your_parent_page_id'    # オプション")
        
        return False
    
    return True

def test_notion_connection():
    """Notion接続テスト"""
    print_step(2, "Notion接続テスト")
    
    try:
        notion = NotionIntegration()
        
        if not notion.client:
            print("❌ Notion認証に失敗しました")
            return None
        
        print("✅ Notion認証成功")
        
        # データベース情報の取得
        if notion.database_id:
            db_info = notion.get_database_info()
            if db_info:
                print(f"✅ データベース接続成功: {db_info['title'][0]['plain_text']}")
            else:
                print("⚠️  データベースにアクセスできません")
        else:
            print("ℹ️  データベースIDが未設定です")
        
        return notion
        
    except Exception as e:
        print(f"❌ Notion接続エラー: {e}")
        return None

def create_or_update_database(notion):
    """データベースの作成・更新"""
    print_step(3, "データベースの作成・更新")
    
    if not notion:
        print("❌ Notion接続が確立されていません")
        return None
    
    try:
        if notion.database_id:
            print("ℹ️  既存のデータベースを使用します")
            db_info = notion.get_database_info()
            if db_info:
                print(f"   データベース名: {db_info['title'][0]['plain_text']}")
                print(f"   プロパティ数: {len(db_info['properties'])}")
                return notion.database_id
        
        # 新しいデータベースの作成
        parent_page_id = os.getenv('NOTION_PAGE_ID')
        if not parent_page_id:
            print("❌ 親ページIDが設定されていません")
            print("   NOTION_PAGE_ID環境変数を設定してください")
            return None
        
        print("🔄 新しいAnalyticsデータベースを作成しています...")
        database_id = notion.create_analytics_database(parent_page_id)
        
        if database_id:
            print(f"✅ データベース作成成功: {database_id}")
            return database_id
        else:
            print("❌ データベース作成に失敗しました")
            return None
            
    except Exception as e:
        print(f"❌ データベース作成エラー: {e}")
        return None

def test_report_conversion():
    """レポート変換テスト"""
    print_step(4, "レポート変換テスト")
    
    try:
        converter = NotionReportConverter()
        
        # テスト用のレポートファイルを検索
        test_files = [
            'data/processed/analysis_report_purchase_7days_20251011_173000.json',
            'data/processed/summary_report_oauth_20251011_170127.json'
        ]
        
        test_file = None
        for file_path in test_files:
            if os.path.exists(file_path):
                test_file = file_path
                break
        
        if not test_file:
            print("⚠️  テスト用のレポートファイルが見つかりません")
            print("   データ収集を実行してからテストしてください")
            return False
        
        print(f"📄 テストファイル: {test_file}")
        
        # レポート変換のテスト
        converted = converter.convert_analysis_report(test_file)
        
        if converted:
            print("✅ レポート変換成功")
            print(f"   サマリー指標: {len(converted.get('summary', {}))} 個")
            print(f"   推奨事項: {len(converted.get('recommendations', []))} 個")
            print(f"   KPI指標: {len(converted.get('kpi_metrics', []))} 個")
            return True
        else:
            print("❌ レポート変換に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ レポート変換テストエラー: {e}")
        return False

def test_notion_page_creation(notion, database_id):
    """Notionページ作成テスト"""
    print_step(5, "Notionページ作成テスト")
    
    if not notion or not database_id:
        print("❌ 前提条件が満たされていません")
        return False
    
    try:
        # テスト用レポートデータの作成
        test_report = {
            'report_date': datetime.now().isoformat(),
            'period': 'テスト期間',
            'site_url': 'https://isetan.mistore.jp/moodmark',
            'summary': {
                'total_sessions': 100000,
                'total_users': 85000,
                'total_revenue': 5000000,
                'purchase_cvr': 0.6,
                'avg_order_value': 6000
            },
            'recommendations': [
                'これはテスト用の推奨事項です。',
                'Notion統合が正常に動作しています。'
            ]
        }
        
        test_content = """# テストレポート

このページは Notion統合のテスト用に自動作成されました。

## 概要
- 統合システムが正常に動作しています
- レポートの自動生成が可能です
- データの同期が完了しました

## 次のステップ
1. 実際の分析レポートの生成
2. スケジュール設定の確認
3. アラート機能のテスト
"""
        
        print("🔄 テストページを作成しています...")
        page_id = notion.create_report_page(test_report, test_content)
        
        if page_id:
            print(f"✅ テストページ作成成功")
            print(f"   ページID: {page_id}")
            return True
        else:
            print("❌ テストページ作成に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ ページ作成テストエラー: {e}")
        return False

def update_configuration_files(database_id):
    """設定ファイルの更新"""
    print_step(6, "設定ファイルの更新")
    
    try:
        # analytics_config.json の更新
        analytics_config_path = 'config/analytics_config.json'
        
        if os.path.exists(analytics_config_path):
            with open(analytics_config_path, 'r', encoding='utf-8') as f:
                analytics_config = json.load(f)
        else:
            analytics_config = {}
        
        # Notion設定の追加・更新
        if 'notion' not in analytics_config:
            analytics_config['notion'] = {}
        
        analytics_config['notion'].update({
            'enabled': True,
            'auto_sync': True,
            'sync_after_report_generation': True,
            'create_database_if_missing': False  # 既に作成済み
        })
        
        # ファイルに保存
        os.makedirs('config', exist_ok=True)
        with open(analytics_config_path, 'w', encoding='utf-8') as f:
            json.dump(analytics_config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ {analytics_config_path} を更新しました")
        
        # notion_config.json の更新
        notion_config_path = 'config/notion_config.json'
        
        if os.path.exists(notion_config_path):
            with open(notion_config_path, 'r', encoding='utf-8') as f:
                notion_config = json.load(f)
            
            # データベースIDの更新
            if database_id:
                notion_config['notion']['database_id'] = database_id
                
                with open(notion_config_path, 'w', encoding='utf-8') as f:
                    json.dump(notion_config, f, ensure_ascii=False, indent=2)
                
                print(f"✅ {notion_config_path} を更新しました")
        
        return True
        
    except Exception as e:
        print(f"❌ 設定ファイル更新エラー: {e}")
        return False

def test_integrated_system():
    """統合システムのテスト"""
    print_step(7, "統合システムのテスト")
    
    try:
        print("🔄 統合分析システムを初期化しています...")
        system = IntegratedAnalyticsSystem()
        
        if system.notion_integration:
            print("✅ Notion統合が正常に初期化されました")
        else:
            print("⚠️  Notion統合は無効です")
        
        # 設定の確認
        notion_config = system.config.get('notion', {})
        print(f"   Auto Sync: {notion_config.get('auto_sync', False)}")
        print(f"   Sync After Report: {notion_config.get('sync_after_report_generation', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 統合システムテストエラー: {e}")
        return False

def generate_setup_summary(database_id):
    """セットアップサマリーの生成"""
    print_header("セットアップ完了サマリー")
    
    print("🎉 Notion統合セットアップが完了しました！")
    
    print(f"\n📋 設定情報:")
    print(f"   - Notion Token: 設定済み")
    if database_id:
        print(f"   - Database ID: {database_id}")
    
    print(f"\n📁 作成・更新されたファイル:")
    print(f"   - config/notion_config.json")
    print(f"   - config/analytics_config.json")
    print(f"   - analytics/notion_integration.py")
    print(f"   - analytics/notion_report_converter.py")
    
    print(f"\n🚀 次のステップ:")
    print(f"   1. 分析システムの実行:")
    print(f"      python analytics/integrated_analytics_system.py once")
    print(f"   ")
    print(f"   2. スケジュール実行:")
    print(f"      python analytics/integrated_analytics_system.py schedule")
    print(f"   ")
    print(f"   3. KPIダッシュボードの作成:")
    print(f"      python -c \"from analytics.integrated_analytics_system import IntegratedAnalyticsSystem; IntegratedAnalyticsSystem().create_notion_kpi_dashboard()\"")
    
    print(f"\n⚠️  注意事項:")
    print(f"   - 環境変数は毎回設定する必要があります")
    print(f"   - Notionワークスペースへのアクセス権限を確認してください")
    print(f"   - データベースの権限設定を適切に行ってください")

def main():
    """メイン実行関数"""
    print_header("MOO-D MARK Notion統合セットアップ")
    
    print("このスクリプトは、分析システムとNotionの統合をセットアップします。")
    
    # Step 1: 環境変数の確認
    if not check_environment_variables():
        print("\n❌ セットアップを中止します")
        sys.exit(1)
    
    # Step 2: Notion接続テスト
    notion = test_notion_connection()
    if not notion:
        print("\n❌ セットアップを中止します")
        sys.exit(1)
    
    # Step 3: データベースの作成・更新
    database_id = create_or_update_database(notion)
    if not database_id:
        print("\n❌ セットアップを中止します")
        sys.exit(1)
    
    # Step 4: レポート変換テスト
    conversion_success = test_report_conversion()
    
    # Step 5: Notionページ作成テスト
    page_creation_success = test_notion_page_creation(notion, database_id)
    
    # Step 6: 設定ファイルの更新
    config_success = update_configuration_files(database_id)
    
    # Step 7: 統合システムのテスト
    system_success = test_integrated_system()
    
    # サマリーの生成
    if all([conversion_success, page_creation_success, config_success, system_success]):
        generate_setup_summary(database_id)
    else:
        print_header("セットアップ不完全")
        print("⚠️  一部のテストが失敗しましたが、基本機能は利用可能です。")
        print("詳細は上記のログを確認してください。")

if __name__ == "__main__":
    main()
