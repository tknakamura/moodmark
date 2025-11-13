#!/usr/bin/env python3
"""
ローカル環境でのAIチャット機能のテストスクリプト
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from analytics.ai_analytics_chat import AIAnalyticsChat

def test_ai_chat():
    """AIチャット機能のテスト"""
    print("=" * 60)
    print("GA4/GSC AI分析チャット テスト")
    print("=" * 60)
    
    # 環境変数の確認
    print("\n=== 環境変数確認 ===")
    openai_api_key = os.getenv('OPENAI_API_KEY')
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'config/google-credentials-474807.json')
    ga4_property_id = os.getenv('GA4_PROPERTY_ID')
    gsc_site_url = os.getenv('GSC_SITE_URL')
    
    print(f"OPENAI_API_KEY: {'設定済み' if openai_api_key else '未設定'}")
    print(f"GOOGLE_CREDENTIALS_FILE: {credentials_file}")
    print(f"GA4_PROPERTY_ID: {ga4_property_id}")
    print(f"GSC_SITE_URL: {gsc_site_url}")
    
    if not openai_api_key:
        print("\n❌ OpenAI APIキーが設定されていません")
        print("環境変数OPENAI_API_KEYを設定するか、.envファイルを作成してください。")
        return False
    
    # AIチャットの初期化
    print("\n=== AIチャット初期化 ===")
    try:
        credentials_path = os.path.join(project_root, credentials_file)
        ai_chat = AIAnalyticsChat(
            credentials_file=credentials_path,
            openai_api_key=openai_api_key
        )
        print("✅ AIチャット初期化成功")
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        return False
    
    # テスト質問
    test_questions = [
        "今週のトラフィックは？",
        "SEOの改善点を教えて",
    ]
    
    print("\n=== テスト質問 ===")
    for i, question in enumerate(test_questions, 1):
        print(f"\n質問 {i}: {question}")
        print("-" * 60)
        
        try:
            answer = ai_chat.ask(question, model="gpt-4o-mini")
            print(f"回答:\n{answer}")
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_ai_chat()

