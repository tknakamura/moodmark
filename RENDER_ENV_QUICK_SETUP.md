# Render.com環境変数 クイックセットアップガイド

## 概要

このガイドでは、Render.comでGoogle認証情報を環境変数として設定する方法を説明します。

## クイックセットアップ（推奨）

### ステップ1: 認証情報JSONを準備

以下のコマンドを実行して、Render.com用の認証情報JSONを準備します：

```bash
python scripts/prepare_credentials_for_render.py
```

このコマンドを実行すると：
- 認証情報JSONがコンソールに表示されます
- `RENDER_CREDENTIALS_JSON.txt`ファイルに保存されます

### ステップ2: Render.comで環境変数を設定

1. **Render.comダッシュボードにアクセス**
   - URL: https://dashboard.render.com/
   - サービス「moodmark-csv-to-html-converter」を選択

2. **環境変数を追加**
   - 左サイドバーから「Environment」をクリック
   - 「Add Environment Variable」ボタンをクリック

3. **以下の環境変数を追加**

#### 環境変数1: GOOGLE_CREDENTIALS_JSON

- **Key**: `GOOGLE_CREDENTIALS_JSON`
- **Value**: `RENDER_CREDENTIALS_JSON.txt`ファイルの内容をコピーして貼り付け
  - ファイルを開く
  - 内容全体を選択（Cmd+A / Ctrl+A）
  - コピー（Cmd+C / Ctrl+C）
  - Render.comの環境変数のValueに貼り付け（Cmd+V / Ctrl+V）

#### 環境変数2: GA4_PROPERTY_ID

- **Key**: `GA4_PROPERTY_ID`
- **Value**: `316302380`

#### 環境変数3: GSC_SITE_URL

- **Key**: `GSC_SITE_URL`
- **Value**: `https://isetan.mistore.jp/moodmark/`

#### 環境変数4: OPENAI_API_KEY

- **Key**: `OPENAI_API_KEY`
- **Value**: あなたのOpenAI APIキー（例: `sk-...`）

#### 環境変数5: PAGESPEED_INSIGHTS_API_KEY（オプション）

- **Key**: `PAGESPEED_INSIGHTS_API_KEY`
- **Value**: あなたのPage Speed Insights APIキー
- **注意**: この環境変数はオプションです。設定しない場合、Page Speed Insightsの分析はスキップされます

### ステップ3: 再デプロイ

環境変数を設定した後、Render.comで再デプロイを実行してください。

## 確認方法

環境変数を設定した後、以下のURLにアクセスして接続状態を確認してください：

- https://moodmark-csv-to-html-converter.onrender.com/analytics_chat

サイドバーの「📊 Google APIs接続状態」セクションで、以下が表示されることを確認してください：

- ✅ GA4: 接続済み
- ✅ GSC: 接続済み

## トラブルシューティング

### エラー: 「認証情報が読み込まれていません」

1. `GOOGLE_CREDENTIALS_JSON`環境変数が正しく設定されているか確認
2. JSONの内容が完全にコピーされているか確認（改行を含む）
3. 環境変数を設定した後、再デプロイを実行しているか確認

### エラー: 「GOOGLE_CREDENTIALS_FILEにJSONが設定されています」

`GOOGLE_CREDENTIALS_FILE`環境変数を削除し、`GOOGLE_CREDENTIALS_JSON`環境変数を使用してください。

## 詳細な手順

より詳細な手順については、`RENDER_ENV_SETUP.md`を参照してください。

