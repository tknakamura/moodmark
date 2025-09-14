#!/usr/bin/env python3
"""
MOO:D MARK IDEA 記事-商品マッチング・推奨エンジン

記事のキーワード、ペルソナ、GSCデータを基に最適な商品を提案するシステム
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ArticleData:
    """記事データの構造"""
    article_id: str
    title: str
    content: str
    target_keywords: List[str]
    persona: str
    scene: str
    target_audience: str
    budget_range: Tuple[int, int]
    seasonal_keywords: List[str]
    gsc_data: Dict  # 実際の流入キーワード等のGSCデータ

@dataclass
class ProductData:
    """商品データの構造"""
    product_id: str
    name: str
    category: str
    subcategory: str
    description: str
    price: int
    tags: List[str]
    target_audience: List[str]
    seasonal_suitability: List[str]
    scene_suitability: List[str]
    popularity_score: float
    conversion_rate: float

@dataclass
class RecommendationResult:
    """推奨結果の構造"""
    product_id: str
    product_name: str
    match_score: float
    match_reasons: List[str]
    confidence: float

class ProductRecommendationEngine:
    """商品推奨エンジン"""
    
    def __init__(self, config_file: str = None):
        """
        初期化
        
        Args:
            config_file (str): 設定ファイルのパス
        """
        self.config = self._load_config(config_file)
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # 日本語のため無効化
            ngram_range=(1, 2)
        )
        self.scaler = StandardScaler()
        
        # データストレージ
        self.articles: Dict[str, ArticleData] = {}
        self.products: Dict[str, ProductData] = {}
        self.keyword_weights = self._initialize_keyword_weights()
        
        logger.info("商品推奨エンジンを初期化しました")
    
    def _load_config(self, config_file: str) -> Dict:
        """設定ファイルの読み込み"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルト設定
        return {
            "matching_weights": {
                "keyword_similarity": 0.3,
                "persona_match": 0.2,
                "scene_match": 0.2,
                "budget_match": 0.1,
                "seasonal_match": 0.1,
                "popularity": 0.05,
                "conversion_rate": 0.05
            },
            "min_confidence_threshold": 0.6,
            "max_recommendations": 10,
            "seasonal_keywords": {
                "spring": ["春", "桜", "新生活", "入学", "卒業"],
                "summer": ["夏", "暑中見舞い", "お中元", "夏休み"],
                "autumn": ["秋", "お歳暮", "ハロウィン", "紅葉"],
                "winter": ["冬", "クリスマス", "年末", "バレンタイン"]
            }
        }
    
    def _initialize_keyword_weights(self) -> Dict[str, float]:
        """キーワードの重み付け初期化"""
        return {
            # シーン別キーワードの重み
            "誕生日プレゼント": 1.0,
            "クリスマスギフト": 1.0,
            "バレンタインデー": 1.0,
            "母の日": 1.0,
            "父の日": 1.0,
            "卒業祝い": 0.9,
            "入学祝い": 0.9,
            
            # 相手別キーワードの重み
            "彼氏": 1.0,
            "彼女": 1.0,
            "上司": 0.8,
            "同僚": 0.8,
            "友達": 0.9,
            "子供": 0.9,
            "両親": 0.9,
            
            # 商品カテゴリの重み
            "スイーツ": 1.0,
            "コスメ": 1.0,
            "花束": 1.0,
            "お酒": 0.9,
            "雑貨": 0.8,
            "インテリア": 0.8
        }
    
    def load_article_data(self, articles_data: List[Dict]) -> None:
        """記事データの読み込み"""
        for article in articles_data:
            article_obj = ArticleData(
                article_id=article['article_id'],
                title=article['title'],
                content=article['content'],
                target_keywords=article['target_keywords'],
                persona=article['persona'],
                scene=article['scene'],
                target_audience=article['target_audience'],
                budget_range=tuple(article['budget_range']),
                seasonal_keywords=article['seasonal_keywords'],
                gsc_data=article.get('gsc_data', {})
            )
            self.articles[article_obj.article_id] = article_obj
        
        logger.info(f"{len(self.articles)}件の記事データを読み込みました")
    
    def load_product_data(self, products_data: List[Dict]) -> None:
        """商品データの読み込み"""
        for product in products_data:
            product_obj = ProductData(
                product_id=product['product_id'],
                name=product['name'],
                category=product['category'],
                subcategory=product['subcategory'],
                description=product['description'],
                price=product['price'],
                tags=product['tags'],
                target_audience=product['target_audience'],
                seasonal_suitability=product['seasonal_suitability'],
                scene_suitability=product['scene_suitability'],
                popularity_score=product['popularity_score'],
                conversion_rate=product['conversion_rate']
            )
            self.products[product_obj.product_id] = product_obj
        
        logger.info(f"{len(self.products)}件の商品データを読み込みました")
    
    def calculate_keyword_similarity(self, article: ArticleData, product: ProductData) -> float:
        """キーワード類似度の計算"""
        # 記事のキーワードとGSCデータを結合
        article_text = " ".join([
            article.title,
            " ".join(article.target_keywords),
            " ".join(article.gsc_data.get('top_queries', [])),
            " ".join(article.seasonal_keywords)
        ])
        
        # 商品のテキスト情報を結合
        product_text = " ".join([
            product.name,
            product.description,
            " ".join(product.tags),
            product.category,
            product.subcategory
        ])
        
        try:
            # TF-IDFベクトル化
            corpus = [article_text, product_text]
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            
            # コサイン類似度計算
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # キーワード重み付け適用
            weighted_similarity = self._apply_keyword_weights(similarity, article.target_keywords)
            
            return min(weighted_similarity, 1.0)  # 最大1.0に制限
            
        except Exception as e:
            logger.warning(f"キーワード類似度計算エラー: {e}")
            return 0.0
    
    def _apply_keyword_weights(self, base_similarity: float, keywords: List[str]) -> float:
        """キーワード重み付けの適用"""
        weight_multiplier = 1.0
        
        for keyword in keywords:
            if keyword in self.keyword_weights:
                weight_multiplier *= self.keyword_weights[keyword]
        
        return base_similarity * weight_multiplier
    
    def calculate_persona_match(self, article: ArticleData, product: ProductData) -> float:
        """ペルソナマッチングスコアの計算"""
        if not article.target_audience or not product.target_audience:
            return 0.5  # デフォルトスコア
        
        # ターゲットオーディエンスの一致度計算
        article_audiences = set(article.target_audience.split(','))
        product_audiences = set(product.target_audience)
        
        if not article_audiences or not product_audiences:
            return 0.5
        
        # ジャッカード係数で類似度計算
        intersection = len(article_audiences.intersection(product_audiences))
        union = len(article_audiences.union(product_audiences))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_scene_match(self, article: ArticleData, product: ProductData) -> float:
        """シーンマッチングスコアの計算"""
        if not article.scene or not product.scene_suitability:
            return 0.5
        
        # 記事のシーンと商品のシーン適合性の一致度
        scene_keywords = article.scene.split(',')
        matching_scenes = 0
        
        for scene in scene_keywords:
            if any(scene.strip() in product_scene for product_scene in product.scene_suitability):
                matching_scenes += 1
        
        return matching_scenes / len(scene_keywords) if scene_keywords else 0.0
    
    def calculate_budget_match(self, article: ArticleData, product: ProductData) -> float:
        """予算マッチングスコアの計算"""
        min_budget, max_budget = article.budget_range
        
        if min_budget <= product.price <= max_budget:
            return 1.0  # 完全一致
        elif product.price < min_budget:
            # 予算より安い場合のペナルティ
            return max(0.0, 1.0 - (min_budget - product.price) / min_budget * 0.5)
        else:
            # 予算より高い場合のペナルティ
            return max(0.0, 1.0 - (product.price - max_budget) / max_budget * 0.3)
    
    def calculate_seasonal_match(self, article: ArticleData, product: ProductData) -> float:
        """季節マッチングスコアの計算"""
        if not article.seasonal_keywords or not product.seasonal_suitability:
            return 0.5
        
        current_season = self._get_current_season()
        seasonal_keywords = self.config['seasonal_keywords'].get(current_season, [])
        
        # 記事の季節キーワードと商品の季節適合性の一致度
        article_seasonal = set(article.seasonal_keywords + seasonal_keywords)
        product_seasonal = set(product.seasonal_suitability)
        
        if not article_seasonal or not product_seasonal:
            return 0.5
        
        intersection = len(article_seasonal.intersection(product_seasonal))
        union = len(article_seasonal.union(product_seasonal))
        
        return intersection / union if union > 0 else 0.0
    
    def _get_current_season(self) -> str:
        """現在の季節を取得"""
        month = datetime.now().month
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"
    
    def calculate_overall_match_score(self, article: ArticleData, product: ProductData) -> Tuple[float, List[str]]:
        """総合マッチングスコアの計算"""
        weights = self.config['matching_weights']
        reasons = []
        
        # 各要素のスコア計算
        keyword_score = self.calculate_keyword_similarity(article, product)
        persona_score = self.calculate_persona_match(article, product)
        scene_score = self.calculate_scene_match(article, product)
        budget_score = self.calculate_budget_match(article, product)
        seasonal_score = self.calculate_seasonal_match(article, product)
        popularity_score = product.popularity_score / 100.0  # 0-1に正規化
        conversion_score = product.conversion_rate / 100.0  # 0-1に正規化
        
        # 重み付き合計スコア計算
        total_score = (
            keyword_score * weights['keyword_similarity'] +
            persona_score * weights['persona_match'] +
            scene_score * weights['scene_match'] +
            budget_score * weights['budget_match'] +
            seasonal_score * weights['seasonal_match'] +
            popularity_score * weights['popularity'] +
            conversion_score * weights['conversion_rate']
        )
        
        # マッチング理由の生成
        if keyword_score > 0.7:
            reasons.append("キーワードの高一致")
        if persona_score > 0.8:
            reasons.append("ターゲットペルソナの一致")
        if scene_score > 0.8:
            reasons.append("シーンの適合性")
        if budget_score > 0.9:
            reasons.append("予算の適合")
        if seasonal_score > 0.8:
            reasons.append("季節性の一致")
        if popularity_score > 0.8:
            reasons.append("人気商品")
        if conversion_score > 0.7:
            reasons.append("高いコンバージョン率")
        
        return total_score, reasons
    
    def get_recommendations(self, article_id: str, limit: int = None) -> List[RecommendationResult]:
        """記事に対する商品推奨の取得"""
        if article_id not in self.articles:
            logger.error(f"記事ID {article_id} が見つかりません")
            return []
        
        article = self.articles[article_id]
        limit = limit or self.config['max_recommendations']
        
        recommendations = []
        
        for product_id, product in self.products.items():
            match_score, reasons = self.calculate_overall_match_score(article, product)
            
            # 信頼度の計算（スコアに基づく）
            confidence = min(match_score * 1.2, 1.0)
            
            # 最低信頼度閾値チェック
            if confidence >= self.config['min_confidence_threshold']:
                recommendation = RecommendationResult(
                    product_id=product_id,
                    product_name=product.name,
                    match_score=match_score,
                    match_reasons=reasons,
                    confidence=confidence
                )
                recommendations.append(recommendation)
        
        # スコア順でソート
        recommendations.sort(key=lambda x: x.match_score, reverse=True)
        
        logger.info(f"記事 {article_id} に対して {len(recommendations)} 件の推奨商品を生成")
        
        return recommendations[:limit]
    
    def get_batch_recommendations(self, article_ids: List[str]) -> Dict[str, List[RecommendationResult]]:
        """複数記事に対する一括推奨の取得"""
        results = {}
        
        for article_id in article_ids:
            results[article_id] = self.get_recommendations(article_id)
        
        return results
    
    def analyze_recommendation_quality(self, article_id: str) -> Dict:
        """推奨品質の分析"""
        recommendations = self.get_recommendations(article_id)
        
        if not recommendations:
            return {"error": "推奨結果がありません"}
        
        scores = [rec.match_score for rec in recommendations]
        
        analysis = {
            "total_recommendations": len(recommendations),
            "average_score": np.mean(scores),
            "max_score": np.max(scores),
            "min_score": np.min(scores),
            "score_std": np.std(scores),
            "high_confidence_count": len([rec for rec in recommendations if rec.confidence > 0.8]),
            "medium_confidence_count": len([rec for rec in recommendations if 0.6 <= rec.confidence <= 0.8]),
            "low_confidence_count": len([rec for rec in recommendations if rec.confidence < 0.6])
        }
        
        return analysis

# 使用例
if __name__ == "__main__":
    # エンジンの初期化
    engine = ProductRecommendationEngine()
    
    # サンプルデータの読み込み（実際のデータに置き換え）
    sample_articles = [
        {
            "article_id": "article_001",
            "title": "彼氏への誕生日プレゼント30選",
            "content": "彼氏への誕生日プレゼントで迷ったら必見！予算別・シーン別のおすすめギフトを紹介。",
            "target_keywords": ["彼氏", "誕生日プレゼント", "ギフト"],
            "persona": "20代女性",
            "scene": "誕生日,デート",
            "target_audience": "20代女性",
            "budget_range": [3000, 15000],
            "seasonal_keywords": ["春", "新生活"],
            "gsc_data": {
                "top_queries": ["彼氏 誕生日 プレゼント", "男性 ギフト", "恋人 プレゼント"]
            }
        }
    ]
    
    sample_products = [
        {
            "product_id": "product_001",
            "name": "高級革財布",
            "category": "ファッション",
            "subcategory": "革製品",
            "description": "職人が手作りした本革の財布。長く使える高品質なアイテム。",
            "price": 8000,
            "tags": ["革", "財布", "高級", "男性"],
            "target_audience": ["20代男性", "30代男性"],
            "seasonal_suitability": ["春", "秋"],
            "scene_suitability": ["誕生日", "記念日"],
            "popularity_score": 85.0,
            "conversion_rate": 12.5
        }
    ]
    
    # データの読み込み
    engine.load_article_data(sample_articles)
    engine.load_product_data(sample_products)
    
    # 推奨の取得
    recommendations = engine.get_recommendations("article_001")
    
    print("推奨結果:")
    for rec in recommendations:
        print(f"- {rec.product_name} (スコア: {rec.match_score:.3f}, 信頼度: {rec.confidence:.3f})")
        print(f"  理由: {', '.join(rec.match_reasons)}")
