# 記事掲載商品の在庫可視化

Streamlit ダッシュボードのページ **`/article_stock`**（[pages/article_stock.py](../pages/article_stock.py)）で、登録した MOO:D MARK 特集記事から商品URLを抽出し、各商品ページの在庫状態を一覧します。

## 在庫判定

- 結果一覧の **商品名** は商品ページの `h1.name` 内の表示用 `<span>`（`brand` / `keyword` 以外）を優先し、なければ `og:title` 等（キャッシュ時も保持）。
- 結果表の在庫関連列は **在庫表示** のみ（在庫コード・ボタン文言・サブ文言は非表示。フィルタは内部で在庫コードを使用）。
- 記事が **1件** のとき、記事別グラフは x 軸を「掲載数 / 在庫注意」の2本バーに切り替え（1カテゴリ×2系列のバーが消える Plotly 挙動の回避）。
- `div.btn-cart.soldout` あり → 在庫なし。`span.main` で **入荷待ち** / **SOLD OUT** を区別。
- 上記なし → **在庫あり** とみなす。

ロジックは [tools/moodmark_stock/scraper.py](../tools/moodmark_stock/scraper.py) に集約。

## データの保存（PostgreSQL 推奨）

永続層は [tools/moodmark_stock/store.py](../tools/moodmark_stock/store.py) が担当します。

| 条件 | 動作 |
|------|------|
| 環境変数 **`DATABASE_URL` が設定されている** | **PostgreSQL**。記事はテーブル `moodmark_stock_articles`、各実行結果は `moodmark_stock_runs`（JSONB）に追記。画面は**最新1件の実行**を表示。 |
| 未設定 | **JSON ファイル**（既定 `data/article_stock_state.json` または `MOODMARK_STOCK_STATE_PATH`）。 |

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

## 定期実行（手動以外）

```bash
export DATABASE_URL='postgresql://...'
export MOODMARK_STOCK_DELAY=0.5   # 推奨 0.3〜0.5
export MOODMARK_STOCK_ARTICLE_WORKERS=4
export MOODMARK_STOCK_PRODUCT_WORKERS=12
export MOODMARK_STOCK_CACHE_HOURS=24
# 毎回フル取得: export MOODMARK_STOCK_FORCE_FULL=1
python scripts/run_article_stock_check.py
```

- **GitHub Actions** / **Render Cron**: 上記を `schedule` 実行。`DATABASE_URL` を渡せば結果が DB に蓄積されます。
- Streamlit 内のタイマーだけに頼らない運用を推奨します。

## 記事で商品が0件になる場合

記事本文が JavaScript 描画のみの場合、`requests` ではリンクが取れません。警告が出ます。必要なら Playwright 等での取得を検討してください。
