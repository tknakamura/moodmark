#!/usr/bin/env python3
"""
修正版期間分析レポート
- pagePathでサイトを分けて分析
- 正しいサイト別データの集計
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# 相対インポートまたは絶対インポートを試みる
try:
    from .oauth_google_apis import OAuthGoogleAPIsIntegration
except ImportError:
    from oauth_google_apis import OAuthGoogleAPIsIntegration

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/corrected_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CorrectedPeriodAnalysis:
    def __init__(self):
        """修正版期間分析システムの初期化"""
        self.api_integration = OAuthGoogleAPIsIntegration()
        self.config = self._load_config()
        
        # ログディレクトリの作成
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        config_file = 'config/analytics_config.json'
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"設定ファイルが見つかりません: {config_file}")
                return {}
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return {}
    
    def get_gsc_data_for_period(self, start_date: str, end_date: str, site_url: str):
        """期間指定でGSCデータを取得"""
        try:
            if not self.api_integration.gsc_service:
                logger.warning("GSCサービスが初期化されていません")
                return pd.DataFrame()
            
            # GSCリクエスト作成
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['page', 'query'],
                'rowLimit': 10000,
                'startRow': 0
            }
            
            # API呼び出し
            response = self.api_integration.gsc_service.searchanalytics().query(
                siteUrl=site_url,
                body=request
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {
                        'page': row['keys'][0] if len(row.get('keys', [])) > 0 else '',
                        'query': row['keys'][1] if len(row.get('keys', [])) > 1 else '',
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    }
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GSCデータ取得完了: {len(df)}行 (サイト: {site_url})")
            return df
            
        except Exception as e:
            logger.error(f"GSCデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_ga4_data_for_period(self, start_date: str, end_date: str):
        """期間指定でGA4データを取得"""
        try:
            if not self.api_integration.ga4_service:
                logger.warning("GA4サービスが初期化されていません")
                return pd.DataFrame()
            
            # メトリクスとディメンション
            metrics = [
                'sessions',
                'totalUsers', 
                'screenPageViews',
                'bounceRate',
                'averageSessionDuration',
                'conversions'
            ]
            
            dimensions = [
                'date',
                'pagePath',
                'sessionDefaultChannelGrouping',
                'deviceCategory'
            ]
            
            # GA4リクエスト作成
            request_body = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [{'name': metric} for metric in metrics],
                'dimensions': [{'name': dimension} for dimension in dimensions],
                'limit': 10000
            }
            
            # プロパティIDを取得
            property_id = self.config.get('sites', {}).get('moodmark', {}).get('ga4_property_id')
            if not property_id:
                logger.error("GA4プロパティIDが設定されていません")
                return pd.DataFrame()
            
            # API呼び出し
            response = self.api_integration.ga4_service.properties().runReport(
                property=f"properties/{property_id}",
                body=request_body
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {}
                    
                    # ディメンション値の取得
                    for i, dimension in enumerate(dimensions):
                        if i < len(row.get('dimensionValues', [])):
                            row_data[dimension] = row['dimensionValues'][i].get('value', '')
                    
                    # メトリクス値の取得
                    for i, metric in enumerate(metrics):
                        if i < len(row.get('metricValues', [])):
                            value = row['metricValues'][i].get('value', '0')
                            try:
                                row_data[metric] = float(value)
                            except ValueError:
                                row_data[metric] = value
                    
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GA4データ取得完了: {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return pd.DataFrame()
    
    def split_data_by_site(self, ga4_data: pd.DataFrame):
        """pagePathでサイト別にデータを分割"""
        try:
            # moodmarkサイトのデータ（/moodmark/で始まるパス）
            moodmark_data = ga4_data[ga4_data['pagePath'].str.startswith('/moodmark/', na=False)].copy()
            
            # moodmarkgiftサイトのデータ（/moodmarkgift/で始まるパス）
            moodmarkgift_data = ga4_data[ga4_data['pagePath'].str.startswith('/moodmarkgift/', na=False)].copy()
            
            logger.info(f"moodmarkデータ: {len(moodmark_data)}行")
            logger.info(f"moodmarkgiftデータ: {len(moodmarkgift_data)}行")
            
            return {
                'moodmark': moodmark_data,
                'moodmarkgift': moodmarkgift_data
            }
            
        except Exception as e:
            logger.error(f"データ分割エラー: {e}")
            return {'moodmark': pd.DataFrame(), 'moodmarkgift': pd.DataFrame()}
    
    def generate_site_summary(self, site_data: pd.DataFrame, site_name: str):
        """サイト別サマリーの生成"""
        try:
            if site_data.empty:
                return {
                    'total_sessions': 0,
                    'total_users': 0,
                    'total_pageviews': 0,
                    'avg_bounce_rate': 0,
                    'avg_session_duration': 0,
                    'total_conversions': 0,
                    'data_rows': 0
                }
            
            summary = {
                'total_sessions': int(site_data['sessions'].sum()) if 'sessions' in site_data.columns else 0,
                'total_users': int(site_data['totalUsers'].sum()) if 'totalUsers' in site_data.columns else 0,
                'total_pageviews': int(site_data['screenPageViews'].sum()) if 'screenPageViews' in site_data.columns else 0,
                'avg_bounce_rate': float(site_data['bounceRate'].mean()) if 'bounceRate' in site_data.columns else 0,
                'avg_session_duration': float(site_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in site_data.columns else 0,
                'total_conversions': int(site_data['conversions'].sum()) if 'conversions' in site_data.columns else 0,
                'data_rows': len(site_data)
            }
            
            logger.info(f"{site_name}サマリー生成完了")
            return summary
            
        except Exception as e:
            logger.error(f"{site_name}サマリー生成エラー: {e}")
            return {}
    
    def get_top_organic_landing_pages(self, site_data: pd.DataFrame, site_name: str, limit: int = 10):
        """オーガニック集客の強いランディングページTOP10を取得"""
        try:
            if site_data.empty:
                return []
            
            # オーガニック検索のデータのみをフィルタリング
            organic_data = site_data[
                site_data['sessionDefaultChannelGrouping'].str.contains('Organic Search', na=False)
            ].copy()
            
            if organic_data.empty:
                logger.warning(f"{site_name}: オーガニック検索データが見つかりません")
                return []
            
            # ページ別で集計
            page_stats = organic_data.groupby('pagePath').agg({
                'sessions': 'sum',
                'totalUsers': 'sum',
                'screenPageViews': 'sum',
                'bounceRate': 'mean',
                'averageSessionDuration': 'mean',
                'conversions': 'sum'
            }).reset_index()
            
            # セッション数でソートしてTOP10を取得
            top_pages = page_stats.sort_values('sessions', ascending=False).head(limit)
            
            # 結果を辞書形式に変換
            result = []
            for _, row in top_pages.iterrows():
                result.append({
                    'page_path': row['pagePath'],
                    'sessions': int(row['sessions']),
                    'users': int(row['totalUsers']),
                    'pageviews': int(row['screenPageViews']),
                    'bounce_rate': float(row['bounceRate']),
                    'avg_session_duration': float(row['averageSessionDuration']),
                    'conversions': int(row['conversions'])
                })
            
            logger.info(f"{site_name}: オーガニックランディングページTOP{limit}を取得完了")
            return result
            
        except Exception as e:
            logger.error(f"{site_name}: オーガニックランディングページ取得エラー: {e}")
            return []
    
    def compare_organic_pages(self, current_pages: List[Dict], previous_pages: List[Dict], site_name: str):
        """オーガニックランディングページの前年対比"""
        try:
            if not current_pages or not previous_pages:
                return []
            
            # 前年のページパスをキーとした辞書を作成
            previous_dict = {page['page_path']: page for page in previous_pages}
            
            comparison_result = []
            
            for current_page in current_pages:
                page_path = current_page['page_path']
                previous_page = previous_dict.get(page_path)
                
                if previous_page:
                    # 前年データがある場合
                    sessions_growth = ((current_page['sessions'] - previous_page['sessions']) / previous_page['sessions'] * 100) if previous_page['sessions'] > 0 else 0
                    users_growth = ((current_page['users'] - previous_page['users']) / previous_page['users'] * 100) if previous_page['users'] > 0 else 0
                    pageviews_growth = ((current_page['pageviews'] - previous_page['pageviews']) / previous_page['pageviews'] * 100) if previous_page['pageviews'] > 0 else 0
                    
                    comparison_result.append({
                        'page_path': page_path,
                        'current': current_page,
                        'previous': previous_page,
                        'growth_rates': {
                            'sessions': sessions_growth,
                            'users': users_growth,
                            'pageviews': pageviews_growth
                        },
                        'has_previous_data': True
                    })
                else:
                    # 前年データがない場合（新規ページ）
                    comparison_result.append({
                        'page_path': page_path,
                        'current': current_page,
                        'previous': None,
                        'growth_rates': None,
                        'has_previous_data': False
                    })
            
            logger.info(f"{site_name}: オーガニックページ前年対比完了")
            return comparison_result
            
        except Exception as e:
            logger.error(f"{site_name}: オーガニックページ前年対比エラー: {e}")
            return []
    
    def get_gsc_summary(self, gsc_data: pd.DataFrame, site_name: str):
        """GSCサマリーの生成"""
        try:
            if gsc_data.empty:
                return {
                    'total_clicks': 0,
                    'total_impressions': 0,
                    'avg_ctr': 0,
                    'avg_position': 0,
                    'top_pages_count': 0,
                    'top_queries_count': 0
                }
            
            # ページ別集計
            page_stats = gsc_data.groupby('page').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            # クエリ別集計
            query_stats = gsc_data.groupby('query').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            summary = {
                'total_clicks': int(gsc_data['clicks'].sum()),
                'total_impressions': int(gsc_data['impressions'].sum()),
                'avg_ctr': float(gsc_data['ctr'].mean() * 100),
                'avg_position': float(gsc_data['position'].mean()),
                'top_pages_count': len(page_stats),
                'top_queries_count': len(query_stats)
            }
            
            logger.info(f"{site_name}: GSCサマリー生成完了")
            return summary
            
        except Exception as e:
            logger.error(f"{site_name}: GSCサマリー生成エラー: {e}")
            return {}
    
    def get_top_gsc_pages(self, gsc_data: pd.DataFrame, site_name: str, limit: int = 10):
        """GSCトップページを取得"""
        try:
            if gsc_data.empty:
                return []
            
            # ページ別で集計
            page_stats = gsc_data.groupby('page').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            # クリック数でソートしてTOP10を取得
            top_pages = page_stats.sort_values('clicks', ascending=False).head(limit)
            
            # 結果を辞書形式に変換
            result = []
            for _, row in top_pages.iterrows():
                result.append({
                    'page': row['page'],
                    'clicks': int(row['clicks']),
                    'impressions': int(row['impressions']),
                    'ctr': float(row['ctr'] * 100),
                    'position': float(row['position'])
                })
            
            logger.info(f"{site_name}: GSCトップページTOP{limit}を取得完了")
            return result
            
        except Exception as e:
            logger.error(f"{site_name}: GSCトップページ取得エラー: {e}")
            return []
    
    def get_top_gsc_queries(self, gsc_data: pd.DataFrame, site_name: str, limit: int = 20):
        """GSCトップクエリを取得"""
        try:
            if gsc_data.empty:
                return []
            
            # クエリ別で集計
            query_stats = gsc_data.groupby('query').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            # クリック数でソートしてTOP20を取得
            top_queries = query_stats.sort_values('clicks', ascending=False).head(limit)
            
            # 結果を辞書形式に変換
            result = []
            for _, row in top_queries.iterrows():
                result.append({
                    'query': row['query'],
                    'clicks': int(row['clicks']),
                    'impressions': int(row['impressions']),
                    'ctr': float(row['ctr'] * 100),
                    'position': float(row['position'])
                })
            
            logger.info(f"{site_name}: GSCトップクエリTOP{limit}を取得完了")
            return result
            
        except Exception as e:
            logger.error(f"{site_name}: GSCトップクエリ取得エラー: {e}")
            return []
    
    def compare_periods(self, current_data: Dict[str, pd.DataFrame], previous_data: Dict[str, pd.DataFrame]):
        """期間比較分析"""
        try:
            comparison = {
                'current_period': '2025-10-01 - 2025-10-15',
                'previous_period': '2024-10-01 - 2024-10-15',
                'sites': {}
            }
            
            for site_name in ['moodmark', 'moodmarkgift']:
                current_site_data = current_data.get(site_name, pd.DataFrame())
                previous_site_data = previous_data.get(site_name, pd.DataFrame())
                
                if current_site_data.empty or previous_site_data.empty:
                    comparison['sites'][site_name] = {
                        'comparison_available': False,
                        'reason': 'データ不足'
                    }
                    continue
                
                current_summary = self.generate_site_summary(current_site_data, site_name)
                previous_summary = self.generate_site_summary(previous_site_data, site_name)
                
                site_comparison = {
                    'comparison_available': True,
                    'current': current_summary,
                    'previous': previous_summary,
                    'growth_rates': {}
                }
                
                # 成長率の計算
                for metric in ['total_sessions', 'total_users', 'total_pageviews', 'total_conversions']:
                    current_val = current_summary.get(metric, 0)
                    previous_val = previous_summary.get(metric, 0)
                    
                    if previous_val > 0:
                        growth_rate = ((current_val - previous_val) / previous_val) * 100
                        site_comparison['growth_rates'][metric] = {
                            'growth_rate': growth_rate,
                            'direction': 'increase' if growth_rate > 0 else 'decrease'
                        }
                
                comparison['sites'][site_name] = site_comparison
            
            return comparison
            
        except Exception as e:
            logger.error(f"期間比較分析エラー: {e}")
            return {}
    
    def generate_corrected_report(self, start_date: str, end_date: str, previous_start_date: str, previous_end_date: str):
        """修正版レポートの生成"""
        try:
            logger.info("修正版レポート生成開始")
            
            # 現在期間のデータ取得
            current_ga4_data = self.get_ga4_data_for_period(start_date, end_date)
            if current_ga4_data.empty:
                logger.error("現在期間のデータ取得に失敗")
                return None
            
            # 前年同期間のデータ取得
            previous_ga4_data = self.get_ga4_data_for_period(previous_start_date, previous_end_date)
            if previous_ga4_data.empty:
                logger.warning("前年同期間のデータ取得に失敗")
                previous_ga4_data = pd.DataFrame()
            
            # サイト別にデータを分割
            current_sites_data = self.split_data_by_site(current_ga4_data)
            previous_sites_data = self.split_data_by_site(previous_ga4_data) if not previous_ga4_data.empty else {'moodmark': pd.DataFrame(), 'moodmarkgift': pd.DataFrame()}
            
            # レポート生成
            report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'current_period': f"{start_date} - {end_date}",
                    'previous_period': f"{previous_start_date} - {previous_end_date}",
                    'sites_analyzed': ['moodmark', 'moodmarkgift'],
                    'analysis_type': 'pagePath_based_split'
                },
                'sites': {},
                'comparison_analysis': {}
            }
            
            # 各サイトの分析
            for site_name, site_data in current_sites_data.items():
                site_url = f"https://isetan.mistore.jp/{site_name}/"
                
                # GSCデータを取得
                current_gsc_data = self.get_gsc_data_for_period(start_date, end_date, site_url)
                
                # オーガニックランディングページTOP10を取得
                current_organic_pages = self.get_top_organic_landing_pages(site_data, site_name, 10)
                
                # GSCサマリーとトップページ・クエリを取得
                gsc_summary = self.get_gsc_summary(current_gsc_data, site_name)
                top_gsc_pages = self.get_top_gsc_pages(current_gsc_data, site_name, 10)
                top_gsc_queries = self.get_top_gsc_queries(current_gsc_data, site_name, 20)
                
                site_report = {
                    'site_url': site_url,
                    'period': f"{start_date} - {end_date}",
                    'ga4_summary': self.generate_site_summary(site_data, site_name),
                    'gsc_summary': gsc_summary,
                    'top_organic_landing_pages': current_organic_pages,
                    'top_gsc_pages': top_gsc_pages,
                    'top_gsc_queries': top_gsc_queries,
                    'recommendations': []
                }
                
                # 推奨事項の生成
                self._generate_recommendations(site_report)
                
                report['sites'][site_name] = site_report
                
                # データ保存
                if not site_data.empty:
                    filename = f'ga4_{site_name}_corrected_{start_date.replace("-", "")}_{end_date.replace("-", "")}.csv'
                    self.api_integration.export_to_csv(site_data, filename)
                
                if not current_gsc_data.empty:
                    filename = f'gsc_{site_name}_corrected_{start_date.replace("-", "")}_{end_date.replace("-", "")}.csv'
                    self.api_integration.export_to_csv(current_gsc_data, filename)
            
            # 期間比較分析
            if not previous_ga4_data.empty:
                comparison = self.compare_periods(current_sites_data, previous_sites_data)
                report['comparison_analysis'] = comparison
                
                # 各サイトのレポートに比較データを追加
                for site_name in ['moodmark', 'moodmarkgift']:
                    if site_name in comparison['sites']:
                        report['sites'][site_name]['year_over_year_comparison'] = comparison['sites'][site_name]
                        
                        # オーガニックランディングページの前年対比を追加
                        current_organic_pages = report['sites'][site_name].get('top_organic_landing_pages', [])
                        previous_organic_pages = self.get_top_organic_landing_pages(previous_sites_data.get(site_name, pd.DataFrame()), site_name, 10)
                        organic_comparison = self.compare_organic_pages(current_organic_pages, previous_organic_pages, site_name)
                        report['sites'][site_name]['organic_pages_year_over_year'] = organic_comparison
            
            # レポート保存
            report_file = f'data/processed/corrected_report_{start_date.replace("-", "")}_{end_date.replace("-", "")}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # Markdownレポート生成
            markdown_report = self._generate_markdown_report(report)
            markdown_file = f'data/processed/corrected_report_{start_date.replace("-", "")}_{end_date.replace("-", "")}.md'
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_report)
            
            logger.info(f"修正版レポート生成完了: {report_file}")
            return report
            
        except Exception as e:
            logger.error(f"修正版レポート生成エラー: {e}")
            return None
    
    def _generate_recommendations(self, site_report: Dict[str, Any]):
        """推奨事項の生成"""
        recommendations = []
        
        ga4_summary = site_report.get('ga4_summary', {})
        if ga4_summary.get('avg_bounce_rate', 0) > 0.6:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'message': f"バウンス率が{ga4_summary['avg_bounce_rate']:.1%}と高すぎます。コンテンツ改善が必要です。"
            })
        
        if ga4_summary.get('avg_session_duration', 0) < 60:
            recommendations.append({
                'type': 'engagement',
                'priority': 'medium',
                'message': f"平均セッション時間が{ga4_summary['avg_session_duration']:.0f}秒と短すぎます。エンゲージメント向上が必要です。"
            })
        
        site_report['recommendations'] = recommendations
    
    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Markdownレポートの生成"""
        try:
            metadata = report['report_metadata']
            
            markdown = f"""# 📊 MOO-D MARK 修正版期間分析レポート

**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
**分析期間**: {metadata['current_period']}
**前年同期間**: {metadata['previous_period']}
**分析方式**: pagePathベースのサイト分割

## 📈 分析概要

このレポートは、MOO-D MARKの2つのサイトについて、pagePathで分割して分析したものです。

### 分析対象サイト
- **moodmark**: https://isetan.mistore.jp/moodmark/
- **moodmarkgift**: https://isetan.mistore.jp/moodmarkgift/

## 📊 サイト別分析結果

"""
            
            # 各サイトの詳細分析
            for site_name, site_data in report['sites'].items():
                site_display_name = site_name.upper()
                markdown += f"### 🌐 {site_display_name}\n\n"
                markdown += f"**サイトURL**: {site_data.get('site_url', '')}\n\n"
                
                # GA4サマリー
                ga4_summary = site_data.get('ga4_summary', {})
                if ga4_summary:
                    markdown += "#### 📈 GA4 パフォーマンス\n\n"
                    markdown += f"- **総セッション数**: {ga4_summary.get('total_sessions', 0):,}\n"
                    markdown += f"- **総ユーザー数**: {ga4_summary.get('total_users', 0):,}\n"
                    markdown += f"- **総ページビュー数**: {ga4_summary.get('total_pageviews', 0):,}\n"
                    markdown += f"- **平均バウンス率**: {ga4_summary.get('avg_bounce_rate', 0):.1%}\n"
                    markdown += f"- **平均セッション時間**: {ga4_summary.get('avg_session_duration', 0):.0f}秒\n"
                    markdown += f"- **総コンバージョン数**: {ga4_summary.get('total_conversions', 0):,}\n"
                    markdown += f"- **データ行数**: {ga4_summary.get('data_rows', 0):,}\n\n"
                
                # 前年同期間対比
                yoy_comparison = site_data.get('year_over_year_comparison', {})
                if yoy_comparison and yoy_comparison.get('comparison_available', False):
                    markdown += "#### 📊 前年同期間対比\n\n"
                    
                    growth_rates = yoy_comparison.get('growth_rates', {})
                    if growth_rates:
                        markdown += "**主要指標の変化**:\n"
                        for metric, data in growth_rates.items():
                            growth_rate = data.get('growth_rate', 0)
                            direction = "📈" if growth_rate > 0 else "📉" if growth_rate < 0 else "➡️"
                            metric_name = {
                                'total_sessions': 'セッション数',
                                'total_users': 'ユーザー数',
                                'total_pageviews': 'ページビュー数',
                                'total_conversions': 'コンバージョン数'
                            }.get(metric, metric)
                            markdown += f"- {metric_name}: {direction} {growth_rate:+.1f}%\n"
                        markdown += "\n"
                elif yoy_comparison and not yoy_comparison.get('comparison_available', False):
                    markdown += "#### 📊 前年同期間対比\n\n"
                    markdown += f"**比較不可**: {yoy_comparison.get('reason', 'データ不足')}\n\n"
                
                # オーガニックランディングページTOP10
                organic_pages = site_data.get('top_organic_landing_pages', [])
                if organic_pages:
                    markdown += "#### 🔍 オーガニック集客ランディングページ TOP10\n\n"
                    markdown += "| 順位 | ページパス | セッション数 | ユーザー数 | ページビュー数 | バウンス率 | セッション時間 | コンバージョン数 |\n"
                    markdown += "|------|------------|------------|------------|----------------|------------|----------------|------------------|\n"
                    
                    for i, page in enumerate(organic_pages, 1):
                        page_path = page.get('page_path', '')[:50] + "..." if len(page.get('page_path', '')) > 50 else page.get('page_path', '')
                        markdown += f"| {i} | {page_path} | {page.get('sessions', 0):,} | {page.get('users', 0):,} | {page.get('pageviews', 0):,} | {page.get('bounce_rate', 0):.1%} | {page.get('avg_session_duration', 0):.0f}秒 | {page.get('conversions', 0):,} |\n"
                    markdown += "\n"
                
                # オーガニックページの前年対比
                organic_yoy = site_data.get('organic_pages_year_over_year', [])
                if organic_yoy:
                    markdown += "#### 📊 オーガニックページ前年対比\n\n"
                    markdown += "| ページパス | セッション数変化 | ユーザー数変化 | ページビュー数変化 | 状況 |\n"
                    markdown += "|------------|------------------|----------------|-------------------|------|\n"
                    
                    for page_comparison in organic_yoy:
                        page_path = page_comparison.get('page_path', '')[:40] + "..." if len(page_comparison.get('page_path', '')) > 40 else page_comparison.get('page_path', '')
                        
                        if page_comparison.get('has_previous_data', False):
                            growth_rates = page_comparison.get('growth_rates', {})
                            sessions_growth = growth_rates.get('sessions', 0)
                            users_growth = growth_rates.get('users', 0)
                            pageviews_growth = growth_rates.get('pageviews', 0)
                            
                            sessions_emoji = "📈" if sessions_growth > 0 else "📉" if sessions_growth < 0 else "➡️"
                            users_emoji = "📈" if users_growth > 0 else "📉" if users_growth < 0 else "➡️"
                            pageviews_emoji = "📈" if pageviews_growth > 0 else "📉" if pageviews_growth < 0 else "➡️"
                            
                            markdown += f"| {page_path} | {sessions_emoji} {sessions_growth:+.1f}% | {users_emoji} {users_growth:+.1f}% | {pageviews_emoji} {pageviews_growth:+.1f}% | 継続 |\n"
                        else:
                            markdown += f"| {page_path} | 🆕 新規 | 🆕 新規 | 🆕 新規 | 新規ページ |\n"
                    markdown += "\n"
                
                # GSCサマリー
                gsc_summary = site_data.get('gsc_summary', {})
                if gsc_summary:
                    markdown += "#### 🔍 検索エンジン最適化 (SEO)\n\n"
                    markdown += f"- **総クリック数**: {gsc_summary.get('total_clicks', 0):,}\n"
                    markdown += f"- **総インプレッション数**: {gsc_summary.get('total_impressions', 0):,}\n"
                    markdown += f"- **平均CTR**: {gsc_summary.get('avg_ctr', 0):.2f}%\n"
                    markdown += f"- **平均検索順位**: {gsc_summary.get('avg_position', 0):.1f}位\n\n"
                
                # GSCトップページ
                top_gsc_pages = site_data.get('top_gsc_pages', [])
                if top_gsc_pages:
                    markdown += "#### 🏆 GSCトップページ (上位10件)\n\n"
                    markdown += "| 順位 | ページ | クリック数 | インプレッション数 | CTR | 平均順位 |\n"
                    markdown += "|------|--------|------------|-------------------|-----|----------|\n"
                    for i, page in enumerate(top_gsc_pages, 1):
                        page_path = page.get('page', '')[:50] + "..." if len(page.get('page', '')) > 50 else page.get('page', '')
                        markdown += f"| {i} | {page_path} | {page.get('clicks', 0):,} | {page.get('impressions', 0):,} | {page.get('ctr', 0):.2f}% | {page.get('position', 0):.1f} |\n"
                    markdown += "\n"
                
                # GSCトップクエリ
                top_gsc_queries = site_data.get('top_gsc_queries', [])
                if top_gsc_queries:
                    markdown += "#### 🔍 GSCトップクエリ (上位20件)\n\n"
                    markdown += "| 順位 | クエリ | クリック数 | インプレッション数 | CTR | 平均順位 |\n"
                    markdown += "|------|--------|------------|-------------------|-----|----------|\n"
                    for i, query in enumerate(top_gsc_queries, 1):
                        markdown += f"| {i} | {query.get('query', '')} | {query.get('clicks', 0):,} | {query.get('impressions', 0):,} | {query.get('ctr', 0):.2f}% | {query.get('position', 0):.1f} |\n"
                    markdown += "\n"
                
                # 推奨事項
                recommendations = site_data.get('recommendations', [])
                if recommendations:
                    markdown += "#### 💡 推奨事項\n\n"
                    for rec in recommendations:
                        priority_emoji = "🔴" if rec.get('priority') == 'high' else "🟡" if rec.get('priority') == 'medium' else "🟢"
                        markdown += f"- {priority_emoji} **{rec.get('type', '').upper()}**: {rec.get('message', '')}\n"
                    markdown += "\n"
                
                markdown += "---\n\n"
            
            markdown += """## 📋 まとめ

このレポートは、pagePathベースでサイトを分割して分析した修正版です。

### 主要な発見
- 各サイトの実際のパフォーマンス指標を正確に分析
- pagePathによる適切なサイト分割により、正確なデータを取得
- 前年同期間との比較により成長トレンドを把握

### 次のステップ
1. 各サイトの個別改善計画の策定
2. 継続的なモニタリングと改善の実施
3. 定期的なレポート生成による進捗管理

---
*このレポートは修正版として自動生成されました。詳細なデータは添付のCSVファイルをご確認ください。*
"""
            
            return markdown
            
        except Exception as e:
            logger.error(f"Markdownレポート生成エラー: {e}")
            return "レポート生成中にエラーが発生しました。"

def main():
    """メイン実行関数"""
    print("=== 修正版期間分析レポート生成システム ===")
    
    # 分析期間の設定
    current_start_date = "2025-10-01"
    current_end_date = "2025-10-15"
    previous_start_date = "2024-10-01"
    previous_end_date = "2024-10-15"
    
    print(f"分析期間: {current_start_date} - {current_end_date}")
    print(f"前年同期間: {previous_start_date} - {previous_end_date}")
    print("分析方式: pagePathベースのサイト分割")
    
    # システム初期化
    analyzer = CorrectedPeriodAnalysis()
    
    # 修正版レポート生成
    report = analyzer.generate_corrected_report(
        current_start_date, current_end_date,
        previous_start_date, previous_end_date
    )
    
    if report:
        print("\n=== 修正版分析完了 ===")
        print(f"レポートファイル: data/processed/corrected_report_{current_start_date.replace('-', '')}_{current_end_date.replace('-', '')}.json")
        print(f"Markdownレポート: data/processed/corrected_report_{current_start_date.replace('-', '')}_{current_end_date.replace('-', '')}.md")
        
        # 簡単なサマリー表示
        print("\n=== 修正版分析サマリー ===")
        for site_name, site_data in report['sites'].items():
            print(f"\n🌐 {site_name.upper()}")
            ga4_summary = site_data.get('ga4_summary', {})
            
            if ga4_summary:
                print(f"  セッション数: {ga4_summary.get('total_sessions', 0):,}")
                print(f"  ユーザー数: {ga4_summary.get('total_users', 0):,}")
                print(f"  ページビュー数: {ga4_summary.get('total_pageviews', 0):,}")
                print(f"  バウンス率: {ga4_summary.get('avg_bounce_rate', 0):.1%}")
                print(f"  セッション時間: {ga4_summary.get('avg_session_duration', 0):.0f}秒")
                print(f"  コンバージョン数: {ga4_summary.get('total_conversions', 0):,}")
                print(f"  データ行数: {ga4_summary.get('data_rows', 0):,}")
    else:
        print("修正版レポート生成に失敗しました。")

if __name__ == "__main__":
    main()
