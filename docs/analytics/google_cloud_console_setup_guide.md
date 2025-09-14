# Google Cloud Console 設定詳細ガイド

## 概要

MOO:D MARK IDEAプロジェクト用のGoogle Cloud Console設定を、スクリーンショット付きで詳細に説明します。

## ステップ1: Google Cloud Console プロジェクトの作成

### 1.1 Google Cloud Console にアクセス

1. **ブラウザでGoogle Cloud Consoleを開く**
   - URL: https://console.cloud.google.com/
   - Googleアカウントでログイン

2. **新しいプロジェクトを作成**
   - 画面左上の「プロジェクトを選択」をクリック
   - 「新しいプロジェクト」をクリック

### 1.2 プロジェクト詳細の設定

```
プロジェクト名: MOOD_MARK_Analytics
組織: [お使いの組織を選択]
場所: [組織のフォルダまたは「なし」を選択]
```

**重要**: プロジェクトIDは自動生成されますが、後で使用するため記録しておいてください。
例: `mood-mark-analytics-123456`

3. **「作成」ボタンをクリック**
4. **プロジェクトが作成されるまで待機**（通常1-2分）

## ステップ2: 必要なAPIの有効化

### 2.1 API ライブラリにアクセス

1. **左メニューから「API とサービス」をクリック**
2. **「ライブラリ」をクリック**

### 2.2 必要なAPIの有効化

以下のAPIを順番に有効化します：

#### A. Google Analytics Reporting API
1. 検索ボックスに「Google Analytics Reporting API」と入力
2. 「Google Analytics Reporting API」をクリック
3. 「有効にする」ボタンをクリック

#### B. Google Analytics Data API
1. 検索ボックスに「Google Analytics Data API」と入力
2. 「Google Analytics Data API」をクリック
3. 「有効にする」ボタンをクリック

#### C. Google Search Console API
1. 検索ボックスに「Google Search Console API」と入力
2. 「Google Search Console API」をクリック
3. 「有効にする」ボタンをクリック

#### D. Google Drive API
1. 検索ボックスに「Google Drive API」と入力
2. 「Google Drive API」をクリック
3. 「有効にする」ボタンをクリック

#### E. Google Sheets API
1. 検索ボックスに「Google Sheets API」と入力
2. 「Google Sheets API」をクリック
3. 「有効にする」ボタンをクリック

### 2.3 API有効化の確認

1. **左メニューから「API とサービス」→「有効なAPI」をクリック**
2. **以下のAPIが表示されることを確認**:
   - Google Analytics Reporting API
   - Google Analytics Data API
   - Google Search Console API
   - Google Drive API
   - Google Sheets API

## ステップ3: サービスアカウントの作成

### 3.1 サービスアカウント作成画面にアクセス

1. **左メニューから「API とサービス」をクリック**
2. **「認証情報」をクリック**
3. **「認証情報を作成」をクリック**
4. **「サービスアカウント」を選択**

### 3.2 サービスアカウント詳細の設定

```
サービスアカウント名: mood-mark-analytics-service
サービスアカウントID: mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com
説明: MOO:D MARK Analytics API Access
```

**注意**: サービスアカウントIDは自動生成されます。後で使用するため記録しておいてください。

5. **「作成して続行」をクリック**

### 3.3 ロールの割り当て

1. **「このサービスアカウントにプロジェクトへのアクセスを許可」セクションで**:
   - ロール: 「編集者」を選択
   - **「続行」をクリック**

2. **「このサービスアカウントへのアクセスをユーザーに許可」セクションで**:
   - **「完了」をクリック**

## ステップ4: サービスアカウントキーの作成

### 4.1 サービスアカウント詳細画面にアクセス

1. **認証情報画面で作成したサービスアカウントをクリック**
2. **「キー」タブをクリック**

### 4.2 新しいキーの作成

1. **「鍵を追加」をクリック**
2. **「新しい鍵を作成」を選択**
3. **キーのタイプ**: 「JSON」を選択
4. **「作成」をクリック**

### 4.3 キーファイルの保存

1. **JSONファイルが自動ダウンロードされます**
2. **ファイル名**: `mood-mark-analytics-123456-xxxxxxxxxxxx.json`
3. **このファイルを安全な場所に保存**
4. **ファイルをプロジェクトの`config/`ディレクトリにコピー**
5. **ファイル名を`google-credentials.json`にリネーム**

## ステップ5: プロジェクト設定の記録

### 5.1 必要な情報の記録

以下の情報を記録してください：

```
プロジェクトID: mood-mark-analytics-123456
プロジェクト名: MOOD_MARK_Analytics
サービスアカウントID: mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com
認証ファイル: config/google-credentials.json
```

### 5.2 環境変数の設定準備

後で設定する環境変数：

```bash
export GOOGLE_CREDENTIALS_FILE='config/google-credentials.json'
export GOOGLE_PROJECT_ID='mood-mark-analytics-123456'
export GOOGLE_SERVICE_ACCOUNT_EMAIL='mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com'
```

## ステップ6: セキュリティ設定

### 6.1 認証ファイルの保護

```bash
# プロジェクトディレクトリで実行
chmod 600 config/google-credentials.json
```

### 6.2 .gitignoreの更新

`.gitignore`ファイルに以下を追加：

```
# Google認証ファイル
config/google-credentials.json
*.json
!config/analytics_config.json
!config/project_config.json
```

## ステップ7: 動作確認

### 7.1 認証ファイルの配置確認

```bash
# ファイルが正しく配置されているか確認
ls -la config/google-credentials.json
```

### 7.2 環境変数の設定

```bash
# .envファイルに追加
echo "GOOGLE_CREDENTIALS_FILE=config/google-credentials.json" >> .env
echo "GOOGLE_PROJECT_ID=mood-mark-analytics-123456" >> .env
echo "GOOGLE_SERVICE_ACCOUNT_EMAIL=mood-mark-analytics@mood-mark-analytics-123456.iam.gserviceaccount.com" >> .env
```

### 7.3 基本認証テスト

```bash
# Google APIs認証テスト
python analytics/test_google_apis.py
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. API有効化エラー
```
エラー: APIを有効にできません
解決方法: 
- 請求アカウントが設定されているか確認
- プロジェクトの権限を確認
- ブラウザを更新して再試行
```

#### 2. サービスアカウント作成エラー
```
エラー: サービスアカウントを作成できません
解決方法:
- 組織の権限を確認
- プロジェクトの編集者権限があるか確認
- 別のプロジェクト名を試す
```

#### 3. キーファイルダウンロードエラー
```
エラー: JSONファイルがダウンロードされません
解決方法:
- ブラウザのポップアップブロックを確認
- 別のブラウザで試す
- 手動でキーを作成
```

#### 4. 認証ファイル読み込みエラー
```
エラー: 認証ファイルが見つかりません
解決方法:
- ファイルパスが正しいか確認
- ファイル権限を確認
- 環境変数が設定されているか確認
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
