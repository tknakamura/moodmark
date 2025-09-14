
# Google Cloud Console 手動セットアップチェックリスト

## ステップ1: プロジェクト作成
- [ ] Google Cloud Console にアクセス (https://console.cloud.google.com/)
- [ ] 新しいプロジェクトを作成
  - [ ] プロジェクト名: MOOD_MARK_Analytics
  - [ ] プロジェクトIDを記録: ________________
- [ ] プロジェクトが作成されるまで待機

## ステップ2: API有効化
- [ ] 左メニュー → 「API とサービス」 → 「ライブラリ」
- [ ] 以下のAPIを有効化:
  - [ ] Google Analytics Reporting API
  - [ ] Google Analytics Data API
  - [ ] Google Search Console API
  - [ ] Google Drive API
  - [ ] Google Sheets API

## ステップ3: サービスアカウント作成
- [ ] 左メニュー → 「API とサービス」 → 「認証情報」
- [ ] 「認証情報を作成」 → 「サービスアカウント」
- [ ] サービスアカウント詳細:
  - [ ] サービスアカウント名: mood-mark-analytics-service
  - [ ] サービスアカウントIDを記録: ________________
  - [ ] 説明: MOO:D MARK Analytics API Access
- [ ] 「作成して続行」をクリック
- [ ] ロール: 「編集者」を選択
- [ ] 「完了」をクリック

## ステップ4: サービスアカウントキー作成
- [ ] 作成したサービスアカウントをクリック
- [ ] 「キー」タブをクリック
- [ ] 「鍵を追加」 → 「新しい鍵を作成」
- [ ] キーのタイプ: JSON
- [ ] 「作成」をクリック
- [ ] JSONファイルをダウンロード
- [ ] ファイルを config/google-credentials.json に保存

## ステップ5: 環境変数設定
- [ ] .envファイルに以下を追加:
  - [ ] GOOGLE_PROJECT_ID=プロジェクトID
  - [ ] GOOGLE_CREDENTIALS_FILE=config/google-credentials.json
  - [ ] GOOGLE_SERVICE_ACCOUNT_EMAIL=サービスアカウントID

## ステップ6: 動作確認
- [ ] python analytics/test_google_apis.py を実行
- [ ] 認証成功メッセージを確認

## 次のステップ
- [ ] GA4プロパティIDの取得
- [ ] GSCサイトURLの設定
- [ ] 権限の付与（GA4、GSC、Drive）
