#!/usr/bin/env python3
"""
GA4/GSC AI分析チャットを直接実行するスクリプト
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# 環境変数の設定
os.environ.setdefault('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY', ''))
os.environ.setdefault('GOOGLE_CREDENTIALS_FILE', os.getenv('GOOGLE_CREDENTIALS_FILE', 'config/google-credentials-474807.json'))
os.environ.setdefault('GA4_PROPERTY_ID', os.getenv('GA4_PROPERTY_ID', '316302380'))
os.environ.setdefault('GSC_SITE_URL', os.getenv('GSC_SITE_URL', 'https://isetan.mistore.jp/moodmark/'))

# Streamlitアプリを起動
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    sys.argv = [
        "streamlit",
        "run",
        "pages/analytics_chat.py",
        "--server.port=8503",
        "--server.address=0.0.0.0"
    ]
    
    sys.exit(stcli.main())

