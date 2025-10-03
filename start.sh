#!/bin/bash

# Render.com用の起動スクリプト
echo "🚀 Starting MOO:D MARK CSV to HTML Converter..."

# ポート番号を環境変数から取得（Render.comが自動設定）
PORT=${PORT:-8501}

# Streamlitアプリケーションを起動
streamlit run csv_to_html_dashboard.py \
  --server.port=$PORT \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
