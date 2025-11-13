# MOO:D MARK IDEA 商品推奨システム

記事に最適な商品を提案するAI推奨システムです。記事のキーワード、ペルソナ、GSCデータを分析し、関連性の高い商品を自動で推奨します。

## クイックスタート

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. データの準備

記事データと商品データのExcelファイルを準備してください。

### 3. データの処理

```python
from data_processor import DataProcessor

processor = DataProcessor()
result = processor.process_all_data(
    articles_file="data/articles_data.xlsx",
    products_file="data/products_data.xlsx",
    load_gsc=True
)
```

### 4. APIサーバーの起動

```bash
python recommendation_api.py
```

### 5. 推奨の取得

```bash
curl "http://localhost:5000/api/v1/recommendations/article_001?limit=10"
```

## ファイル構成

- `product_recommendation_engine.py` - 推奨アルゴリズムの中核
- `data_processor.py` - データの統合・処理
- `recommendation_api.py` - RESTful API
- `recommendation_tester.py` - テスト・評価フレームワーク
- `requirements.txt` - 依存関係

## 詳細ドキュメント

詳細な使用方法については、[商品推奨システム 使用ガイド](../../docs/ai/product_recommendation_system_guide.md)をご覧ください。

## ライセンス

このプロジェクトはMOO:D MARK IDEAプロジェクトの一部です。










