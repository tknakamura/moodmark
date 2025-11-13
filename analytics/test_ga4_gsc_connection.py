#!/usr/bin/env python3
"""
GA4とGSCへの接続テストスクリプト
"""

import os
import sys
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ga4_connection(credentials_file, property_id):
    """GA4への接続テスト"""
    print("\n" + "=" * 60)
    print("=== GA4接続テスト ===")
    print("=" * 60)
    
    try:
        # 認証
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        
        # GA4 APIサービス構築
        ga4_service = build('analyticsdata', 'v1beta', credentials=credentials)
        
        print(f"✅ 認証成功: {credentials.service_account_email}")
        print(f"✅ GA4 APIサービス構築成功")
        
        # プロパティ情報の取得テスト
        print(f"\nプロパティID: {property_id}")
        print("プロパティ情報を取得中...")
        
        # 簡単なデータ取得テスト（過去7日間のセッション数）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        request = {
            'requests': [{
                'property': f'properties/{property_id}',
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [{'name': 'sessions'}],
                'dimensions': [{'name': 'date'}],
                'limit': 10
            }]
        }
        
        response = ga4_service.properties().batchRunReports(
            property=f'properties/{property_id}',
            body=request
        ).execute()
        
        print(f"✅ GA4データ取得成功")
        
        # 結果の表示
        if 'reports' in response and len(response['reports']) > 0:
            report = response['reports'][0]
            if 'rows' in report and len(report['rows']) > 0:
                print(f"\n取得データ件数: {len(report['rows'])}行")
                print("\nサンプルデータ（最初の3行）:")
                for i, row in enumerate(report['rows'][:3], 1):
                    date = row['dimensionValues'][0]['value']
                    sessions = row['metricValues'][0]['value']
                    print(f"  {i}. 日付: {date}, セッション数: {sessions}")
            else:
                print("⚠️  データが0件でした（期間内にデータがない可能性があります）")
        else:
            print("⚠️  レスポンスにデータが含まれていません")
        
        return True
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        print(f"❌ GA4 API エラー: {e}")
        print(f"エラー詳細: {error_details}")
        
        if e.resp.status == 403:
            print("\n⚠️  権限エラーの可能性があります。以下を確認してください:")
            print("1. サービスアカウントにGA4プロパティへのアクセス権限が付与されているか")
            print("2. Google Cloud ConsoleでAnalytics Data APIが有効になっているか")
        elif e.resp.status == 404:
            print("\n⚠️  プロパティが見つかりません。プロパティIDを確認してください。")
        
        return False
        
    except Exception as e:
        print(f"❌ GA4接続エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gsc_connection(credentials_file, site_url):
    """GSCへの接続テスト"""
    print("\n" + "=" * 60)
    print("=== GSC接続テスト ===")
    print("=" * 60)
    
    try:
        # 認証
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        
        # GSC APIサービス構築
        gsc_service = build('searchconsole', 'v1', credentials=credentials)
        
        print(f"✅ 認証成功: {credentials.service_account_email}")
        print(f"✅ GSC APIサービス構築成功")
        
        # サイト情報の確認
        print(f"\nサイトURL: {site_url}")
        print("サイト情報を取得中...")
        
        # サイトリストの取得
        sites = gsc_service.sites().list().execute()
        
        if 'siteEntry' in sites:
            print(f"✅ アクセス可能なサイト数: {len(sites['siteEntry'])}")
            print("\nアクセス可能なサイト一覧:")
            for site in sites['siteEntry']:
                permission = site.get('permissionLevel', 'unknown')
                print(f"  - {site['siteUrl']} (権限: {permission})")
            
            # 指定されたサイトがリストに含まれているか確認
            site_found = any(s['siteUrl'] == site_url for s in sites['siteEntry'])
            if not site_found:
                print(f"\n⚠️  指定されたサイトURL ({site_url}) がリストに含まれていません")
                print("サイトURLが正しいか、またはサービスアカウントにアクセス権限があるか確認してください。")
        else:
            print("⚠️  アクセス可能なサイトが見つかりませんでした")
        
        # データ取得テスト（過去7日間）
        print(f"\nデータ取得テスト（過去7日間）...")
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['date'],
            'rowLimit': 10
        }
        
        response = gsc_service.searchanalytics().query(
            siteUrl=site_url,
            body=request
        ).execute()
        
        print(f"✅ GSCデータ取得成功")
        
        # 結果の表示
        if 'rows' in response and len(response['rows']) > 0:
            print(f"\n取得データ件数: {len(response['rows'])}行")
            total_clicks = sum(row.get('clicks', 0) for row in response['rows'])
            total_impressions = sum(row.get('impressions', 0) for row in response['rows'])
            print(f"合計クリック数: {total_clicks:,}")
            print(f"合計インプレッション数: {total_impressions:,}")
            
            print("\nサンプルデータ（最初の3行）:")
            for i, row in enumerate(response['rows'][:3], 1):
                date = row['keys'][0]
                clicks = row.get('clicks', 0)
                impressions = row.get('impressions', 0)
                print(f"  {i}. 日付: {date}, クリック: {clicks}, インプレッション: {impressions}")
        else:
            print("⚠️  データが0件でした（期間内にデータがない可能性があります）")
        
        return True
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        print(f"❌ GSC API エラー: {e}")
        print(f"エラー詳細: {error_details}")
        
        if e.resp.status == 403:
            print("\n⚠️  権限エラーの可能性があります。以下を確認してください:")
            print("1. サービスアカウントにGSCサイトへのアクセス権限が付与されているか")
            print("2. Google Cloud ConsoleでSearch Console APIが有効になっているか")
            print("3. GSCでサービスアカウントのメールアドレスを所有者またはユーザーとして追加しているか")
        elif e.resp.status == 404:
            print("\n⚠️  サイトが見つかりません。サイトURLを確認してください。")
        
        return False
        
    except Exception as e:
        print(f"❌ GSC接続エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("GA4とGSC接続テスト")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 設定
    credentials_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config',
        'google-credentials-474807.json'
    )
    
    ga4_property_id = '316302380'
    gsc_site_url = 'https://isetan.mistore.jp/moodmark/'
    
    # ファイルの存在確認
    if not os.path.exists(credentials_file):
        print(f"❌ 認証ファイルが見つかりません: {credentials_file}")
        print("キーファイルが正しい場所に配置されているか確認してください。")
        return
    
    print(f"\n認証ファイル: {credentials_file}")
    print(f"GA4プロパティID: {ga4_property_id}")
    print(f"GSCサイトURL: {gsc_site_url}")
    
    # テスト実行
    results = []
    
    # GA4テスト
    ga4_result = test_ga4_connection(credentials_file, ga4_property_id)
    results.append(('GA4', ga4_result))
    
    # GSCテスト
    gsc_result = test_gsc_connection(credentials_file, gsc_site_url)
    results.append(('GSC', gsc_result))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("=== テスト結果サマリー ===")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 すべての接続テストが成功しました！")
        print("\n次のステップ:")
        print("1. 環境変数を設定:")
        print("   export GOOGLE_CREDENTIALS_FILE='config/google-credentials-474807.json'")
        print("   export GA4_PROPERTY_ID='316302380'")
        print("   export GSC_SITE_URL='https://isetan.mistore.jp/moodmark/'")
        print("\n2. データ取得テスト:")
        print("   python analytics/google_apis_integration.py")
    else:
        print("\n⚠️  一部の接続テストが失敗しました。")
        print("エラーメッセージを確認して設定を修正してください。")

if __name__ == "__main__":
    main()

