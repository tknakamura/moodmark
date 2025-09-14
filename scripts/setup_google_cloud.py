#!/usr/bin/env python3
"""
Google Cloud Console セットアップ支援スクリプト
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def check_requirements():
    """必要なツールの確認"""
    print("=== 必要なツールの確認 ===")
    
    # gcloud CLIの確認
    try:
        result = subprocess.run(['gcloud', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Google Cloud CLI: {result.stdout.split()[0]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Google Cloud CLIがインストールされていません")
        print("インストール方法:")
        print("  macOS: brew install google-cloud-sdk")
        print("  または: https://cloud.google.com/sdk/docs/install")
        return False

def create_project_config():
    """プロジェクト設定ファイルの作成"""
    print("\n=== プロジェクト設定ファイルの作成 ===")
    
    config = {
        "project_name": "MOOD_MARK_Analytics",
        "service_account_name": "mood-mark-analytics-service",
        "apis_to_enable": [
            "analyticsreporting.googleapis.com",
            "analyticsdata.googleapis.com",
            "searchconsole.googleapis.com",
            "drive.googleapis.com",
            "sheets.googleapis.com"
        ],
        "roles": [
            "roles/editor"
        ]
    }
    
    config_file = "config/google_cloud_setup.json"
    os.makedirs("config", exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 設定ファイル作成: {config_file}")
    return config

def generate_setup_commands(project_id):
    """セットアップコマンドの生成"""
    print(f"\n=== Google Cloud セットアップコマンド (プロジェクトID: {project_id}) ===")
    
    commands = [
        "# 1. プロジェクトの設定",
        f"gcloud config set project {project_id}",
        "",
        "# 2. 必要なAPIの有効化",
        "gcloud services enable analyticsreporting.googleapis.com",
        "gcloud services enable analyticsdata.googleapis.com", 
        "gcloud services enable searchconsole.googleapis.com",
        "gcloud services enable drive.googleapis.com",
        "gcloud services enable sheets.googleapis.com",
        "",
        "# 3. サービスアカウントの作成",
        "gcloud iam service-accounts create mood-mark-analytics-service \\",
        f"    --display-name='MOO:D MARK Analytics Service' \\",
        f"    --description='MOO:D MARK Analytics API Access'",
        "",
        "# 4. サービスアカウントに権限を付与",
        f"gcloud projects add-iam-policy-binding {project_id} \\",
        "    --member='serviceAccount:mood-mark-analytics@'${GOOGLE_PROJECT_ID}'.iam.gserviceaccount.com' \\",
        "    --role='roles/editor'",
        "",
        "# 5. サービスアカウントキーの作成",
        "gcloud iam service-accounts keys create config/google-credentials.json \\",
        f"    --iam-account=mood-mark-analytics@'{project_id}'.iam.gserviceaccount.com",
        "",
        "# 6. 環境変数の設定",
        f"echo 'export GOOGLE_PROJECT_ID=\"{project_id}\"' >> .env",
        "echo 'export GOOGLE_CREDENTIALS_FILE=\"config/google-credentials.json\"' >> .env",
        f"echo 'export GOOGLE_SERVICE_ACCOUNT_EMAIL=\"mood-mark-analytics@{project_id}.iam.gserviceaccount.com\"' >> .env"
    ]
    
    # コマンドをファイルに保存
    script_file = "scripts/google_cloud_setup_commands.sh"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write("#!/bin/bash\n")
        f.write("# Google Cloud Console セットアップコマンド\n")
        f.write("# MOO:D MARK IDEA プロジェクト用\n\n")
        f.write("set -e  # エラー時に停止\n\n")
        
        for command in commands:
            if command.startswith("#"):
                f.write(f"\n{command}\n")
            elif command.strip():
                f.write(f"{command}\n")
            else:
                f.write("\n")
    
    # 実行権限を付与
    os.chmod(script_file, 0o755)
    
    print(f"✅ セットアップコマンド生成: {script_file}")
    
    # コンソールに表示
    print("\n" + "="*60)
    for command in commands:
        print(command)
    print("="*60)
    
    return script_file

def create_manual_setup_checklist():
    """手動セットアップチェックリストの作成"""
    print("\n=== 手動セットアップチェックリストの作成 ===")
    
    checklist = """
# Google Cloud Console 手動セットアップチェックリスト

## ステップ1: プロジェクト作成
- [ ] Google Cloud Console にアクセス (https://console.cloud.google.com/)
- [ ] 新しいプロジェクトを作成
  - [ ] プロジェクト名: MOOD_MARK_Analytics
  - [ ] プロジェクトIDを記録: ________________
- [ ] プロジェクトが作成されるまで待機

## ステップ2: API有効化
- [ ] 左メニュー → 「API とサービス」 → 「ライブラリ」
- [ ] 以下のAPIを有効化:
  - [ ] Google Analytics Reporting API
  - [ ] Google Analytics Data API
  - [ ] Google Search Console API
  - [ ] Google Drive API
  - [ ] Google Sheets API

## ステップ3: サービスアカウント作成
- [ ] 左メニュー → 「API とサービス」 → 「認証情報」
- [ ] 「認証情報を作成」 → 「サービスアカウント」
- [ ] サービスアカウント詳細:
  - [ ] サービスアカウント名: mood-mark-analytics-service
  - [ ] サービスアカウントIDを記録: ________________
  - [ ] 説明: MOO:D MARK Analytics API Access
- [ ] 「作成して続行」をクリック
- [ ] ロール: 「編集者」を選択
- [ ] 「完了」をクリック

## ステップ4: サービスアカウントキー作成
- [ ] 作成したサービスアカウントをクリック
- [ ] 「キー」タブをクリック
- [ ] 「鍵を追加」 → 「新しい鍵を作成」
- [ ] キーのタイプ: JSON
- [ ] 「作成」をクリック
- [ ] JSONファイルをダウンロード
- [ ] ファイルを config/google-credentials.json に保存

## ステップ5: 環境変数設定
- [ ] .envファイルに以下を追加:
  - [ ] GOOGLE_PROJECT_ID=プロジェクトID
  - [ ] GOOGLE_CREDENTIALS_FILE=config/google-credentials.json
  - [ ] GOOGLE_SERVICE_ACCOUNT_EMAIL=サービスアカウントID

## ステップ6: 動作確認
- [ ] python analytics/test_google_apis.py を実行
- [ ] 認証成功メッセージを確認

## 次のステップ
- [ ] GA4プロパティIDの取得
- [ ] GSCサイトURLの設定
- [ ] 権限の付与（GA4、GSC、Drive）
"""
    
    checklist_file = "docs/analytics/google_cloud_setup_checklist.md"
    with open(checklist_file, 'w', encoding='utf-8') as f:
        f.write(checklist)
    
    print(f"✅ チェックリスト作成: {checklist_file}")
    return checklist_file

def update_env_template():
    """環境変数テンプレートの更新"""
    print("\n=== 環境変数テンプレートの更新 ===")
    
    env_template = """# Google Cloud Console設定
GOOGLE_PROJECT_ID=your-google-cloud-project-id
GOOGLE_CREDENTIALS_FILE=config/google-credentials.json
GOOGLE_SERVICE_ACCOUNT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com

# Google Analytics 4設定
GA4_PROPERTY_ID=your-ga4-property-id

# Google Search Console設定
GSC_SITE_URL=https://isetan.mistore.jp/moodmarkgift/

# Looker Studio設定
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
    
    env_template_file = ".env.template"
    with open(env_template_file, 'w', encoding='utf-8') as f:
        f.write(env_template)
    
    print(f"✅ 環境変数テンプレート更新: {env_template_file}")

def main():
    """メイン実行関数"""
    print("Google Cloud Console セットアップ支援スクリプト")
    print("="*50)
    
    # 必要なツールの確認
    if not check_requirements():
        print("\n⚠️  Google Cloud CLIをインストールしてから再実行してください。")
        return
    
    # プロジェクト設定の作成
    config = create_project_config()
    
    # 手動セットアップチェックリストの作成
    checklist_file = create_manual_setup_checklist()
    
    # 環境変数テンプレートの更新
    update_env_template()
    
    # プロジェクトIDの入力
    print("\n" + "="*50)
    project_id = input("Google Cloud プロジェクトIDを入力してください: ").strip()
    
    if not project_id:
        print("❌ プロジェクトIDが入力されていません。")
        return
    
    # セットアップコマンドの生成
    script_file = generate_setup_commands(project_id)
    
    print(f"\n✅ セットアップ支援ファイルが作成されました:")
    print(f"  - 手動チェックリスト: {checklist_file}")
    print(f"  - 自動セットアップスクリプト: {script_file}")
    print(f"  - 環境変数テンプレート: .env.template")
    
    print(f"\n📋 次のステップ:")
    print(f"1. 手動チェックリストに従ってGoogle Cloud Consoleで設定")
    print(f"2. または自動セットアップスクリプトを実行:")
    print(f"   bash {script_file}")
    print(f"3. 環境変数を設定: cp .env.template .env")
    print(f"4. 動作確認: python analytics/test_google_apis.py")

if __name__ == "__main__":
    main()
