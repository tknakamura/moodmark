# 既存プロジェクト「MOOD-MARK-Analytics」の設定

## 現在の状況

✅ **完了済み**:
- 既存プロジェクト「MOOD-MARK-Analytics」（ID: mood-mark-analytics）を選択
- Google Cloud CLI設定を既存プロジェクトに切り替え
- 環境変数ファイル（.env）を更新

## 次の手順（Google Cloud Console で手動実行）

### ステップ1: Google Cloud Console にアクセス

1. **ブラウザでGoogle Cloud Consoleを開く**
   - URL: https://console.cloud.google.com/
   - プロジェクトID: `mood-mark-analytics` を選択

### ステップ2: 請求アカウントの確認・設定

1. **左メニューから「課金」をクリック**
2. **請求アカウントが設定されているか確認**
   - 設定されていない場合は「請求アカウントをリンク」をクリック
   - 請求アカウントを選択または作成

### ステップ3: 必要なAPIの有効化

1. **左メニューから「API とサービス」をクリック**
2. **「ライブラリ」をクリック**
3. **以下のAPIを順番に有効化**:

#### 有効化するAPI一覧
- **Google Analytics Reporting API**
- **Google Analytics Data API**
- **Google Search Console API**
- **Google Drive API**
- **Google Sheets API**

#### 有効化手順（各API共通）
1. 検索ボックスにAPI名を入力
2. APIをクリック
3. **「有効にする」ボタンをクリック**

### ステップ4: サービスアカウントの作成

#### 4.1 サービスアカウント作成画面にアクセス
1. **左メニューから「API とサービス」をクリック**
2. **「認証情報」をクリック**
3. **「認証情報を作成」をクリック**
4. **「サービスアカウント」を選択**

#### 4.2 サービスアカウント詳細の設定
```
サービスアカウント名: mood-mark-analytics-service
サービスアカウントID: mood-mark-analytics@mood-mark-analytics.iam.gserviceaccount.com
説明: MOO:D MARK Analytics API Access
```

5. **「作成して続行」をクリック**
6. **ロール: 「編集者」を選択**
7. **「完了」をクリック**

### ステップ5: サービスアカウントキーの作成

#### 5.1 サービスアカウント詳細画面にアクセス
1. **作成したサービスアカウントをクリック**
2. **「キー」タブをクリック**

#### 5.2 新しいキーの作成
1. **「鍵を追加」をクリック**
2. **「新しい鍵を作成」を選択**
3. **キーのタイプ: 「JSON」を選択**
4. **「作成」をクリック**

#### 5.3 キーファイルの保存
1. **JSONファイルが自動ダウンロードされます**
2. **ファイルを `config/google-credentials.json` に保存**

### ステップ6: 動作確認

#### 6.1 認証ファイルの配置確認
```bash
# ファイルが正しく配置されているか確認
ls -la config/google-credentials.json
```

#### 6.2 基本認証テスト
```bash
# Google APIs認証テスト
python analytics/test_google_apis.py
```

## 重要な情報（更新済み）

### プロジェクト情報
```
プロジェクトID: mood-mark-analytics
プロジェクト名: MOOD-MARK-Analytics
サービスアカウントID: mood-mark-analytics@mood-mark-analytics.iam.gserviceaccount.com
認証ファイル: config/google-credentials.json
```

### 環境変数設定（更新済み）
```bash
GOOGLE_PROJECT_ID=mood-mark-analytics
GOOGLE_CREDENTIALS_FILE=config/google-credentials.json
GOOGLE_SERVICE_ACCOUNT_EMAIL=mood-mark-analytics@mood-mark-analytics.iam.gserviceaccount.com
```

## 完了後の次のステップ

### 1. GA4プロパティIDの取得
- Google Analytics 4でプロパティIDを取得
- 環境変数に設定

### 2. GSCサイトURLの設定
- Google Search ConsoleでサイトURLを確認
- 環境変数に設定

### 3. 権限の付与
- GA4プロパティにサービスアカウントを追加
- GSCプロパティにサービスアカウントを追加
- Google Driveフォルダを共有

### 4. 統合テストの実行
- 全APIの動作確認
- データ取得テスト
- Looker Studio連携テスト

## トラブルシューティング

### よくある問題と解決方法

#### 1. 請求アカウントエラー
```
エラー: APIを有効にできません
解決方法: 請求アカウントを設定してください
```

#### 2. サービスアカウント作成エラー
```
エラー: サービスアカウントを作成できません
解決方法: プロジェクトの編集者権限があるか確認してください
```

#### 3. キーファイルダウンロードエラー
```
エラー: JSONファイルがダウンロードされません
解決方法: ブラウザのポップアップブロックを確認してください
```

## セキュリティ注意事項

### 1. 認証ファイルの管理
- **絶対にGitにコミットしない** (`.gitignore`で設定済み)
- **定期的なローテーション**
- **最小権限の原則**

### 2. アクセス制御
- **不要な権限は付与しない**
- **定期的な権限見直し**
- **アクセスログの監視**

この手順が完了すると、既存の「MOOD-MARK-Analytics」プロジェクトでGoogle APIsを活用した高度な分析システムが利用可能になります。
