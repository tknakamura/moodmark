#!/usr/bin/env python3
"""
MOO:D MARK IDEA 商品推奨ダッシュボード

記事URL、ターゲットキーワード、ペルソナを入力して最適な商品を提案するWebダッシュボード
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
import traceback

# 相対インポート
from product_recommendation_engine import ProductRecommendationEngine, ArticleData
from data_processor import DataProcessor

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリケーションの初期化
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'moodmark-dashboard-secret-key')

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
            
            articles_list = list(data_processor.articles_data.values())
            products_list = list(data_processor.products_data.values())
            
            recommendation_engine.load_article_data(articles_list)
            recommendation_engine.load_product_data(products_list)
            
            logger.info("サービス群の初期化が完了しました")
            return True
        else:
            logger.warning("処理済みデータが見つからないため、サンプルデータで初期化します")
            # サンプルデータでの初期化
            return initialize_with_sample_data()
            
    except Exception as e:
        logger.error(f"サービス初期化エラー: {e}")
        return initialize_with_sample_data()

def initialize_with_sample_data():
    """サンプルデータでの初期化"""
    global recommendation_engine, data_processor
    
    try:
        # サンプルデータの作成
        sample_articles = [
            {
                "article_id": "sample_001",
                "title": "サンプル記事",
                "content": "サンプル記事の内容",
                "target_keywords": ["サンプル", "キーワード"],
                "persona": "20代女性",
                "scene": "サンプルシーン",
                "target_audience": "20代女性",
                "budget_range": [3000, 15000],
                "seasonal_keywords": ["春"],
                "gsc_data": {}
            }
        ]
        
        sample_products = [
            {
                "product_id": "sample_product_001",
                "name": "サンプル商品1",
                "category": "ファッション",
                "subcategory": "アクセサリー",
                "description": "サンプル商品の説明",
                "price": 5000,
                "tags": ["サンプル", "アクセサリー"],
                "target_audience": ["20代女性"],
                "seasonal_suitability": ["春", "夏"],
                "scene_suitability": ["日常", "特別な日"],
                "popularity_score": 75.0,
                "conversion_rate": 10.0
            },
            {
                "product_id": "sample_product_002",
                "name": "サンプル商品2",
                "category": "食品",
                "subcategory": "スイーツ",
                "description": "サンプルスイーツの説明",
                "price": 3000,
                "tags": ["サンプル", "スイーツ"],
                "target_audience": ["全年齢"],
                "seasonal_suitability": ["春", "夏", "秋", "冬"],
                "scene_suitability": ["ギフト", "お祝い"],
                "popularity_score": 85.0,
                "conversion_rate": 15.0
            }
        ]
        
        # 推奨エンジンの初期化
        recommendation_engine = ProductRecommendationEngine()
        recommendation_engine.load_article_data(sample_articles)
        recommendation_engine.load_product_data(sample_products)
        
        logger.info("サンプルデータでサービスを初期化しました")
        return True
        
    except Exception as e:
        logger.error(f"サンプルデータ初期化エラー: {e}")
        return False

def generate_optimized_copy(product_data: Dict, article_keywords: List[str], persona: str, scene: str) -> Dict:
    """
    商品説明の記事最適化コピーを生成
    
    Args:
        product_data (Dict): 商品データ
        article_keywords (List[str]): 記事のキーワード
        persona (str): ペルソナ
        scene (str): シーン
        
    Returns:
        Dict: 最適化されたコピー
    """
    product_name = product_data.get('name', '')
    product_description = product_data.get('description', '')
    product_category = product_data.get('category', '')
    product_price = product_data.get('price', 0)
    
    # キャッチコピーの生成
    catch_copy = generate_catch_copy(product_name, product_category, persona, scene, product_price)
    
    # ボディコピーの生成
    body_copy = generate_body_copy(product_name, product_description, article_keywords, persona, scene, product_price)
    
    return {
        "catch_copy": catch_copy,
        "body_copy": body_copy
    }

def generate_catch_copy(product_name: str, category: str, persona: str, scene: str, price: int) -> str:
    """キャッチコピーの生成"""
    price_text = f"¥{price:,}" if price > 0 else ""
    
    # シーン別のキャッチコピーテンプレート
    scene_templates = {
        "誕生日": f"【{persona}必見】{product_name}で特別な誕生日を！{price_text}で実現する素敵なプレゼント",
        "クリスマス": f"【クリスマス限定】{product_name}で最高のクリスマスを！{persona}にぴったりの{price_text}ギフト",
        "母の日": f"【母の日特集】{product_name}で感謝を伝える{price_text}の贈り物",
        "父の日": f"【父の日おすすめ】{product_name}で父親に感謝を{price_text}の特別なギフト",
        "記念日": f"【記念日限定】{product_name}で大切な記念日を{price_text}で彩る特別な贈り物",
        "日常": f"【{persona}向け】{product_name}で日常を特別に{price_text}の素敵なアイテム"
    }
    
    # シーンに応じたキャッチコピー選択
    for scene_key, template in scene_templates.items():
        if scene_key in scene:
            return template
    
    # デフォルトキャッチコピー
    return f"【{persona}におすすめ】{product_name}で{scene}を特別に{price_text}の素敵なアイテム"

def generate_body_copy(product_name: str, description: str, keywords: List[str], persona: str, scene: str, price: int) -> str:
    """ボディコピーの生成"""
    
    # 基本情報
    price_text = f"¥{price:,}" if price > 0 else ""
    
    # キーワードを活用した説明
    keyword_benefits = []
    for keyword in keywords[:3]:  # 上位3つのキーワードを使用
        if "プレゼント" in keyword or "ギフト" in keyword:
            keyword_benefits.append("プレゼントに最適")
        elif "誕生日" in keyword:
            keyword_benefits.append("誕生日の特別な瞬間を演出")
        elif "クリスマス" in keyword:
            keyword_benefits.append("クリスマスの思い出に")
        elif "感謝" in keyword:
            keyword_benefits.append("感謝の気持ちを込めて")
    
    benefits_text = "、".join(keyword_benefits) if keyword_benefits else "特別なシーンに最適"
    
    # ボディコピーの構成
    body_parts = [
        f"{product_name}は、{description}",
        f"",
        f"【{persona}におすすめの理由】",
        f"• {benefits_text}",
        f"• {scene}にぴったりのアイテム",
        f"• {price_text}の価格で高品質な商品",
        f"",
        f"【商品の特徴】",
        f"• 厳選された素材と丁寧な仕上げ",
        f"• 長く愛用できるデザイン",
        f"• ギフト包装にも対応可能",
        f"",
        f"{persona}の{scene}を特別なものにする{product_name}をお選びください。"
    ]
    
    return "\n".join(body_parts)

@app.route('/')
def dashboard():
    """ダッシュボードのメインページ"""
    return render_template('dashboard.html')

@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """
    商品推奨API
    
    Request Body:
        {
            "article_url": "記事のURL",
            "target_keywords": ["キーワード1", "キーワード2"],
            "persona": "ペルソナ",
            "num_recommendations": 5
        }
    
    Returns:
        JSON: 推奨結果
    """
    if not recommendation_engine:
        return jsonify({"error": "推奨エンジンが初期化されていません"}), 500
    
    try:
        # リクエストデータの取得
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "リクエストデータがありません"}), 400
        
        article_url = data.get('article_url', '')
        target_keywords = data.get('target_keywords', [])
        persona = data.get('persona', '')
        num_recommendations = data.get('num_recommendations', 5)
        
        # バリデーション
        if not target_keywords:
            return jsonify({"error": "ターゲットキーワードが必要です"}), 400
        
        if not persona:
            return jsonify({"error": "ペルソナが必要です"}), 400
        
        # 動的記事データの作成
        article_id = f"dynamic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 記事URLからシーンを推測
        scene = extract_scene_from_url(article_url)
        
        # 予算範囲の設定（ペルソナベース）
        budget_range = get_budget_range_for_persona(persona)
        
        article_data = ArticleData(
            article_id=article_id,
            title=f"記事: {article_url}",
            content=f"URL: {article_url}",
            target_keywords=target_keywords,
            persona=persona,
            scene=scene,
            target_audience=persona,
            budget_range=budget_range,
            seasonal_keywords=get_seasonal_keywords(),
            gsc_data={"top_queries": target_keywords}
        )
        
        # 一時的に記事データを追加
        recommendation_engine.articles[article_id] = article_data
        
        # 推奨の取得
        recommendations = recommendation_engine.get_recommendations(article_id, num_recommendations)
        
        # 推奨結果の構築
        results = []
        for rec in recommendations:
            product_data = recommendation_engine.products.get(rec.product_id, {})
            
            # 最適化されたコピーを生成
            optimized_copy = generate_optimized_copy(
                product_data,
                target_keywords,
                persona,
                scene
            )
            
            result = {
                "product_name": rec.product_name,
                "product_id": rec.product_id,
                "catch_copy": optimized_copy["catch_copy"],
                "body_copy": optimized_copy["body_copy"],
                "product_url": f"https://isetan.mistore.jp/moodmark/products/{rec.product_id}",
                "recommendation_reasons": rec.match_reasons,
                "match_score": round(rec.match_score, 3),
                "confidence": round(rec.confidence, 3),
                "price": product_data.get('price', 0),
                "category": product_data.get('category', ''),
                "image_url": product_data.get('image_url', '')
            }
            results.append(result)
        
        # 一時的に追加した記事データを削除
        if article_id in recommendation_engine.articles:
            del recommendation_engine.articles[article_id]
        
        return jsonify({
            "success": True,
            "recommendations": results,
            "total_count": len(results),
            "article_url": article_url,
            "target_keywords": target_keywords,
            "persona": persona,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"推奨取得エラー: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"推奨の取得に失敗しました: {str(e)}"}), 500

def extract_scene_from_url(url: str) -> str:
    """URLからシーンを推測"""
    url_lower = url.lower()
    
    scene_keywords = {
        "誕生日": ["birthday", "誕生日", "バースデー"],
        "クリスマス": ["christmas", "クリスマス", "xmas"],
        "母の日": ["mother", "母の日", "mothers-day"],
        "父の日": ["father", "父の日", "fathers-day"],
        "バレンタイン": ["valentine", "バレンタイン", "valentines"],
        "ハロウィン": ["halloween", "ハロウィン"],
        "記念日": ["anniversary", "記念日", "記念"],
        "ギフト": ["gift", "ギフト", "プレゼント"],
        "日常": ["daily", "日常", "everyday"]
    }
    
    for scene, keywords in scene_keywords.items():
        if any(keyword in url_lower for keyword in keywords):
            return scene
    
    return "ギフト"  # デフォルト

def get_budget_range_for_persona(persona: str) -> tuple:
    """ペルソナに基づく予算範囲の取得"""
    persona_lower = persona.lower()
    
    if "高級" in persona_lower or "プレミアム" in persona_lower:
        return (10000, 50000)
    elif "20代" in persona_lower:
        return (2000, 10000)
    elif "30代" in persona_lower:
        return (3000, 15000)
    elif "40代" in persona_lower:
        return (5000, 25000)
    else:
        return (3000, 15000)  # デフォルト

def get_seasonal_keywords() -> List[str]:
    """現在の季節キーワードを取得"""
    month = datetime.now().month
    
    if month in [3, 4, 5]:
        return ["春", "桜", "新生活"]
    elif month in [6, 7, 8]:
        return ["夏", "暑中見舞い", "お中元"]
    elif month in [9, 10, 11]:
        return ["秋", "お歳暮", "ハロウィン"]
    else:
        return ["冬", "クリスマス", "年末"]

@app.route('/api/sample-data', methods=['GET'])
def get_sample_data():
    """サンプルデータの取得"""
    return jsonify({
        "sample_keywords": [
            "彼氏", "誕生日プレゼント", "男性ギフト", "20代男性",
            "クリスマスギフト", "家族", "恋人",
            "母の日", "お母さん", "感謝", "5月"
        ],
        "sample_personas": [
            "20代女性", "30代女性", "20代男性", "30代男性",
            "40代女性", "40代男性", "全年齢", "ファミリー"
        ],
        "sample_urls": [
            "https://example.com/birthday-gifts-for-boyfriend",
            "https://example.com/christmas-gift-guide",
            "https://example.com/mothers-day-gifts"
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_initialized": recommendation_engine is not None,
        "data_processor_initialized": data_processor is not None
    })

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
        port = int(os.getenv('PORT', 5001))
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        
        logger.info(f"商品推奨ダッシュボードを起動します (ポート: {port}, デバッグ: {debug})")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug
        )
    else:
        logger.error("アプリケーションの起動に失敗しました")
