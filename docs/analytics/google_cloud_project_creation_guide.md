# Google Cloud プロジェクト新規作成ガイド

## 概要

MOO:D MARK IDEAプロジェクト用のGoogle Cloudプロジェクトを新規作成する詳細手順をご案内します。

## ステップ1: Google Cloud Console にアクセス

### 1.1 ブラウザでGoogle Cloud Consoleを開く

1. **ブラウザを開いて以下のURLにアクセス**
   - URL: https://console.cloud.google.com/
   - Googleアカウントでログイン（まだの場合はアカウント作成）

2. **初回アクセスの場合**
   - 利用規約に同意
   - 請求アカウントの設定（必要に応じて）

### 1.2 プロジェクト選択画面の確認

- 画面左上に「プロジェクトを選択」または現在のプロジェクト名が表示されます
- 初回の場合は「プロジェクトなし」と表示される可能性があります

## ステップ2: 新しいプロジェクトを作成

### 2.1 プロジェクト作成画面にアクセス

1. **画面左上の「プロジェクトを選択」をクリック**
2. **「新しいプロジェクト」をクリック**

### 2.2 プロジェクト詳細の入力

以下の情報を入力してください：

```
プロジェクト名: MOOD_MARK_Analytics
組織: [お使いの組織を選択、または「なし」]
場所: [組織のフォルダまたは「なし」を選択]
```

**重要事項**:
- **プロジェクト名**: 分かりやすい名前を入力
- **プロジェクトID**: 自動生成されますが、後で使用するため記録してください
- **組織**: 個人利用の場合は「なし」を選択

### 2.3 プロジェクトIDの確認

プロジェクトIDは以下のような形式で自動生成されます：
```
mood-mark-analytics-123456
```

**必ずこのプロジェクトIDを記録してください！**

### 2.4 プロジェクトの作成

1. **「作成」ボタンをクリック**
2. **プロジェクトが作成されるまで待機**（通常1-2分）
3. **作成完了後、自動的にそのプロジェクトが選択されます**

## ステップ3: プロジェクト情報の確認

### 3.1 プロジェクト詳細の確認

1. **画面左上のプロジェクト名をクリック**
2. **「プロジェクト設定」をクリック**
3. **以下の情報を確認・記録**:
   - プロジェクト名
   - プロジェクトID
   - プロジェクト番号

### 3.2 請求アカウントの設定（必要に応じて）

1. **左メニューから「課金」をクリック**
2. **「請求アカウントをリンク」をクリック**
3. **請求アカウントを選択または作成**

**注意**: 一部のAPIは請求アカウントが必要です。

## ステップ4: 必要なAPIの有効化

### 4.1 API ライブラリにアクセス

1. **左メニューから「API とサービス」をクリック**
2. **「ライブラリ」をクリック**

### 4.2 必要なAPIの有効化

以下のAPIを順番に有効化します：

#### A. Google Analytics Reporting API
1. 検索ボックスに「Google Analytics Reporting API」と入力
2. 「Google Analytics Reporting API」をクリック
3. **「有効にする」ボタンをクリック**

#### B. Google Analytics Data API
1. 検索ボックスに「Google Analytics Data API」と入力
2. 「Google Analytics Data API」をクリック
3. **「有効にする」ボタンをクリック**

#### C. Google Search Console API
1. 検索ボックスに「Google Search Console API」と入力
2. 「Google Search Console API」をクリック
3. **「有効にする」ボタンをクリック**

#### D. Google Drive API
1. 検索ボックスに「Google Drive API」と入力
2. 「Google Drive API」をクリック
3. **「有効にする」ボタンをクリック**

#### E. Google Sheets API
1. 検索ボックスに「Google Sheets API」と入力
2. 「Google Sheets API」をクリック
3. **「有効にする」ボタンをクリック**

### 4.3 API有効化の確認

1. **左メニューから「API とサービス」→「有効なAPI」をクリック**
2. **以下のAPIが表示されることを確認**:
   - Google Analytics Reporting API
   - Google Analytics Data API
   - Google Search Console API
   - Google Drive API
   - Google Sheets API

## ステップ5: サービスアカウントの作成

### 5.1 サービスアカウント作成画面にアクセス

1. **左メニューから「API とサービス」をクリック**
2. **「認証情報」をクリック**
3. **「認証情報を作成」をクリック**
4. **「サービスアカウント」を選択**

### 5.2 サービスアカウント詳細の設定

以下の情報を入力してください：

```
サービスアカウント名: mood-mark-analytics-service
サービスアカウントID: mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com
説明: MOO:D MARK Analytics API Access
```

**注意**: サービスアカウントIDは自動生成されます。後で使用するため記録してください。

5. **「作成して続行」をクリック**

### 5.3 ロールの割り当て

1. **「このサービスアカウントにプロジェクトへのアクセスを許可」セクションで**:
   - ロール: 「編集者」を選択
   - **「続行」をクリック**

2. **「このサービスアカウントへのアクセスをユーザーに許可」セクションで**:
   - **「完了」をクリック**

## ステップ6: サービスアカウントキーの作成

### 6.1 サービスアカウント詳細画面にアクセス

1. **認証情報画面で作成したサービスアカウントをクリック**
2. **「キー」タブをクリック**

### 6.2 新しいキーの作成

1. **「鍵を追加」をクリック**
2. **「新しい鍵を作成」を選択**
3. **キーのタイプ**: 「JSON」を選択
4. **「作成」をクリック**

### 6.3 キーファイルの保存

1. **JSONファイルが自動ダウンロードされます**
2. **ファイル名**: `mood-mark-analytics-123456-xxxxxxxxxxxx.json`
3. **このファイルを安全な場所に保存**
4. **ファイルをプロジェクトの`config/`ディレクトリにコピー**
5. **ファイル名を`google-credentials.json`にリネーム**

## ステップ7: 環境変数の設定

### 7.1 必要な情報の記録

以下の情報を記録してください：

```
プロジェクトID: mood-mark-analytics-123456
プロジェクト名: MOOD_MARK_Analytics
サービスアカウントID: mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com
認証ファイル: config/google-credentials.json
```

### 7.2 環境変数の設定

`.env`ファイルに以下を追加：

```bash
# Google Cloud Console設定
GOOGLE_PROJECT_ID=mood-mark-analytics-123456
GOOGLE_CREDENTIALS_FILE=config/google-credentials.json
GOOGLE_SERVICE_ACCOUNT_EMAIL=mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com

# Google Analytics 4設定（後で設定）
GA4_PROPERTY_ID=your-ga4-property-id

# Google Search Console設定（後で設定）
GSC_SITE_URL=https://isetan.mistore.jp/moodmarkgift/

# Looker Studio設定（後で設定）
LOOKER_STUDIO_FOLDER_ID=your-looker-studio-folder-id
DATA_SOURCE_FOLDER_ID=your-data-source-folder-id
```

## ステップ8: セキュリティ設定

### 8.1 認証ファイルの保護

```bash
# プロジェクトディレクトリで実行
chmod 600 config/google-credentials.json
```

### 8.2 .gitignoreの更新

`.gitignore`ファイルに以下を追加：

```
# Google認証ファイル
config/google-credentials.json
*.json
!config/analytics_config.json
!config/project_config.json
!config/google_cloud_setup.json
```

## ステップ9: 動作確認

### 9.1 認証ファイルの配置確認

```bash
# ファイルが正しく配置されているか確認
ls -la config/google-credentials.json
```

### 9.2 基本認証テスト

```bash
# Google APIs認証テスト
python analytics/test_google_apis.py
```

## 次のステップ

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

#### 1. プロジェクト作成エラー
```
エラー: プロジェクトを作成できません
解決方法:
- プロジェクト名が既に使用されていないか確認
- 組織の権限を確認
- 別のプロジェクト名を試す
```

#### 2. API有効化エラー
```
エラー: APIを有効にできません
解決方法:
- 請求アカウントが設定されているか確認
- プロジェクトの権限を確認
- ブラウザを更新して再試行
```

#### 3. サービスアカウント作成エラー
```
エラー: サービスアカウントを作成できません
解決方法:
- 組織の権限を確認
- プロジェクトの編集者権限があるか確認
- 別のサービスアカウント名を試す
```

#### 4. キーファイルダウンロードエラー
```
エラー: JSONファイルがダウンロードされません
解決方法:
- ブラウザのポップアップブロックを確認
- 別のブラウザで試す
- 手動でキーを作成
```

## セキュリティ注意事項

### 1. 認証ファイルの管理
- **絶対にGitにコミットしない**
- **定期的なローテーション**
- **最小権限の原則**

### 2. アクセス制御
- **不要な権限は付与しない**
- **定期的な権限見直し**
- **アクセスログの監視**

### 3. 監視とアラート
- **異常なアクセスパターンの監視**
- **API使用量の監視**
- **コストアラートの設定**

この設定が完了すると、MOO:D MARK IDEAプロジェクトでGoogle APIsを活用した高度な分析システムが利用可能になります。
