#!/usr/bin/env python3
"""
MOO:D MARK IDEA 商品推奨システム デモスクリプト

実際のデータを使用せずに、システムの動作をデモンストレーションするスクリプト
"""

import json
import sys
import os
from datetime import datetime

# 相対インポート
from product_recommendation_engine import ProductRecommendationEngine
from data_processor import DataProcessor

def create_sample_data():
    """サンプルデータの作成"""
    
    # サンプル記事データ
    sample_articles = [
        {
            "article_id": "article_001",
            "title": "彼氏への誕生日プレゼント30選 | 2024年最新版",
            "content": "彼氏への誕生日プレゼントで迷ったら必見！予算別・シーン別のおすすめギフトを紹介。20代・30代の男性が喜ぶプレゼントを厳選しました。",
            "target_keywords": ["彼氏", "誕生日プレゼント", "男性ギフト", "20代男性", "30代男性"],
            "persona": "20代女性",
            "scene": "誕生日,デート,記念日",
            "target_audience": "20代女性",
            "budget_range": [3000, 15000],
            "seasonal_keywords": ["春", "新生活"],
            "gsc_data": {
                "top_queries": ["彼氏 誕生日 プレゼント", "男性 ギフト おすすめ", "恋人 プレゼント アイデア"]
            }
        },
        {
            "article_id": "article_002",
            "title": "クリスマスギフト完全ガイド | 予算別おすすめ商品",
            "content": "クリスマスギフト選びの決定版！予算別・相手別のおすすめ商品を紹介。家族、恋人、友人へのプレゼント選びに役立つ情報満載です。",
            "target_keywords": ["クリスマスギフト", "クリスマスプレゼント", "冬のギフト", "家族", "恋人"],
            "persona": "20-30代男女",
            "scene": "クリスマス,年末,冬のギフト",
            "target_audience": "20代,30代",
            "budget_range": [2000, 20000],
            "seasonal_keywords": ["冬", "クリスマス", "年末"],
            "gsc_data": {
                "top_queries": ["クリスマス ギフト", "クリスマス プレゼント おすすめ", "冬 ギフト"]
            }
        },
        {
            "article_id": "article_003",
            "title": "母の日ギフト特集 | 感謝を込めた贈り物",
            "content": "母の日にお母さんに贈りたいギフトを厳選。毎年使える定番商品から、今年話題の新商品まで幅広く紹介します。",
            "target_keywords": ["母の日", "お母さん", "ギフト", "感謝", "5月"],
            "persona": "全年齢",
            "scene": "母の日,感謝,5月",
            "target_audience": "全年齢",
            "budget_range": [1000, 10000],
            "seasonal_keywords": ["春", "5月", "母の日"],
            "gsc_data": {
                "top_queries": ["母の日 ギフト", "お母さん プレゼント", "母の日 おすすめ"]
            }
        }
    ]
    
    # サンプル商品データ
    sample_products = [
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
            "conversion_rate": 12.5
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
            "conversion_rate": 18.7
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
            "conversion_rate": 15.2
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
            "conversion_rate": 8.9
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
            "conversion_rate": 11.3
        }
    ]
    
    return sample_articles, sample_products

def run_demo():
    """デモの実行"""
    print("=" * 60)
    print("MOO:D MARK IDEA 商品推奨システム デモ")
    print("=" * 60)
    print()
    
    # サンプルデータの作成
    print("📊 サンプルデータの準備中...")
    articles, products = create_sample_data()
    print(f"✅ 記事データ: {len(articles)}件")
    print(f"✅ 商品データ: {len(products)}件")
    print()
    
    # 推奨エンジンの初期化
    print("🤖 推奨エンジンの初期化中...")
    engine = ProductRecommendationEngine()
    engine.load_article_data(articles)
    engine.load_product_data(products)
    print("✅ 推奨エンジンの初期化完了")
    print()
    
    # 各記事に対する推奨の実行
    print("🎯 商品推奨の実行...")
    print("-" * 40)
    
    for article in articles:
        article_id = article["article_id"]
        title = article["title"]
        
        print(f"\n📝 記事: {title}")
        print(f"   ID: {article_id}")
        print(f"   ターゲットキーワード: {', '.join(article['target_keywords'])}")
        print(f"   ペルソナ: {article['persona']}")
        print(f"   予算範囲: ¥{article['budget_range'][0]:,} - ¥{article['budget_range'][1]:,}")
        
        # 推奨の取得
        recommendations = engine.get_recommendations(article_id, limit=3)
        
        if recommendations:
            print("\n   🎁 推奨商品:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec.product_name}")
                print(f"      スコア: {rec.match_score:.3f}")
                print(f"      信頼度: {rec.confidence:.3f}")
                print(f"      理由: {', '.join(rec.match_reasons)}")
                print()
        else:
            print("   ❌ 推奨商品が見つかりませんでした")
        
        print("-" * 40)
    
    # 推奨品質の分析
    print("\n📈 推奨品質の分析...")
    sample_article_id = articles[0]["article_id"]
    analysis = engine.analyze_recommendation_quality(sample_article_id)
    
    print(f"記事ID: {sample_article_id}")
    print(f"総推奨数: {analysis['total_recommendations']}")
    print(f"平均スコア: {analysis['average_score']:.3f}")
    print(f"最高スコア: {analysis['max_score']:.3f}")
    print(f"高信頼度推奨数: {analysis['high_confidence_count']}")
    
    print("\n" + "=" * 60)
    print("🎉 デモ完了!")
    print("=" * 60)
    
    # 次のステップの案内
    print("\n📋 次のステップ:")
    print("1. 実際のデータでのテスト実行")
    print("2. APIサーバーの起動")
    print("3. フロントエンドとの統合")
    print("4. 本格運用の開始")
    
    print(f"\n📚 詳細情報:")
    print("- 使用ガイド: docs/ai/product_recommendation_system_guide.md")
    print("- API仕様: tools/ai/recommendation_api.py")
    print("- テストフレームワーク: tools/ai/recommendation_tester.py")

def main():
    """メイン関数"""
    try:
        run_demo()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        print("詳細なエラー情報:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
