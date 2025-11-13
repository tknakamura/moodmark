# OAuth 2.0を使用したGA4 API連携

## 概要

このディレクトリには、OAuth 2.0ユーザー認証を使用してGoogle Analytics 4 (GA4) APIと連携するためのモジュールが含まれています。

## ファイル構成

```
analytics/
├── oauth_google_apis.py       # OAuth 2.0認証を使用したGoogle APIs統合モジュール
├── test_oauth_ga4.py          # OAuth認証とGA4接続のテストスクリプト
├── google_apis_integration.py # サービスアカウント認証版（従来版）
└── README_OAuth.md            # このファイル
```

## クイックスタート

### 1. 必要なパッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. OAuth 2.0クライアントIDの設定

詳細な手順は [docs/analytics/oauth_setup_guide.md](../docs/analytics/oauth_setup_guide.md) を参照してください。

簡単な手順：
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Google Analytics Data API v1を有効化
3. OAuth 2.0クライアントID（デスクトップアプリ）を作成
4. JSONファイルをダウンロードして `config/oauth_credentials.json` に配置

### 3. テスト実行

```bash
python analytics/test_oauth_ga4.py
```

初回実行時：
- ブラウザが開きます
- Googleアカウントでログイン
- アクセスを許可
- 認証トークンが `config/token.json` に保存されます

### 4. データ取得

```bash
python analytics/oauth_google_apis.py
```

## 使用例

### Pythonスクリプトでの使用

```python
from analytics.oauth_google_apis import OAuthGoogleAPIsIntegration

# インスタンス作成
api = OAuthGoogleAPIsIntegration()

# 過去30日間のGA4データを取得
ga4_data = api.get_ga4_data(date_range_days=30)
print(f"取得行数: {len(ga4_data)}")
print(ga4_data.head())

# カスタムメトリクスとディメンションで取得
custom_data = api.get_ga4_data(
    date_range_days=7,
    metrics=['sessions', 'totalUsers', 'screenPageViews'],
    dimensions=['date', 'deviceCategory', 'pagePath']
)

# Google Search Consoleデータを取得
gsc_data = api.get_gsc_data(date_range_days=30)
print(f"GSCデータ: {len(gsc_data)}行")

# サマリーレポートを生成
summary = api.get_summary_report(date_range_days=30)
print(f"総セッション数: {summary['ga4_summary']['total_sessions']:,}")
print(f"総ユーザー数: {summary['ga4_summary']['total_users']:,}")

# CSVにエクスポート
api.export_to_csv(ga4_data, 'my_ga4_data.csv')
```

## 主要な機能

### OAuthGoogleAPIsIntegration クラス

#### メソッド

##### `get_ga4_data(date_range_days, metrics, dimensions, property_id)`
GA4からデータを取得します。

**パラメータ**：
- `date_range_days` (int): 取得する日数（デフォルト: 30）
- `metrics` (list): 取得するメトリクス
- `dimensions` (list): 取得するディメンション
- `property_id` (str): GA4プロパティID（オプション）

**戻り値**：
- `pd.DataFrame`: GA4データ

**デフォルトメトリクス**：
- `sessions`: セッション数
- `totalUsers`: ユーザー数
- `screenPageViews`: ページビュー数
- `bounceRate`: 直帰率
- `averageSessionDuration`: 平均セッション時間
- `conversions`: コンバージョン数

**デフォルトディメンション**：
- `date`: 日付
- `pagePath`: ページパス
- `sessionDefaultChannelGrouping`: チャネル
- `deviceCategory`: デバイスカテゴリ

##### `get_gsc_data(date_range_days, dimensions, row_limit, site_url)`
Google Search Consoleからデータを取得します。

**パラメータ**：
- `date_range_days` (int): 取得する日数（デフォルト: 30）
- `dimensions` (list): 取得するディメンション
- `row_limit` (int): 取得行数上限（デフォルト: 25000）
- `site_url` (str): サイトURL（オプション）

**戻り値**：
- `pd.DataFrame`: GSCデータ

##### `get_summary_report(date_range_days)`
GA4とGSCの統合サマリーレポートを生成します。

**パラメータ**：
- `date_range_days` (int): 取得する日数（デフォルト: 30）

**戻り値**：
- `dict`: サマリーレポート（GA4とGSCの統計情報）

##### `export_to_csv(data, filename, output_dir)`
DataFrameをCSVファイルにエクスポートします。

**パラメータ**：
- `data` (pd.DataFrame): エクスポートするデータ
- `filename` (str): ファイル名
- `output_dir` (str): 出力ディレクトリ（デフォルト: 'data/processed'）

## 設定

### config/analytics_config.json

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

## サービスアカウント版との違い

| 項目 | OAuth 2.0版 | サービスアカウント版 |
|------|------------|-------------------|
| 認証方式 | ユーザー認証 | サービスアカウント |
| 初回セットアップ | ブラウザでログイン | JSONキー配置のみ |
| 権限管理 | 個人のGA4権限を使用 | サービスアカウントに権限付与が必要 |
| トークン管理 | 自動更新（有効期限あり） | キーファイル（期限なし） |
| 適用場面 | 個人使用、開発環境 | 本番環境、自動化 |
| ファイル | `oauth_google_apis.py` | `google_apis_integration.py` |

## トラブルシューティング

### よくある問題

#### 1. 「認証ファイルが見つかりません」

**原因**：`config/oauth_credentials.json` が存在しない

**解決方法**：
1. Google Cloud ConsoleでOAuth 2.0クライアントIDを作成
2. JSONファイルをダウンロード
3. `config/oauth_credentials.json` に配置

#### 2. 「権限エラー」

**原因**：GA4プロパティへのアクセス権限がない

**解決方法**：
1. GA4の管理画面で権限を確認
2. 「閲覧者」以上の権限が必要
3. 正しいGoogleアカウントでログインしているか確認

#### 3. 「データが取得できない」

**原因**：プロパティIDが間違っている、またはデータが存在しない

**解決方法**：
1. GA4プロパティID（316302380）が正しいか確認
2. GA4管理画面でデータが記録されているか確認
3. 日付範囲にデータが存在するか確認

#### 4. トークンの期限切れ

**症状**：以前は動作していたが、突然エラーが発生

**解決方法**：
```bash
# トークンファイルを削除して再認証
rm config/token.json
python analytics/test_oauth_ga4.py
```

## セキュリティ

### 重要な注意事項

以下のファイルは**絶対にGitにコミットしないでください**：
- `config/oauth_credentials.json` - OAuth 2.0クライアント認証情報
- `config/token.json` - 認証トークン

これらのファイルは `.gitignore` で除外されています。

### ファイル権限

```bash
# 適切な権限を設定
chmod 600 config/oauth_credentials.json
chmod 600 config/token.json
```

## 次のステップ

1. **定期的なデータ収集**：
   cronやスケジューラーで定期実行

2. **データ分析**：
   取得したCSVデータを分析ツールで活用

3. **カスタムレポート**：
   必要なメトリクスとディメンションでカスタマイズ

4. **自動化**：
   統合分析システムとの連携を検討

## 参考資料

- [OAuth 2.0セットアップガイド](../docs/analytics/oauth_setup_guide.md)
- [Google Analytics Data API v1](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Google Search Console API](https://developers.google.com/webmaster-tools/search-console-api-original)

---

**最終更新**: 2025-10-11
**対象サイト**: https://isetan.mistore.jp/moodmark
**GA4プロパティID**: 316302380


