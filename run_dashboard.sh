#!/bin/bash

# CSV to HTML Converter Dashboard 起動スクリプト

echo "🍰 CSV to HTML Converter Dashboard を起動しています..."
echo "================================================"

# 依存関係のインストール確認
echo "📦 依存関係を確認中..."
pip install -r requirements_dashboard.txt

# ダッシュボード起動
echo "🚀 ダッシュボードを起動中..."
echo "ブラウザで http://localhost:8501 にアクセスしてください"
echo ""

streamlit run csv_to_html_dashboard.py


