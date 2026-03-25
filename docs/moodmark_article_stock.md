# 記事掲載商品の在庫可視化

Streamlit ダッシュボードのページ **`/article_stock`**（[pages/article_stock.py](../pages/article_stock.py)）で、登録した MOO:D MARK 特集記事から商品URLを抽出し、各商品ページの在庫状態を一覧します。

## 在庫判定

- 結果一覧の **商品名** は商品ページの `h1.name` 内の表示用 `<span>`（`brand` / `keyword` 以外）を優先し、なければ `og:title` 等（キャッシュ時も保持）。
- 結果表の在庫関連列は **在庫表示** のみ（在庫コード・ボタン文言・サブ文言は非表示。フィルタは内部で在庫コードを使用）。
- 記事が **1件** のとき、記事別グラフは x 軸を「掲載数 / 在庫注意」の2本バーに切り替え（1カテゴリ×2系列のバーが消える Plotly 挙動の回避）。
- `div.btn-cart.soldout` あり → 在庫なし。`span.main` で **入荷待ち** / **SOLD OUT** を区別。
- 上記なし → **在庫あり** とみなす。

ロジックは [tools/moodmark_stock/scraper.py](../tools/moodmark_stock/scraper.py) に集約。

- **記事からの商品URL抽出**: `/moodmark/product/MM-…`（および `MMV-…`）の `href` に加え、**moodmarkgift（IDEA）** 記事で使われる `data-moodmark-product-id="…"` も検出します。在庫チェック用の取得先はいずれも `https://isetan.mistore.jp/moodmark/product/{slug}.html` に正規化されます（静的HTMLに ID が含まれる限り、ヘッドレスは不要なケースが多いです）。

## データの保存（PostgreSQL 推奨）

永続層は [tools/moodmark_stock/store.py](../tools/moodmark_stock/store.py) が担当します。

| 条件 | 動作 |
|------|------|
| 環境変数 **`DATABASE_URL` が設定されている** | **PostgreSQL**。記事はテーブル `moodmark_stock_articles`、各実行結果は `moodmark_stock_runs`（JSONB）に追記。画面は**最新1件の実行**を表示。 |
| 未設定 | **JSON ファイル**（既定 `data/article_stock_state.json` または `MOODMARK_STOCK_STATE_PATH`）。 |

#### 既存 PostgreSQL へのカラム追加（GA4 表示回数）

アプリ起動時に [store.py](../tools/moodmark_stock/store.py) が **`ADD COLUMN IF NOT EXISTS`** で GA4 用の列を自動追加します（手動 SQL は原則不要）。

手動で実行する場合や、自動追加に失敗したとき用の例:

```sql
ALTER TABLE moodmark_stock_articles
  ADD COLUMN IF NOT EXISTS ga4_pageviews_7d INTEGER;
ALTER TABLE moodmark_stock_articles
  ADD COLUMN IF NOT EXISTS ga4_pv_fetched_at TIMESTAMPTZ;
ALTER TABLE moodmark_stock_articles
  ADD COLUMN IF NOT EXISTS ga4_pv_error VARCHAR(512);
```

### GA4 の記事 PV（ダッシュボード）

記事の登録・URL 更新直後に、GA4 Data API で **screenPageViews** を取得し、記事別サマリに **PV(7日)** として表示します。

- **環境変数**: `GA4_PROPERTY_ID`、および既存の Google 認証（`GOOGLE_CREDENTIALS_JSON` または `GOOGLE_CREDENTIALS_FILE`）。未設定時は取得をスキップし、列は「未設定」扱いです。
- **集計期間**: 反映遅延を避けるため、**終端＝今日から3日前**、そこから **さかのぼる7日間**（両端含む）。
- **突合**: 記事 URL から `pagePath` を取り、GA4 の `pagePath` に **CONTAINS** でフィルタ（`/moodmark`・`/moodmarkgift` 配下ではサイト用 **BEGINS_WITH** と AND）。

### GA4 の商品 itemName・購入数・収益（在庫チェック実行時）

「在庫チェック実行」でオプション **GA4で商品名（itemName）・購入数・収益を取得**（既定 ON）を有効にすると、実行完了後に GA4 Data API で商品行を拡張します。

- **集計期間**: 記事 PV と**同一**（終端＝今日から3日前、そこからさかのぼる7日間）。
- **メトリクス**: **`itemsPurchased`**（購入ユニット数）、**`itemRevenue`**（アイテム収益・返金控除後。通貨はプロパティ設定に依存）。
- **ディメンション**: **`itemId`**（商品 URL のパス上スラッグ、例 `MM-…` / `MMV-…` と一致することを想定）、**`itemName`**（一覧の「商品名」表示に優先）。
- **タグ前提**: EC の `purchase` 等で `items` が送られていること。期間内に購入がない商品は **0** 表示になり得ます。
- **未設定時**: `GA4_PROPERTY_ID` または認証が無い場合はスキップ（ページ上の商品名のみ）。

### 結果タブの並べ替え・表記

- **記事別サマリ**: 「並べ替え（多い順）」で **PV(7日)**（既定）または **在庫注意率** を選ぶと、その値の大きい順に並びます（未取得 PV は後方）。
- **商品一覧**: 同ラベルで **収益**（既定）・**購入数**・**記事数** のいずれかで降順ソートします。表内の列名は **購入数** / **収益** に短縮しており、GA4・期間・通貨の意味は表直上のキャプションに記載します。
- **記事で絞り込み**: 商品一覧の前にある **記事検索（部分一致）** で、記事ラベルまたは URL の一部入力により候補を絞り込めます。

### Render

[render.yaml](../render.yaml) では Web サービス用 PostgreSQL（`moodmark-article-stock`）と `DATABASE_URL` の自動連携を定義しています。Blueprint を初めて適用する場合、ダッシュボードでサービスとDBの作成・紐づけを確認してください。

- **無料 PostgreSQL** は一定期間で期限切れになるプランがあります。本番は有料プランやバックアップ（`pg_dump`、またはダッシュボードの **JSON ダウンロード**）を推奨します。
- JSON のみ運用したい場合は、Render 上で **`DATABASE_URL` 環境変数を削除**すればローカルJSON相当の挙動になります（無料Webではファイルは再デプロイで消えやすいので非推奨）。

### 依存パッケージ

`SQLAlchemy`、`psycopg2-binary`（[requirements.txt](../requirements.txt)）。

### JSON から PostgreSQL へ初回移行

ローカルに残っている `article_stock_state.json` を DB に載せる場合（**既存DBの記事・実行履歴は削除**されます）:

```bash
export DATABASE_URL='postgresql://...'   # ローカルからは External URL
python scripts/migrate_article_stock_json_to_db.py /path/to/article_stock_state.json
```

ダッシュボードの「バックアップ / 復元」で JSON をアップロードしても同様に取り込めます。

## 速度・キャッシュ

- **リクエスト前待機**: ワーカーごとに GET の直前にスリープする秒数。**0.3〜0.5秒を推奨**（ダッシュボード既定 0.5 秒）。短すぎると相手サイトへの負荷・ブロックのリスクが上がります。
- **並列取得**: 記事ページ・商品ページをそれぞれ同時接続数上限付きで並列 GET（ダッシュボードのスライダー、または CLI の環境変数）。
- **TTL キャッシュ**（既定 24 時間）: 前回スナップショットの `cache_meta` を使い、期間内の記事は掲載商品URLの再取得を省略、商品は在庫結果の再取得を省略。**強制フルチェック**で無効化可能。
- 記事取得失敗・商品取得エラー時は、その URL のキャッシュを更新せず次回再試行します。

### 特定記事だけ在庫チェック（部分実行）

Streamlit の「在庫チェック実行」では **在庫チェックする記事** を複数選択できます。一部だけ選ぶと、その記事の HTML のみ再取得し、**選んでいない記事は直前のスナップショット**の `article_to_products`（と記事側 `cache_meta`）を引き継ぎます。初回実行前に部分だけ走らせると、未選択記事は商品0件扱いになる点に注意してください。

CLI では環境変数 **`MOODMARK_STOCK_ONLY_URLS`** にカンマ区切りで記事URLを渡すと同様に部分実行になります（`previous_snapshot` として DB / JSON の最終結果が読み込まれる前提）。

## 定期実行（手動以外）

```bash
export DATABASE_URL='postgresql://...'
export MOODMARK_STOCK_DELAY=0.5   # 推奨 0.3〜0.5
export MOODMARK_STOCK_ARTICLE_WORKERS=4
export MOODMARK_STOCK_PRODUCT_WORKERS=12
export MOODMARK_STOCK_CACHE_HOURS=24
# 毎回フル取得: export MOODMARK_STOCK_FORCE_FULL=1
# 特定記事のみ: export MOODMARK_STOCK_ONLY_URLS='https://...,https://...'
python scripts/run_article_stock_check.py
```

- **GitHub Actions** / **Render Cron**: 上記を `schedule` 実行。`DATABASE_URL` を渡せば結果が DB に蓄積されます。
- Streamlit 内のタイマーだけに頼らない運用を推奨します。

## 記事で商品が0件になる場合

記事本文が JavaScript 描画のみの場合、`requests` ではリンクが取れません。警告が出ます。必要なら Playwright 等での取得を検討してください。
