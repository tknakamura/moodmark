# アクセスガイド

## GA4/GSC AI分析チャットへのアクセス方法

### 方法1: メインページからアクセス（推奨）

1. メインページにアクセス: http://localhost:8502
2. 左サイドバーの「📊 GA4/GSC AI分析チャット」ボタンをクリック

### 方法2: 直接URLでアクセス

Streamlitのマルチページ機能を使用している場合、以下のURLで直接アクセスできます:

- http://localhost:8502/analytics-chat
- http://localhost:8502/Analytics_Chat

### 方法3: ページファイルを直接実行

別のポート（8503）で直接実行:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export GOOGLE_CREDENTIALS_FILE="config/google-credentials-474807.json"
export GA4_PROPERTY_ID="316302380"
export GSC_SITE_URL="https://isetan.mistore.jp/moodmark/"

streamlit run pages/analytics_chat.py --server.port 8503
```

その後、http://localhost:8503 にアクセス

## トラブルシューティング

### "Page not found" エラーが表示される場合

1. **メインページのサイドバーからアクセス**
   - メインページ（http://localhost:8502）にアクセス
   - 左サイドバーの「📊 GA4/GSC AI分析チャット」ボタンをクリック

2. **ページファイルを直接実行**
   - 上記の「方法3」を使用

3. **Streamlitのマルチページ機能を確認**
   - `pages/`ディレクトリが正しく認識されているか確認
   - Streamlitのバージョンが1.18.0以上であることを確認

### サイドバーにページが表示されない場合

Streamlitのマルチページ機能では、`pages/`ディレクトリ内のファイルが自動的にサイドバーに表示されます。表示されない場合は：

1. ブラウザをリロード（F5またはCmd+R）
2. Streamlitアプリを再起動
3. ページファイルが正しい場所にあるか確認（`pages/analytics_chat.py`）

## 現在の設定

- **メインページ**: http://localhost:8502
- **AI分析チャット**: http://localhost:8502/analytics-chat（またはサイドバーからアクセス）

