#!/usr/bin/env python3
"""
nakamura@likepass.netアカウント用OAuth認証情報設定スクリプト
Google Cloud ConsoleでOAuth 2.0クライアントIDを作成し、
認証情報ファイルを設定します。
"""

import os
import json
import webbrowser
from pathlib import Path

def create_oauth_credentials_template():
    """OAuth認証情報テンプレートの作成"""
    
    print("=== nakamura@likepass.net アカウント用OAuth認証情報設定 ===")
    print()
    print("以下の手順でOAuth認証情報を設定してください：")
    print()
    print("1. Google Cloud Consoleにアクセス")
    print("   https://console.cloud.google.com/")
    print()
    print("2. nakamura@likepass.netでログイン")
    print()
    print("3. プロジェクトを作成または選択")
    print("   - プロジェクト名: mood-mark-analytics (推奨)")
    print()
    print("4. APIs & Services > Credentials に移動")
    print()
    print("5. 'Create Credentials' > 'OAuth client ID' をクリック")
    print()
    print("6. Application type: 'Desktop application' を選択")
    print()
    print("7. Name: 'MOO-D MARK Analytics' (任意)")
    print()
    print("8. 'Create' をクリック")
    print()
    print("9. ダウンロードされたJSONファイルを config/oauth_credentials.json として保存")
    print()
    
    # 設定ディレクトリの作成
    config_dir = Path('config')
    config_dir.mkdir(exist_ok=True)
    
    # テンプレートファイルの作成
    template_content = {
        "web": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "your-project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    template_file = config_dir / 'oauth_credentials_template.json'
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template_content, f, indent=2, ensure_ascii=False)
    
    print(f"テンプレートファイルを作成しました: {template_file}")
    print()
    print("実際の認証情報ファイル (config/oauth_credentials.json) を作成する際の参考にしてください。")
    print()
    
    # Google Cloud Consoleを開く
    try:
        webbrowser.open('https://console.cloud.google.com/')
        print("Google Cloud Consoleをブラウザで開きました。")
    except:
        print("ブラウザを手動で開いてください: https://console.cloud.google.com/")
    
    print()
    print("=== 必要な権限設定 ===")
    print()
    print("OAuth認証情報作成後、以下のAPIを有効化してください：")
    print()
    print("1. Google Analytics Reporting API")
    print("2. Google Search Console API")
    print()
    print("APIs & Services > Library で検索して有効化してください。")
    print()
    print("=== GA4プロパティとGSCサイトの設定 ===")
    print()
    print("nakamura@likepass.netアカウントで以下にアクセス権限が必要です：")
    print()
    print("1. GA4プロパティ (ID: 316302380)")
    print("   - https://analytics.google.com/")
    print("   - プロパティにアクセス権限を付与してもらう")
    print()
    print("2. Search Consoleサイト")
    print("   - https://search.google.com/search-console/")
    print("   - https://isetan.mistore.jp/moodmarkgift/ のサイトにアクセス権限を付与してもらう")
    print()
    print("=== 設定完了後の確認 ===")
    print()
    print("認証情報設定完了後、以下のコマンドでテストしてください：")
    print()
    print("python analytics/christmas_oauth_report.py")
    print()
    print("初回実行時にブラウザが開き、nakamura@likepass.netでログインが求められます。")
    print("ログイン後、トークンが自動保存され、以降は自動で認証されます。")

def check_existing_credentials():
    """既存の認証情報ファイルの確認"""
    credentials_file = Path('config/oauth_credentials.json')
    token_file = Path('config/token.json')
    
    print("=== 既存の認証情報確認 ===")
    print()
    
    if credentials_file.exists():
        print("✅ OAuth認証情報ファイルが見つかりました:")
        print(f"   {credentials_file}")
        
        try:
            with open(credentials_file, 'r', encoding='utf-8') as f:
                creds = json.load(f)
            
            if 'web' in creds and 'client_id' in creds['web']:
                client_id = creds['web']['client_id']
                print(f"   クライアントID: {client_id}")
                print("   認証情報ファイルは正常です。")
            else:
                print("   ⚠️  認証情報ファイルの形式が正しくありません。")
                return False
                
        except Exception as e:
            print(f"   ❌ 認証情報ファイルの読み込みエラー: {e}")
            return False
    else:
        print("❌ OAuth認証情報ファイルが見つかりません:")
        print(f"   {credentials_file}")
        return False
    
    if token_file.exists():
        print("✅ トークンファイルが見つかりました:")
        print(f"   {token_file}")
        print("   既に認証済みです。")
    else:
        print("ℹ️  トークンファイルが見つかりません:")
        print(f"   {token_file}")
        print("   初回実行時に認証が必要です。")
    
    return True

def main():
    """メイン実行関数"""
    print("nakamura@likepass.net アカウント用 OAuth認証情報設定")
    print("=" * 60)
    
    # 既存の認証情報確認
    if check_existing_credentials():
        print()
        print("認証情報は既に設定されています。")
        print("クリスマスシーズンレポートを生成するには:")
        print("python analytics/christmas_oauth_report.py")
    else:
        print()
        create_oauth_credentials_template()

if __name__ == "__main__":
    main()







