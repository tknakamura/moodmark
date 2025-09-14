# Google Analytics 4 と Google Search Console 権限設定ガイド

## 概要
サービスアカウント `mood-mark-analytics@mood-mark-analytics.iam.gserviceaccount.com` にGA4とGSCのアクセス権限を付与する手順です。

## 1. Google Analytics 4 権限設定

### ステップ1: GA4管理画面にアクセス
1. [Google Analytics](https://analytics.google.com/) にアクセス
2. 左サイドバーの「管理」をクリック
3. 「アカウント」列で「Isetan Mitsuk」を選択
4. 「プロパティ」列で「ムードマ」を選択

### ステップ2: プロパティアクセス管理
1. 「プロパティ」列の「アクセス管理」をクリック
2. 「+」ボタンをクリックして「ユーザーを追加」を選択
3. 以下の情報を入力：
   - **メールアドレス**: `mood-mark-analytics@mood-mark-analytics.iam.gserviceaccount.com`
   - **ロール**: 「表示者」または「編集者」を選択
   - **通知**: チェックを外す（サービスアカウントのため）
4. 「追加」をクリック

### ステップ3: 権限確認
- サービスアカウントが「表示者」ロールで追加されていることを確認

## 2. Google Search Console 権限設定

### ステップ1: GSC管理画面にアクセス
1. [Google Search Console](https://search.google.com/search-console) にアクセス
2. プロパティ「https://isetan.mistore.jp/moodmark」を選択

### ステップ2: 所有者とユーザー管理
1. 左サイドバーの「設定」をクリック
2. 「所有者とユーザー」をクリック
3. 「ユーザーを追加」をクリック
4. 以下の情報を入力：
   - **メールアドレス**: `mood-mark-analytics@mood-mark-analytics.iam.gserviceaccount.com`
   - **権限**: 「フル」または「制限」を選択
   - **通知**: チェックを外す（サービスアカウントのため）
5. 「追加」をクリック

### ステップ3: 権限確認
- サービスアカウントがユーザー一覧に追加されていることを確認

## 3. 権限設定後の確認

### テスト実行
```bash
# 環境変数を設定
export GOOGLE_CREDENTIALS_FILE='config/google-credentials.json'
export GA4_PROPERTY_ID='3580827351'
export GSC_SITE_URL='https://isetan.mistore.jp/moodmark'

# データ取得テスト
python analytics/google_apis_integration.py
```

### 期待される結果
- GA4データが正常に取得される
- GSCデータが正常に取得される
- エラーメッセージが表示されない

## 4. トラブルシューティング

### よくあるエラー

#### 「User does not have sufficient permissions for this property」
- **原因**: GA4プロパティへのアクセス権限がない
- **解決策**: 上記のステップ1-2を実行

#### 「User does not have sufficient permission for site」
- **原因**: GSCサイトへのアクセス権限がない
- **解決策**: 上記のステップ2-2を実行

#### 「Property ID not found」
- **原因**: プロパティIDが間違っている
- **解決策**: GA4管理画面で正しいプロパティIDを確認

### 権限設定の確認方法

#### GA4権限確認
1. GA4管理画面 → アクセス管理
2. サービスアカウントが一覧に表示されているか確認
3. ロールが「表示者」以上になっているか確認

#### GSC権限確認
1. GSC管理画面 → 設定 → 所有者とユーザー
2. サービスアカウントが一覧に表示されているか確認
3. 権限が「制限」以上になっているか確認

## 5. セキュリティ注意事項

### サービスアカウントの管理
- 認証キーファイルは適切に保護する
- 必要最小限の権限を付与する
- 定期的に権限を確認する

### アクセスログの監視
- 異常なアクセスパターンを監視
- 定期的にアクセスログを確認
- 不要な権限は削除する

## 6. 次のステップ

権限設定が完了したら：

1. **データ取得テスト**: `python analytics/google_apis_integration.py`
2. **統合分析システムテスト**: `python analytics/integrated_analytics_system.py once`
3. **Looker Studio連携**: ダッシュボードの作成
4. **自動化設定**: 定期実行の設定

## サポート

権限設定で問題が発生した場合：
1. エラーメッセージを確認
2. 上記のトラブルシューティングを参照
3. Google Cloud Consoleでサービスアカウントの状態を確認
4. 必要に応じて権限を再設定
