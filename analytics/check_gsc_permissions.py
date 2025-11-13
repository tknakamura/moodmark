#!/usr/bin/env python3
"""
GSC権限確認スクリプト
- nakamura@likepass.netのGSC権限確認
- 利用可能なサイトの確認
"""

import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_gsc_sites():
    """GSCサイトの権限確認"""
    try:
        # OAuth認証でGSC APIサービス構築
        token_path = 'config/token.json'
        if not os.path.exists(token_path):
            logger.error("OAuthトークンファイルが見つかりません")
            return
        
        credentials = Credentials.from_authorized_user_file(
            token_path, 
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        
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

def test_gsc_data_access():
    """GSCデータアクセステスト"""
    try:
        # OAuth認証でGSC APIサービス構築
        token_path = 'config/token.json'
        if not os.path.exists(token_path):
            logger.error("OAuthトークンファイルが見つかりません")
            return
        
        credentials = Credentials.from_authorized_user_file(
            token_path, 
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        
        service = build('searchconsole', 'v1', credentials=credentials)
        
        # テスト対象サイト
        test_sites = [
            'sc-domain:isetan.mistore.jp',
            'https://isetan.mistore.jp/moodmark/',
            'https://isetan.mistore.jp/moodmarkgift/'
        ]
        
        for site_url in test_sites:
            try:
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
                print()
                
            except HttpError as e:
                print(f"=== GSC データアクセステスト (サイトURL: {site_url}) ===")
                print(f"❌ アクセス失敗: {e}")
                print()
            except Exception as e:
                print(f"=== GSC データアクセステスト (サイトURL: {site_url}) ===")
                print(f"❌ エラー: {e}")
                print()
            
    except Exception as e:
        logger.error(f"GSCデータアクセステストエラー: {e}")

def main():
    """メイン実行関数"""
    print("=== GSC権限確認スクリプト ===")
    print("nakamura@likepass.netのGSC権限を確認します\n")
    
    # GSCサイト確認
    check_gsc_sites()
    print()
    
    # GSCデータアクセステスト
    test_gsc_data_access()

if __name__ == "__main__":
    main()







