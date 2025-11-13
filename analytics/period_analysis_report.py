#!/usr/bin/env python3
"""
期間指定分析レポート生成システム
- 2025/10/1-10/15期間の分析
- 前年同期間対比
- 2サイト別レポート
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
        logging.FileHandler('logs/period_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PeriodAnalysisReport:
    def __init__(self):
        """期間分析レポートシステムの初期化"""
        # OAuth認証を使用
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
                    config = json.load(f)
                return config
            else:
                logger.error("設定ファイルが見つかりません")
                return {}
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            return {}
    
    def get_period_data(self, start_date: str, end_date: str, site_config: Dict[str, str]):
        """
        指定期間のデータを取得
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            site_config (dict): サイト設定
        
        Returns:
            dict: 取得したデータ
        """
        try:
            logger.info(f"期間データ取得開始: {start_date} - {end_date}")
            
            # 一時的にプロパティIDとサイトURLを設定
            original_ga4_property_id = self.api_integration.ga4_property_id
            original_gsc_site_url = self.api_integration.gsc_site_url
            
            self.api_integration.ga4_property_id = site_config.get('ga4_property_id')
            self.api_integration.gsc_site_url = site_config.get('gsc_site_url')
            
            # 日付範囲の計算
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            date_range_days = (end_dt - start_dt).days + 1
            
            # GA4データ取得（期間指定）
            ga4_data = self._get_ga4_data_for_period(start_date, end_date, site_config)
            
            # GSCデータ取得（期間指定）
            gsc_pages = self._get_gsc_pages_for_period(start_date, end_date, site_config)
            gsc_queries = self._get_gsc_queries_for_period(start_date, end_date, site_config)
            
            # 元の設定を復元
            self.api_integration.ga4_property_id = original_ga4_property_id
            self.api_integration.gsc_site_url = original_gsc_site_url
            
            return {
                'ga4_data': ga4_data,
                'gsc_pages': gsc_pages,
                'gsc_queries': gsc_queries,
                'period': f"{start_date} - {end_date}",
                'site_url': site_config.get('url', ''),
                'date_range_days': date_range_days
            }
            
        except Exception as e:
            logger.error(f"期間データ取得エラー: {e}")
            return None
    
    def _get_ga4_data_for_period(self, start_date: str, end_date: str, site_config: Dict[str, str]):
        """期間指定でGA4データを取得"""
        try:
            if not self.api_integration.ga4_service or not site_config.get('ga4_property_id'):
                logger.warning("GA4サービスまたはプロパティIDが設定されていません")
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
            
            # API呼び出し
            response = self.api_integration.ga4_service.properties().runReport(
                property=f"properties/{site_config['ga4_property_id']}",
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
    
    def _get_gsc_pages_for_period(self, start_date: str, end_date: str, site_config: Dict[str, str]):
        """期間指定でGSCページデータを取得"""
        try:
            if not self.api_integration.gsc_service or not site_config.get('gsc_site_url'):
                logger.warning("GSCサービスまたはサイトURLが設定されていません")
                return pd.DataFrame()
            
            # GSCリクエスト作成
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['page'],
                'rowLimit': 10000,
                'startRow': 0
            }
            
            # API呼び出し
            response = self.api_integration.gsc_service.searchanalytics().query(
                siteUrl=site_config['gsc_site_url'],
                body=request
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {
                        'page': row['keys'][0] if row.get('keys') else '',
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    }
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                # CTRとポジションを計算し直し
                df['ctr_calculated'] = (df['clicks'] / df['impressions'] * 100).round(2)
                df['avg_position'] = df['position'].round(2)
                # ソート（クリック数順）
                df = df.sort_values('clicks', ascending=False).reset_index(drop=True)
            
            logger.info(f"GSCページデータ取得完了: {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"GSCページデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def _get_gsc_queries_for_period(self, start_date: str, end_date: str, site_config: Dict[str, str]):
        """期間指定でGSCクエリデータを取得"""
        try:
            if not self.api_integration.gsc_service or not site_config.get('gsc_site_url'):
                logger.warning("GSCサービスまたはサイトURLが設定されていません")
                return pd.DataFrame()
            
            # GSCリクエスト作成
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'rowLimit': 10000,
                'startRow': 0
            }
            
            # API呼び出し
            response = self.api_integration.gsc_service.searchanalytics().query(
                siteUrl=site_config['gsc_site_url'],
                body=request
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {
                        'query': row['keys'][0] if row.get('keys') else '',
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    }
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                # CTRとポジションを計算し直し
                df['ctr_calculated'] = (df['clicks'] / df['impressions'] * 100).round(2)
                df['avg_position'] = df['position'].round(2)
                # ソート（クリック数順）
                df = df.sort_values('clicks', ascending=False).reset_index(drop=True)
            
            logger.info(f"GSCクエリデータ取得完了: {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"GSCクエリデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def generate_site_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """サイト別レポートの生成"""
        try:
            logger.info(f"サイトレポート生成開始: {data['site_url']}")
            
            report = {
                'site_url': data['site_url'],
                'period': data['period'],
                'date_range_days': data['date_range_days'],
                'generated_at': datetime.now().isoformat(),
                'ga4_summary': {},
                'gsc_summary': {},
                'top_pages': [],
                'top_queries': [],
                'recommendations': []
            }
            
            # GA4サマリー
            if not data['ga4_data'].empty:
                ga4_data = data['ga4_data']
                report['ga4_summary'] = {
                    'total_sessions': int(ga4_data['sessions'].sum()) if 'sessions' in ga4_data.columns else 0,
                    'total_users': int(ga4_data['totalUsers'].sum()) if 'totalUsers' in ga4_data.columns else 0,
                    'total_pageviews': int(ga4_data['screenPageViews'].sum()) if 'screenPageViews' in ga4_data.columns else 0,
                    'avg_bounce_rate': float(ga4_data['bounceRate'].mean()) if 'bounceRate' in ga4_data.columns else 0,
                    'avg_session_duration': float(ga4_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in ga4_data.columns else 0,
                    'total_conversions': int(ga4_data['conversions'].sum()) if 'conversions' in ga4_data.columns else 0,
                    'data_rows': len(ga4_data)
                }
            else:
                report['ga4_summary'] = {
                    'total_sessions': 0,
                    'total_users': 0,
                    'total_pageviews': 0,
                    'avg_bounce_rate': 0,
                    'avg_session_duration': 0,
                    'total_conversions': 0,
                    'data_rows': 0
                }
            
            # GSCサマリー（データがある場合のみ）
            if not data['gsc_pages'].empty:
                gsc_pages = data['gsc_pages']
                report['gsc_summary'] = {
                    'total_clicks': gsc_pages['clicks'].sum(),
                    'total_impressions': gsc_pages['impressions'].sum(),
                    'avg_ctr': gsc_pages['ctr_calculated'].mean() if 'ctr_calculated' in gsc_pages.columns else 0,
                    'avg_position': gsc_pages['avg_position'].mean() if 'avg_position' in gsc_pages.columns else 0,
                    'top_pages_count': len(gsc_pages)
                }
                
                # トップページ（上位10件）
                report['top_pages'] = gsc_pages.head(10).to_dict('records')
            else:
                report['gsc_summary'] = {
                    'total_clicks': 0,
                    'total_impressions': 0,
                    'avg_ctr': 0,
                    'avg_position': 0,
                    'top_pages_count': 0
                }
                report['top_pages'] = []
            
            # トップクエリ（データがある場合のみ）
            if not data['gsc_queries'].empty:
                gsc_queries = data['gsc_queries']
                report['gsc_summary']['top_queries_count'] = len(gsc_queries)
                report['top_queries'] = gsc_queries.head(20).to_dict('records')
            else:
                report['gsc_summary']['top_queries_count'] = 0
                report['top_queries'] = []
            
            # 推奨事項の生成
            self._generate_recommendations(report)
            
            logger.info(f"サイトレポート生成完了: {data['site_url']}")
            return report
            
        except Exception as e:
            logger.error(f"サイトレポート生成エラー: {e}")
            return {}
    
    def _generate_recommendations(self, report: Dict[str, Any]):
        """推奨事項の生成"""
        recommendations = []
        
        # GA4関連の推奨事項
        ga4_summary = report.get('ga4_summary', {})
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
        
        # GSC関連の推奨事項
        gsc_summary = report.get('gsc_summary', {})
        if gsc_summary.get('avg_position', 0) > 10:
            recommendations.append({
                'type': 'seo',
                'priority': 'high',
                'message': f"平均検索順位が{gsc_summary['avg_position']:.1f}位と低すぎます。SEO改善が必要です。"
            })
        
        if gsc_summary.get('avg_ctr', 0) < 2:
            recommendations.append({
                'type': 'seo',
                'priority': 'medium',
                'message': f"CTRが{gsc_summary['avg_ctr']:.2f}%と低すぎます。タイトルとメタディスクリプションの最適化が必要です。"
            })
        
        report['recommendations'] = recommendations
    
    def compare_periods(self, current_data: Dict[str, Any], previous_data: Dict[str, Any]) -> Dict[str, Any]:
        """期間比較分析"""
        try:
            logger.info("期間比較分析開始")
            
            comparison = {
                'current_period': current_data['period'],
                'previous_period': previous_data['period'],
                'ga4_comparison': {},
                'gsc_comparison': {},
                'growth_analysis': {}
            }
            
            # GA4比較
            current_ga4 = current_data.get('ga4_summary', {})
            previous_ga4 = previous_data.get('ga4_summary', {})
            
            for metric in ['total_sessions', 'total_users', 'total_pageviews', 'total_conversions', 'total_revenue']:
                current_val = current_ga4.get(metric, 0)
                previous_val = previous_ga4.get(metric, 0)
                
                if previous_val > 0:
                    growth_rate = ((current_val - previous_val) / previous_val) * 100
                    comparison['ga4_comparison'][metric] = {
                        'current': current_val,
                        'previous': previous_val,
                        'growth_rate': growth_rate,
                        'growth_direction': 'increase' if growth_rate > 0 else 'decrease'
                    }
            
            # GSC比較
            current_gsc = current_data.get('gsc_summary', {})
            previous_gsc = previous_data.get('gsc_summary', {})
            
            for metric in ['total_clicks', 'total_impressions']:
                current_val = current_gsc.get(metric, 0)
                previous_val = previous_gsc.get(metric, 0)
                
                if previous_val > 0:
                    growth_rate = ((current_val - previous_val) / previous_val) * 100
                    comparison['gsc_comparison'][metric] = {
                        'current': current_val,
                        'previous': previous_val,
                        'growth_rate': growth_rate,
                        'growth_direction': 'increase' if growth_rate > 0 else 'decrease'
                    }
            
            # 成長分析
            comparison['growth_analysis'] = self._analyze_growth_trends(comparison)
            
            logger.info("期間比較分析完了")
            return comparison
            
        except Exception as e:
            logger.error(f"期間比較分析エラー: {e}")
            return {}
    
    def _analyze_growth_trends(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """成長トレンド分析"""
        growth_analysis = {
            'overall_trend': 'stable',
            'key_insights': [],
            'concerns': []
        }
        
        # GA4成長率の分析
        ga4_growth_rates = []
        for metric, data in comparison.get('ga4_comparison', {}).items():
            growth_rate = data.get('growth_rate', 0)
            ga4_growth_rates.append(growth_rate)
            
            if growth_rate > 20:
                growth_analysis['key_insights'].append(f"{metric}が{growth_rate:.1f}%大幅増加")
            elif growth_rate < -20:
                growth_analysis['concerns'].append(f"{metric}が{abs(growth_rate):.1f}%大幅減少")
        
        # GSC成長率の分析
        gsc_growth_rates = []
        for metric, data in comparison.get('gsc_comparison', {}).items():
            growth_rate = data.get('growth_rate', 0)
            gsc_growth_rates.append(growth_rate)
            
            if growth_rate > 20:
                growth_analysis['key_insights'].append(f"{metric}が{growth_rate:.1f}%大幅増加")
            elif growth_rate < -20:
                growth_analysis['concerns'].append(f"{metric}が{abs(growth_rate):.1f}%大幅減少")
        
        # 全体トレンドの判定
        all_growth_rates = ga4_growth_rates + gsc_growth_rates
        if all_growth_rates:
            avg_growth = sum(all_growth_rates) / len(all_growth_rates)
            if avg_growth > 10:
                growth_analysis['overall_trend'] = 'positive'
            elif avg_growth < -10:
                growth_analysis['overall_trend'] = 'negative'
        
        return growth_analysis
    
    def generate_comprehensive_report(self, start_date: str, end_date: str, previous_start_date: str, previous_end_date: str):
        """包括的レポートの生成"""
        try:
            logger.info("包括的レポート生成開始")
            
            # サイト設定の取得
            sites_config = self.config.get('sites', {})
            
            comprehensive_report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'current_period': f"{start_date} - {end_date}",
                    'previous_period': f"{previous_start_date} - {previous_end_date}",
                    'sites_analyzed': list(sites_config.keys())
                },
                'sites': {},
                'comparison_analysis': {}
            }
            
            # 各サイトの分析
            for site_name, site_config in sites_config.items():
                logger.info(f"サイト分析開始: {site_name}")
                
                # 現在期間のデータ取得
                current_data = self.get_period_data(start_date, end_date, site_config)
                if not current_data:
                    logger.error(f"現在期間のデータ取得に失敗: {site_name}")
                    continue
                
                # 前年同期間のデータ取得
                previous_data = self.get_period_data(previous_start_date, previous_end_date, site_config)
                if not previous_data:
                    logger.warning(f"前年同期間のデータ取得に失敗: {site_name}")
                    previous_data = {}
                
                # サイトレポート生成
                site_report = self.generate_site_report(current_data)
                
                # 期間比較（前年データがある場合）
                if previous_data:
                    comparison = self.compare_periods(current_data, previous_data)
                    site_report['year_over_year_comparison'] = comparison
                
                comprehensive_report['sites'][site_name] = site_report
                
                # データ保存
                self._save_site_data(current_data, site_name, start_date, end_date)
                if previous_data:
                    self._save_site_data(previous_data, site_name, previous_start_date, previous_end_date)
            
            # レポート保存
            report_file = f'data/processed/comprehensive_report_{start_date.replace("-", "")}_{end_date.replace("-", "")}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(comprehensive_report, f, ensure_ascii=False, indent=2)
            
            # Markdownレポート生成
            markdown_report = self._generate_markdown_report(comprehensive_report)
            markdown_file = f'data/processed/comprehensive_report_{start_date.replace("-", "")}_{end_date.replace("-", "")}.md'
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_report)
            
            logger.info(f"包括的レポート生成完了: {report_file}")
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"包括的レポート生成エラー: {e}")
            return None
    
    def _save_site_data(self, data: Dict[str, Any], site_name: str, start_date: str, end_date: str):
        """サイトデータの保存"""
        try:
            timestamp = f"{start_date.replace('-', '')}_{end_date.replace('-', '')}"
            
            # GA4データ保存
            if not data['ga4_data'].empty:
                filename = f'ga4_{site_name}_{timestamp}.csv'
                self.api_integration.export_to_csv(data['ga4_data'], filename)
            
            # GSCページデータ保存
            if not data['gsc_pages'].empty:
                filename = f'gsc_pages_{site_name}_{timestamp}.csv'
                self.api_integration.export_to_csv(data['gsc_pages'], filename)
            
            # GSCクエリデータ保存
            if not data['gsc_queries'].empty:
                filename = f'gsc_queries_{site_name}_{timestamp}.csv'
                self.api_integration.export_to_csv(data['gsc_queries'], filename)
                
        except Exception as e:
            logger.error(f"サイトデータ保存エラー: {e}")
    
    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Markdownレポートの生成"""
        try:
            metadata = report['report_metadata']
            
            markdown = f"""# 📊 MOO-D MARK 期間分析レポート

**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
**分析期間**: {metadata['current_period']}
**前年同期間**: {metadata['previous_period']}

## 📈 分析概要

このレポートは、MOO-D MARKの2つのサイトについて、指定期間のパフォーマンスを分析したものです。

### 分析対象サイト
"""
            
            for site_name, site_data in report['sites'].items():
                site_url = site_data.get('site_url', '')
                markdown += f"- **{site_name}**: {site_url}\n"
            
            markdown += "\n## 📊 サイト別分析結果\n\n"
            
            # 各サイトの詳細分析
            for site_name, site_data in report['sites'].items():
                markdown += f"### 🌐 {site_name.upper()}\n\n"
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
                    markdown += f"- **総収益**: ¥{ga4_summary.get('total_revenue', 0):,.0f}\n\n"
                
                # GSCサマリー
                gsc_summary = site_data.get('gsc_summary', {})
                if gsc_summary:
                    markdown += "#### 🔍 検索エンジン最適化 (SEO)\n\n"
                    markdown += f"- **総クリック数**: {gsc_summary.get('total_clicks', 0):,}\n"
                    markdown += f"- **総インプレッション数**: {gsc_summary.get('total_impressions', 0):,}\n"
                    markdown += f"- **平均CTR**: {gsc_summary.get('avg_ctr', 0):.2f}%\n"
                    markdown += f"- **平均検索順位**: {gsc_summary.get('avg_position', 0):.1f}位\n\n"
                
                # 前年同期間対比
                yoy_comparison = site_data.get('year_over_year_comparison', {})
                if yoy_comparison:
                    markdown += "#### 📊 前年同期間対比\n\n"
                    
                    # GA4比較
                    ga4_comparison = yoy_comparison.get('ga4_comparison', {})
                    if ga4_comparison:
                        markdown += "**GA4指標の変化**:\n"
                        for metric, data in ga4_comparison.items():
                            growth_rate = data.get('growth_rate', 0)
                            direction = "📈" if growth_rate > 0 else "📉" if growth_rate < 0 else "➡️"
                            markdown += f"- {metric}: {direction} {growth_rate:+.1f}%\n"
                        markdown += "\n"
                    
                    # GSC比較
                    gsc_comparison = yoy_comparison.get('gsc_comparison', {})
                    if gsc_comparison:
                        markdown += "**GSC指標の変化**:\n"
                        for metric, data in gsc_comparison.items():
                            growth_rate = data.get('growth_rate', 0)
                            direction = "📈" if growth_rate > 0 else "📉" if growth_rate < 0 else "➡️"
                            markdown += f"- {metric}: {direction} {growth_rate:+.1f}%\n"
                        markdown += "\n"
                    
                    # 成長分析
                    growth_analysis = yoy_comparison.get('growth_analysis', {})
                    if growth_analysis:
                        trend = growth_analysis.get('overall_trend', 'stable')
                        trend_emoji = "📈" if trend == 'positive' else "📉" if trend == 'negative' else "➡️"
                        markdown += f"**全体トレンド**: {trend_emoji} {trend}\n\n"
                        
                        if growth_analysis.get('key_insights'):
                            markdown += "**主要インサイト**:\n"
                            for insight in growth_analysis['key_insights']:
                                markdown += f"- ✅ {insight}\n"
                            markdown += "\n"
                        
                        if growth_analysis.get('concerns'):
                            markdown += "**懸念事項**:\n"
                            for concern in growth_analysis['concerns']:
                                markdown += f"- ⚠️ {concern}\n"
                            markdown += "\n"
                
                # 推奨事項
                recommendations = site_data.get('recommendations', [])
                if recommendations:
                    markdown += "#### 💡 推奨事項\n\n"
                    for rec in recommendations:
                        priority_emoji = "🔴" if rec.get('priority') == 'high' else "🟡" if rec.get('priority') == 'medium' else "🟢"
                        markdown += f"- {priority_emoji} **{rec.get('type', '').upper()}**: {rec.get('message', '')}\n"
                    markdown += "\n"
                
                # トップページ
                top_pages = site_data.get('top_pages', [])
                if top_pages:
                    markdown += "#### 🏆 トップページ (上位10件)\n\n"
                    markdown += "| 順位 | ページ | クリック数 | インプレッション数 | CTR | 平均順位 |\n"
                    markdown += "|------|--------|------------|-------------------|-----|----------|\n"
                    for i, page in enumerate(top_pages[:10], 1):
                        markdown += f"| {i} | {page.get('page', '')[:50]}... | {page.get('clicks', 0):,} | {page.get('impressions', 0):,} | {page.get('ctr_calculated', 0):.2f}% | {page.get('avg_position', 0):.1f} |\n"
                    markdown += "\n"
                
                # トップクエリ
                top_queries = site_data.get('top_queries', [])
                if top_queries:
                    markdown += "#### 🔍 トップクエリ (上位20件)\n\n"
                    markdown += "| 順位 | クエリ | クリック数 | インプレッション数 | CTR | 平均順位 |\n"
                    markdown += "|------|--------|------------|-------------------|-----|----------|\n"
                    for i, query in enumerate(top_queries[:20], 1):
                        markdown += f"| {i} | {query.get('query', '')} | {query.get('clicks', 0):,} | {query.get('impressions', 0):,} | {query.get('ctr_calculated', 0):.2f}% | {query.get('avg_position', 0):.1f} |\n"
                    markdown += "\n"
                
                markdown += "---\n\n"
            
            markdown += """## 📋 まとめ

このレポートは、MOO-D MARKの2つのサイトについて、指定期間のパフォーマンスを詳細に分析したものです。

### 主要な発見
- 各サイトのパフォーマンス指標を詳細に分析
- 前年同期間との比較により成長トレンドを把握
- SEOとユーザーエンゲージメントの改善点を特定

### 次のステップ
1. 推奨事項の優先順位付けと実装計画の策定
2. 継続的なモニタリングと改善の実施
3. 定期的なレポート生成による進捗管理

---
*このレポートは自動生成されました。詳細なデータは添付のCSVファイルをご確認ください。*
"""
            
            return markdown
            
        except Exception as e:
            logger.error(f"Markdownレポート生成エラー: {e}")
            return "レポート生成中にエラーが発生しました。"

def main():
    """メイン実行関数"""
    print("=== 期間分析レポート生成システム ===")
    
    # 分析期間の設定
    current_start_date = "2025-10-01"
    current_end_date = "2025-10-15"
    previous_start_date = "2024-10-01"
    previous_end_date = "2024-10-15"
    
    print(f"分析期間: {current_start_date} - {current_end_date}")
    print(f"前年同期間: {previous_start_date} - {previous_end_date}")
    
    # システム初期化
    analyzer = PeriodAnalysisReport()
    
    # 包括的レポート生成
    report = analyzer.generate_comprehensive_report(
        current_start_date, current_end_date,
        previous_start_date, previous_end_date
    )
    
    if report:
        print("\n=== 分析完了 ===")
        print(f"レポートファイル: data/processed/comprehensive_report_{current_start_date.replace('-', '')}_{current_end_date.replace('-', '')}.json")
        print(f"Markdownレポート: data/processed/comprehensive_report_{current_start_date.replace('-', '')}_{current_end_date.replace('-', '')}.md")
        
        # 簡単なサマリー表示
        print("\n=== 分析サマリー ===")
        for site_name, site_data in report['sites'].items():
            print(f"\n🌐 {site_name.upper()}")
            ga4_summary = site_data.get('ga4_summary', {})
            gsc_summary = site_data.get('gsc_summary', {})
            
            if ga4_summary:
                print(f"  セッション数: {ga4_summary.get('total_sessions', 0):,}")
                print(f"  ユーザー数: {ga4_summary.get('total_users', 0):,}")
                print(f"  ページビュー数: {ga4_summary.get('total_pageviews', 0):,}")
            
            if gsc_summary:
                print(f"  クリック数: {gsc_summary.get('total_clicks', 0):,}")
                print(f"  インプレッション数: {gsc_summary.get('total_impressions', 0):,}")
                print(f"  平均CTR: {gsc_summary.get('avg_ctr', 0):.2f}%")
    else:
        print("レポート生成に失敗しました。")

if __name__ == "__main__":
    main()
