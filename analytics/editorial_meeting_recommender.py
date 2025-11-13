#!/usr/bin/env python3
"""
編集会議用コンテンツメンテナンス推奨システム
- クリスマス以外で見落としがちなコンテンツ機会を自動発見
- 直近30日間の成長分析と前年同時期比較
- データドリブンな編集計画支援
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

# OAuth認証システムをインポート
try:
    from .oauth_google_apis import OAuthGoogleAPIsIntegration
except ImportError:
    from oauth_google_apis import OAuthGoogleAPIsIntegration

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/editorial_meeting_recommender.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EditorialMeetingRecommender:
    def __init__(self, credentials_path='config/oauth_credentials.json', token_path='config/token.json'):
        """
        編集会議推奨システムの初期化
        
        Args:
            credentials_path (str): OAuth認証情報ファイルのパス
            token_path (str): トークンファイルのパス
        """
        self.api = OAuthGoogleAPIsIntegration(credentials_path, token_path)
        self.non_christmas_keywords = self._define_non_christmas_keywords()
        
        # ログディレクトリの作成
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
        os.makedirs('data/editorial_meeting', exist_ok=True)
    
    def _define_non_christmas_keywords(self) -> Dict[str, List[str]]:
        """クリスマス以外の季節イベントキーワードの定義"""
        return {
            'new_year': [
                '正月', '年賀', 'お年賀', '新年', '迎春', '初詣',
                'お正月', '正月ギフト', '新年ギフト', '年賀状'
            ],
            'coming_of_age': [
                '成人式', '振袖', '成人祝い', '成人式ギフト',
                '成人式プレゼント', '振袖ギフト'
            ],
            'valentine_prep': [
                'バレンタイン', 'チョコ', 'チョコレート', 'バレンタインギフト',
                'バレンタイン準備', '手作りチョコ'
            ],
            'school_entrance': [
                '入学祝い', '入園祝い', '入学式', '入園式',
                '入学祝いギフト', '入園祝いギフト', '卒業祝い'
            ],
            'white_day': [
                'ホワイトデー', 'お返し', 'ホワイトデー灰返し',
                'ホワイトデーギフト', 'お返しギフト'
            ],
            'winter_events': [
                '冬ギフト', '寒中見舞い', '節分', 'ひな祭り',
                '春ギフト', '卒業シーズン', '春のギフト'
            ]
        }
    
    def get_ga4_data_for_period(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        指定期間のGA4データを取得（売上データ含む）
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: GA4データ
        """
        if not self.api.ga4_service:
            logger.error("GA4サービスが初期化されていません")
            return pd.DataFrame()
        
        try:
            # GA4リクエスト作成
            request_body = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'dimensions': [
                    {'name': 'pagePath'},
                    {'name': 'pageTitle'}
                ],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                    {'name': 'screenPageViews'},
                    {'name': 'conversions'},
                    {'name': 'totalRevenue'},
                    {'name': 'purchaseRevenue'}
                ],
                'limit': 10000
            }
            
            # API呼び出し
            response = self.api.ga4_service.properties().runReport(
                property=f'properties/{self.api.ga4_property_id}',
                body=request_body
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {}
                    
                    # ディメンション値の取得
                    row_data['pagePath'] = row['dimensionValues'][0].get('value', '')
                    row_data['pageTitle'] = row['dimensionValues'][1].get('value', '')
                    
                    # メトリクス値の取得
                    row_data['sessions'] = float(row['metricValues'][0].get('value', '0'))
                    row_data['totalUsers'] = float(row['metricValues'][1].get('value', '0'))
                    row_data['screenPageViews'] = float(row['metricValues'][2].get('value', '0'))
                    row_data['conversions'] = float(row['metricValues'][3].get('value', '0'))
                    row_data['totalRevenue'] = float(row['metricValues'][4].get('value', '0'))
                    row_data['purchaseRevenue'] = float(row['metricValues'][5].get('value', '0'))
                    
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GA4データ取得完了: {len(df)}行 ({start_date} - {end_date})")
            return df
            
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_gsc_data_for_period(self, start_date: str, end_date: str, 
                              dimensions: List[str] = None, row_limit: int = 25000) -> pd.DataFrame:
        """
        指定期間のGSCデータを取得
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            dimensions (list): 取得するディメンション
            row_limit (int): 取得行数上限
        
        Returns:
            pd.DataFrame: GSCデータ
        """
        if not self.api.gsc_service:
            logger.error("GSCサービスが初期化されていません")
            return pd.DataFrame()
        
        if not dimensions:
            dimensions = ['date', 'query', 'page', 'country', 'device']
        
        try:
            # GSCリクエスト作成
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': row_limit,
                'startRow': 0
            }
            
            # API呼び出し
            response = self.api.gsc_service.searchanalytics().query(
                siteUrl=self.api.gsc_site_url,
                body=request
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    }
                    
                    # ディメンション値の追加
                    for i, dimension in enumerate(dimensions):
                        if i < len(row.get('keys', [])):
                            row_data[dimension] = row['keys'][i]
                    
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GSCデータ取得完了: {len(df)}行 ({start_date} - {end_date})")
            return df
            
        except Exception as e:
            logger.error(f"GSCデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def analyze_recent_growth(self) -> Dict[str, pd.DataFrame]:
        """
        直近30日間で伸びているコンテンツの分析
        
        Returns:
            Dict[str, pd.DataFrame]: 成長分析結果
        """
        logger.info("直近30日間の成長分析開始")
        
        try:
            # 期間設定
            end_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')  # GSCは3日前まで
            recent_start = (datetime.now() - timedelta(days=33)).strftime('%Y-%m-%d')  # 直近30日
            previous_start = (datetime.now() - timedelta(days=63)).strftime('%Y-%m-%d')  # 前30日
            
            # GSCデータ取得
            recent_gsc_data = self.get_gsc_data_for_period(recent_start, end_date)
            previous_gsc_data = self.get_gsc_data_for_period(previous_start, recent_start)
            
            # GA4データ取得（売上とページタイトル用）
            recent_ga4_data = self.get_ga4_data_for_period(recent_start, end_date)
            
            if recent_gsc_data.empty or previous_gsc_data.empty:
                logger.warning("比較用データが不足しています")
                return {}
            
            # ページ別で集計
            recent_pages = self._aggregate_page_data(recent_gsc_data)
            previous_pages = self._aggregate_page_data(previous_gsc_data)
            
            # 成長率計算
            growth_analysis = self._calculate_growth_metrics(recent_pages, previous_pages)
            
            # GA4データを統合（売上とページタイトル）
            growth_analysis = self._integrate_ga4_data(growth_analysis, recent_ga4_data)
            
            logger.info(f"成長分析完了: {len(growth_analysis)}ページ")
            return {
                'recent_gsc_data': recent_gsc_data,
                'previous_gsc_data': previous_gsc_data,
                'recent_ga4_data': recent_ga4_data,
                'growth_analysis': growth_analysis
            }
            
        except Exception as e:
            logger.error(f"成長分析エラー: {e}")
            return {}
    
    def _aggregate_page_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """ページ別でGSCデータを集計"""
        if data.empty or 'page' not in data.columns:
            return pd.DataFrame()
        
        page_stats = data.groupby('page').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # CTRを再計算
        page_stats['ctr_calculated'] = (page_stats['clicks'] / page_stats['impressions'] * 100).fillna(0)
        page_stats['avg_position'] = page_stats['position'].round(2)
        
        return page_stats
    
    def _calculate_growth_metrics(self, recent_data: pd.DataFrame, previous_data: pd.DataFrame) -> pd.DataFrame:
        """成長メトリクスの計算"""
        if recent_data.empty or previous_data.empty:
            return pd.DataFrame()
        
        # マージ
        merged = pd.merge(
            recent_data, 
            previous_data, 
            on='page', 
            suffixes=('_recent', '_previous'),
            how='outer'
        ).fillna(0)
        
        # 成長率計算
        merged['clicks_growth_rate'] = (
            (merged['clicks_recent'] - merged['clicks_previous']) / 
            merged['clicks_previous'].replace(0, 1) * 100
        ).fillna(0)
        
        merged['impressions_growth_rate'] = (
            (merged['impressions_recent'] - merged['impressions_previous']) / 
            merged['impressions_previous'].replace(0, 1) * 100
        ).fillna(0)
        
        # ポジション改善
        merged['position_improvement'] = merged['avg_position_previous'] - merged['avg_position_recent']
        
        # CTR改善
        merged['ctr_improvement'] = merged['ctr_calculated_recent'] - merged['ctr_calculated_previous']
        
        return merged
    
    def _integrate_ga4_data(self, growth_data: pd.DataFrame, ga4_data: pd.DataFrame) -> pd.DataFrame:
        """GA4データを成長分析データに統合"""
        if growth_data.empty or ga4_data.empty:
            return growth_data
        
        try:
            # GA4データをページパスで集計
            ga4_aggregated = ga4_data.groupby('pagePath').agg({
                'sessions': 'sum',
                'totalUsers': 'sum',
                'screenPageViews': 'sum',
                'conversions': 'sum',
                'totalRevenue': 'sum',
                'purchaseRevenue': 'sum',
                'pageTitle': 'first'  # 最初のタイトルを取得
            }).reset_index()
            
            # 売上データを統合（複数の売上指標から最大値を取得）
            ga4_aggregated['max_revenue'] = ga4_aggregated[['totalRevenue', 'purchaseRevenue']].max(axis=1)
            
            # ページパスを統一（GSCの'page'とGA4の'pagePath'をマッチング）
            # GSCのページURLからGA4のページパスに変換
            def normalize_page_path(url):
                if pd.isna(url):
                    return ''
                # ドメイン部分を除去してパス部分のみ取得
                if 'moodmark' in url:
                    parts = url.split('/moodmark')
                    if len(parts) > 1:
                        return '/moodmark' + parts[1].split('?')[0]  # クエリパラメータ除去
                return url
            
            growth_data['normalized_page'] = growth_data['page'].apply(normalize_page_path)
            ga4_aggregated['normalized_page'] = ga4_aggregated['pagePath'].apply(normalize_page_path)
            
            # マージ
            merged = pd.merge(
                growth_data,
                ga4_aggregated[['normalized_page', 'sessions', 'totalUsers', 'screenPageViews', 'conversions', 'totalRevenue', 'purchaseRevenue', 'max_revenue', 'pageTitle']],
                on='normalized_page',
                how='left'
            )
            
            # 不要な列を削除
            merged = merged.drop('normalized_page', axis=1)
            
            # 欠損値を0で埋める
            merged['sessions'] = merged['sessions'].fillna(0)
            merged['totalUsers'] = merged['totalUsers'].fillna(0)
            merged['screenPageViews'] = merged['screenPageViews'].fillna(0)
            merged['conversions'] = merged['conversions'].fillna(0)
            merged['totalRevenue'] = merged['totalRevenue'].fillna(0)
            merged['purchaseRevenue'] = merged['purchaseRevenue'].fillna(0)
            merged['max_revenue'] = merged['max_revenue'].fillna(0)
            merged['pageTitle'] = merged['pageTitle'].fillna('')
            
            logger.info(f"GA4データ統合完了: {len(merged)}ページ")
            return merged
            
        except Exception as e:
            logger.error(f"GA4データ統合エラー: {e}")
            return growth_data
    
    def analyze_year_over_year(self) -> Dict[str, Any]:
        """
        前年同時期（2023年12月-2024年1月）との比較分析
        
        Returns:
            Dict[str, Any]: 前年比較分析結果
        """
        logger.info("前年同時期比較分析開始")
        
        try:
            # 前年期間（2023年12月-2024年1月）
            last_year_start = '2023-12-01'
            last_year_end = '2024-01-31'
            
            # 今年の同じ期間（2024年12月-2025年1月の予測または現在まで）
            current_start = '2024-12-01'
            current_end = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            
            # データ取得
            last_year_data = self.get_gsc_data_for_period(last_year_start, last_year_end)
            current_data = self.get_gsc_data_for_period(current_start, current_end)
            
            if last_year_data.empty:
                logger.warning("前年データが取得できませんでした")
                return {}
            
            # 分析実行
            yoy_analysis = {
                'last_year_data': last_year_data,
                'current_data': current_data,
                'trending_keywords': self._identify_trending_keywords(last_year_data),
                'seasonal_patterns': self._analyze_seasonal_patterns(last_year_data),
                'preparation_gaps': self._identify_preparation_gaps(last_year_data, current_data)
            }
            
            logger.info("前年同時期比較分析完了")
            return yoy_analysis
            
        except Exception as e:
            logger.error(f"前年比較分析エラー: {e}")
            return {}
    
    def _identify_trending_keywords(self, data: pd.DataFrame) -> List[Dict]:
        """前年にトレンドだったキーワードを特定"""
        if data.empty or 'query' not in data.columns:
            return []
        
        # クエリ別で集計
        query_stats = data.groupby('query').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # 高パフォーマンスキーワードを抽出
        high_performance = query_stats[
            (query_stats['clicks'] >= 100) & 
            (query_stats['position'] <= 10)
        ].sort_values('clicks', ascending=False)
        
        return high_performance.head(50).to_dict('records')
    
    def _analyze_seasonal_patterns(self, data: pd.DataFrame) -> Dict[str, List]:
        """季節パターンの分析"""
        if data.empty:
            return {}
        
        seasonal_patterns = {}
        
        # 各季節イベントカテゴリでフィルタリング
        for category, keywords in self.non_christmas_keywords.items():
            pattern_data = self._filter_data_by_keywords(data, keywords)
            if not pattern_data.empty:
                # ページ別で集計
                page_stats = pattern_data.groupby('page').agg({
                    'clicks': 'sum',
                    'impressions': 'sum',
                    'position': 'mean'
                }).reset_index()
                
                seasonal_patterns[category] = page_stats.sort_values('clicks', ascending=False).head(20).to_dict('records')
        
        return seasonal_patterns
    
    def _filter_data_by_keywords(self, data: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
        """キーワードリストでデータをフィルタリング"""
        if data.empty or 'query' not in data.columns:
            return pd.DataFrame()
        
        keyword_pattern = '|'.join(keywords)
        filtered_data = data[
            data['query'].str.contains(keyword_pattern, case=False, na=False)
        ].copy()
        
        return filtered_data
    
    def _identify_preparation_gaps(self, last_year_data: pd.DataFrame, current_data: pd.DataFrame) -> List[Dict]:
        """今年の準備ギャップを特定"""
        gaps = []
        
        # 前年に伸びたキーワードで今年の準備状況をチェック
        last_year_keywords = self._identify_trending_keywords(last_year_data)
        
        if current_data.empty:
            # 現在データがない場合、全ての前年トレンドをギャップとして報告
            for keyword in last_year_keywords[:20]:
                gaps.append({
                    'keyword': keyword['query'],
                    'last_year_clicks': keyword['clicks'],
                    'preparation_status': 'not_started',
                    'recommendation': '早急にコンテンツ準備を開始'
                })
        else:
            # 今年のデータと比較
            current_keywords = self._identify_trending_keywords(current_data)
            current_keyword_set = set([kw['query'] for kw in current_keywords])
            
            for keyword in last_year_keywords[:20]:
                if keyword['query'] not in current_keyword_set:
                    gaps.append({
                        'keyword': keyword['query'],
                        'last_year_clicks': keyword['clicks'],
                        'preparation_status': 'missing',
                        'recommendation': '前年実績のあるキーワードの準備が不足'
                    })
        
        return gaps
    
    def calculate_maintenance_priority_score(self, page_data: Dict) -> Dict:
        """
        メンテナンス優先度スコアの計算
        
        Args:
            page_data (Dict): ページデータ
        
        Returns:
            Dict: スコアリング結果
        """
        try:
            # 各要素のスコア計算
            impression_score = self._calculate_impression_score(page_data)
            ctr_opportunity_score = self._calculate_ctr_opportunity_score(page_data)
            ranking_opportunity_score = self._calculate_ranking_opportunity_score(page_data)
            growth_score = self._calculate_growth_score(page_data)
            
            # 重み付け総合スコア（より実用的な配分）
            weights = {
                'clicks': 0.35,        # クリック数（最重要）
                'impression': 0.25,    # インプレッション数
                'ranking_opportunity': 0.20,  # 順位改善機会
                'ctr_opportunity': 0.10,      # CTR改善機会
                'growth': 0.10         # 成長率
            }
            
            # クリック数スコアを追加
            clicks_score = self._calculate_clicks_score(page_data)
            
            total_score = (
                impression_score * weights['impression'] +
                ctr_opportunity_score * weights['ctr_opportunity'] +
                ranking_opportunity_score * weights['ranking_opportunity'] +
                growth_score * weights['growth'] +
                clicks_score * weights['clicks']
            )
            
            return {
                'total_score': round(total_score, 2),
                'impression_score': round(impression_score, 2),
                'ctr_opportunity_score': round(ctr_opportunity_score, 2),
                'ranking_opportunity_score': round(ranking_opportunity_score, 2),
                'growth_score': round(growth_score, 2),
                'clicks_score': round(clicks_score, 2),
                'weights': weights
            }
            
        except Exception as e:
            logger.error(f"スコアリングエラー: {e}")
            return {'total_score': 0}
    
    def _calculate_impression_score(self, page_data: Dict) -> float:
        """インプレッション数によるスコア計算（0-100）"""
        impressions = page_data.get('impressions_recent', 0)
        if impressions == 0:
            return 0
        
        # 対数スケールで正規化
        import math
        score = min(100, math.log10(impressions + 1) * 20)
        return score
    
    def _calculate_ctr_opportunity_score(self, page_data: Dict) -> float:
        """CTR改善機会スコア計算（0-100）"""
        ctr = page_data.get('ctr_calculated_recent', 0)
        impressions = page_data.get('impressions_recent', 0)
        
        if impressions < 100:  # 最小インプレッション数
            return 0
        
        # CTRが低いほど高スコア（改善余地大）
        if ctr < 1.0:
            return 100
        elif ctr < 2.0:
            return 80
        elif ctr < 3.0:
            return 60
        elif ctr < 5.0:
            return 40
        else:
            return 20
    
    def _calculate_ranking_opportunity_score(self, page_data: Dict) -> float:
        """順位改善機会スコア計算（0-100）"""
        position = page_data.get('avg_position_recent', 0)
        
        if position == 0:
            return 0
        
        # 10-20位が最適改善機会
        if 10 <= position <= 20:
            return 100
        elif 5 <= position < 10:
            return 80
        elif 20 < position <= 30:
            return 60
        elif position > 30:
            return 40
        else:  # 上位5位以内
            return 20
    
    def _calculate_growth_score(self, page_data: Dict) -> float:
        """成長率スコア計算（0-100）"""
        growth_rate = page_data.get('clicks_growth_rate', 0)
        
        if growth_rate >= 50:
            return 100
        elif growth_rate >= 25:
            return 80
        elif growth_rate >= 10:
            return 60
        elif growth_rate >= 0:
            return 40
        else:
            return 20
    
    def _calculate_clicks_score(self, page_data: Dict) -> float:
        """クリック数によるスコア計算（0-100）"""
        clicks = page_data.get('clicks_recent', 0)
        if clicks == 0:
            return 0
        
        # より実用的なスコアリング
        if clicks >= 10000:
            return 100
        elif clicks >= 5000:
            return 90
        elif clicks >= 2000:
            return 80
        elif clicks >= 1000:
            return 70
        elif clicks >= 500:
            return 60
        elif clicks >= 200:
            return 50
        elif clicks >= 100:
            return 40
        elif clicks >= 50:
            return 30
        elif clicks >= 20:
            return 20
        else:
            return 10
    
    def filter_non_christmas_content(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        クリスマス以外のコンテンツを抽出
        
        Args:
            data (pd.DataFrame): GSCデータ
        
        Returns:
            Dict[str, pd.DataFrame]: カテゴリ別フィルタリング結果
        """
        logger.info("クリスマス以外のコンテンツ抽出開始")
        
        non_christmas_data = {}
        
        for category, keywords in self.non_christmas_keywords.items():
            filtered_data = self._filter_data_by_keywords(data, keywords)
            if not filtered_data.empty:
                non_christmas_data[category] = filtered_data
                logger.info(f"{category}: {len(filtered_data)}件のデータを抽出")
        
        return non_christmas_data
    
    def generate_editorial_recommendations(self, meeting_date: str = None) -> Dict[str, Any]:
        """
        編集会議推奨レポートの生成
        
        Args:
            meeting_date (str): 編集会議日付 (YYYY-MM-DD)
        
        Returns:
            Dict[str, Any]: 推奨レポート
        """
        logger.info("編集会議推奨レポート生成開始")
        
        try:
            # 日付設定
            if not meeting_date:
                meeting_date = datetime.now().strftime('%Y-%m-%d')
            
            # 分析実行
            growth_analysis = self.analyze_recent_growth()
            yoy_analysis = self.analyze_year_over_year()
            
            # 推奨記事の選定
            recommendations = self._generate_recommendations(growth_analysis, yoy_analysis)
            
            # レポート統合
            report = {
                'report_metadata': {
                    'title': '編集会議用コンテンツメンテナンス推奨レポート',
                    'meeting_date': meeting_date,
                    'generated_at': datetime.now().isoformat(),
                    'site_url': self.api.gsc_site_url,
                    'account': 'nakamura@likepass.net'
                },
                'growth_analysis': growth_analysis,
                'yoy_analysis': yoy_analysis,
                'recommendations': recommendations,
                'non_christmas_opportunities': self._extract_non_christmas_opportunities(yoy_analysis)
            }
            
            # レポート保存
            self._save_reports(report, meeting_date)
            
            logger.info("編集会議推奨レポート生成完了")
            return report
            
        except Exception as e:
            logger.error(f"推奨レポート生成エラー: {e}")
            return {}
    
    def _generate_recommendations(self, growth_analysis: Dict, yoy_analysis: Dict) -> Dict[str, List]:
        """推奨記事の生成"""
        recommendations = {
            'top_priority': [],
            'high_growth': [],
            'seasonal_opportunities': [],
            'preparation_gaps': []
        }
        
        try:
            # 成長分析から上位推奨を選定
            if 'growth_analysis' in growth_analysis:
                growth_data = growth_analysis['growth_analysis']
                if not growth_data.empty:
                    # スコアリング
                    scored_pages = []
                    for _, row in growth_data.iterrows():
                        page_data = row.to_dict()
                        scores = self.calculate_maintenance_priority_score(page_data)
                        
                        scored_pages.append({
                            'page': row['page'],
                            'page_title': row.get('pageTitle', ''),
                            'scores': scores,
                            'metrics': {
                                'recent_clicks': int(row.get('clicks_recent', 0)),
                                'recent_impressions': int(row.get('impressions_recent', 0)),
                                'recent_ctr': round(row.get('ctr_calculated_recent', 0), 2),
                                'recent_position': round(row.get('avg_position_recent', 0), 1),
                                'clicks_growth_rate': round(row.get('clicks_growth_rate', 0), 1),
                                'impressions_growth_rate': round(row.get('impressions_growth_rate', 0), 1),
                                'recent_revenue': round(row.get('max_revenue', 0), 0),
                                'recent_sessions': int(row.get('sessions', 0)),
                                'recent_conversions': int(row.get('conversions', 0))
                            }
                        })
                    
                    # 総合スコアでソート
                    scored_pages.sort(key=lambda x: x['scores']['total_score'], reverse=True)
                    
                    # 上位20件を推奨
                    recommendations['top_priority'] = scored_pages[:20]
                    recommendations['high_growth'] = scored_pages[20:40]
            
            # 前年分析から季節機会を抽出
            if 'seasonal_patterns' in yoy_analysis:
                for category, pages in yoy_analysis['seasonal_patterns'].items():
                    if pages:
                        recommendations['seasonal_opportunities'].extend(pages[:10])
            
            # 準備ギャップ
            if 'preparation_gaps' in yoy_analysis:
                recommendations['preparation_gaps'] = yoy_analysis['preparation_gaps'][:20]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"推奨生成エラー: {e}")
            return recommendations
    
    def _extract_non_christmas_opportunities(self, yoy_analysis: Dict) -> Dict[str, List]:
        """クリスマス以外の機会を抽出"""
        opportunities = {}
        
        if 'seasonal_patterns' in yoy_analysis:
            for category, pages in yoy_analysis['seasonal_patterns'].items():
                if pages:
                    opportunities[category] = pages[:10]
        
        return opportunities
    
    def _save_reports(self, report: Dict[str, Any], meeting_date: str):
        """レポートの保存（Markdown、JSON、CSV）"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # JSON詳細データ
            json_file = f'data/editorial_meeting/editorial_recommendations_{timestamp}.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            # Markdownレポート
            markdown_file = f'data/editorial_meeting/editorial_recommendations_{timestamp}.md'
            markdown_content = self._format_report_as_markdown(report)
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # CSV編集会議用一覧表
            csv_file = f'data/editorial_meeting/editorial_recommendations_{timestamp}.csv'
            csv_data = self._format_recommendations_as_csv(report)
            csv_data.to_csv(csv_file, index=False, encoding='utf-8-sig')
            
            logger.info(f"レポート保存完了:")
            logger.info(f"  JSON: {json_file}")
            logger.info(f"  Markdown: {markdown_file}")
            logger.info(f"  CSV: {csv_file}")
            
        except Exception as e:
            logger.error(f"レポート保存エラー: {e}")
    
    def _format_report_as_markdown(self, report: Dict[str, Any]) -> str:
        """Markdownレポートのフォーマット"""
        metadata = report.get('report_metadata', {})
        recommendations = report.get('recommendations', {})
        non_christmas = report.get('non_christmas_opportunities', {})
        
        content = f"""# {metadata.get('title', '編集会議推奨レポート')}

**編集会議日**: {metadata.get('meeting_date', 'N/A')}  
**生成日時**: {metadata.get('generated_at', 'N/A')}  
**サイトURL**: {metadata.get('site_url', 'N/A')}  
**アカウント**: {metadata.get('account', 'N/A')}

## 📋 エグゼクティブサマリー

### 🎯 最優先メンテナンス記事 TOP10

| 順位 | ページURL | ページタイトル | 総合スコア | 現在順位 | 直近30日クリック | 前月比成長率 | 直近30日売上 | 推奨アクション |
|------|-----------|----------------|------------|----------|------------------|--------------|--------------|----------------|
"""
        
        # 最優先記事の表示
        top_priority = recommendations.get('top_priority', [])
        for i, item in enumerate(top_priority[:10], 1):
            page_url = item['page'][:60] + "..." if len(item['page']) > 60 else item['page']
            page_title = item.get('page_title', '')[:30] + "..." if len(item.get('page_title', '')) > 30 else item.get('page_title', '')
            content += f"| {i} | {page_url} | {page_title} | {item['scores']['total_score']} | {item['metrics']['recent_position']}位 | {item['metrics']['recent_clicks']:,} | +{item['metrics']['clicks_growth_rate']}% | ¥{item['metrics']['recent_revenue']:,} | メンテナンス推奨 |\n"
        
        content += f"""
## 📈 直近伸びているコンテンツ TOP20

| ページURL | ページタイトル | 総合スコア | 直近30日クリック | クリック成長率 | インプレッション成長率 | 現在CTR | 現在順位 | 直近30日売上 |
|-----------|----------------|------------|------------------|----------------|----------------------|---------|----------|--------------|
"""
        
        # 高成長記事の表示
        high_growth = recommendations.get('high_growth', [])
        for item in high_growth[:20]:
            page_url = item['page'][:50] + "..." if len(item['page']) > 50 else item['page']
            page_title = item.get('page_title', '')[:25] + "..." if len(item.get('page_title', '')) > 25 else item.get('page_title', '')
            content += f"| {page_url} | {page_title} | {item['scores']['total_score']} | {item['metrics']['recent_clicks']:,} | +{item['metrics']['clicks_growth_rate']}% | +{item['metrics']['impressions_growth_rate']}% | {item['metrics']['recent_ctr']}% | {item['metrics']['recent_position']}位 | ¥{item['metrics']['recent_revenue']:,} |\n"
        
        content += f"""
## 🎄 クリスマス以外の季節イベント機会

"""
        
        # 季節イベント機会
        for category, pages in non_christmas.items():
            if pages:
                category_name = category.replace('_', ' ').title()
                content += f"### {category_name}\n\n"
                content += "| ページURL | クリック数 | インプレッション数 | 平均順位 |\n"
                content += "|-----------|------------|------------------|----------|\n"
                
                for page in pages[:10]:
                    page_url = page['page'][:60] + "..." if len(page['page']) > 60 else page['page']
                    content += f"| {page_url} | {page['clicks']:,} | {page['impressions']:,} | {page['position']:.1f}位 |\n"
                content += "\n"
        
        # 準備ギャップ
        preparation_gaps = recommendations.get('preparation_gaps', [])
        if preparation_gaps:
            content += f"""
## ⚠️ 前年実績から見た準備ギャップ

| キーワード | 前年クリック数 | 準備状況 | 推奨アクション |
|------------|----------------|----------|----------------|
"""
            for gap in preparation_gaps[:15]:
                content += f"| {gap['keyword']} | {gap['last_year_clicks']:,} | {gap['preparation_status']} | {gap['recommendation']} |\n"
        
        content += f"""
## 📋 推奨アクション

### 11月末納品（12月UP）推奨記事

1. **最優先メンテナンス**: 総合スコア上位10記事の改善
2. **成長機会活用**: 直近伸びている記事のさらなる最適化
3. **季節準備**: クリスマス以外のイベントコンテンツ準備
4. **ギャップ解消**: 前年実績があるが今年準備不足のキーワード対応

### メンテナンス期限

- **11月25日**: 最優先記事のメンテナンス完了
- **11月30日**: 高成長記事の最適化完了
- **12月5日**: 季節イベント記事の準備完了

---
*このレポートはnakamura@likepass.netアカウントを使用して自動生成されました。*
"""
        
        return content
    
    def _format_recommendations_as_csv(self, report: Dict[str, Any]) -> pd.DataFrame:
        """CSV形式の編集会議用一覧表を作成"""
        try:
            recommendations = report.get('recommendations', {})
            
            csv_data = []
            
            # 最優先記事
            for i, item in enumerate(recommendations.get('top_priority', []), 1):
                csv_data.append({
                    '優先順位': i,
                    '完全URL': item['page'],
                    'ページタイトル': item.get('page_title', ''),
                    '記事タイトル': self._extract_article_title(item['page']),
                    '総合スコア': item['scores']['total_score'],
                    '現在の順位': f"{item['metrics']['recent_position']}位",
                    '直近30日クリック数': item['metrics']['recent_clicks'],
                    '前月比成長率': f"+{item['metrics']['clicks_growth_rate']}%",
                    'インプレッション数': item['metrics']['recent_impressions'],
                    '現在CTR': f"{item['metrics']['recent_ctr']}%",
                    '直近30日売上': f"¥{item['metrics']['recent_revenue']:,}",
                    '直近30日セッション数': item['metrics']['recent_sessions'],
                    '直近30日コンバージョン数': item['metrics']['recent_conversions'],
                    '推奨アクション': 'メンテナンス推奨',
                    'メンテナンス期限': '11月末推奨'
                })
            
            return pd.DataFrame(csv_data)
            
        except Exception as e:
            logger.error(f"CSV形式変換エラー: {e}")
            return pd.DataFrame()
    
    def _extract_article_title(self, page_path: str) -> str:
        """ページパスから記事タイトルを抽出"""
        try:
            # パスの最後の部分をタイトルとして使用
            title = page_path.split('/')[-1]
            # URLエンコードをデコード
            import urllib.parse
            title = urllib.parse.unquote(title)
            # ファイル拡張子を除去
            title = title.replace('.html', '').replace('.htm', '')
            # クエリパラメータを除去
            if '?' in title:
                title = title.split('?')[0]
            return title[:80] + "..." if len(title) > 80 else title
        except:
            return page_path[:80] + "..." if len(page_path) > 80 else page_path

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='編集会議用コンテンツ推奨システム')
    parser.add_argument('--meeting-date', help='編集会議日付 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    print("=== 編集会議用コンテンツメンテナンス推奨システム ===")
    if args.meeting_date:
        print(f"編集会議日: {args.meeting_date}")
    print()
    
    # 推奨システムの初期化
    recommender = EditorialMeetingRecommender()
    
    # 認証確認
    if not recommender.api.credentials:
        print("❌ 認証に失敗しました。")
        print("以下を確認してください：")
        print("1. nakamura@likepass.netでGoogle Cloud Consoleにアクセスできるか")
        print("2. config/oauth_credentials.json が存在するか")
        print("3. GA4プロパティとGSCサイトへのアクセス権限があるか")
        return
    
    print("✅ 認証成功: nakamura@likepass.net")
    
    # 推奨レポート生成
    report = recommender.generate_editorial_recommendations(args.meeting_date)
    
    if report:
        print("\n=== 推奨レポート生成完了 ===")
        print(f"編集会議日: {report['report_metadata']['meeting_date']}")
        print(f"生成日時: {report['report_metadata']['generated_at']}")
        
        # サマリー表示
        recommendations = report.get('recommendations', {})
        print(f"\n--- 推奨記事サマリー ---")
        print(f"最優先メンテナンス: {len(recommendations.get('top_priority', []))}記事")
        print(f"高成長記事: {len(recommendations.get('high_growth', []))}記事")
        print(f"季節機会: {len(recommendations.get('seasonal_opportunities', []))}記事")
        print(f"準備ギャップ: {len(recommendations.get('preparation_gaps', []))}キーワード")
        
        # 最優先記事の表示
        top_priority = recommendations.get('top_priority', [])
        if top_priority:
            print(f"\n--- 最優先メンテナンス記事 TOP5 ---")
            for i, item in enumerate(top_priority[:5], 1):
                print(f"{i}. {item['page'][:60]}... (スコア: {item['scores']['total_score']})")
        
        print(f"\n詳細レポートは data/editorial_meeting/ に保存されました。")
    else:
        print("推奨レポート生成に失敗しました。ログを確認してください。")

if __name__ == "__main__":
    main()
