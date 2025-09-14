# Google APIs連携セットアップガイド

## 概要

MOO:D MARK IDEAプロジェクトでGoogle Analytics 4、Google Search Console、Google Looker StudioのAPI連携を設定するための詳細ガイドです。

## 必要なAPI

### 1. Google Analytics 4 API
- **目的**: ウェブサイトのトラフィック、ユーザー行動データの取得
- **スコープ**: `https://www.googleapis.com/auth/analytics.readonly`

### 2. Google Search Console API
- **目的**: 検索パフォーマンス、SEOデータの取得
- **スコープ**: `https://www.googleapis.com/auth/webmasters.readonly`

### 3. Google Drive API
- **目的**: Looker Studio用データソースファイルの管理
- **スコープ**: `https://www.googleapis.com/auth/drive`

### 4. Google Sheets API
- **目的**: データソース用スプレッドシートの作成・更新
- **スコープ**: `https://www.googleapis.com/auth/spreadsheets`

## セットアップ手順

### ステップ1: Google Cloud Console プロジェクトの作成

1. **Google Cloud Console にアクセス**
   - https://console.cloud.google.com/

2. **新しいプロジェクトを作成**
   - プロジェクト名: `MOOD_MARK_Analytics`
   - プロジェクトID: `mood-mark-analytics-xxxxx`

3. **請求アカウントの設定**
   - 必要に応じて請求アカウントを設定（API使用量に応じて）

### ステップ2: 必要なAPIの有効化

1. **API ライブラリにアクセス**
   - 左メニュー → 「API とサービス」 → 「ライブラリ」

2. **以下のAPIを有効化**
   - Google Analytics Reporting API
   - Google Analytics Data API
   - Google Search Console API
   - Google Drive API
   - Google Sheets API

### ステップ3: サービスアカウントの作成

1. **サービスアカウント作成**
   - 左メニュー → 「API とサービス」 → 「認証情報」
   - 「認証情報を作成」 → 「サービスアカウント」

2. **サービスアカウント詳細**
   - サービスアカウント名: `mood-mark-analytics-service`
   - サービスアカウントID: `mood-mark-analytics@mood-mark-analytics-xxxxx.iam.gserviceaccount.com`
   - 説明: `MOO:D MARK Analytics API Access`

3. **キーの作成**
   - 作成したサービスアカウントをクリック
   - 「キー」タブ → 「鍵を追加」 → 「新しい鍵を作成」
   - キーのタイプ: JSON
   - ダウンロードしたJSONファイルを安全な場所に保存

### ステップ4: 権限の設定

#### Google Analytics 4 の権限設定

1. **GA4プロパティにアクセス**
   - https://analytics.google.com/

2. **管理設定**
   - 左下の「管理」をクリック
   - プロパティ列の「アクセス管理」

3. **ユーザーを追加**
   - 「+」ボタン → 「ユーザーを追加」
   - メールアドレス: `mood-mark-analytics@mood-mark-analytics-xxxxx.iam.gserviceaccount.com`
   - 権限: 「表示者」または「アナリスト」

#### Google Search Console の権限設定

1. **GSCプロパティにアクセス**
   - https://search.google.com/search-console/

2. **設定**
   - 左メニュー → 「設定」
   - 「ユーザーと権限」

3. **ユーザーを追加**
   - 「ユーザーを追加」
   - メールアドレス: `mood-mark-analytics@mood-mark-analytics-xxxxx.iam.gserviceaccount.com`
   - 権限: 「フル」

#### Google Drive の権限設定

1. **共有フォルダの作成**
   - Looker Studio用のフォルダを作成
   - フォルダ名: `MOOD_MARK_Analytics_Data`

2. **フォルダを共有**
   - フォルダを右クリック → 「共有」
   - メールアドレス: `mood-mark-analytics@mood-mark-analytics-xxxxx.iam.gserviceaccount.com`
   - 権限: 「編集者」

### ステップ5: 環境変数の設定

1. **認証ファイルの配置**
   ```bash
   # プロジェクトルートに認証ファイルを配置
   cp /path/to/your/service-account-key.json config/google-credentials.json
   ```

2. **環境変数の設定**
   ```bash
   # .envファイルに追加
   echo "GOOGLE_CREDENTIALS_FILE=config/google-credentials.json" >> .env
   echo "GA4_PROPERTY_ID=your-ga4-property-id" >> .env
   echo "GSC_SITE_URL=https://isetan.mistore.jp/moodmarkgift/" >> .env
   echo "LOOKER_STUDIO_FOLDER_ID=your-looker-studio-folder-id" >> .env
   echo "DATA_SOURCE_FOLDER_ID=your-data-source-folder-id" >> .env
   ```

### ステップ6: GA4プロパティIDの取得

1. **GA4プロパティにアクセス**
   - https://analytics.google.com/

2. **管理設定**
   - 左下の「管理」をクリック
   - プロパティ列の「データストリーム」

3. **プロパティIDを確認**
   - ウェブストリームをクリック
   - 「測定ID」の値（例: `G-XXXXXXXXXX`）

### ステップ7: フォルダIDの取得

1. **Google Drive でフォルダを開く**
   - 作成したフォルダのURLからIDを取得
   - 例: `https://drive.google.com/drive/folders/1ABC123DEF456GHI789`
   - フォルダID: `1ABC123DEF456GHI789`

## 設定ファイルの更新

### analytics_config.json の更新

```json
{
  "sites": {
    "moodmark_idea": {
      "url": "https://isetan.mistore.jp/moodmarkgift/",
      "ga4_property_id": "G-XXXXXXXXXX",
      "gsc_site_url": "https://isetan.mistore.jp/moodmarkgift/"
    },
    "moodmark": {
      "url": "https://isetan.mistore.jp/moodmark/",
      "ga4_property_id": "G-YYYYYYYYYY",
      "gsc_site_url": "https://isetan.mistore.jp/moodmark/"
    }
  },
  "looker_studio": {
    "dashboard_folder_id": "1ABC123DEF456GHI789",
    "data_source_folder_id": "1XYZ789ABC123DEF456"
  }
}
```

## 動作確認

### 1. 基本的な動作確認

```bash
# Google APIs統合システムのテスト
python analytics/google_apis_integration.py
```

### 2. Looker Studio連携のテスト

```bash
# Looker Studio コネクタのテスト
python analytics/looker_studio_connector.py
```

### 3. 統合分析システムのテスト

```bash
# 統合分析システムの一回実行
python analytics/integrated_analytics_system.py once
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. 認証エラー
```
エラー: 認証ファイルが見つかりません
解決方法: GOOGLE_CREDENTIALS_FILE環境変数が正しく設定されているか確認
```

#### 2. 権限エラー
```
エラー: Insufficient permissions
解決方法: サービスアカウントに適切な権限が付与されているか確認
```

#### 3. プロパティIDエラー
```
エラー: Invalid property ID
解決方法: GA4プロパティIDが正しいか確認（G-で始まる形式）
```

#### 4. フォルダアクセスエラー
```
エラー: Folder not found
解決方法: フォルダIDが正しく、サービスアカウントに共有されているか確認
```

## セキュリティ考慮事項

### 1. 認証ファイルの保護
- 認証ファイルをGitリポジトリにコミットしない
- `.gitignore`に追加: `config/google-credentials.json`
- ファイル権限を適切に設定: `chmod 600 config/google-credentials.json`

### 2. 環境変数の保護
- `.env`ファイルをGitリポジトリにコミットしない
- 本番環境では適切な秘密管理システムを使用

### 3. 最小権限の原則
- サービスアカウントには必要最小限の権限のみ付与
- 定期的な権限見直しを実施

## 次のステップ

1. **API連携の動作確認**
2. **Looker Studioダッシュボードの作成**
3. **自動レポートシステムの設定**
4. **アラート機能の有効化**
5. **定期的な監視とメンテナンス**

このセットアップが完了すると、MOO:D MARK IDEAプロジェクトでGoogle APIsを活用した高度な分析システムが利用可能になります。
