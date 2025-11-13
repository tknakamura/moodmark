#!/usr/bin/env python3
"""
商品推奨API

記事に最適な商品を提案するRESTful API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import traceback

# 相対インポート
from product_recommendation_engine import ProductRecommendationEngine, ArticleData, ProductData
from data_processor import DataProcessor

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリケーションの初期化
app = Flask(__name__)
CORS(app)  # CORSを有効化

# グローバル変数
recommendation_engine = None
data_processor = None

def initialize_services():
    """サービス群の初期化"""
    global recommendation_engine, data_processor
    
    try:
        # データプロセッサーの初期化
        data_processor = DataProcessor()
        
        # 処理済みデータの読み込み
        if data_processor.load_processed_data():
            # 推奨エンジンの初期化
            recommendation_engine = ProductRecommendationEngine()
            
            # データの読み込み
            articles_list = list(data_processor.articles_data.values())
            products_list = list(data_processor.products_data.values())
            
            recommendation_engine.load_article_data(articles_list)
            recommendation_engine.load_product_data(products_list)
            
            logger.info("サービス群の初期化が完了しました")
            return True
        else:
            logger.error("処理済みデータの読み込みに失敗しました")
            return False
            
    except Exception as e:
        logger.error(f"サービス初期化エラー: {e}")
        logger.error(traceback.format_exc())
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェックエンドポイント"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "recommendation_engine": recommendation_engine is not None,
            "data_processor": data_processor is not None
        }
    })

@app.route('/api/v1/recommendations/<article_id>', methods=['GET'])
def get_recommendations(article_id: str):
    """
    記事に対する商品推奨を取得
    
    Args:
        article_id (str): 記事ID
        
    Query Parameters:
        limit (int): 推奨数の上限（デフォルト: 10）
        min_confidence (float): 最低信頼度（デフォルト: 0.6）
    
    Returns:
        JSON: 推奨結果
    """
    if not recommendation_engine:
        return jsonify({"error": "推奨エンジンが初期化されていません"}), 500
    
    try:
        # クエリパラメータの取得
        limit = request.args.get('limit', 10, type=int)
        min_confidence = request.args.get('min_confidence', 0.6, type=float)
        
        # 推奨の取得
        recommendations = recommendation_engine.get_recommendations(article_id, limit)
        
        # 信頼度フィルタリング
        filtered_recommendations = [
            rec for rec in recommendations 
            if rec.confidence >= min_confidence
        ]
        
        # レスポンスの構築
        response = {
            "article_id": article_id,
            "recommendations": [
                {
                    "product_id": rec.product_id,
                    "product_name": rec.product_name,
                    "match_score": round(rec.match_score, 3),
                    "confidence": round(rec.confidence, 3),
                    "match_reasons": rec.match_reasons
                }
                for rec in filtered_recommendations
            ],
            "total_recommendations": len(filtered_recommendations),
            "requested_limit": limit,
            "min_confidence": min_confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"推奨取得エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"推奨の取得に失敗しました: {str(e)}"}), 500

@app.route('/api/v1/recommendations/batch', methods=['POST'])
def get_batch_recommendations():
    """
    複数記事に対する一括推奨を取得
    
    Request Body:
        {
            "article_ids": ["article_001", "article_002"],
            "limit": 10,
            "min_confidence": 0.6
        }
    
    Returns:
        JSON: 一括推奨結果
    """
    if not recommendation_engine:
        return jsonify({"error": "推奨エンジンが初期化されていません"}), 500
    
    try:
        # リクエストボディの取得
        data = request.get_json()
        
        if not data or 'article_ids' not in data:
            return jsonify({"error": "article_idsが必要です"}), 400
        
        article_ids = data['article_ids']
        limit = data.get('limit', 10)
        min_confidence = data.get('min_confidence', 0.6)
        
        # 一括推奨の取得
        batch_results = recommendation_engine.get_batch_recommendations(article_ids)
        
        # レスポンスの構築
        response = {
            "results": {},
            "total_articles": len(article_ids),
            "requested_limit": limit,
            "min_confidence": min_confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        for article_id, recommendations in batch_results.items():
            # 信頼度フィルタリング
            filtered_recommendations = [
                rec for rec in recommendations 
                if rec.confidence >= min_confidence
            ]
            
            response["results"][article_id] = {
                "recommendations": [
                    {
                        "product_id": rec.product_id,
                        "product_name": rec.product_name,
                        "match_score": round(rec.match_score, 3),
                        "confidence": round(rec.confidence, 3),
                        "match_reasons": rec.match_reasons
                    }
                    for rec in filtered_recommendations[:limit]
                ],
                "total_recommendations": len(filtered_recommendations)
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"一括推奨取得エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"一括推奨の取得に失敗しました: {str(e)}"}), 500

@app.route('/api/v1/analyze/<article_id>', methods=['GET'])
def analyze_recommendations(article_id: str):
    """
    推奨品質の分析
    
    Args:
        article_id (str): 記事ID
    
    Returns:
        JSON: 分析結果
    """
    if not recommendation_engine:
        return jsonify({"error": "推奨エンジンが初期化されていません"}), 500
    
    try:
        # 分析の実行
        analysis = recommendation_engine.analyze_recommendation_quality(article_id)
        
        # レスポンスの構築
        response = {
            "article_id": article_id,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"分析エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"分析に失敗しました: {str(e)}"}), 500

@app.route('/api/v1/data/refresh', methods=['POST'])
def refresh_data():
    """
    データの更新
    
    Request Body:
        {
            "articles_file": "path/to/articles.xlsx",
            "products_file": "path/to/products.xlsx",
            "load_gsc": true
        }
    
    Returns:
        JSON: 更新結果
    """
    if not data_processor:
        return jsonify({"error": "データプロセッサーが初期化されていません"}), 500
    
    try:
        # リクエストボディの取得
        data = request.get_json() or {}
        
        articles_file = data.get('articles_file')
        products_file = data.get('products_file')
        load_gsc = data.get('load_gsc', True)
        
        # データの処理
        result = data_processor.process_all_data(
            articles_file=articles_file,
            products_file=products_file,
            load_gsc=load_gsc
        )
        
        # 推奨エンジンの再初期化
        if result.get('success'):
            global recommendation_engine
            recommendation_engine = ProductRecommendationEngine()
            
            articles_list = list(data_processor.articles_data.values())
            products_list = list(data_processor.products_data.values())
            
            recommendation_engine.load_article_data(articles_list)
            recommendation_engine.load_product_data(products_list)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"データ更新エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"データの更新に失敗しました: {str(e)}"}), 500

@app.route('/api/v1/data/summary', methods=['GET'])
def get_data_summary():
    """
    データサマリーの取得
    
    Returns:
        JSON: データサマリー
    """
    if not data_processor:
        return jsonify({"error": "データプロセッサーが初期化されていません"}), 500
    
    try:
        summary = data_processor.get_data_summary()
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"サマリー取得エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"サマリーの取得に失敗しました: {str(e)}"}), 500

@app.route('/api/v1/articles', methods=['GET'])
def list_articles():
    """
    記事一覧の取得
    
    Query Parameters:
        limit (int): 取得件数の上限
        offset (int): オフセット
    
    Returns:
        JSON: 記事一覧
    """
    if not data_processor:
        return jsonify({"error": "データプロセッサーが初期化されていません"}), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        articles = list(data_processor.articles_data.values())
        
        # ページネーション
        paginated_articles = articles[offset:offset + limit]
        
        response = {
            "articles": [
                {
                    "article_id": article["article_id"],
                    "title": article["title"],
                    "persona": article["persona"],
                    "scene": article["scene"],
                    "target_keywords": article["target_keywords"][:5],  # 最初の5個のみ
                    "budget_range": article["budget_range"]
                }
                for article in paginated_articles
            ],
            "total_count": len(articles),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(articles)
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"記事一覧取得エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"記事一覧の取得に失敗しました: {str(e)}"}), 500

@app.route('/api/v1/products', methods=['GET'])
def list_products():
    """
    商品一覧の取得
    
    Query Parameters:
        category (str): カテゴリフィルタ
        limit (int): 取得件数の上限
        offset (int): オフセット
    
    Returns:
        JSON: 商品一覧
    """
    if not data_processor:
        return jsonify({"error": "データプロセッサーが初期化されていません"}), 500
    
    try:
        category = request.args.get('category')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        products = list(data_processor.products_data.values())
        
        # カテゴリフィルタリング
        if category:
            products = [p for p in products if p.get('category') == category]
        
        # ページネーション
        paginated_products = products[offset:offset + limit]
        
        response = {
            "products": [
                {
                    "product_id": product["product_id"],
                    "name": product["name"],
                    "category": product["category"],
                    "price": product["price"],
                    "popularity_score": product["popularity_score"],
                    "conversion_rate": product["conversion_rate"]
                }
                for product in paginated_products
            ],
            "total_count": len(products),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(products)
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"商品一覧取得エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"商品一覧の取得に失敗しました: {str(e)}"}), 500

@app.errorhandler(404)
def not_found(error):
    """404エラーハンドラー"""
    return jsonify({"error": "エンドポイントが見つかりません"}), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラー"""
    return jsonify({"error": "内部サーバーエラーが発生しました"}), 500

def create_app():
    """アプリケーションの作成と設定"""
    # サービスの初期化
    if not initialize_services():
        logger.error("サービス初期化に失敗しました")
        return None
    
    return app

if __name__ == '__main__':
    # アプリケーションの作成
    app = create_app()
    
    if app:
        # サーバーの起動
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        logger.info(f"商品推奨APIを起動します (ポート: {port}, デバッグ: {debug})")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug
        )
    else:
        logger.error("アプリケーションの起動に失敗しました")










