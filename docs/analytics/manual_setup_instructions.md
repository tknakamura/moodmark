# Google Cloud Console 手動セットアップ手順

## 現在の状況

プロジェクト `mood-mark-analytics-1757811164` が作成されましたが、API有効化で権限エラーが発生しています。

## 次の手順（手動で実行）

### ステップ1: Google Cloud Console にアクセス

1. **ブラウザでGoogle Cloud Consoleを開く**
   - URL: https://console.cloud.google.com/
   - プロジェクトID: `mood-mark-analytics-1757811164` を選択

### ステップ2: 請求アカウントの設定

1. **左メニューから「課金」をクリック**
2. **「請求アカウントをリンク」をクリック**
3. **請求アカウントを選択または作成**
   - 個人利用の場合は「新しい請求アカウントを作成」
   - 組織利用の場合は既存の請求アカウントを選択

### ステップ3: 必要なAPIの有効化

1. **左メニューから「API とサービス」をクリック**
2. **「ライブラリ」をクリック**
3. **以下のAPIを順番に有効化**:

#### A. Google Analytics Reporting API
- 検索ボックスに「Google Analytics Reporting API」と入力
- 「Google Analytics Reporting API」をクリック
- **「有効にする」ボタンをクリック**

#### B. Google Analytics Data API
- 検索ボックスに「Google Analytics Data API」と入力
- 「Google Analytics Data API」をクリック
- **「有効にする」ボタンをクリック**

#### C. Google Search Console API
- 検索ボックスに「Google Search Console API」と入力
- 「Google Search Console API」をクリック
- **「有効にする」ボタンをクリック**

#### D. Google Drive API
- 検索ボックスに「Google Drive API」と入力
- 「Google Drive API」をクリック
- **「有効にする」ボタンをクリック**

#### E. Google Sheets API
- 検索ボックスに「Google Sheets API」と入力
- 「Google Sheets API」をクリック
- **「有効にする」ボタンをクリック**

### ステップ4: サービスアカウントの作成

1. **左メニューから「API とサービス」をクリック**
2. **「認証情報」をクリック**
3. **「認証情報を作成」をクリック**
4. **「サービスアカウント」を選択**

#### サービスアカウント詳細
```
サービスアカウント名: mood-mark-analytics-service
サービスアカウントID: mood-mark-analytics@mood-mark-analytics-1757811164.iam.gserviceaccount.com
説明: MOO:D MARK Analytics API Access
```

5. **「作成して続行」をクリック**
6. **ロール: 「編集者」を選択**
7. **「完了」をクリック**

### ステップ5: サービスアカウントキーの作成

1. **作成したサービスアカウントをクリック**
2. **「キー」タブをクリック**
3. **「鍵を追加」をクリック**
4. **「新しい鍵を作成」を選択**
5. **キーのタイプ: 「JSON」を選択**
6. **「作成」をクリック**

### ステップ6: キーファイルの保存

1. **JSONファイルが自動ダウンロードされます**
2. **ファイルを `config/google-credentials.json` に保存**

### ステップ7: 環境変数の設定

`.env`ファイルに以下を追加：

```bash
# Google Cloud Console設定
GOOGLE_PROJECT_ID=mood-mark-analytics-1757811164
GOOGLE_CREDENTIALS_FILE=config/google-credentials.json
GOOGLE_SERVICE_ACCOUNT_EMAIL=mood-mark-analytics@mood-mark-analytics-1757811164.iam.gserviceaccount.com

# Google Analytics 4設定（後で設定）
GA4_PROPERTY_ID=your-ga4-property-id

# Google Search Console設定（後で設定）
GSC_SITE_URL=https://isetan.mistore.jp/moodmarkgift/

# Looker Studio設定（後で設定）
LOOKER_STUDIO_FOLDER_ID=your-looker-studio-folder-id
DATA_SOURCE_FOLDER_ID=your-data-source-folder-id
```

### ステップ8: 動作確認

```bash
# 認証テスト
python analytics/test_google_apis.py
```

## 完了後の次のステップ

1. **GA4プロパティIDの取得**
2. **GSCサイトURLの設定**
3. **GA4・GSC・Driveの権限付与**
4. **統合テストの実行**

## トラブルシューティング

### よくある問題

1. **請求アカウントエラー**
   - 請求アカウントが設定されていない
   - 解決方法: ステップ2を実行

2. **API有効化エラー**
   - 権限が不足している
   - 解決方法: 請求アカウント設定後に再試行

3. **サービスアカウント作成エラー**
   - 組織の権限が不足している
   - 解決方法: 個人利用でプロジェクトを作成

## サポート

問題が発生した場合は、作成されたドキュメントを参照してください：
- `docs/analytics/google_cloud_project_creation_guide.md`
- `docs/analytics/google_apis_setup_guide.md`
