# MOO:D MARK｜CSV to HTML コンバーター
*developed by Takeshi Nakamura*

結婚祝いお菓子記事のCSVファイルをHTMLに変換するダッシュボードです。

## 機能

- CSVファイルのアップロード
- リアルタイムプレビュー
- HTMLファイルのダウンロード
- サンプルCSVでのデモ実行

## 使用方法

### 1. 環境セットアップ

```bash
pip install -r requirements_dashboard.txt
```

### 2. ダッシュボード起動

```bash
streamlit run csv_to_html_dashboard.py
```

### 3. 使用方法

1. ブラウザで `http://localhost:8501` にアクセス
2. CSVファイルをアップロード
3. プレビューで内容を確認
4. HTMLファイルをダウンロード

## CSV形式

以下の列を含むCSVファイルが必要です：

- `タグ`: title, description, H2, H3, H4
- `title or description or heedline`: タイトルや見出しテキスト
- `見出し下に＜p＞タグを入れる場合のテキスト`: 説明文
- `URL（商品・リンク）①`: 商品リンクURL
- `alt（商品名）①`: 商品名（alt属性用）
- `span（商品名）①`: 商品名（表示用）
- `URL（商品・リンク）②`: 追加商品リンクURL（オプション）
- `span（商品名）②`: 追加商品名（オプション）

## 変換ルール

- `title` → `<h1>`タグ
- `description` → `<p>`タグ（メイン説明）
- `H2` → `<h2 class="section-title">`タグ
- `H3` → `<h3 class="section-subtitle">`タグ
- `H4` → `<h4 class="item-box-subtitle">`タグ（商品名）

## ファイル構成

```
├── csv_to_html_dashboard.py    # メインダッシュボード
├── requirements_dashboard.txt  # 依存関係
├── README_dashboard.md        # このファイル
└── csv/                       # サンプルCSVファイル
    └── MOODMARK｜結婚祝い お菓子 - to中村さん結婚祝い お菓子｜改善案 コピー.csv
```

## 注意事項

- CSVファイルはUTF-8エンコーディングで保存してください
- 商品画像は `assets/images/s_article/` ディレクトリに配置する必要があります
- 生成されるHTMLは既存のCSSファイル（`assets/css/c_article.css`）に依存します
