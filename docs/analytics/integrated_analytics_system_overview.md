# 統合分析システム概要

## システム構成

MOO:D MARK IDEAプロジェクト用のGoogle APIs統合分析システムを構築しました。このシステムは、GA4、Google Search Console、Looker Studioを連携させ、精緻な計測と分析を自動化します。

## 主要機能

### 1. Google APIs統合システム
**ファイル**: `analytics/google_apis_integration.py`

#### 機能
- **GA4データ取得**: セッション、ユーザー、ページビュー、コンバージョン等の詳細データ
- **GSCデータ取得**: 検索クエリ、ページ別パフォーマンス、検索順位等のSEOデータ
- **自動データエクスポート**: CSV形式でのデータ保存
- **統合サマリーレポート**: 包括的な分析レポート生成

#### 取得可能なデータ
- **GA4**: セッション数、ユーザー数、ページビュー数、バウンス率、平均セッション時間、コンバージョン数、収益
- **GSC**: クリック数、インプレッション数、CTR、平均検索順位、上位ページ、上位クエリ

### 2. Looker Studio コネクタ
**ファイル**: `analytics/looker_studio_connector.py`

#### 機能
- **データソース自動作成**: Google Sheetsをデータソースとして自動作成
- **ダッシュボードテンプレート**: 分析用ダッシュボードの自動生成
- **自動更新機能**: データソースの定期更新
- **セットアップ手順生成**: Looker Studio設定の詳細手順

#### 作成されるダッシュボード要素
- 概要メトリクス（セッション数、ユーザー数、ページビュー数）
- 時系列グラフ（日別の主要メトリクス）
- ページ別パフォーマンス（上位ページのトラフィック）
- 検索クエリ分析（上位検索クエリのクリック数・インプレッション数）
- デバイス別分析（デバイスカテゴリ別のパフォーマンス）
- 地理的分布（国別のトラフィック分布）

### 3. 統合分析システム
**ファイル**: `analytics/integrated_analytics_system.py`

#### 機能
- **自動データ収集**: 定期的なデータ取得と保存
- **詳細分析**: パフォーマンス、SEO、コンテンツ分析
- **アラート機能**: 閾値超過時の自動通知
- **スケジュール実行**: 日次・週次・時間単位での自動実行

#### 分析項目
- **パフォーマンス分析**: セッション、バウンス率、セッション時間
- **SEO分析**: 検索順位、CTR、上位ページ・クエリ
- **コンテンツ分析**: キーワードカテゴリ別分析
- **推奨事項**: 自動的な改善提案

## セットアップ要件

### 必要なGoogle APIs
1. **Google Analytics Data API**: GA4データ取得
2. **Google Search Console API**: GSCデータ取得
3. **Google Drive API**: Looker Studio用ファイル管理
4. **Google Sheets API**: データソース作成

### 必要な権限設定
1. **GA4プロパティ**: サービスアカウントに「表示者」権限
2. **GSCプロパティ**: サービスアカウントに「フル」権限
3. **Google Drive**: 共有フォルダへの「編集者」権限

### 環境変数設定
```bash
export GOOGLE_CREDENTIALS_FILE='config/google-credentials.json'
export GA4_PROPERTY_ID='your-ga4-property-id'
export GSC_SITE_URL='https://isetan.mistore.jp/moodmarkgift/'
export LOOKER_STUDIO_FOLDER_ID='your-looker-studio-folder-id'
export DATA_SOURCE_FOLDER_ID='your-data-source-folder-id'
```

## 実行方法

### 1. 基本的なテスト
```bash
# Google APIs連携テスト
python analytics/test_google_apis.py
```

### 2. 一回だけの分析実行
```bash
# 統合分析システムの一回実行
python analytics/integrated_analytics_system.py once
```

### 3. スケジュール実行
```bash
# 日次自動実行
python analytics/integrated_analytics_system.py schedule
```

### 4. 個別機能テスト
```bash
# GA4・GSCデータ取得のみ
python analytics/google_apis_integration.py

# Looker Studio連携のみ
python analytics/looker_studio_connector.py
```

## 出力ファイル

### データファイル
- `data/processed/ga4_data_YYYYMMDD_HHMMSS.csv`: GA4データ
- `data/processed/gsc_pages_YYYYMMDD_HHMMSS.csv`: GSCページデータ
- `data/processed/gsc_queries_YYYYMMDD_HHMMSS.csv`: GSCクエリデータ

### レポートファイル
- `data/processed/analytics_report_YYYYMMDD_HHMMSS.json`: 統合分析レポート
- `data/processed/summary_report_YYYYMMDD_HHMMSS.json`: サマリーレポート
- `data/processed/alerts_YYYYMMDD_HHMMSS.json`: アラート情報

### Looker Studio関連
- `data/processed/looker_studio_setup_YYYYMMDD.md`: セットアップ手順
- Google Sheets: データソース用スプレッドシート（自動作成）

## アラート機能

### 設定可能な閾値
- **バウンス率**: 70%超過でアラート
- **平均検索順位**: 10位以下でアラート
- **CTR**: 2%未満でアラート

### アラート内容
- パフォーマンス問題の自動検出
- SEO改善の必要性通知
- 具体的な改善提案

## カスタマイズ

### 設定ファイル
**ファイル**: `config/analytics_config.json`

```json
{
  "data_collection": {
    "ga4_date_range_days": 30,
    "gsc_date_range_days": 30,
    "top_pages_limit": 100,
    "top_queries_limit": 100
  },
  "reporting": {
    "auto_report_enabled": true,
    "report_frequency": "daily",
    "looker_studio_enabled": true
  },
  "alerts": {
    "performance_threshold": {
      "bounce_rate": 0.7,
      "avg_position": 10,
      "ctr": 0.02
    }
  }
}
```

### 分析項目の追加
- 新しいメトリクスやディメンションの追加
- カスタム分析ロジックの実装
- 追加のアラート条件設定

## 期待効果

### データ分析の精緻化
- **リアルタイム監視**: 定期的なデータ収集による継続的監視
- **統合分析**: GA4とGSCデータの統合による包括的分析
- **自動レポート**: Looker Studioによる視覚的な分析レポート

### 意思決定の高速化
- **自動アラート**: 問題の早期発見と通知
- **推奨事項**: データに基づく具体的な改善提案
- **トレンド分析**: 時系列データによる傾向把握

### 運用効率の向上
- **自動化**: 手動作業の削減
- **標準化**: 統一された分析フレームワーク
- **スケーラビリティ**: 複数サイトへの展開可能性

## 次のステップ

1. **認証設定**: Google Cloud ConsoleでのAPI設定
2. **権限設定**: GA4・GSC・Driveの権限付与
3. **環境変数設定**: 必要な環境変数の設定
4. **動作確認**: テストスクリプトでの動作確認
5. **本格運用**: スケジュール実行の開始

この統合分析システムにより、MOO:D MARK IDEAの計測が大幅に精緻化され、データドリブンな意思決定が可能になります。
