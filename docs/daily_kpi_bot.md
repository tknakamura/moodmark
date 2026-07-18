# Daily KPI Bot 運用手順

GA4 の **前々日** KPI を毎朝 **09:00 JST** に Slack へ配信する Bot です。  
（GA4 の日次データは翌日午後まで確定しないことがあるため、前日ではなく前々日を対象にします）  
在庫チェック Bot（[`article_stock_daily.yml`](../.github/workflows/article_stock_daily.yml)）と同様、GitHub Actions + Slack Bot API（スレッド形式）で動作します。

## 配信内容

| 投稿 | 内容 |
|------|------|
| **親メッセージ** | `MOO:D MARK Daily KPI（mm/dd）` + EC 購入サマリ + IDEA セッション |
| **返信 1** | サイト横断の前年同曜日比較（EC / IDEA） |
| **返信 2** | moodmark（EC）購買・デバイス・チャネル |
| **返信 3** | moodmarkgift（IDEA）記事 PV / LP / チャネル Top5 |
| **返信 4** | アラート + GitHub Actions 実行ログ |

**対象日**: 前々日（JST）  
**比較**: 前年同曜日（対象日の364日前）

Slack では Markdown 表が崩れるため、詳細は **箇条書き形式** で配信します。

## Slack チャンネル

- 通知先: [kikinews #C011BDFHN7N](https://kikinews.slack.com/archives/C011BDFHN7N)
- Secret `SLACK_KPI_CHANNEL_ID` = `C011BDFHN7N`

## GitHub Secrets

Settings → Secrets and variables → Actions に以下を登録してください。

| Secret | 説明 |
|--------|------|
| `GOOGLE_CREDENTIALS_JSON` | サービスアカウント JSON 全文（[GA4_PERMISSION_SETUP.md](../GA4_PERMISSION_SETUP.md) 参照） |
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token（`xoxb-...`、scope: `chat:write`） |
| `SLACK_KPI_CHANNEL_ID` | `C011BDFHN7N` |
| `SLACK_WEBHOOK_URL` | 任意。Bot トークン未設定時のフォールバック（スレッド不可） |

在庫 Bot と **Bot トークンは共用**できます。チャンネル ID のみ KPI 用に分離しています。

## Slack App の準備

1. [Slack API](https://api.slack.com/apps) で App を作成（または在庫 Bot の App を流用）
2. **OAuth & Permissions** → Bot Token Scopes に `chat:write` を追加
3. ワークスペースにインストールし **Bot User OAuth Token** を取得
4. 通知先チャンネル `#C011BDFHN7N` に Bot を招待: `/invite @Bot名`

## 手動実行

### GitHub Actions

1. リポジトリ → **Actions** → **daily-kpi-bot**
2. **Run workflow** → **Run workflow**

### ローカル（dry-run）

Slack に投稿せず stdout に出力:

```bash
cd /path/to/moodmark
export GOOGLE_CREDENTIALS_JSON='...'
MOODMARK_KPI_DRY_RUN=1 python scripts/run_daily_kpi_bot.py
```

Slack に実際に投稿:

```bash
export GOOGLE_CREDENTIALS_JSON='...'
export SLACK_BOT_TOKEN='xoxb-...'
export SLACK_KPI_CHANNEL_ID='C011BDFHN7N'
python scripts/run_daily_kpi_bot.py
```

## ファイル構成

```
.github/workflows/daily_kpi.yml
scripts/run_daily_kpi_bot.py
tools/daily_kpi/
  ga4_collector.py    # GA4 データ取得・集計
  format_slack.py     # Slack メッセージ生成
  notify.py           # Slack 投稿
tools/slack_client.py # Slack Web API 共通
```

## GA4 KPI 定義（Phase 1）

| 指標 | メトリクス | 備考 |
|------|-----------|------|
| EC 購入数 | `ecommercePurchases` | landingPage ベースで moodmark EC のみ |
| EC 売上 | `purchaseRevenue` | 同上 |
| EC 直帰率・滞在 | `bounceRate`, `averageSessionDuration` | サイト全体平均（`date` 次元のみ。LP 別の単純平均は使わない） |
| Purchase CVR | 購入数 ÷ セッション | `conversions` は使わない |
| IDEA セッション | `sessions` | `/moodmarkgift` フィルタ |

## アラート閾値

[`config/analytics_config.json`](../config/analytics_config.json) の `alerts.performance_threshold` を参照:

- 直帰率 > 70%（サイト別）
- セッション 前年比 -20% 超
- EC 購入数 前年比 -30% 超

## Phase 2（未実装）

GSC 連携時は返信 5 として SEO KPI（クリック / インプレッション / CTR / Top クエリ）を追加予定。  
[`GSC_PERMISSION_SETUP.md`](../GSC_PERMISSION_SETUP.md) を参照。

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| GA4 403 | サービスアカウントに GA4 プロパティ `316302380` の閲覧者権限を付与 |
| Slack `not_in_channel` | Bot をチャンネルに `/invite` |
| 対象日データが 0 | GA4 確定遅延の可能性。`MOODMARK_KPI_OFFSET_DAYS=1` でさらに1日過去へずらして再実行 |
| スレッドにならない | `SLACK_BOT_TOKEN` + `SLACK_KPI_CHANNEL_ID` を確認（Webhook はスレッド不可） |
