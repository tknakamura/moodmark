# MOO:D MARK IDEA 商品推奨システム 使用ガイド

## 概要

MOO:D MARK IDEAの記事に最適な商品を提案するAI推奨システムです。記事のキーワード、ペルソナ、GSCデータを分析し、関連性の高い商品を自動で推奨します。

## システム構成

### 主要コンポーネント

1. **ProductRecommendationEngine** - 推奨アルゴリズムの中核
2. **DataProcessor** - データの統合・処理
3. **RecommendationAPI** - RESTful API
4. **RecommendationTester** - テスト・評価フレームワーク

### ファイル構成

```
tools/ai/
├── product_recommendation_engine.py  # 推奨エンジン
├── data_processor.py                 # データ処理モジュール
├── recommendation_api.py             # REST API
└── recommendation_tester.py          # テストフレームワーク
```

## 機能概要

### 推奨アルゴリズム

記事と商品のマッチングは以下の要素を総合的に評価します：

#### 1. キーワード類似度（重み: 30%）
- TF-IDFベクトル化によるコサイン類似度
- 記事のターゲットキーワードとGSCデータの活用
- キーワードの重要度による重み付け

#### 2. ペルソナマッチング（重み: 20%）
- ターゲットオーディエンスの一致度
- ジャッカード係数による類似度計算

#### 3. シーンマッチング（重み: 20%）
- 記事のシーンと商品のシーン適合性
- 誕生日、クリスマス、記念日等のマッチング

#### 4. 予算マッチング（重み: 10%）
- 記事の予算範囲と商品価格の適合性
- 予算超過時のペナルティ設定

#### 5. 季節マッチング（重み: 10%）
- 現在の季節と記事・商品の季節性
- 春、夏、秋、冬の自動判定

#### 6. 人気度・コンバージョン率（重み: 10%）
- 商品の人気度スコア
- 過去のコンバージョン率

## セットアップ

### 1. 依存関係のインストール

```bash
pip install pandas numpy scikit-learn flask flask-cors matplotlib seaborn requests
```

### 2. データの準備

#### 記事データ（Excel形式）
以下の列を含むスプレッドシートを準備：

| 列名 | 説明 | 例 |
|------|------|-----|
| article_id | 記事ID | article_001 |
| title | 記事タイトル | 彼氏への誕生日プレゼント30選 |
| content | 記事本文 | 彼氏への誕生日プレゼントで... |
| target_keywords | ターゲットキーワード | 彼氏,誕生日プレゼント,ギフト |
| persona | ペルソナ | 20代女性 |
| scene | シーン | 誕生日,デート |
| target_audience | ターゲットオーディエンス | 20代女性 |
| budget_range | 予算範囲 | 3000-15000 |
| seasonal_keywords | 季節キーワード | 春,新生活 |

#### 商品データ（Excel形式）
以下の列を含むスプレッドシートを準備：

| 列名 | 説明 | 例 |
|------|------|-----|
| product_id | 商品ID | product_001 |
| name | 商品名 | 高級革財布 |
| category | カテゴリ | ファッション |
| subcategory | サブカテゴリ | 革製品 |
| description | 商品説明 | 職人が手作りした本革の財布... |
| price | 価格 | 8000 |
| tags | タグ | 革,財布,高級,男性 |
| target_audience | ターゲットオーディエンス | 20代男性,30代男性 |
| seasonal_suitability | 季節適合性 | 春,秋 |
| scene_suitability | シーン適合性 | 誕生日,記念日 |
| popularity_score | 人気度スコア | 85.0 |
| conversion_rate | コンバージョン率 | 12.5 |

### 3. データの処理

```python
from data_processor import DataProcessor

# データプロセッサーの初期化
processor = DataProcessor()

# 全データの処理
result = processor.process_all_data(
    articles_file="data/articles_data.xlsx",
    products_file="data/products_data.xlsx",
    load_gsc=True  # GSCデータも取得
)

print("処理結果:", result)
```

## API使用法

### 1. APIサーバーの起動

```bash
python tools/ai/recommendation_api.py
```

デフォルトでポート5000で起動します。

### 2. APIエンドポイント

#### ヘルスチェック
```http
GET /health
```

#### 商品推奨の取得
```http
GET /api/v1/recommendations/{article_id}?limit=10&min_confidence=0.6
```

**パラメータ:**
- `article_id`: 記事ID
- `limit`: 推奨数の上限（デフォルト: 10）
- `min_confidence`: 最低信頼度（デフォルト: 0.6）

**レスポンス例:**
```json
{
  "article_id": "article_001",
  "recommendations": [
    {
      "product_id": "product_001",
      "product_name": "高級革財布",
      "match_score": 0.856,
      "confidence": 0.923,
      "match_reasons": ["キーワードの高一致", "ペルソナの一致", "予算の適合"]
    }
  ],
  "total_recommendations": 8,
  "timestamp": "2024-01-15T10:30:00"
}
```

#### 一括推奨の取得
```http
POST /api/v1/recommendations/batch
Content-Type: application/json

{
  "article_ids": ["article_001", "article_002"],
  "limit": 10,
  "min_confidence": 0.6
}
```

#### 推奨品質の分析
```http
GET /api/v1/analyze/{article_id}
```

#### データの更新
```http
POST /api/v1/data/refresh
Content-Type: application/json

{
  "articles_file": "path/to/articles.xlsx",
  "products_file": "path/to/products.xlsx",
  "load_gsc": true
}
```

#### データサマリーの取得
```http
GET /api/v1/data/summary
```

#### 記事一覧の取得
```http
GET /api/v1/articles?limit=50&offset=0
```

#### 商品一覧の取得
```http
GET /api/v1/products?category=ファッション&limit=50&offset=0
```

## テスト・評価

### 1. テストフレームワークの使用

```python
from recommendation_tester import RecommendationTester

# テストフレームワークの初期化
tester = RecommendationTester()

# エンジンの初期化
tester.initialize_engine()

# 合成正解データの生成
tester.generate_synthetic_ground_truth(sample_size=50)

# 全テストの実行
results = tester.run_all_tests(include_api_test=True)

# レポートの生成
report_file = tester.generate_test_report()
```

### 2. 評価指標

#### 精度・再現率（Precision & Recall）
- Precision@K: 上位K件の推奨における関連商品の割合
- Recall@K: 全関連商品中で上位K件に含まれる割合
- F1-Score@K: 精度と再現率の調和平均

#### NDCG（Normalized Discounted Cumulative Gain）
- 順位を考慮した関連度の評価
- 上位の推奨により大きな重みを付与

#### パフォーマンス指標
- 平均実行時間
- 最大実行時間
- メモリ使用量

### 3. テストレポート

JSON形式で詳細なテスト結果を出力：

```json
{
  "test_summary": {
    "total_tests": 4,
    "successful_tests": 4,
    "failed_tests": 0,
    "generated_at": "2024-01-15T10:30:00"
  },
  "test_results": [
    {
      "test_name": "precision_recall",
      "success": true,
      "metrics": {
        "precision_at_5": 0.756,
        "recall_at_5": 0.634,
        "f1_at_5": 0.689
      }
    }
  ]
}
```

## カスタマイズ

### 1. マッチング重みの調整

`product_recommendation_engine.py`の設定で重みを変更可能：

```python
"matching_weights": {
    "keyword_similarity": 0.3,    # キーワード類似度
    "persona_match": 0.2,         # ペルソナマッチング
    "scene_match": 0.2,           # シーンマッチング
    "budget_match": 0.1,          # 予算マッチング
    "seasonal_match": 0.1,        # 季節マッチング
    "popularity": 0.05,           # 人気度
    "conversion_rate": 0.05       # コンバージョン率
}
```

### 2. キーワード重みの追加

```python
self.keyword_weights = {
    "誕生日プレゼント": 1.0,
    "クリスマスギフト": 1.0,
    "彼氏": 1.0,
    "彼女": 1.0,
    # 新しいキーワードを追加
    "新商品": 1.2
}
```

### 3. 季節キーワードの追加

```python
"seasonal_keywords": {
    "spring": ["春", "桜", "新生活", "入学", "卒業"],
    "summer": ["夏", "暑中見舞い", "お中元", "夏休み"],
    "autumn": ["秋", "お歳暮", "ハロウィン", "紅葉"],
    "winter": ["冬", "クリスマス", "年末", "バレンタイン"],
    # 新しい季節キーワードを追加
    "special": ["限定", "特別", "記念"]
}
```

## トラブルシューティング

### よくある問題

#### 1. データ読み込みエラー
```
エラー: 記事データの読み込みに失敗しました
解決策: Excelファイルの形式と列名を確認してください
```

#### 2. GSCデータ取得エラー
```
エラー: GSCサービスまたはサイトURLが設定されていません
解決策: Google APIsの認証設定を確認してください
```

#### 3. 推奨結果が空
```
原因: 信頼度閾値が高すぎる、またはデータの不整合
解決策: min_confidenceパラメータを下げる、データの品質を確認
```

#### 4. パフォーマンスが遅い
```
原因: 大量のデータまたは複雑な計算
解決策: データの前処理、キャッシュの実装、並列処理の導入
```

### ログの確認

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 運用・監視

### 1. 定期データ更新

```bash
# 毎日午前2時にデータを更新
0 2 * * * cd /path/to/project && python tools/ai/data_processor.py
```

### 2. パフォーマンス監視

```python
# 推奨品質の定期チェック
from recommendation_tester import RecommendationTester

tester = RecommendationTester()
tester.initialize_engine()

# 週次テスト
weekly_results = tester.run_all_tests()
tester.generate_test_report("weekly_report.json")
```

### 3. API監視

```bash
# ヘルスチェックの定期実行
curl -f http://localhost:5000/health || echo "API is down"
```

## 今後の拡張予定

### 1. 機械学習の導入
- 協調フィルタリング
- 深層学習による特徴抽出
- リアルタイム学習

### 2. 高度なパーソナライゼーション
- ユーザー行動履歴の活用
- セッション情報の考慮
- A/Bテスト機能

### 3. 多言語対応
- 英語コンテンツへの対応
- 多言語キーワードマッチング

### 4. リアルタイム推奨
- WebSocketによるリアルタイム更新
- ストリーミングデータ処理

## サポート

質問や問題がございましたら、以下の情報と共にお問い合わせください：

- エラーメッセージ
- 実行環境（OS、Pythonバージョン）
- 使用しているデータの概要
- 再現手順

---

**注意**: このシステムは開発・テスト環境での使用を前提としています。本番環境での使用前に、十分なテストとセキュリティチェックを行ってください。
