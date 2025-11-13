# GA4・GSC API権限設定ガイド

## 現在の状況

サービスアカウント `mood-mark-analytics-service@mood-mark-analytics.iam.gserviceaccount.com` に以下の権限が不足しています：

### GA4 (Google Analytics 4)
- **エラー**: `User does not have sufficient permissions for this property`
- **プロパティID**: 316302380
- **必要な権限**: ビューアー権限以上

### GSC (Google Search Console)
- **エラー**: `User does not have sufficient permission for site`
- **サイトURL**: `sc-domain:isetan.mistore.jp`
- **必要な権限**: フルアクセス権限

## 権限設定手順

### 1. GA4権限設定

1. **Google Analytics 4 にアクセス**
   - https://analytics.google.com/ にアクセス
   - 対象のプロパティ（ID: 316302380）を選択

2. **管理画面に移動**
   - 左下の「管理」をクリック
   - 「プロパティ」列の「アクセス管理」をクリック

3. **ユーザーを追加**
   - 「+」ボタンをクリック
   - 「ユーザーを追加」を選択

4. **サービスアカウントの追加**
   - メールアドレス: `mood-mark-analytics-service@mood-mark-analytics.iam.gserviceaccount.com`
   - 権限: 「ビューアー」以上を選択
   - 「追加」をクリック

### 2. GSC権限設定

1. **Google Search Console にアクセス**
   - https://search.google.com/search-console/ にアクセス
   - 対象のサイト（`isetan.mistore.jp`）を選択

2. **設定画面に移動**
   - 左下の「設定」をクリック
   - 「ユーザーと権限」を選択

3. **ユーザーを追加**
   - 「ユーザーを追加」をクリック

4. **サービスアカウントの追加**
   - メールアドレス: `mood-mark-analytics-service@mood-mark-analytics.iam.gserviceaccount.com`
   - 権限: 「フル」を選択
   - 「追加」をクリック

## 権限設定後の確認

権限設定後、以下のコマンドでアクセスを確認できます：

```bash
python analytics/check_permissions.py
```

## 代替案：サンプルデータでのレポート

権限設定が完了するまでの間、サンプルデータを使用してレポートシステムの動作確認ができます。

### サンプルデータレポートの実行

```bash
python analytics/sample_data_report.py
```

## 注意事項

1. **権限設定の反映時間**
   - GA4: 即座に反映
   - GSC: 数分〜数時間かかる場合があります

2. **プロパティIDの確認**
   - GA4のプロパティIDが正しいことを確認してください
   - プロパティIDは「管理」→「プロパティ設定」で確認できます

3. **サイトURLの確認**
   - GSCのサイトURLが正しいことを確認してください
   - ドメインプロパティの場合は `sc-domain:` プレフィックスが必要です

## トラブルシューティング

### よくある問題

1. **403 Forbidden エラー**
   - 権限が正しく設定されていない
   - プロパティIDまたはサイトURLが間違っている

2. **アカウントが見つからない**
   - サービスアカウントがGA4/GSCに追加されていない
   - メールアドレスが間違っている

3. **データが取得できない**
   - 対象期間にデータが存在しない
   - フィルタ設定が間違っている

### 解決方法

1. **権限の再確認**
   - GA4/GSCの管理画面でユーザー一覧を確認
   - サービスアカウントが正しく追加されているか確認

2. **設定ファイルの確認**
   - `config/analytics_config.json` の設定を確認
   - プロパティIDとサイトURLが正しいか確認

3. **ログの確認**
   - `logs/` ディレクトリのログファイルを確認
   - エラーメッセージの詳細を確認