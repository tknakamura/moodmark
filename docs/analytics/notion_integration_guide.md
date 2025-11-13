# 📊 Notion分析レポート連携ガイド

## 概要

このガイドでは、MOO:D MARKの分析システムをNotionワークスペースと連携し、GA4分析結果を自動的にNotionページに送信・管理する方法を説明します。

## 🚀 機能概要

### 主要機能
- **自動レポート送信**: 分析レポート生成後、自動的にNotionページを作成
- **構造化データ管理**: KPI指標をNotionデータベースで管理
- **リアルタイム同期**: スケジュール実行による定期的なデータ更新
- **カスタマイズ可能**: レポート形式やダッシュボード設定の柔軟な調整

### 対応レポートタイプ
- 週次分析レポート（Markdownファイル）
- サマリーデータ（JSONファイル）
- KPIダッシュボード
- アラート通知

## 📋 事前準備

### 1. Notion Integration Token の取得

1. [Notion Developers](https://developers.notion.com/) にアクセス
2. 「New integration」をクリック
3. Integration名を入力（例：MOO:D MARK Analytics）
4. 適切なCapabilitiesを選択：
   - Read content
   - Update content
   - Insert content
5. 「Submit」をクリック
6. **Integration Token**をコピー（`secret_` で始まる文字列）

### 2. Notionワークスペースの準備

1. 分析レポート用のページを作成
2. 作成したページのURLから**Page ID**を取得
   - URL例: `https://notion.so/workspace/Analytics-Dashboard-abc123def456`
   - Page ID: `abc123def456`
3. IntegrationをページとWorkspaceに招待
   - ページの「Share」→「Invite」→作成したIntegrationを選択

### 3. 環境変数の設定

```bash
# 必須
export NOTION_TOKEN='secret_your_integration_token'

# オプション（後でセットアップスクリプトで設定可能）
export NOTION_DATABASE_ID='your_database_id'
export NOTION_PAGE_ID='your_parent_page_id'
```

## 🔧 セットアップ手順

### Step 1: 依存関係のインストール

```bash
cd /path/to/moodmark
pip install -r requirements.txt
```

### Step 2: セットアップスクリプトの実行

```bash
python setup_notion_integration.py
```

このスクリプトは以下を自動実行します：
- 環境変数の確認
- Notion接続テスト
- Analytics データベースの作成
- レポート変換機能のテスト
- 設定ファイルの更新

### Step 3: 統合システムのテスト

```bash
# 一回だけ実行してテスト
python analytics/integrated_analytics_system.py once
```

## 📊 作成されるNotionデータベース構造

### Analytics Reports データベース

| プロパティ名 | タイプ | 説明 |
|------------|--------|------|
| Title | タイトル | レポートのタイトル |
| Report Date | 日付 | レポート生成日 |
| Period | リッチテキスト | 分析期間 |
| Total Sessions | 数値 | 総セッション数 |
| Total Users | 数値 | 総ユーザー数 |
| Total Revenue (¥) | 数値 | 総売上（円） |
| CVR (%) | 数値 | コンバージョン率 |
| AOV (¥) | 数値 | 平均注文単価（円） |
| Status | セレクト | ステータス（Generated/Reviewed/Actioned） |
| Priority | セレクト | 優先度（High/Medium/Low） |
| Tags | マルチセレクト | タグ（Weekly Report/Performance/SEO等） |

## ⚙️ 設定ファイル

### config/notion_config.json

```json
{
  "notion": {
    "integration_token": "",
    "database_id": "your_database_id",
    "page_id": "your_page_id",
    "workspace_name": "MOO:D MARK Analytics"
  },
  "report_settings": {
    "auto_sync_enabled": true,
    "sync_frequency": "daily",
    "report_types": ["weekly_analysis", "kpi_dashboard"],
    "include_charts": true
  }
}
```

### config/analytics_config.json

```json
{
  "notion": {
    "enabled": true,
    "auto_sync": true,
    "sync_after_report_generation": true,
    "create_database_if_missing": true
  }
}
```

## 🚀 使用方法

### 1. 手動でのレポート送信

```python
from analytics.integrated_analytics_system import IntegratedAnalyticsSystem

# システム初期化
system = IntegratedAnalyticsSystem()

# 分析実行（自動的にNotionに送信）
system.run_analysis_cycle()
```

### 2. スケジュール実行

```bash
# 毎日9時に自動実行
python analytics/integrated_analytics_system.py schedule
```

### 3. KPIダッシュボードの作成

```python
from analytics.integrated_analytics_system import IntegratedAnalyticsSystem

system = IntegratedAnalyticsSystem()
dashboard_page_id = system.create_notion_kpi_dashboard()
print(f"ダッシュボード作成完了: {dashboard_page_id}")
```

### 4. 個別レポートの変換・送信

```python
from analytics.notion_integration import NotionIntegration
from analytics.notion_report_converter import NotionReportConverter

# 初期化
notion = NotionIntegration()
converter = NotionReportConverter()

# レポート変換
json_file = 'data/processed/analysis_report_purchase_7days_20251011_173000.json'
md_file = 'docs/analytics/moodmark_7days_analysis_report.md'

converted = converter.convert_analysis_report(json_file, md_file)

# Notionに送信
with open(md_file, 'r', encoding='utf-8') as f:
    markdown_content = f.read()

page_id = notion.create_report_page(converted, markdown_content)
print(f"ページ作成完了: {page_id}")
```

## 📈 レポートページの内容

### 自動生成される情報

1. **エグゼクティブサマリー**
   - 主要指標の表示
   - 重要な改善点の抽出

2. **詳細メトリクス**
   - セッション数、ユーザー数
   - 売上、CVR、AOV
   - 直帰率、セッション時間

3. **推奨事項**
   - 優先度別の改善提案
   - カテゴリ別の分類
   - 期待されるインパクト

4. **詳細レポート**
   - 完全なMarkdownコンテンツ
   - セクション別の構造化表示

## 🔍 トラブルシューティング

### よくある問題

#### 1. 認証エラー
```
❌ Notion API認証エラー
```

**解決方法:**
- `NOTION_TOKEN`環境変数が正しく設定されているか確認
- Integration TokenがNotionワークスペースに招待されているか確認

#### 2. データベース作成エラー
```
❌ データベース作成に失敗しました
```

**解決方法:**
- `NOTION_PAGE_ID`が正しく設定されているか確認
- 親ページに対する適切な権限があるか確認

#### 3. レポート変換エラー
```
❌ レポート変換に失敗しました
```

**解決方法:**
- JSONファイルの形式が正しいか確認
- Markdownファイルが存在するか確認

### ログの確認

```bash
# 詳細ログの確認
tail -f logs/analytics_system.log

# エラーログのフィルタ
grep "ERROR" logs/analytics_system.log
```

## 🎯 活用例

### 1. 週次レポートの自動化
- 毎週月曜日に前週のレポートを自動生成
- Notionデータベースで推移を管理
- アラートによる異常値の検出

### 2. KPIダッシュボードの運用
- リアルタイムKPI監視
- 目標値との比較
- トレンド分析

### 3. チームでのレポート共有
- Notionワークスペースでの一元管理
- コメント機能による議論
- タスク管理との連携

## 🔧 カスタマイズ

### レポートテンプレートの変更

`config/notion_config.json`の`templates`セクションを編集：

```json
{
  "templates": {
    "weekly_report_template": {
      "title_format": "📊 {site_name} 週次分析レポート - {date_range}",
      "sections": [
        "Executive Summary",
        "Key Metrics",
        "Recommendations"
      ]
    }
  }
}
```

### 数値フォーマットの変更

```json
{
  "formatting": {
    "currency_symbol": "¥",
    "percentage_decimal_places": 2,
    "date_format": "YYYY年MM月DD日"
  }
}
```

## 📚 参考資料

- [Notion API Documentation](https://developers.notion.com/)
- [Google Analytics 4 API](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [MOO:D MARK 分析システムガイド](./analytics_system_guide.md)

## 🆘 サポート

問題が発生した場合：

1. ログファイルを確認 (`logs/analytics_system.log`)
2. セットアップスクリプトを再実行 (`python setup_notion_integration.py`)
3. 環境変数の設定を確認
4. Notionの権限設定を確認

---

**更新日**: 2025年10月11日  
**バージョン**: 1.0.0  
**対応システム**: MOO:D MARK Analytics v2.0+
