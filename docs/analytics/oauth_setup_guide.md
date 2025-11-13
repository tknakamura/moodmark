# OAuth 2.0を使用したGA4 API連携セットアップガイド

## 概要

このガイドでは、OAuth 2.0ユーザー認証を使用してGoogle Analytics 4 (GA4) APIとの連携を設定する方法を説明します。サービスアカウントではなく、ご自身のGoogleアカウントの権限を使用してGA4データにアクセスします。

## 前提条件

- GA4プロパティへのアクセス権限（閲覧者以上）があること
- Google Cloud Consoleへのアクセス権限があること
- Python 3.8以上がインストールされていること

## セットアップ手順

### ステップ1: Google Cloud Projectの作成または選択

#### 1.1 Google Cloud Consoleにアクセス

1. ブラウザで https://console.cloud.google.com/ を開く
2. Googleアカウントでログイン

#### 1.2 プロジェクトの作成または選択

既存のプロジェクトを使用する場合：
- 画面上部のプロジェクト選択ドロップダウンからプロジェクトを選択

新規プロジェクトを作成する場合：
1. 画面上部の「プロジェクトを選択」をクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト名を入力（例：`MOOD-MARK-Analytics`）
4. 「作成」をクリック

### ステップ2: Google Analytics Data API v1の有効化

1. 左メニューから **「APIとサービス」** → **「ライブラリ」** をクリック
2. 検索ボックスに「Google Analytics Data API」と入力
3. **「Google Analytics Data API」** をクリック
4. **「有効にする」** ボタンをクリック

同様に以下のAPIも有効化（オプション）：
- **Google Search Console API**（Search Consoleデータを取得する場合）

### ステップ3: OAuth 2.0クライアントIDの作成

#### 3.1 OAuth同意画面の設定

1. 左メニューから **「APIとサービス」** → **「OAuth同意画面」** をクリック

2. **User Type（ユーザータイプ）の選択**：
   - **内部**：組織内のユーザーのみ（Google Workspace組織の場合）
   - **外部**：任意のGoogleアカウント（個人使用の場合はこちら）
   - 「外部」を選択して「作成」をクリック

3. **アプリ情報の入力**：
   - **アプリ名**：`MOOD MARK Analytics`
   - **ユーザーサポートメール**：ご自身のメールアドレス
   - **デベロッパーの連絡先情報**：ご自身のメールアドレス
   - 「保存して次へ」をクリック

4. **スコープ**：
   - 「保存して次へ」をクリック（スコープは後で自動的に設定されます）

5. **テストユーザー**（外部を選択した場合）：
   - 「ADD USERS」をクリック
   - GA4にアクセスできるGoogleアカウントのメールアドレスを追加
   - 「保存して次へ」をクリック

6. **概要**：
   - 内容を確認して「ダッシュボードに戻る」をクリック

#### 3.2 OAuth 2.0クライアントIDの作成

1. 左メニューから **「APIとサービス」** → **「認証情報」** をクリック

2. 上部の **「認証情報を作成」** → **「OAuth クライアント ID」** をクリック

3. **アプリケーションの種類**：
   - **「デスクトップアプリ」** を選択
   - 名前：`MOOD MARK OAuth Client`
   - 「作成」をクリック

4. **認証情報のダウンロード**：
   - 作成完了のダイアログが表示されたら「JSONをダウンロード」をクリック
   - または、認証情報一覧から作成したOAuthクライアントの右側のダウンロードアイコンをクリック

5. **ファイルの配置**：
   - ダウンロードしたJSONファイルを `config/oauth_credentials.json` にリネームして配置
   
   ```bash
   # プロジェクトルートで実行
   mv ~/Downloads/client_secret_*.json config/oauth_credentials.json
   ```

### ステップ4: 必要なパッケージのインストール

```bash
# プロジェクトルートで実行
pip install -r requirements.txt
```

インストールされるパッケージ：
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`

### ステップ5: 設定ファイルの確認

`config/analytics_config.json` を開き、以下の設定を確認：

```json
{
  "sites": {
    "moodmark": {
      "url": "https://isetan.mistore.jp/moodmark/",
      "ga4_property_id": "316302380",
      "gsc_site_url": "sc-domain:isetan.mistore.jp"
    }
  },
  "oauth": {
    "credentials_file": "config/oauth_credentials.json",
    "token_file": "config/token.json"
  }
}
```

### ステップ6: OAuth認証フローの実行

#### 6.1 テストスクリプトの実行

```bash
# プロジェクトルートで実行
python analytics/test_oauth_ga4.py
```

#### 6.2 OAuth認証フロー

1. **ブラウザが自動的に開く**：
   - 開かない場合は、ターミナルに表示されるURLをコピーしてブラウザで開く

2. **Googleアカウントでログイン**：
   - GA4プロパティへのアクセス権限を持つアカウントでログイン

3. **アクセス許可**：
   - 「このアプリは Google で確認されていません」と表示される場合：
     - 「詳細」をクリック
     - 「MOOD MARK Analytics（安全ではないページ）に移動」をクリック
   - 「Google Analytics のデータを表示および管理します」の許可を確認
   - 「続行」をクリック

4. **認証完了**：
   - 「認証フローが完了しました。このウィンドウを閉じてください。」と表示される
   - ブラウザを閉じる

5. **トークンの保存**：
   - 認証トークンが `config/token.json` に自動保存される
   - 次回以降はこのトークンが使用される（有効期限まで）

### ステップ7: 動作確認

テストスクリプトが以下のテストを実行します：

1. ✅ OAuth 2.0認証
2. ✅ GA4 API接続とデータ取得
3. ✅ Google Search Console API接続とデータ取得（オプション）
4. ✅ サマリーレポート生成

成功すると以下のようなメッセージが表示されます：

```
🎉 すべてのテストが成功しました！
```

## 使用方法

### 基本的な使用方法

```python
from analytics.oauth_google_apis import OAuthGoogleAPIsIntegration

# インスタンス作成（初回のみブラウザでログイン）
api = OAuthGoogleAPIsIntegration()

# GA4データ取得
ga4_data = api.get_ga4_data(date_range_days=30)
print(ga4_data)

# サマリーレポート生成
summary = api.get_summary_report(date_range_days=30)
print(summary)
```

### コマンドラインからの実行

```bash
# サマリーレポート生成とCSVエクスポート
python analytics/oauth_google_apis.py
```

## トラブルシューティング

### 1. 「認証ファイルが見つかりません」エラー

**エラーメッセージ**：
```
OAuth認証情報ファイルが見つかりません: config/oauth_credentials.json
```

**解決方法**：
1. Google Cloud ConsoleでOAuth 2.0クライアントIDを作成したか確認
2. JSONファイルをダウンロードし、`config/oauth_credentials.json` に配置
3. ファイル名とパスが正しいか確認

### 2. 「このアプリは確認されていません」警告

**表示される場合**：
OAuth同意画面で「外部」を選択し、アプリを公開していない場合

**解決方法**：
1. 「詳細」をクリック
2. 「MOOD MARK Analytics（安全ではないページ）に移動」をクリック
3. これは自分で作成したアプリなので問題ありません

### 3. 「権限エラー」

**エラーメッセージ**：
```
権限エラー: GA4プロパティへのアクセス権限を確認してください
```

**解決方法**：
1. GA4プロパティへのアクセス権限があるGoogleアカウントでログインしているか確認
2. GA4の管理画面で、使用しているアカウントに「閲覧者」以上の権限があるか確認
3. プロパティID（316302380）が正しいか確認

### 4. トークンの期限切れ

**症状**：以前は動作していたが、突然エラーが発生する

**解決方法**：
1. `config/token.json` を削除
2. スクリプトを再実行
3. ブラウザで再度ログイン

```bash
rm config/token.json
python analytics/test_oauth_ga4.py
```

### 5. データが取得できない

**確認項目**：
1. GA4プロパティID（316302380）が正しいか
2. 対象の期間にデータが存在するか
3. GA4プロパティにデータが実際に記録されているか

**デバッグ方法**：
```bash
# ログレベルをDEBUGに変更
export LOG_LEVEL=DEBUG
python analytics/test_oauth_ga4.py
```

## セキュリティ考慮事項

### 1. 認証ファイルの保護

```bash
# .gitignoreに追加されていることを確認
cat .gitignore | grep oauth_credentials.json
cat .gitignore | grep token.json
```

以下のファイルは**絶対にGitリポジトリにコミットしない**：
- `config/oauth_credentials.json`
- `config/token.json`

### 2. ファイル権限の設定

```bash
# 適切な権限を設定
chmod 600 config/oauth_credentials.json
chmod 600 config/token.json
```

### 3. トークンの管理

- トークンファイルには認証情報が含まれています
- 第三者と共有しない
- 定期的にトークンを更新（自動的に行われます）

## 次のステップ

✅ OAuth 2.0認証が完了したら：

1. **定期的なデータ収集**：
   ```bash
   python analytics/oauth_google_apis.py
   ```

2. **統合分析システムの活用**：
   - `analytics/integrated_analytics_system.py` でOAuth版を検討

3. **自動化**：
   - cronジョブやスケジューラーで定期実行

4. **データ分析**：
   - CSVファイルでエクスポートされたデータを分析
   - Looker StudioやBIツールと連携

## 参考資料

- [Google Analytics Data API v1 ドキュメント](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Google Cloud Console](https://console.cloud.google.com/)

## サポート

問題が解決しない場合：
1. エラーメッセージをコピー
2. `config/analytics_config.json` の設定を確認
3. ログファイルを確認：`data/processed/` ディレクトリ

---

**最終更新**: 2025-10-11


