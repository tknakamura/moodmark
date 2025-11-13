#!/usr/bin/env python3
"""
MOO:D MARK IDEA 商品推奨ダッシュボード（サンプル版）

ダミーデータを使用した見本ダッシュボード
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime
from typing import Dict, List
import random

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flaskアプリケーションの初期化
app = Flask(__name__)
CORS(app)

# サンプル商品データ
SAMPLE_PRODUCTS = [
    {
        "product_id": "product_001",
        "name": "高級革財布 ブラック",
        "category": "ファッション",
        "subcategory": "革製品",
        "description": "職人が手作りした本革の財布。長く使える高品質なアイテムで、ビジネスシーンでも活躍します。",
        "price": 8000,
        "tags": ["革", "財布", "高級", "男性", "ビジネス"],
        "target_audience": ["20代男性", "30代男性"],
        "seasonal_suitability": ["春", "秋"],
        "scene_suitability": ["誕生日", "記念日", "昇進祝い"],
        "popularity_score": 85.0,
        "conversion_rate": 12.5,
        "image_url": "https://via.placeholder.com/300x300?text=革財布"
    },
    {
        "product_id": "product_002",
        "name": "クリスマス限定 スイーツギフトセット",
        "category": "食品",
        "subcategory": "スイーツ",
        "description": "クリスマス限定の特別なスイーツギフトセット。家族みんなで楽しめる豊富な種類のスイーツが入っています。",
        "price": 3500,
        "tags": ["スイーツ", "クリスマス", "限定", "家族", "冬"],
        "target_audience": ["全年齢", "家族"],
        "seasonal_suitability": ["冬"],
        "scene_suitability": ["クリスマス", "年末", "家族"],
        "popularity_score": 92.0,
        "conversion_rate": 18.7,
        "image_url": "https://via.placeholder.com/300x300?text=スイーツセット"
    },
    {
        "product_id": "product_003",
        "name": "母の日特別 花束アレンジメント",
        "category": "花・植物",
        "subcategory": "花束",
        "description": "母の日にぴったりの美しい花束アレンジメント。感謝の気持ちを込めて選んだ季節の花々で構成されています。",
        "price": 4500,
        "tags": ["花束", "母の日", "感謝", "春", "アレンジメント"],
        "target_audience": ["全年齢"],
        "seasonal_suitability": ["春"],
        "scene_suitability": ["母の日", "感謝", "記念日"],
        "popularity_score": 88.0,
        "conversion_rate": 15.2,
        "image_url": "https://via.placeholder.com/300x300?text=花束"
    },
    {
        "product_id": "product_004",
        "name": "高級腕時計 シンプルデザイン",
        "category": "アクセサリー",
        "subcategory": "腕時計",
        "description": "シンプルで上品なデザインの高級腕時計。どんなシーンでも使える汎用性の高いアイテムです。",
        "price": 25000,
        "tags": ["腕時計", "高級", "シンプル", "男性", "ビジネス"],
        "target_audience": ["30代男性", "40代男性"],
        "seasonal_suitability": ["全年"],
        "scene_suitability": ["誕生日", "記念日", "昇進祝い", "退職祝い"],
        "popularity_score": 75.0,
        "conversion_rate": 8.9,
        "image_url": "https://via.placeholder.com/300x300?text=腕時計"
    },
    {
        "product_id": "product_005",
        "name": "季節のフルーツギフト",
        "category": "食品",
        "subcategory": "フルーツ",
        "description": "旬の美味しいフルーツを厳選したギフト。季節感あふれる新鮮なフルーツで特別な日をお祝いします。",
        "price": 2800,
        "tags": ["フルーツ", "季節", "新鮮", "健康", "ギフト"],
        "target_audience": ["全年齢"],
        "seasonal_suitability": ["春", "夏", "秋", "冬"],
        "scene_suitability": ["誕生日", "お見舞い", "感謝", "季節の挨拶"],
        "popularity_score": 78.0,
        "conversion_rate": 11.3,
        "image_url": "https://via.placeholder.com/300x300?text=フルーツギフト"
    },
    {
        "product_id": "product_006",
        "name": "プレミアム コーヒーギフトセット",
        "category": "食品",
        "subcategory": "飲料",
        "description": "厳選されたコーヒー豆を使用したプレミアムコーヒーギフトセット。コーヒー好きの方に喜ばれる特別なセットです。",
        "price": 5500,
        "tags": ["コーヒー", "プレミアム", "ギフト", "飲料", "大人"],
        "target_audience": ["30代以上"],
        "seasonal_suitability": ["全年"],
        "scene_suitability": ["誕生日", "記念日", "感謝", "ビジネス"],
        "popularity_score": 82.0,
        "conversion_rate": 14.1,
        "image_url": "https://via.placeholder.com/300x300?text=コーヒーセット"
    },
    {
        "product_id": "product_007",
        "name": "可愛い ハンドクリームセット",
        "category": "コスメ",
        "subcategory": "スキンケア",
        "description": "保湿効果抜群の可愛いハンドクリームセット。日常使いからギフトまで幅広く活用できるアイテムです。",
        "price": 3200,
        "tags": ["ハンドクリーム", "スキンケア", "可愛い", "保湿", "ギフト"],
        "target_audience": ["20代女性", "30代女性"],
        "seasonal_suitability": ["秋", "冬"],
        "scene_suitability": ["誕生日", "感謝", "日常", "季節の挨拶"],
        "popularity_score": 90.0,
        "conversion_rate": 16.8,
        "image_url": "https://via.placeholder.com/300x300?text=ハンドクリーム"
    },
    {
        "product_id": "product_008",
        "name": "上質な 紅茶ギフトボックス",
        "category": "食品",
        "subcategory": "飲料",
        "description": "世界各地から厳選した上質な紅茶のギフトボックス。ティータイムを特別なものにする逸品です。",
        "price": 4200,
        "tags": ["紅茶", "上質", "ギフト", "飲料", "大人"],
        "target_audience": ["30代以上", "女性"],
        "seasonal_suitability": ["秋", "冬"],
        "scene_suitability": ["誕生日", "感謝", "季節の挨拶", "お見舞い"],
        "popularity_score": 76.0,
        "conversion_rate": 13.2,
        "image_url": "https://via.placeholder.com/300x300?text=紅茶ギフト"
    }
]

def generate_catch_copy(product_data: Dict, keywords: List[str], persona: str, scene: str) -> str:
    """キャッチコピーの生成"""
    product_name = product_data['name']
    price = product_data['price']
    category = product_data['category']
    
    # キーワードからシーンを推測
    if any(kw in keywords for kw in ['誕生日', 'バースデー']):
        scene = '誕生日'
    elif any(kw in keywords for kw in ['クリスマス']):
        scene = 'クリスマス'
    elif any(kw in keywords for kw in ['母の日']):
        scene = '母の日'
    elif any(kw in keywords for kw in ['父の日']):
        scene = '父の日'
    elif any(kw in keywords for kw in ['感謝', 'お礼']):
        scene = '感謝'
    else:
        scene = 'ギフト'
    
    # シーン別キャッチコピーテンプレート
    templates = {
        '誕生日': f"【{persona}必見】{product_name}で特別な誕生日を！¥{price:,}で実現する素敵なプレゼント",
        'クリスマス': f"【クリスマス限定】{product_name}で最高のクリスマスを！{persona}にぴったりの¥{price:,}ギフト",
        '母の日': f"【母の日特集】{product_name}で感謝を伝える¥{price:,}の贈り物",
        '父の日': f"【父の日おすすめ】{product_name}で父親に感謝を¥{price:,}の特別なギフト",
        '感謝': f"【感謝の気持ち】{product_name}で気持ちを伝える¥{price:,}の素敵なギフト",
        'ギフト': f"【{persona}におすすめ】{product_name}で{scene}を特別に¥{price:,}の素敵なアイテム"
    }
    
    return templates.get(scene, templates['ギフト'])

def generate_body_copy(product_data: Dict, keywords: List[str], persona: str, scene: str) -> str:
    """ボディコピーの生成"""
    product_name = product_data['name']
    description = product_data['description']
    price = product_data['price']
    category = product_data['category']
    
    # キーワードからメリットを生成
    benefits = []
    for keyword in keywords[:3]:
        if 'プレゼント' in keyword or 'ギフト' in keyword:
            benefits.append('プレゼントに最適')
        elif '誕生日' in keyword:
            benefits.append('誕生日の特別な瞬間を演出')
        elif 'クリスマス' in keyword:
            benefits.append('クリスマスの思い出に')
        elif '感謝' in keyword:
            benefits.append('感謝の気持ちを込めて')
        elif '可愛い' in keyword or 'かわいい' in keyword:
            benefits.append('可愛いデザインで喜ばれる')
        elif '高級' in keyword:
            benefits.append('高級感のある逸品')
    
    if not benefits:
        benefits = ['特別なシーンに最適']
    
    benefits_text = '、'.join(benefits)
    
    # ボディコピーの構成
    body_parts = [
        f"{product_name}は、{description}",
        f"",
        f"【{persona}におすすめの理由】",
        f"• {benefits_text}",
        f"• {scene}にぴったりのアイテム",
        f"• ¥{price:,}の価格で高品質な商品",
        f"",
        f"【商品の特徴】",
        f"• 厳選された素材と丁寧な仕上げ",
        f"• 長く愛用できるデザイン",
        f"• ギフト包装にも対応可能",
        f"",
        f"{persona}の{scene}を特別なものにする{product_name}をお選びください。"
    ]
    
    return '\n'.join(body_parts)

def calculate_match_score(product_data: Dict, keywords: List[str], persona: str, scene: str) -> float:
    """マッチングスコアの計算（簡易版）"""
    score = 0.0
    
    # キーワードマッチング（40%）
    keyword_matches = 0
    for keyword in keywords:
        for tag in product_data['tags']:
            if keyword.lower() in tag.lower() or tag.lower() in keyword.lower():
                keyword_matches += 1
                break
    
    if keywords:
        score += (keyword_matches / len(keywords)) * 0.4
    
    # ペルソナマッチング（30%）
    if persona in product_data['target_audience']:
        score += 0.3
    elif '全年齢' in product_data['target_audience']:
        score += 0.2
    
    # シーンマッチング（20%）
    if any(kw in keywords for kw in ['誕生日', 'バースデー']):
        if '誕生日' in product_data['scene_suitability']:
            score += 0.2
    elif any(kw in keywords for kw in ['クリスマス']):
        if 'クリスマス' in product_data['scene_suitability']:
            score += 0.2
    elif any(kw in keywords for kw in ['母の日']):
        if '母の日' in product_data['scene_suitability']:
            score += 0.2
    elif any(kw in keywords for kw in ['感謝', 'お礼']):
        if '感謝' in product_data['scene_suitability']:
            score += 0.2
    else:
        score += 0.1  # デフォルトスコア
    
    # 人気度・コンバージョン率（10%）
    popularity_score = product_data['popularity_score'] / 100.0
    conversion_score = product_data['conversion_rate'] / 20.0  # 20%を最大とする
    score += (popularity_score + conversion_score) * 0.05
    
    # ランダム要素を追加（実際のシステムでは不要）
    score += random.uniform(0.0, 0.1)
    
    return min(score, 1.0)

@app.route('/')
def dashboard():
    """ダッシュボードのメインページ"""
    return render_template('sample_dashboard.html')

@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """商品推奨API（サンプル版）"""
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
        
        # キーワードからシーンを推測
        scene = 'ギフト'
        for keyword in target_keywords:
            if '誕生日' in keyword:
                scene = '誕生日'
                break
            elif 'クリスマス' in keyword:
                scene = 'クリスマス'
                break
            elif '母の日' in keyword:
                scene = '母の日'
                break
            elif '父の日' in keyword:
                scene = '父の日'
                break
            elif '感謝' in keyword:
                scene = '感謝'
                break
        
        # 各商品のスコアを計算
        product_scores = []
        for product in SAMPLE_PRODUCTS:
            match_score = calculate_match_score(product, target_keywords, persona, scene)
            confidence = min(match_score * 1.2, 1.0)
            
            if confidence >= 0.5:  # 最低信頼度フィルタ
                product_scores.append({
                    'product': product,
                    'match_score': match_score,
                    'confidence': confidence
                })
        
        # スコア順でソート
        product_scores.sort(key=lambda x: x['match_score'], reverse=True)
        
        # 推奨結果の構築
        results = []
        for i, item in enumerate(product_scores[:num_recommendations]):
            product = item['product']
            match_score = item['match_score']
            confidence = item['confidence']
            
            # 推奨理由の生成
            reasons = []
            if match_score > 0.7:
                reasons.append('キーワードの高一致')
            if persona in product['target_audience']:
                reasons.append('ペルソナの一致')
            if scene in product['scene_suitability']:
                reasons.append('シーンの適合性')
            if product['popularity_score'] > 80:
                reasons.append('人気商品')
            if product['conversion_rate'] > 15:
                reasons.append('高いコンバージョン率')
            
            if not reasons:
                reasons.append('おすすめ商品')
            
            # 最適化されたコピーを生成
            catch_copy = generate_catch_copy(product, target_keywords, persona, scene)
            body_copy = generate_body_copy(product, target_keywords, persona, scene)
            
            result = {
                "product_name": product['name'],
                "product_id": product['product_id'],
                "catch_copy": catch_copy,
                "body_copy": body_copy,
                "product_url": f"https://isetan.mistore.jp/moodmark/products/{product['product_id']}",
                "recommendation_reasons": reasons,
                "match_score": round(match_score, 3),
                "confidence": round(confidence, 3),
                "price": product['price'],
                "category": product['category'],
                "image_url": product['image_url']
            }
            results.append(result)
        
        return jsonify({
            "success": True,
            "recommendations": results,
            "total_count": len(results),
            "article_url": article_url,
            "target_keywords": target_keywords,
            "persona": persona,
            "scene": scene,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"推奨取得エラー: {e}")
        return jsonify({"error": f"推奨の取得に失敗しました: {str(e)}"}), 500

@app.route('/api/sample-data', methods=['GET'])
def get_sample_data():
    """サンプルデータの取得"""
    return jsonify({
        "sample_keywords": [
            "彼氏", "誕生日プレゼント", "男性ギフト", "20代男性",
            "クリスマスギフト", "家族", "恋人",
            "母の日", "お母さん", "感謝", "5月",
            "高級", "可愛い", "プレミアム"
        ],
        "sample_personas": [
            "20代女性", "30代女性", "20代男性", "30代男性",
            "40代女性", "40代男性", "全年齢", "ファミリー"
        ],
        "sample_urls": [
            "https://example.com/birthday-gifts-for-boyfriend",
            "https://example.com/christmas-gift-guide",
            "https://example.com/mothers-day-gifts",
            "https://example.com/valentines-gift-ideas"
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_initialized": True,
        "data_processor_initialized": True,
        "sample_mode": True,
        "products_count": len(SAMPLE_PRODUCTS)
    })

if __name__ == '__main__':
    # サーバーの起動
    port = int(os.getenv('PORT', 5002))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"商品推奨ダッシュボード（サンプル版）を起動します (ポート: {port}, デバッグ: {debug})")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
