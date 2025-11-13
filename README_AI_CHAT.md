# GA4/GSC AI分析チャット機能

## 概要

Google Analytics 4 (GA4)とGoogle Search Console (GSC)のデータをAIが分析し、自然言語で質問に答えるチャット機能です。

## 機能

- チャット形式での質問応答
- GA4データの自動取得と分析（セッション、ユーザー、ページビューなど）
- GSCデータの自動取得と分析（クリック、インプレッション、CTR、ポジションなど）
- 自然言語での質問（例：「今週のトラフィックは？」「SEOの改善点は？」）
- 複数のAIモデルから選択可能（GPT-4o-mini, GPT-4o, GPT-4-turbo, GPT-3.5-turbo）

## アクセス方法

### ローカル環境

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してOPENAI_API_KEYを設定

# Streamlitアプリの起動
streamlit run csv_to_html_dashboard.py
```

ブラウザで `http://localhost:8501/analytics-chat` にアクセス

### Render.com（本番環境）

1. Render.comダッシュボードにログイン
2. 既存のWebサービス（`moodmark-csv-to-html-converter`）を選択
3. 「Environment」タブで以下の環境変数を設定：
   - `OPENAI_API_KEY`: OpenAI APIキー
   - `GOOGLE_CREDENTIALS_FILE`: `config/google-credentials-474807.json`
   - `GA4_PROPERTY_ID`: `316302380`
   - `GSC_SITE_URL`: `https://isetan.mistore.jp/moodmark/`
4. デプロイを実行

アクセスURL: `https://moodmark-csv-to-html-converter.onrender.com/analytics-chat`

## 使用例

### 質問例

- 「今週のトラフィックは？」
- 「SEOの改善点を教えて」
- 「人気のページは？」
- 「検索流入の状況は？」
- 「バウンス率はどう？」
- 「CTRを改善するには？」

### データ取得期間

質問に含まれるキーワードから自動的に期間を判定：
- 「今日」「本日」→ 1日
- 「今週」「この週」→ 7日
- 「今月」→ 30日
- 「過去X日」→ 指定日数
- デフォルト → 30日

## 技術仕様

### 使用技術

- **フレームワーク**: Streamlit
- **AI**: OpenAI API (GPT-4o-mini推奨)
- **データソース**: Google Analytics 4, Google Search Console
- **言語**: Python 3.9+

### ファイル構成

```
moodmark/
├── pages/
│   └── analytics_chat.py          # Streamlitチャットページ
├── analytics/
│   ├── google_apis_integration.py  # GA4/GSC API統合（既存）
│   └── ai_analytics_chat.py        # AI統合ロジック
├── csv_to_html_dashboard.py        # メインページ
└── requirements.txt                # 依存関係
```

## ローカルテスト

```bash
# テストスクリプトの実行
python test_ai_chat_local.py
```

## トラブルシューティング

### OpenAI APIキーが設定されていない

エラー: `OpenAI APIキーが設定されていません`

解決方法:
1. `.env`ファイルを作成
2. `OPENAI_API_KEY`を設定
3. または環境変数として設定: `export OPENAI_API_KEY=your_key`

### Google APIs認証エラー

エラー: `認証ファイルが見つかりません`

解決方法:
1. `config/google-credentials-474807.json`が存在するか確認
2. 環境変数`GOOGLE_CREDENTIALS_FILE`を確認

### データが取得できない

エラー: `データが取得できませんでした`

解決方法:
1. GA4プロパティIDとGSCサイトURLが正しいか確認
2. サービスアカウントに適切な権限が付与されているか確認
3. Google Cloud ConsoleでAPIが有効になっているか確認

## 将来の拡張機能

- 商品ページのSEO改善提案（タイトル・ディスクリプション・見出し・本文）
- 自動レポート生成
- トレンド分析と予測
- カスタムダッシュボード

## ライセンス

このプロジェクトはMOO:D MARK IDEAプロジェクトの一部です。

