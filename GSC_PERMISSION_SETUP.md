# Google Search Console (GSC) 権限設定手順

## 概要
サービスアカウントにGoogle Search Consoleへのアクセス権限を付与する手順です。

## 必要な情報
- **サービスアカウントのメールアドレス**: `mood-mark-analytics@mood-mark-analytics-474807.iam.gserviceaccount.com`
- **対象サイト**:
  - `https://isetan.mistore.jp/moodmark/` (MOODMARK)
  - `https://isetan.mistore.jp/moodmarkgift/` (MOODMARK GIFT)

## 設定手順

### ステップ1: Google Search Consoleにアクセス
1. **Google Search Console**にアクセス
   - URL: https://search.google.com/search-console
   - あなたのGoogleアカウントでログイン

### ステップ2: プロパティ（サイト）を選択
1. 左側のメニューから「プロパティ」を選択
2. 設定するサイトを選択
   - `https://isetan.mistore.jp/moodmark/` または
   - `https://isetan.mistore.jp/moodmarkgift/`

### ステップ3: 設定メニューを開く
1. 左側のメニューから「設定」をクリック
2. 「ユーザーと権限」をクリック

### ステップ4: ユーザーを追加
1. 「ユーザーを追加」ボタンをクリック
2. **ユーザー**フィールドに以下を入力：
   ```
   mood-mark-analytics@mood-mark-analytics-474807.iam.gserviceaccount.com
   ```
3. **権限レベル**を選択：
   - **推奨**: 「フル」または「所有者」
   - **最小限**: 「閲覧者」（データ取得のみ可能）
4. 「追加」ボタンをクリック

### ステップ5: 両方のサイトに権限を付与
**重要**: 以下の2つのサイトの両方に権限を付与してください。

1. **MOODMARKサイト**
   - プロパティ: `https://isetan.mistore.jp/moodmark/`
   - サービスアカウント: `mood-mark-analytics@mood-mark-analytics-474807.iam.gserviceaccount.com`
   - 権限: フル または 閲覧者

2. **MOODMARK GIFTサイト**
   - プロパティ: `https://isetan.mistore.jp/moodmarkgift/`
   - サービスアカウント: `mood-mark-analytics@mood-mark-analytics-474807.iam.gserviceaccount.com`
   - 権限: フル または 閲覧者

## 確認方法

### 方法1: Google Search Consoleで確認
1. 各サイトの「設定」→「ユーザーと権限」を開く
2. サービスアカウントのメールアドレスがリストに表示されていることを確認

### 方法2: ダッシュボードで確認
1. https://moodmark-csv-to-html-converter.onrender.com/analytics_chat にアクセス
2. サイドバーの「📊 Google APIs接続状態」セクションを確認
3. 「🔍 GSC接続テスト」ボタンをクリック
4. 両方のサイト（MOODMARKとMOODMARK GIFT）で接続テストを実行

### 方法3: テストスクリプトで確認
ローカル環境で以下のコマンドを実行：

```bash
python test_api_integration.py https://isetan.mistore.jp/moodmarkgift/24482
```

## 注意事項

### 権限が反映されるまで
- 権限を付与してから、反映まで数分かかる場合があります
- すぐに反映されない場合は、数分待ってから再度テストしてください

### エラーメッセージ
- **403 Forbidden**: 権限が付与されていない、または反映されていない
- **404 Not Found**: サイトURLが間違っている、またはサイトがGSCに登録されていない

### トラブルシューティング
1. **サービスアカウントのメールアドレスが正しいか確認**
   - `mood-mark-analytics@mood-mark-analytics-474807.iam.gserviceaccount.com`
   - スペルミスやタイポがないか確認

2. **両方のサイトに権限を付与したか確認**
   - `moodmark`と`moodmarkgift`の両方に権限が必要です

3. **権限レベルを確認**
   - 「閲覧者」以上の権限が必要です
   - 「フル」または「所有者」を推奨します

4. **時間を置いて再試行**
   - 権限付与後、数分待ってから再度テストしてください

## 完了後の確認

権限付与が完了したら、以下を確認してください：

1. ✅ MOODMARKサイトにサービスアカウントが追加されている
2. ✅ MOODMARK GIFTサイトにサービスアカウントが追加されている
3. ✅ ダッシュボードでGSC接続テストが成功する
4. ✅ 実際の分析でGSCデータが取得できる

## 参考リンク
- [Google Search Console ヘルプ: ユーザーと権限](https://support.google.com/webmasters/answer/2451999)
- [サービスアカウントの権限設定](https://cloud.google.com/iam/docs/service-accounts)

