#!/usr/bin/env python3
"""
インタラクティブ Google Cloud セットアップスクリプト
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def print_header():
    """ヘッダーの表示"""
    print("=" * 60)
    print("Google Cloud Console セットアップ支援")
    print("MOO:D MARK IDEA プロジェクト用")
    print("=" * 60)

def check_gcloud_installation():
    """gcloud CLIの確認"""
    print("\n=== Google Cloud CLI の確認 ===")
    
    try:
        result = subprocess.run(['gcloud', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Google Cloud CLI がインストールされています")
        print(f"   バージョン: {result.stdout.split()[0]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Google Cloud CLI がインストールされていません")
        print("\n📋 インストール方法:")
        print("   macOS: brew install google-cloud-sdk")
        print("   Windows: https://cloud.google.com/sdk/docs/install")
        print("   Linux: https://cloud.google.com/sdk/docs/install")
        return False

def get_user_input():
    """ユーザー入力の取得"""
    print("\n=== プロジェクト情報の入力 ===")
    
    # プロジェクト名の入力
    project_name = input("プロジェクト名を入力してください [MOOD_MARK_Analytics]: ").strip()
    if not project_name:
        project_name = "MOOD_MARK_Analytics"
    
    # 組織の確認
    print("\n組織について:")
    print("1. 組織あり")
    print("2. 個人利用（組織なし）")
    
    org_choice = input("選択してください [2]: ").strip()
    has_organization = org_choice == "1"
    
    return {
        'project_name': project_name,
        'has_organization': has_organization
    }

def create_project_with_gcloud(project_name, has_organization):
    """gcloud CLIでプロジェクトを作成"""
    print(f"\n=== プロジェクト作成: {project_name} ===")
    
    # プロジェクト作成コマンド
    cmd = ['gcloud', 'projects', 'create', project_name]
    
    if has_organization:
        org_id = input("組織IDを入力してください: ").strip()
        if org_id:
            cmd.extend(['--organization', org_id])
    
    try:
        print("プロジェクトを作成中...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ プロジェクトが作成されました: {project_name}")
        return project_name
    except subprocess.CalledProcessError as e:
        print(f"❌ プロジェクト作成エラー: {e.stderr}")
        
        # 手動入力の提案
        manual_id = input("プロジェクトIDを手動で入力してください: ").strip()
        if manual_id:
            return manual_id
        return None

def enable_apis(project_id):
    """必要なAPIを有効化"""
    print(f"\n=== API有効化: {project_id} ===")
    
    apis = [
        "analyticsreporting.googleapis.com",
        "analyticsdata.googleapis.com", 
        "searchconsole.googleapis.com",
        "drive.googleapis.com",
        "sheets.googleapis.com"
    ]
    
    # プロジェクトを設定
    subprocess.run(['gcloud', 'config', 'set', 'project', project_id], 
                  capture_output=True, check=True)
    
    for api in apis:
        try:
            print(f"  {api} を有効化中...")
            subprocess.run(['gcloud', 'services', 'enable', api], 
                         capture_output=True, check=True)
            print(f"  ✅ {api}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {api}: {e.stderr}")
    
    print("✅ API有効化完了")

def create_service_account(project_id):
    """サービスアカウントの作成"""
    print(f"\n=== サービスアカウント作成 ===")
    
    service_account_name = "mood-mark-analytics-service"
    service_account_email = f"{service_account_name}@{project_id}.iam.gserviceaccount.com"
    
    try:
        # サービスアカウント作成
        cmd = [
            'gcloud', 'iam', 'service-accounts', 'create', service_account_name,
            '--display-name=MOO:D MARK Analytics Service',
            '--description=MOO:D MARK Analytics API Access'
        ]
        
        print("サービスアカウントを作成中...")
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"✅ サービスアカウント作成完了: {service_account_email}")
        
        # 権限付与
        print("権限を付与中...")
        subprocess.run([
            'gcloud', 'projects', 'add-iam-policy-binding', project_id,
            '--member', f'serviceAccount:{service_account_email}',
            '--role', 'roles/editor'
        ], capture_output=True, check=True)
        print("✅ 権限付与完了")
        
        return service_account_email
        
    except subprocess.CalledProcessError as e:
        print(f"❌ サービスアカウント作成エラー: {e.stderr}")
        return None

def create_service_account_key(service_account_email):
    """サービスアカウントキーの作成"""
    print(f"\n=== サービスアカウントキー作成 ===")
    
    key_file = "config/google-credentials.json"
    os.makedirs("config", exist_ok=True)
    
    try:
        cmd = [
            'gcloud', 'iam', 'service-accounts', 'keys', 'create', key_file,
            '--iam-account', service_account_email
        ]
        
        print("キーファイルを作成中...")
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"✅ キーファイル作成完了: {key_file}")
        
        # ファイル権限の設定
        os.chmod(key_file, 0o600)
        print("✅ ファイル権限設定完了")
        
        return key_file
        
    except subprocess.CalledProcessError as e:
        print(f"❌ キーファイル作成エラー: {e.stderr}")
        return None

def update_env_file(project_id, service_account_email, key_file):
    """環境変数ファイルの更新"""
    print(f"\n=== 環境変数ファイルの更新 ===")
    
    env_content = f"""# Google Cloud Console設定
GOOGLE_PROJECT_ID={project_id}
GOOGLE_CREDENTIALS_FILE={key_file}
GOOGLE_SERVICE_ACCOUNT_EMAIL={service_account_email}

# Google Analytics 4設定（後で設定）
GA4_PROPERTY_ID=your-ga4-property-id

# Google Search Console設定（後で設定）
GSC_SITE_URL=https://isetan.mistore.jp/moodmarkgift/

# Looker Studio設定（後で設定）
LOOKER_STUDIO_FOLDER_ID=your-looker-studio-folder-id
DATA_SOURCE_FOLDER_ID=your-data-source-folder-id

# データベース設定
DATABASE_URL=postgresql://username:password@localhost:5432/moodmark_db

# Redis設定
REDIS_URL=redis://localhost:6379/0

# API設定
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_ANALYTICS_ID=your_ga_id_here

# 外部サービス設定
MOODMARK_API_URL=https://api.isetan.mistore.jp
MOODMARK_API_KEY=your_api_key_here

# 開発設定
DEBUG=True
LOG_LEVEL=INFO
ENVIRONMENT=development

# セキュリティ設定
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1
"""
    
    # .envファイルに書き込み
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ .envファイル更新完了")

def update_gitignore():
    """gitignoreの更新"""
    print(f"\n=== .gitignoreの更新 ===")
    
    gitignore_content = """
# Google認証ファイル
config/google-credentials.json
*.json
!config/analytics_config.json
!config/project_config.json
!config/google_cloud_setup.json

# 環境変数ファイル
.env

# ログファイル
logs/
*.log

# データファイル
data/processed/*.csv
data/processed/*.json
"""
    
    gitignore_file = '.gitignore'
    
    # 既存のgitignoreファイルがあるかチェック
    if os.path.exists(gitignore_file):
        with open(gitignore_file, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # 既にGoogle認証ファイルの設定があるかチェック
        if 'google-credentials.json' not in existing_content:
            with open(gitignore_file, 'a', encoding='utf-8') as f:
                f.write(gitignore_content)
            print("✅ .gitignore更新完了")
        else:
            print("✅ .gitignoreは既に更新済み")
    else:
        with open(gitignore_file, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print("✅ .gitignore作成完了")

def test_authentication():
    """認証のテスト"""
    print(f"\n=== 認証テスト ===")
    
    try:
        # テストスクリプトの実行
        result = subprocess.run([
            sys.executable, 'analytics/test_google_apis.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 認証テスト成功")
            return True
        else:
            print("❌ 認証テスト失敗")
            print("エラー:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 認証テストエラー: {e}")
        return False

def create_summary_report(project_info):
    """サマリーレポートの作成"""
    print(f"\n=== セットアップサマリー ===")
    
    summary = f"""
Google Cloud Console セットアップ完了！

📋 設定情報:
   プロジェクトID: {project_info['project_id']}
   プロジェクト名: {project_info['project_name']}
   サービスアカウント: {project_info['service_account_email']}
   認証ファイル: {project_info['key_file']}

📁 作成されたファイル:
   - config/google-credentials.json
   - .env
   - .gitignore

🔧 次のステップ:
   1. GA4プロパティIDの取得と設定
   2. GSCサイトURLの設定
   3. GA4・GSC・Driveの権限付与
   4. 統合テストの実行

📚 参考ドキュメント:
   - docs/analytics/google_cloud_project_creation_guide.md
   - docs/analytics/google_apis_setup_guide.md
   - docs/analytics/integrated_analytics_system_overview.md
"""
    
    print(summary)
    
    # サマリーファイルに保存
    with open('docs/analytics/setup_summary.md', 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print("✅ サマリーレポート保存完了: docs/analytics/setup_summary.md")

def main():
    """メイン実行関数"""
    print_header()
    
    # gcloud CLIの確認
    if not check_gcloud_installation():
        print("\n❌ Google Cloud CLIをインストールしてから再実行してください。")
        return
    
    # ユーザー入力の取得
    user_input = get_user_input()
    
    # プロジェクト作成
    project_id = create_project_with_gcloud(
        user_input['project_name'], 
        user_input['has_organization']
    )
    
    if not project_id:
        print("❌ プロジェクト作成に失敗しました。")
        return
    
    # API有効化
    enable_apis(project_id)
    
    # サービスアカウント作成
    service_account_email = create_service_account(project_id)
    if not service_account_email:
        print("❌ サービスアカウント作成に失敗しました。")
        return
    
    # キーファイル作成
    key_file = create_service_account_key(service_account_email)
    if not key_file:
        print("❌ キーファイル作成に失敗しました。")
        return
    
    # 環境変数ファイル更新
    update_env_file(project_id, service_account_email, key_file)
    
    # gitignore更新
    update_gitignore()
    
    # 認証テスト
    if test_authentication():
        print("🎉 セットアップ完了！")
    else:
        print("⚠️ セットアップは完了しましたが、認証テストに失敗しました。")
        print("   設定を確認してください。")
    
    # サマリーレポート作成
    project_info = {
        'project_id': project_id,
        'project_name': user_input['project_name'],
        'service_account_email': service_account_email,
        'key_file': key_file
    }
    
    create_summary_report(project_info)

if __name__ == "__main__":
    main()
