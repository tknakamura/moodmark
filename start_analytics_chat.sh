#!/bin/bash
# GA4/GSC AI分析チャット起動スクリプト

# 環境変数の設定
export OPENAI_API_KEY="your_openai_api_key_here"
export GOOGLE_CREDENTIALS_FILE="config/google-credentials-474807.json"
export GA4_PROPERTY_ID="316302380"
export GSC_SITE_URL="https://isetan.mistore.jp/moodmark/"

# Streamlitアプリを起動
echo "Streamlitアプリを起動しています..."
echo "ブラウザで http://localhost:8501 にアクセスしてください"
echo "AI分析チャットは http://localhost:8501/analytics-chat で利用できます"
echo ""
streamlit run csv_to_html_dashboard.py
