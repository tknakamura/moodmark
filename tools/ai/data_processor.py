#!/usr/bin/env python3
"""
データ処理モジュール

スプレッドシート（記事キーワード・ペルソナ、商品データ）とGSCデータを統合し、
商品推奨エンジンで使用できる形式に変換する
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

# 既存のGoogle APIs統合システムをインポート
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'analytics'))
from google_apis_integration import GoogleAPIsIntegration

logger = logging.getLogger(__name__)

class DataProcessor:
    """データ処理クラス"""
    
    def __init__(self, config_file: str = None):
        """
        初期化
        
        Args:
            config_file (str): 設定ファイルのパス
        """
        self.config = self._load_config(config_file)
        self.google_apis = GoogleAPIsIntegration()
        
        # データストレージ
        self.articles_data = {}
        self.products_data = {}
        self.gsc_data = {}
        
        logger.info("データプロセッサーを初期化しました")
    
    def _load_config(self, config_file: str) -> Dict:
        """設定ファイルの読み込み"""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルト設定
        return {
            "data_sources": {
                "articles_spreadsheet": "data/articles_data.xlsx",
                "products_spreadsheet": "data/products_data.xlsx",
                "gsc_data_file": "data/gsc_data.csv"
            },
            "data_processing": {
                "date_range_days": 90,
                "min_clicks_threshold": 10,
                "min_impressions_threshold": 100
            },
            "output": {
                "processed_articles_file": "data/processed/articles.json",
                "processed_products_file": "data/processed/products.json"
            }
        }
    
    def load_articles_from_spreadsheet(self, file_path: str) -> Dict:
        """
        スプレッドシートから記事データを読み込み
        
        Args:
            file_path (str): スプレッドシートファイルのパス
            
        Returns:
            Dict: 記事データの辞書
        """
        try:
            # Excelファイルの読み込み
            df = pd.read_excel(file_path)
            
            articles = {}
            
            for _, row in df.iterrows():
                article_id = str(row.get('article_id', f"article_{len(articles) + 1}"))
                
                # キーワードの処理
                target_keywords = self._parse_keywords(row.get('target_keywords', ''))
                seasonal_keywords = self._parse_keywords(row.get('seasonal_keywords', ''))
                
                # 予算範囲の処理
                budget_range = self._parse_budget_range(row.get('budget_range', ''))
                
                article_data = {
                    "article_id": article_id,
                    "title": str(row.get('title', '')),
                    "content": str(row.get('content', '')),
                    "target_keywords": target_keywords,
                    "persona": str(row.get('persona', '')),
                    "scene": str(row.get('scene', '')),
                    "target_audience": str(row.get('target_audience', '')),
                    "budget_range": budget_range,
                    "seasonal_keywords": seasonal_keywords,
                    "category": str(row.get('category', '')),
                    "priority": str(row.get('priority', 'medium')),
                    "created_date": row.get('created_date', datetime.now()),
                    "gsc_data": {}  # 後でGSCデータと統合
                }
                
                articles[article_id] = article_data
            
            self.articles_data = articles
            logger.info(f"{len(articles)}件の記事データを読み込みました")
            
            return articles
            
        except Exception as e:
            logger.error(f"記事データの読み込みエラー: {e}")
            return {}
    
    def load_products_from_spreadsheet(self, file_path: str) -> Dict:
        """
        スプレッドシートから商品データを読み込み
        
        Args:
            file_path (str): スプレッドシートファイルのパス
            
        Returns:
            Dict: 商品データの辞書
        """
        try:
            # Excelファイルの読み込み
            df = pd.read_excel(file_path)
            
            products = {}
            
            for _, row in df.iterrows():
                product_id = str(row.get('product_id', f"product_{len(products) + 1}"))
                
                # タグとターゲットオーディエンスの処理
                tags = self._parse_keywords(row.get('tags', ''))
                target_audience = self._parse_keywords(row.get('target_audience', ''))
                seasonal_suitability = self._parse_keywords(row.get('seasonal_suitability', ''))
                scene_suitability = self._parse_keywords(row.get('scene_suitability', ''))
                
                product_data = {
                    "product_id": product_id,
                    "name": str(row.get('name', '')),
                    "category": str(row.get('category', '')),
                    "subcategory": str(row.get('subcategory', '')),
                    "description": str(row.get('description', '')),
                    "price": int(row.get('price', 0)),
                    "tags": tags,
                    "target_audience": target_audience,
                    "seasonal_suitability": seasonal_suitability,
                    "scene_suitability": scene_suitability,
                    "popularity_score": float(row.get('popularity_score', 50.0)),
                    "conversion_rate": float(row.get('conversion_rate', 5.0)),
                    "stock_status": str(row.get('stock_status', 'available')),
                    "brand": str(row.get('brand', '')),
                    "image_url": str(row.get('image_url', '')),
                    "product_url": str(row.get('product_url', ''))
                }
                
                products[product_id] = product_data
            
            self.products_data = products
            logger.info(f"{len(products)}件の商品データを読み込みました")
            
            return products
            
        except Exception as e:
            logger.error(f"商品データの読み込みエラー: {e}")
            return {}
    
    def load_gsc_data(self, date_range_days: int = None) -> Dict:
        """
        Google Search Consoleからデータを取得・読み込み
        
        Args:
            date_range_days (int): 取得する日数
            
        Returns:
            Dict: GSCデータ
        """
        try:
            date_range_days = date_range_days or self.config['data_processing']['date_range_days']
            
            # GSCデータの取得
            gsc_pages = self.google_apis.get_top_pages_gsc(
                date_range_days=date_range_days,
                limit=1000
            )
            
            gsc_queries = self.google_apis.get_top_queries_gsc(
                date_range_days=date_range_days,
                limit=1000
            )
            
            # データの構造化
            gsc_data = {
                "pages": gsc_pages.to_dict('records') if not gsc_pages.empty else [],
                "queries": gsc_queries.to_dict('records') if not gsc_queries.empty else [],
                "last_updated": datetime.now().isoformat()
            }
            
            self.gsc_data = gsc_data
            logger.info(f"GSCデータを取得しました: ページ {len(gsc_data['pages'])}件, クエリ {len(gsc_data['queries'])}件")
            
            return gsc_data
            
        except Exception as e:
            logger.error(f"GSCデータの取得エラー: {e}")
            return {}
    
    def integrate_gsc_with_articles(self) -> Dict:
        """
        GSCデータを記事データと統合
        
        Returns:
            Dict: GSCデータが統合された記事データ
        """
        if not self.gsc_data or not self.articles_data:
            logger.warning("GSCデータまたは記事データが不足しています")
            return self.articles_data
        
        integrated_articles = self.articles_data.copy()
        
        # 各記事に対してGSCデータをマッチング
        for article_id, article_data in integrated_articles.items():
            gsc_data_for_article = self._match_gsc_data_to_article(article_data)
            article_data['gsc_data'] = gsc_data_for_article
        
        logger.info("GSCデータを記事データと統合しました")
        
        return integrated_articles
    
    def _match_gsc_data_to_article(self, article_data: Dict) -> Dict:
        """
        記事にGSCデータをマッチング
        
        Args:
            article_data (Dict): 記事データ
            
        Returns:
            Dict: マッチングされたGSCデータ
        """
        article_url = article_data.get('article_url', '')
        article_keywords = article_data.get('target_keywords', [])
        
        matched_data = {
            "top_queries": [],
            "top_pages": [],
            "total_clicks": 0,
            "total_impressions": 0,
            "avg_position": 0.0,
            "ctr": 0.0
        }
        
        # ページデータのマッチング
        for page_data in self.gsc_data.get('pages', []):
            if article_url in page_data.get('page', ''):
                matched_data['top_pages'].append(page_data)
                matched_data['total_clicks'] += page_data.get('clicks', 0)
                matched_data['total_impressions'] += page_data.get('impressions', 0)
        
        # クエリデータのマッチング
        for query_data in self.gsc_data.get('queries', []):
            query = query_data.get('query', '').lower()
            
            # キーワードマッチング
            if any(keyword.lower() in query for keyword in article_keywords):
                matched_data['top_queries'].append(query_data)
        
        # 平均値の計算
        if matched_data['top_queries']:
            positions = [q.get('position', 0) for q in matched_data['top_queries']]
            matched_data['avg_position'] = sum(positions) / len(positions)
            
            clicks = sum(q.get('clicks', 0) for q in matched_data['top_queries'])
            impressions = sum(q.get('impressions', 0) for q in matched_data['top_queries'])
            
            if impressions > 0:
                matched_data['ctr'] = (clicks / impressions) * 100
        
        return matched_data
    
    def _parse_keywords(self, keywords_str: str) -> List[str]:
        """キーワード文字列をリストに変換"""
        if not keywords_str or pd.isna(keywords_str):
            return []
        
        # カンマ、セミコロン、改行で分割
        keywords = []
        for delimiter in [',', ';', '\n']:
            if delimiter in str(keywords_str):
                keywords = str(keywords_str).split(delimiter)
                break
        else:
            keywords = [str(keywords_str)]
        
        # 空白を除去し、空文字列を除外
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        
        return keywords
    
    def _parse_budget_range(self, budget_str: str) -> Tuple[int, int]:
        """予算範囲文字列をタプルに変換"""
        if not budget_str or pd.isna(budget_str):
            return (1000, 50000)  # デフォルト範囲
        
        budget_str = str(budget_str)
        
        # 範囲の形式を解析（例: "3000-15000", "3000〜15000", "3000-15000円"）
        import re
        
        # 数値を抽出
        numbers = re.findall(r'\d+', budget_str)
        
        if len(numbers) >= 2:
            return (int(numbers[0]), int(numbers[1]))
        elif len(numbers) == 1:
            # 単一の値の場合、±50%の範囲を設定
            value = int(numbers[0])
            return (int(value * 0.5), int(value * 1.5))
        else:
            return (1000, 50000)  # デフォルト範囲
    
    def save_processed_data(self, output_dir: str = None) -> Dict[str, str]:
        """
        処理済みデータを保存
        
        Args:
            output_dir (str): 出力ディレクトリ
            
        Returns:
            Dict[str, str]: 保存されたファイルのパス
        """
        output_dir = output_dir or self.config['output'].get('output_dir', 'data/processed')
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # 記事データの保存
        if self.articles_data:
            articles_file = os.path.join(output_dir, 'articles.json')
            with open(articles_file, 'w', encoding='utf-8') as f:
                json.dump(self.articles_data, f, ensure_ascii=False, indent=2, default=str)
            saved_files['articles'] = articles_file
        
        # 商品データの保存
        if self.products_data:
            products_file = os.path.join(output_dir, 'products.json')
            with open(products_file, 'w', encoding='utf-8') as f:
                json.dump(self.products_data, f, ensure_ascii=False, indent=2, default=str)
            saved_files['products'] = products_file
        
        # GSCデータの保存
        if self.gsc_data:
            gsc_file = os.path.join(output_dir, 'gsc_data.json')
            with open(gsc_file, 'w', encoding='utf-8') as f:
                json.dump(self.gsc_data, f, ensure_ascii=False, indent=2, default=str)
            saved_files['gsc'] = gsc_file
        
        logger.info(f"処理済みデータを保存しました: {saved_files}")
        
        return saved_files
    
    def load_processed_data(self, data_dir: str = None) -> bool:
        """
        処理済みデータを読み込み
        
        Args:
            data_dir (str): データディレクトリ
            
        Returns:
            bool: 読み込み成功フラグ
        """
        data_dir = data_dir or self.config['output'].get('output_dir', 'data/processed')
        
        success = True
        
        # 記事データの読み込み
        articles_file = os.path.join(data_dir, 'articles.json')
        if os.path.exists(articles_file):
            try:
                with open(articles_file, 'r', encoding='utf-8') as f:
                    self.articles_data = json.load(f)
                logger.info(f"記事データを読み込みました: {len(self.articles_data)}件")
            except Exception as e:
                logger.error(f"記事データの読み込みエラー: {e}")
                success = False
        
        # 商品データの読み込み
        products_file = os.path.join(data_dir, 'products.json')
        if os.path.exists(products_file):
            try:
                with open(products_file, 'r', encoding='utf-8') as f:
                    self.products_data = json.load(f)
                logger.info(f"商品データを読み込みました: {len(self.products_data)}件")
            except Exception as e:
                logger.error(f"商品データの読み込みエラー: {e}")
                success = False
        
        # GSCデータの読み込み
        gsc_file = os.path.join(data_dir, 'gsc_data.json')
        if os.path.exists(gsc_file):
            try:
                with open(gsc_file, 'r', encoding='utf-8') as f:
                    self.gsc_data = json.load(f)
                logger.info("GSCデータを読み込みました")
            except Exception as e:
                logger.error(f"GSCデータの読み込みエラー: {e}")
                success = False
        
        return success
    
    def get_data_summary(self) -> Dict:
        """データのサマリーを取得"""
        summary = {
            "articles_count": len(self.articles_data),
            "products_count": len(self.products_data),
            "gsc_data_available": bool(self.gsc_data),
            "last_updated": datetime.now().isoformat()
        }
        
        if self.gsc_data:
            summary.update({
                "gsc_pages_count": len(self.gsc_data.get('pages', [])),
                "gsc_queries_count": len(self.gsc_data.get('queries', [])),
                "gsc_last_updated": self.gsc_data.get('last_updated', '')
            })
        
        return summary
    
    def process_all_data(self, 
                        articles_file: str = None, 
                        products_file: str = None,
                        load_gsc: bool = True) -> Dict:
        """
        全データの処理を実行
        
        Args:
            articles_file (str): 記事スプレッドシートファイル
            products_file (str): 商品スプレッドシートファイル
            load_gsc (bool): GSCデータの取得フラグ
            
        Returns:
            Dict: 処理結果
        """
        logger.info("全データの処理を開始します")
        
        # 記事データの処理
        if articles_file:
            self.load_articles_from_spreadsheet(articles_file)
        
        # 商品データの処理
        if products_file:
            self.load_products_from_spreadsheet(products_file)
        
        # GSCデータの処理
        if load_gsc:
            self.load_gsc_data()
            self.integrate_gsc_with_articles()
        
        # 処理済みデータの保存
        saved_files = self.save_processed_data()
        
        # サマリーの生成
        summary = self.get_data_summary()
        
        result = {
            "success": True,
            "summary": summary,
            "saved_files": saved_files,
            "message": "全データの処理が完了しました"
        }
        
        logger.info("全データの処理が完了しました")
        
        return result

# 使用例
if __name__ == "__main__":
    # データプロセッサーの初期化
    processor = DataProcessor()
    
    # 全データの処理
    result = processor.process_all_data(
        articles_file="data/articles_data.xlsx",
        products_file="data/products_data.xlsx",
        load_gsc=True
    )
    
    print("処理結果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
