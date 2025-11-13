#!/usr/bin/env python3
"""
権限確認スクリプト
- 利用可能なGA4プロパティの確認
- 利用可能なGSCサイトの確認
- 権限設定の確認
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_ga4_properties(credentials_file):
    """利用可能なGA4プロパティを確認"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        # GA4 Admin APIサービス構築
        service = build('analyticsadmin', 'v1beta', credentials=credentials)
        
        # アカウント一覧取得
        accounts = service.accounts().list().execute()
        
        print("=== GA4 アカウント一覧 ===")
        if 'accounts' in accounts:
            for account in accounts['accounts']:
                print(f"アカウント名: {account.get('displayName', 'N/A')}")
                print(f"アカウントID: {account.get('name', 'N/A')}")
                print(f"作成日: {account.get('createTime', 'N/A')}")
                print("---")
                
                # プロパティ一覧取得
                account_id = account['name'].split('/')[-1]
                try:
                    properties = service.accounts().properties().list(
                        parent=f"accounts/{account_id}"
                    ).execute()
                    
                    if 'properties' in properties:
                        print("プロパティ一覧:")
                        for prop in properties['properties']:
                            print(f"  - プロパティ名: {prop.get('displayName', 'N/A')}")
                            print(f"    プロパティID: {prop.get('name', 'N/A')}")
                            print(f"    作成日: {prop.get('createTime', 'N/A')}")
                            print()
                except HttpError as e:
                    print(f"  プロパティ取得エラー: {e}")
                    print()
        else:
            print("アカウントが見つかりません")
            
    except Exception as e:
        logger.error(f"GA4プロパティ確認エラー: {e}")

def check_gsc_sites(credentials_file):
    """利用可能なGSCサイトを確認"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        
        # GSC APIサービス構築
        service = build('searchconsole', 'v1', credentials=credentials)
        
        # サイト一覧取得
        sites = service.sites().list().execute()
        
        print("=== GSC サイト一覧 ===")
        if 'siteEntry' in sites:
            for site in sites['siteEntry']:
                print(f"サイトURL: {site.get('siteUrl', 'N/A')}")
                print(f"権限レベル: {site.get('permissionLevel', 'N/A')}")
                print("---")
        else:
            print("サイトが見つかりません")
            
    except Exception as e:
        logger.error(f"GSCサイト確認エラー: {e}")

def test_ga4_data_access(credentials_file, property_id):
    """GA4データアクセステスト"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        # GA4 Data APIサービス構築
        service = build('analyticsdata', 'v1beta', credentials=credentials)
        
        # 簡単なリクエスト
        request = {
            'requests': [{
                'property': f'properties/{property_id}',
                'dateRanges': [{'startDate': '2025-10-01', 'endDate': '2025-10-01'}],
                'metrics': [{'name': 'sessions'}],
                'dimensions': [{'name': 'date'}],
                'limit': 1
            }]
        }
        
        response = service.properties().batchRunReports(
            property=f'properties/{property_id}',
            body=request
        ).execute()
        
        print(f"=== GA4 データアクセステスト (プロパティID: {property_id}) ===")
        print("✅ アクセス成功")
        if 'reports' in response and response['reports']:
            report = response['reports'][0]
            if 'rows' in report:
                print(f"データ行数: {len(report['rows'])}")
            else:
                print("データ行なし")
        else:
            print("レポートデータなし")
            
    except HttpError as e:
        print(f"=== GA4 データアクセステスト (プロパティID: {property_id}) ===")
        print(f"❌ アクセス失敗: {e}")
    except Exception as e:
        print(f"=== GA4 データアクセステスト (プロパティID: {property_id}) ===")
        print(f"❌ エラー: {e}")

def test_gsc_data_access(credentials_file, site_url):
    """GSCデータアクセステスト"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        
        # GSC APIサービス構築
        service = build('searchconsole', 'v1', credentials=credentials)
        
        # 簡単なリクエスト
        request = {
            'startDate': '2025-10-01',
            'endDate': '2025-10-01',
            'dimensions': ['date'],
            'rowLimit': 1
        }
        
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body=request
        ).execute()
        
        print(f"=== GSC データアクセステスト (サイトURL: {site_url}) ===")
        print("✅ アクセス成功")
        if 'rows' in response:
            print(f"データ行数: {len(response['rows'])}")
        else:
            print("データ行なし")
            
    except HttpError as e:
        print(f"=== GSC データアクセステスト (サイトURL: {site_url}) ===")
        print(f"❌ アクセス失敗: {e}")
    except Exception as e:
        print(f"=== GSC データアクセステスト (サイトURL: {site_url}) ===")
        print(f"❌ エラー: {e}")

def main():
    """メイン実行関数"""
    print("=== 権限確認スクリプト ===")
    
    credentials_file = 'config/google-credentials.json'
    
    if not os.path.exists(credentials_file):
        print(f"認証ファイルが見つかりません: {credentials_file}")
        return
    
    print(f"認証ファイル: {credentials_file}")
    print()
    
    # GA4プロパティ確認
    check_ga4_properties(credentials_file)
    print()
    
    # GSCサイト確認
    check_gsc_sites(credentials_file)
    print()
    
    # 設定ファイルのプロパティIDでテスト
    config_file = 'config/analytics_config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        sites = config.get('sites', {})
        for site_name, site_config in sites.items():
            print(f"=== {site_name.upper()} サイトのテスト ===")
            
            # GA4テスト
            ga4_property_id = site_config.get('ga4_property_id')
            if ga4_property_id and ga4_property_id != 'your-ga4-property-id-for-idea':
                test_ga4_data_access(credentials_file, ga4_property_id)
            
            # GSCテスト
            gsc_site_url = site_config.get('gsc_site_url')
            if gsc_site_url:
                test_gsc_data_access(credentials_file, gsc_site_url)
            
            print()

if __name__ == "__main__":
    main()







