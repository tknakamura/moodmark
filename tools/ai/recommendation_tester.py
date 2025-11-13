#!/usr/bin/env python3
"""
商品推奨システムのテストフレームワーク

推奨精度の評価、A/Bテスト、パフォーマンステストを実行
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import precision_score, recall_score, f1_score, ndcg_score
import time
import requests

from product_recommendation_engine import ProductRecommendationEngine, ArticleData, ProductData
from data_processor import DataProcessor

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """テスト結果のデータクラス"""
    test_name: str
    timestamp: str
    metrics: Dict
    recommendations: List[Dict]
    execution_time: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class GroundTruth:
    """正解データのデータクラス"""
    article_id: str
    relevant_products: List[str]
    irrelevant_products: List[str]
    user_feedback: Dict[str, float]  # product_id -> rating

class RecommendationTester:
    """推奨システムのテストクラス"""
    
    def __init__(self, config_file: str = None):
        """
        初期化
        
        Args:
            config_file (str): 設定ファイルのパス
        """
        self.config = self._load_config(config_file)
        self.engine = None
        self.data_processor = None
        self.ground_truth_data = {}
        self.test_results = []
        
        logger.info("推奨テストフレームワークを初期化しました")
    
    def _load_config(self, config_file: str) -> Dict:
        """設定ファイルの読み込み"""
        if config_file:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # デフォルト設定
        return {
            "test_settings": {
                "min_recommendations": 5,
                "max_recommendations": 20,
                "confidence_threshold": 0.6,
                "precision_at_k": [5, 10, 20],
                "ndcg_at_k": [5, 10, 20]
            },
            "performance_settings": {
                "max_execution_time": 5.0,  # 秒
                "memory_limit_mb": 1000
            },
            "output": {
                "results_dir": "test_results",
                "plots_dir": "test_plots"
            }
        }
    
    def initialize_engine(self, data_dir: str = None) -> bool:
        """
        推奨エンジンの初期化
        
        Args:
            data_dir (str): データディレクトリ
            
        Returns:
            bool: 初期化成功フラグ
        """
        try:
            # データプロセッサーの初期化
            self.data_processor = DataProcessor()
            
            # データの読み込み
            if self.data_processor.load_processed_data(data_dir):
                # 推奨エンジンの初期化
                self.engine = ProductRecommendationEngine()
                
                articles_list = list(self.data_processor.articles_data.values())
                products_list = list(self.data_processor.products_data.values())
                
                self.engine.load_article_data(articles_list)
                self.engine.load_product_data(products_list)
                
                logger.info("推奨エンジンの初期化が完了しました")
                return True
            else:
                logger.error("データの読み込みに失敗しました")
                return False
                
        except Exception as e:
            logger.error(f"エンジン初期化エラー: {e}")
            return False
    
    def load_ground_truth(self, ground_truth_file: str) -> bool:
        """
        正解データの読み込み
        
        Args:
            ground_truth_file (str): 正解データファイルのパス
            
        Returns:
            bool: 読み込み成功フラグ
        """
        try:
            with open(ground_truth_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                article_id = item['article_id']
                self.ground_truth_data[article_id] = GroundTruth(
                    article_id=article_id,
                    relevant_products=item['relevant_products'],
                    irrelevant_products=item['irrelevant_products'],
                    user_feedback=item.get('user_feedback', {})
                )
            
            logger.info(f"{len(self.ground_truth_data)}件の正解データを読み込みました")
            return True
            
        except Exception as e:
            logger.error(f"正解データ読み込みエラー: {e}")
            return False
    
    def generate_synthetic_ground_truth(self, sample_size: int = 50) -> bool:
        """
        合成正解データの生成（テスト用）
        
        Args:
            sample_size (int): サンプルサイズ
            
        Returns:
            bool: 生成成功フラグ
        """
        try:
            if not self.engine:
                logger.error("エンジンが初期化されていません")
                return False
            
            articles = list(self.engine.articles.keys())
            products = list(self.engine.products.keys())
            
            # ランダムサンプリング
            sample_articles = np.random.choice(articles, min(sample_size, len(articles)), replace=False)
            
            for article_id in sample_articles:
                # 記事の特徴に基づいて関連商品を生成
                article = self.engine.articles[article_id]
                
                # キーワードベースで関連商品を選択
                relevant_products = []
                for product_id, product in self.engine.products.items():
                    # 簡単なキーワードマッチング
                    if any(keyword in product.description.lower() 
                           for keyword in article.target_keywords):
                        relevant_products.append(product_id)
                
                # ランダムに不関連商品を選択
                irrelevant_products = np.random.choice(
                    [p for p in products if p not in relevant_products],
                    min(len(relevant_products), 10),
                    replace=False
                ).tolist()
                
                self.ground_truth_data[article_id] = GroundTruth(
                    article_id=article_id,
                    relevant_products=relevant_products[:5],  # 上位5件
                    irrelevant_products=irrelevant_products,
                    user_feedback={}
                )
            
            logger.info(f"{len(self.ground_truth_data)}件の合成正解データを生成しました")
            return True
            
        except Exception as e:
            logger.error(f"合成正解データ生成エラー: {e}")
            return False
    
    def test_precision_recall(self, k_values: List[int] = None) -> TestResult:
        """
        精度・再現率のテスト
        
        Args:
            k_values (List[int]): 評価するk値のリスト
            
        Returns:
            TestResult: テスト結果
        """
        if not self.engine or not self.ground_truth_data:
            return TestResult(
                test_name="precision_recall",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=0.0,
                success=False,
                error_message="エンジンまたは正解データが初期化されていません"
            )
        
        k_values = k_values or self.config['test_settings']['precision_at_k']
        start_time = time.time()
        
        try:
            metrics = {}
            all_precisions = {k: [] for k in k_values}
            all_recalls = {k: [] for k in k_values}
            all_f1s = {k: [] for k in k_values}
            
            for article_id, ground_truth in self.ground_truth_data.items():
                # 推奨の取得
                recommendations = self.engine.get_recommendations(article_id, max(k_values))
                recommended_products = [rec.product_id for rec in recommendations]
                
                # 各k値での評価
                for k in k_values:
                    top_k_products = recommended_products[:k]
                    
                    # 正解データとの比較
                    relevant_set = set(ground_truth.relevant_products)
                    recommended_set = set(top_k_products)
                    
                    # 精度・再現率の計算
                    if len(recommended_set) > 0:
                        precision = len(relevant_set.intersection(recommended_set)) / len(recommended_set)
                    else:
                        precision = 0.0
                    
                    if len(relevant_set) > 0:
                        recall = len(relevant_set.intersection(recommended_set)) / len(relevant_set)
                    else:
                        recall = 0.0
                    
                    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
                    
                    all_precisions[k].append(precision)
                    all_recalls[k].append(recall)
                    all_f1s[k].append(f1)
            
            # 平均値の計算
            for k in k_values:
                metrics[f'precision_at_{k}'] = np.mean(all_precisions[k])
                metrics[f'recall_at_{k}'] = np.mean(all_recalls[k])
                metrics[f'f1_at_{k}'] = np.mean(all_f1s[k])
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name="precision_recall",
                timestamp=datetime.now().isoformat(),
                metrics=metrics,
                recommendations=[],
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"精度・再現率テストエラー: {e}")
            return TestResult(
                test_name="precision_recall",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
    
    def test_ndcg(self, k_values: List[int] = None) -> TestResult:
        """
        NDCG（Normalized Discounted Cumulative Gain）のテスト
        
        Args:
            k_values (List[int]): 評価するk値のリスト
            
        Returns:
            TestResult: テスト結果
        """
        if not self.engine or not self.ground_truth_data:
            return TestResult(
                test_name="ndcg",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=0.0,
                success=False,
                error_message="エンジンまたは正解データが初期化されていません"
            )
        
        k_values = k_values or self.config['test_settings']['ndcg_at_k']
        start_time = time.time()
        
        try:
            metrics = {}
            all_ndcgs = {k: [] for k in k_values}
            
            for article_id, ground_truth in self.ground_truth_data.items():
                # 推奨の取得
                recommendations = self.engine.get_recommendations(article_id, max(k_values))
                
                # スコアベースのNDCG計算
                for k in k_values:
                    top_k_recommendations = recommendations[:k]
                    
                    # 関連度スコアの生成（マッチスコアベース）
                    y_true = []
                    y_score = []
                    
                    for rec in top_k_recommendations:
                        y_score.append(rec.match_score)
                        # 正解データに含まれているかチェック
                        relevance = 1.0 if rec.product_id in ground_truth.relevant_products else 0.0
                        y_true.append(relevance)
                    
                    # NDCGの計算
                    if len(y_true) > 0 and len(y_score) > 0:
                        ndcg = ndcg_score([y_true], [y_score], k=k)
                        all_ndcgs[k].append(ndcg)
            
            # 平均値の計算
            for k in k_values:
                metrics[f'ndcg_at_{k}'] = np.mean(all_ndcgs[k]) if all_ndcgs[k] else 0.0
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name="ndcg",
                timestamp=datetime.now().isoformat(),
                metrics=metrics,
                recommendations=[],
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"NDCGテストエラー: {e}")
            return TestResult(
                test_name="ndcg",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
    
    def test_performance(self, test_articles: List[str] = None, iterations: int = 10) -> TestResult:
        """
        パフォーマンステスト
        
        Args:
            test_articles (List[str]): テスト対象の記事IDリスト
            iterations (int): 反復回数
            
        Returns:
            TestResult: テスト結果
        """
        if not self.engine:
            return TestResult(
                test_name="performance",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=0.0,
                success=False,
                error_message="エンジンが初期化されていません"
            )
        
        start_time = time.time()
        
        try:
            # テスト記事の選択
            if not test_articles:
                test_articles = list(self.engine.articles.keys())[:10]
            
            execution_times = []
            memory_usage = []
            
            for i in range(iterations):
                iteration_start = time.time()
                
                # 各記事での推奨実行
                for article_id in test_articles:
                    recommendations = self.engine.get_recommendations(article_id, 10)
                
                iteration_time = time.time() - iteration_start
                execution_times.append(iteration_time)
            
            # メトリクスの計算
            metrics = {
                'avg_execution_time': np.mean(execution_times),
                'min_execution_time': np.min(execution_times),
                'max_execution_time': np.max(execution_times),
                'std_execution_time': np.std(execution_times),
                'total_articles_tested': len(test_articles),
                'iterations': iterations
            }
            
            # パフォーマンス基準との比較
            max_allowed_time = self.config['performance_settings']['max_execution_time']
            metrics['performance_acceptable'] = metrics['avg_execution_time'] <= max_allowed_time
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name="performance",
                timestamp=datetime.now().isoformat(),
                metrics=metrics,
                recommendations=[],
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"パフォーマンステストエラー: {e}")
            return TestResult(
                test_name="performance",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
    
    def test_api_endpoints(self, api_base_url: str = "http://localhost:5000") -> TestResult:
        """
        APIエンドポイントのテスト
        
        Args:
            api_base_url (str): APIのベースURL
            
        Returns:
            TestResult: テスト結果
        """
        start_time = time.time()
        
        try:
            metrics = {}
            endpoint_results = {}
            
            # ヘルスチェック
            try:
                response = requests.get(f"{api_base_url}/health", timeout=5)
                endpoint_results['health_check'] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code == 200
                }
            except Exception as e:
                endpoint_results['health_check'] = {'success': False, 'error': str(e)}
            
            # データサマリー
            try:
                response = requests.get(f"{api_base_url}/api/v1/data/summary", timeout=5)
                endpoint_results['data_summary'] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code == 200
                }
            except Exception as e:
                endpoint_results['data_summary'] = {'success': False, 'error': str(e)}
            
            # 記事一覧
            try:
                response = requests.get(f"{api_base_url}/api/v1/articles?limit=5", timeout=5)
                endpoint_results['articles_list'] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code == 200
                }
            except Exception as e:
                endpoint_results['articles_list'] = {'success': False, 'error': str(e)}
            
            # 推奨取得（サンプル記事IDで）
            try:
                response = requests.get(f"{api_base_url}/api/v1/recommendations/sample_article", timeout=10)
                endpoint_results['recommendations'] = {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code == 200
                }
            except Exception as e:
                endpoint_results['recommendations'] = {'success': False, 'error': str(e)}
            
            # 成功率の計算
            successful_endpoints = sum(1 for result in endpoint_results.values() if result.get('success', False))
            total_endpoints = len(endpoint_results)
            
            metrics = {
                'total_endpoints_tested': total_endpoints,
                'successful_endpoints': successful_endpoints,
                'success_rate': successful_endpoints / total_endpoints if total_endpoints > 0 else 0.0,
                'endpoint_results': endpoint_results
            }
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name="api_endpoints",
                timestamp=datetime.now().isoformat(),
                metrics=metrics,
                recommendations=[],
                execution_time=execution_time,
                success=metrics['success_rate'] > 0.8  # 80%以上の成功率
            )
            
        except Exception as e:
            logger.error(f"APIテストエラー: {e}")
            return TestResult(
                test_name="api_endpoints",
                timestamp=datetime.now().isoformat(),
                metrics={},
                recommendations=[],
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
    
    def run_all_tests(self, include_api_test: bool = False, api_url: str = None) -> List[TestResult]:
        """
        全テストの実行
        
        Args:
            include_api_test (bool): APIテストを含むかどうか
            api_url (str): APIのURL
            
        Returns:
            List[TestResult]: 全テスト結果
        """
        logger.info("全テストの実行を開始します")
        
        test_results = []
        
        # 1. 精度・再現率テスト
        logger.info("精度・再現率テストを実行中...")
        precision_result = self.test_precision_recall()
        test_results.append(precision_result)
        
        # 2. NDCGテスト
        logger.info("NDCGテストを実行中...")
        ndcg_result = self.test_ndcg()
        test_results.append(ndcg_result)
        
        # 3. パフォーマンステスト
        logger.info("パフォーマンステストを実行中...")
        performance_result = self.test_performance()
        test_results.append(performance_result)
        
        # 4. APIテスト（オプション）
        if include_api_test:
            logger.info("APIテストを実行中...")
            api_result = self.test_api_endpoints(api_url or "http://localhost:5000")
            test_results.append(api_result)
        
        self.test_results.extend(test_results)
        
        logger.info("全テストの実行が完了しました")
        return test_results
    
    def generate_test_report(self, output_file: str = None) -> str:
        """
        テストレポートの生成
        
        Args:
            output_file (str): 出力ファイルパス
            
        Returns:
            str: レポートファイルのパス
        """
        if not self.test_results:
            logger.warning("テスト結果がありません")
            return None
        
        # レポートの生成
        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "successful_tests": sum(1 for result in self.test_results if result.success),
                "failed_tests": sum(1 for result in self.test_results if not result.success),
                "generated_at": datetime.now().isoformat()
            },
            "test_results": [
                {
                    "test_name": result.test_name,
                    "timestamp": result.timestamp,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "metrics": result.metrics,
                    "error_message": result.error_message
                }
                for result in self.test_results
            ]
        }
        
        # ファイル出力
        if not output_file:
            output_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"テストレポートを生成しました: {output_file}")
        return output_file

# 使用例
if __name__ == "__main__":
    # テストフレームワークの初期化
    tester = RecommendationTester()
    
    # エンジンの初期化
    if tester.initialize_engine():
        # 合成正解データの生成
        tester.generate_synthetic_ground_truth(sample_size=20)
        
        # 全テストの実行
        results = tester.run_all_tests(include_api_test=False)
        
        # レポートの生成
        report_file = tester.generate_test_report()
        
        print(f"テスト完了: {report_file}")
    else:
        print("エンジンの初期化に失敗しました")










