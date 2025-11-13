# 🚀 Render.com デプロイガイド

## 📋 デプロイ手順

### 1. Render.comアカウント作成
1. [Render.com](https://render.com) にアクセス
2. GitHubアカウントでサインアップ

### 2. 新しいWebサービス作成
1. Render.comダッシュボードで「New +」→「Web Service」を選択
2. GitHubリポジトリを接続: `tknakamura/moodmark`
3. 以下の設定を入力：

#### 基本設定
- **Name**: `moodmark-csv-to-html-converter`
- **Environment**: `Python 3`
- **Region**: `Oregon (US West)`
- **Branch**: `main`

#### ビルド設定
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `streamlit run csv_to_html_dashboard.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false`

#### 環境変数
- `PYTHON_VERSION`: `3.9.18`
- `STREAMLIT_SERVER_PORT`: `$PORT`
- `STREAMLIT_SERVER_ADDRESS`: `0.0.0.0`
- `STREAMLIT_SERVER_HEADLESS`: `true`
- `STREAMLIT_SERVER_ENABLE_CORS`: `false`
- `STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION`: `false`

### 3. デプロイ実行
1. 「Create Web Service」をクリック
2. ビルドプロセスを待機（約2-3分）
3. デプロイ完了後、提供されるURLでアクセス

## 🔧 トラブルシューティング

### よくある問題
1. **ビルドエラー**: requirements.txtの依存関係を確認
2. **ポートエラー**: 環境変数`$PORT`が正しく設定されているか確認
3. **CORSエラー**: StreamlitのCORS設定を確認

### ログ確認
- Render.comダッシュボードの「Logs」タブでエラーログを確認

## 📊 パフォーマンス
- **無料プラン**: 月間750時間まで
- **スリープ**: 15分間の非アクティブ後に自動スリープ
- **起動時間**: 初回アクセス時に約30秒

## 🔗 アクセス
デプロイ完了後、以下のようなURLでアクセス可能：
`https://moodmark-csv-to-html-converter.onrender.com`

## 📝 注意事項
- 無料プランでは、15分間の非アクティブ後にアプリがスリープします
- 初回アクセス時は起動に時間がかかります
- ファイルアップロード機能は正常に動作します


