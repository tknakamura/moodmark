# クイックスタートガイド

## Streamlitアプリの起動方法

### 方法1: 起動スクリプトを使用（推奨）

```bash
./start_analytics_chat.sh
```

### 方法2: 手動で起動

```bash
# 環境変数を設定
export OPENAI_API_KEY="your_openai_api_key_here"
export GOOGLE_CREDENTIALS_FILE="config/google-credentials-474807.json"
export GA4_PROPERTY_ID="316302380"
export GSC_SITE_URL="https://isetan.mistore.jp/moodmark/"

# Streamlitアプリを起動
streamlit run csv_to_html_dashboard.py
```

### 方法3: .envファイルを使用

1. `.env`ファイルを作成（既に存在する場合は編集）:
```bash
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_CREDENTIALS_FILE=config/google-credentials-474807.json
GA4_PROPERTY_ID=316302380
GSC_SITE_URL=https://isetan.mistore.jp/moodmark/
```

2. Streamlitアプリを起動:
```bash
streamlit run csv_to_html_dashboard.py
```

## アクセス方法

アプリが起動したら、ブラウザで以下のURLにアクセス:

- **メインページ**: http://localhost:8501
- **AI分析チャット**: http://localhost:8501/analytics-chat

## トラブルシューティング

### ポート8501が既に使用されている場合

別のポートで起動:
```bash
streamlit run csv_to_html_dashboard.py --server.port 8502
```

### 環境変数が読み込まれない場合

`.env`ファイルがプロジェクトルートにあることを確認してください。

### モジュールが見つからないエラー

依存関係をインストール:
```bash
pip install -r requirements.txt
```

## 注意事項

- Streamlitアプリを起動するには、ターミナルでコマンドを実行する必要があります
- アプリを停止するには、ターミナルで `Ctrl+C` を押してください
- ブラウザは自動的に開きますが、開かない場合は手動で上記のURLにアクセスしてください

