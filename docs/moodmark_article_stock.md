# 記事掲載商品の在庫可視化

Streamlit ダッシュボードのページ **`/article_stock`**（[pages/article_stock.py](../pages/article_stock.py)）で、登録した MOO:D MARK 特集記事から商品URLを抽出し、各商品ページの在庫状態を一覧します。

## 在庫判定

- `div.btn-cart.soldout` あり → 在庫なし。`span.main` で **入荷待ち** / **SOLD OUT** を区別。
- 上記なし → **在庫あり** とみなす。

ロジックは [tools/moodmark_stock/scraper.py](../tools/moodmark_stock/scraper.py) に集約。

## データの保存場所

- 既定: リポジトリ直下の `data/article_stock_state.json`（`.gitignore` 対象のためコミットされません）。
- 環境変数 **`MOODMARK_STOCK_STATE_PATH`** でファイルパスを上書き可能（Render の Persistent Disk 等）。

Render の無料 Web は再デプロイでローカルファイルが消えるため、**JSON のダウンロード／アップロード**でバックアップするか、永続ディスクをマウントしてください。

## 定期実行（手動以外）

Streamlit プロセス内のタイマーはスリープで止まりがちなので、別ジョブでの実行を推奨します。

```bash
# 記事一覧が state JSON に入っている前提
export MOODMARK_STOCK_STATE_PATH=/path/to/article_stock_state.json
python scripts/run_article_stock_check.py
```

- **GitHub Actions**: `schedule` で上記を実行し、生成 JSON を Artifact に保存するか、プライベートリポジトリへコミット。その後ダッシュボードの「バックアップ / 復元」で取り込み。
- **Render Cron**（利用可能な場合）: 同コマンドをスケジュール実行。

## 記事で商品が0件になる場合

記事本文が JavaScript 描画のみの場合、`requests` ではリンクが取れません。警告が出ます。必要なら Playwright 等での取得を検討してください。
