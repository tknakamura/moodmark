#!/usr/bin/env python3
"""
コンテンツパフォーマンス分析ツール
- ページ別のコンバージョン率算出
- 流入チャネル別のパフォーマンス比較
- 高パフォーマンスページの共通パターン抽出
- 改善が必要なページの特定（高トラフィック・低CVR）
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
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
        logging.FileHandler('logs/content_performance_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentPerformanceAnalyzer:
    def __init__(self):
        """コンテンツパフォーマンス分析ツールの初期化"""
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
    
    def get_ga4_data_for_period(self, start_date: str, end_date: str):
        """期間指定でGA4データを取得"""
        try:
            if not self.api_integration.ga4_service:
                logger.warning("GA4サービスが初期化されていません")
                return pd.DataFrame()
            
            # GA4リクエスト作成
            request = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'dimensions': [
                    {'name': 'pagePath'},
                    {'name': 'sessionDefaultChannelGrouping'},
                    {'name': 'deviceCategory'},
                    {'name': 'country'}
                ],
                'metrics': [
                    {'name': 'sessions'},
                    {'name': 'totalUsers'},
                    {'name': 'screenPageViews'},
                    {'name': 'bounceRate'},
                    {'name': 'averageSessionDuration'},
                    {'name': 'conversions'},
                    {'name': 'newUsers'},
                    {'name': 'engagedSessions'}
                ],
                'limit': 10000
            }
            
            # API呼び出し
            response = self.api_integration.ga4_service.properties().runReport(
                property=f"properties/{self.config.get('sites', {}).get('moodmark', {}).get('ga4_property_id', '')}",
                body=request
            ).execute()
            
            # データの変換
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {}
                    
                    # ディメンション
                    for i, dimension in enumerate(request['dimensions']):
                        row_data[dimension['name']] = row['dimensionValues'][i]['value']
                    
                    # メトリクス
                    for i, metric in enumerate(request['metrics']):
                        row_data[metric['name']] = float(row['metricValues'][i]['value'])
                    
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GA4データ取得完了: {len(df)}行")
            return df
            
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return pd.DataFrame()
    
    def segment_data_by_site(self, ga4_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """pagePathでサイトを分割"""
        try:
            if ga4_data.empty:
                return {'moodmark': pd.DataFrame(), 'moodmarkgift': pd.DataFrame()}
            
            # moodmarkデータ（/moodmark/で始まるパス）
            moodmark_data = ga4_data[ga4_data['pagePath'].str.startswith('/moodmark/', na=False)].copy()
            
            # moodmarkgiftデータ（/moodmarkgift/で始まるパス）
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
    
    def calculate_page_conversion_rates(self, site_data: pd.DataFrame, site_name: str) -> pd.DataFrame:
        """ページ別のコンバージョン率算出"""
        try:
            if site_data.empty:
                return pd.DataFrame()
            
            # ページ別で集計
            page_stats = site_data.groupby('pagePath').agg({
                'sessions': 'sum',
                'totalUsers': 'sum',
                'screenPageViews': 'sum',
                'bounceRate': 'mean',
                'averageSessionDuration': 'mean',
                'conversions': 'sum',
                'newUsers': 'sum',
                'engagedSessions': 'sum'
            }).reset_index()
            
            # コンバージョン率を計算
            page_stats['conversion_rate'] = (page_stats['conversions'] / page_stats['sessions'] * 100).fillna(0)
            page_stats['engagement_rate'] = (page_stats['engagedSessions'] / page_stats['sessions'] * 100).fillna(0)
            page_stats['new_user_rate'] = (page_stats['newUsers'] / page_stats['totalUsers'] * 100).fillna(0)
            
            # 最小セッション数でフィルタリング
            page_stats = page_stats[page_stats['sessions'] >= 10]
            
            # コンバージョン率でソート
            page_stats = page_stats.sort_values('conversion_rate', ascending=False)
            
            logger.info(f"{site_name}: ページ別CVR分析完了 - {len(page_stats)}ページ")
            return page_stats
            
        except Exception as e:
            logger.error(f"{site_name}: ページ別CVR分析エラー: {e}")
            return pd.DataFrame()
    
    def analyze_channel_performance(self, site_data: pd.DataFrame, site_name: str) -> Dict:
        """流入チャネル別のパフォーマンス比較"""
        try:
            if site_data.empty:
                return {}
            
            # チャネル別で集計
            channel_stats = site_data.groupby('sessionDefaultChannelGrouping').agg({
                'sessions': 'sum',
                'totalUsers': 'sum',
                'screenPageViews': 'sum',
                'bounceRate': 'mean',
                'averageSessionDuration': 'mean',
                'conversions': 'sum',
                'newUsers': 'sum',
                'engagedSessions': 'sum'
            }).reset_index()
            
            # メトリクス計算
            channel_stats['conversion_rate'] = (channel_stats['conversions'] / channel_stats['sessions'] * 100).fillna(0)
            channel_stats['engagement_rate'] = (channel_stats['engagedSessions'] / channel_stats['sessions'] * 100).fillna(0)
            channel_stats['new_user_rate'] = (channel_stats['newUsers'] / channel_stats['totalUsers'] * 100).fillna(0)
            channel_stats['pages_per_session'] = channel_stats['screenPageViews'] / channel_stats['sessions']
            
            # セッション数でソート
            channel_stats = channel_stats.sort_values('sessions', ascending=False)
            
            # 結果を辞書形式に変換
            result = []
            for _, row in channel_stats.iterrows():
                result.append({
                    'channel': row['sessionDefaultChannelGrouping'],
                    'sessions': int(row['sessions']),
                    'users': int(row['totalUsers']),
                    'pageviews': int(row['screenPageViews']),
                    'bounce_rate': round(row['bounceRate'] * 100, 2),
                    'avg_session_duration': round(row['averageSessionDuration'], 1),
                    'conversions': int(row['conversions']),
                    'conversion_rate': round(row['conversion_rate'], 2),
                    'engagement_rate': round(row['engagement_rate'], 2),
                    'new_user_rate': round(row['new_user_rate'], 2),
                    'pages_per_session': round(row['pages_per_session'], 2)
                })
            
            logger.info(f"{site_name}: チャネル別パフォーマンス分析完了 - {len(result)}チャネル")
            return {'channels': result}
            
        except Exception as e:
            logger.error(f"{site_name}: チャネル別パフォーマンス分析エラー: {e}")
            return {}
    
    def identify_high_performance_patterns(self, page_stats: pd.DataFrame, site_name: str) -> Dict:
        """高パフォーマンスページの共通パターン抽出"""
        try:
            if page_stats.empty:
                return {}
            
            # 高CVRページの定義（上位20%またはCVR 5%以上）
            high_cvr_threshold = max(page_stats['conversion_rate'].quantile(0.8), 5.0)
            high_cvr_pages = page_stats[page_stats['conversion_rate'] >= high_cvr_threshold].copy()
            
            if high_cvr_pages.empty:
                logger.warning(f"{site_name}: 高CVRページが見つかりません")
                return {}
            
            # パターン分析
            patterns = {
                'high_cvr_pages_count': len(high_cvr_pages),
                'avg_cvr_high_performers': round(high_cvr_pages['conversion_rate'].mean(), 2),
                'avg_sessions_high_performers': round(high_cvr_pages['sessions'].mean(), 0),
                'avg_bounce_rate_high_performers': round(high_cvr_pages['bounceRate'].mean() * 100, 2),
                'avg_session_duration_high_performers': round(high_cvr_pages['averageSessionDuration'].mean(), 1),
                'common_path_patterns': self._analyze_path_patterns(high_cvr_pages),
                'performance_insights': self._generate_performance_insights(high_cvr_pages)
            }
            
            logger.info(f"{site_name}: 高パフォーマンスパターン分析完了")
            return patterns
            
        except Exception as e:
            logger.error(f"{site_name}: 高パフォーマンスパターン分析エラー: {e}")
            return {}
    
    def _analyze_path_patterns(self, high_cvr_pages: pd.DataFrame) -> List[Dict]:
        """パスパターンの分析"""
        patterns = []
        
        # カテゴリ別の分析
        categories = {}
        for _, row in high_cvr_pages.iterrows():
            path = row['pagePath']
            cvr = row['conversion_rate']
            
            # カテゴリの抽出
            if '/beauty/' in path:
                category = 'beauty'
            elif '/wedding/' in path:
                category = 'wedding'
            elif '/birthday/' in path:
                category = 'birthday'
            elif '/christmas/' in path:
                category = 'christmas'
            elif '/mombaby/' in path:
                category = 'mombaby'
            elif '/temiyage/' in path:
                category = 'temiyage'
            elif '/foods-drink/' in path:
                category = 'foods-drink'
            else:
                category = 'other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append(cvr)
        
        # カテゴリ別の平均CVRを計算
        for category, cvrs in categories.items():
            if len(cvrs) >= 2:  # 2ページ以上あるカテゴリのみ
                patterns.append({
                    'category': category,
                    'page_count': len(cvrs),
                    'avg_cvr': round(sum(cvrs) / len(cvrs), 2),
                    'max_cvr': round(max(cvrs), 2),
                    'pattern_type': 'category_performance'
                })
        
        return sorted(patterns, key=lambda x: x['avg_cvr'], reverse=True)
    
    def _generate_performance_insights(self, high_cvr_pages: pd.DataFrame) -> List[str]:
        """パフォーマンスインサイトの生成"""
        insights = []
        
        # バウンス率の分析
        avg_bounce_rate = high_cvr_pages['bounceRate'].mean() * 100
        if avg_bounce_rate < 20:
            insights.append("高CVRページは低バウンス率（20%未満）の傾向")
        elif avg_bounce_rate < 40:
            insights.append("高CVRページは中程度のバウンス率（20-40%）")
        else:
            insights.append("高CVRページでもバウンス率が高い（40%以上）")
        
        # セッション時間の分析
        avg_duration = high_cvr_pages['averageSessionDuration'].mean()
        if avg_duration > 120:
            insights.append("高CVRページは長いセッション時間（2分以上）")
        elif avg_duration > 60:
            insights.append("高CVRページは中程度のセッション時間（1-2分）")
        else:
            insights.append("高CVRページは短いセッション時間（1分未満）")
        
        # セッション数の分析
        avg_sessions = high_cvr_pages['sessions'].mean()
        if avg_sessions > 1000:
            insights.append("高CVRページは高トラフィック（1,000セッション以上）")
        elif avg_sessions > 100:
            insights.append("高CVRページは中程度のトラフィック（100-1,000セッション）")
        else:
            insights.append("高CVRページは低トラフィック（100セッション未満）")
        
        return insights
    
    def identify_improvement_opportunities(self, page_stats: pd.DataFrame, site_name: str) -> Dict:
        """改善が必要なページの特定（4象限分析）"""
        try:
            if page_stats.empty:
                return {}
            
            # 閾値の設定
            high_traffic_threshold = page_stats['sessions'].quantile(0.7)  # 上位30%
            high_cvr_threshold = page_stats['conversion_rate'].quantile(0.7)  # 上位30%
            
            # 4象限に分類
            opportunities = {
                'high_priority': [],  # 高トラフィック・低CVR
                'reinforce': [],      # 高トラフィック・高CVR
                'maintain': [],       # 低トラフィック・高CVR
                'low_priority': []    # 低トラフィック・低CVR
            }
            
            for _, row in page_stats.iterrows():
                page_info = {
                    'page_path': row['pagePath'],
                    'sessions': int(row['sessions']),
                    'conversion_rate': round(row['conversion_rate'], 2),
                    'conversions': int(row['conversions']),
                    'bounce_rate': round(row['bounceRate'] * 100, 2),
                    'avg_session_duration': round(row['averageSessionDuration'], 1)
                }
                
                is_high_traffic = row['sessions'] >= high_traffic_threshold
                is_high_cvr = row['conversion_rate'] >= high_cvr_threshold
                
                if is_high_traffic and not is_high_cvr:
                    opportunities['high_priority'].append(page_info)
                elif is_high_traffic and is_high_cvr:
                    opportunities['reinforce'].append(page_info)
                elif not is_high_traffic and is_high_cvr:
                    opportunities['maintain'].append(page_info)
                else:
                    opportunities['low_priority'].append(page_info)
            
            # 各カテゴリをセッション数でソート
            for category in opportunities:
                opportunities[category].sort(key=lambda x: x['sessions'], reverse=True)
            
            # 改善提案の生成
            opportunities['improvement_suggestions'] = self._generate_improvement_suggestions(opportunities)
            
            logger.info(f"{site_name}: 改善機会分析完了")
            logger.info(f"  - 最優先改善: {len(opportunities['high_priority'])}ページ")
            logger.info(f"  - 強化推奨: {len(opportunities['reinforce'])}ページ")
            logger.info(f"  - 維持: {len(opportunities['maintain'])}ページ")
            logger.info(f"  - 低優先: {len(opportunities['low_priority'])}ページ")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"{site_name}: 改善機会分析エラー: {e}")
            return {}
    
    def _generate_improvement_suggestions(self, opportunities: Dict) -> List[Dict]:
        """改善提案の生成"""
        suggestions = []
        
        # 最優先改善ページの提案
        for page in opportunities['high_priority'][:5]:
            suggestions.append({
                'page_path': page['page_path'],
                'priority': 'high',
                'current_cvr': page['conversion_rate'],
                'sessions': page['sessions'],
                'potential_impact': f"+{int(page['sessions'] * 0.02)} CV/月（CVR 2%改善時）",
                'suggested_actions': [
                    "CTAボタンの最適化",
                    "ページ速度の改善",
                    "コンテンツの充実",
                    "ユーザビリティの向上"
                ]
            })
        
        # 強化推奨ページの提案
        for page in opportunities['reinforce'][:3]:
            suggestions.append({
                'page_path': page['page_path'],
                'priority': 'medium',
                'current_cvr': page['conversion_rate'],
                'sessions': page['sessions'],
                'potential_impact': f"成功パターンの他ページへの展開",
                'suggested_actions': [
                    "成功要因の分析",
                    "他ページへの横展開",
                    "さらなる最適化"
                ]
            })
        
        return suggestions
    
    def generate_content_performance_report(self, start_date: str, end_date: str, min_sessions: int = 10):
        """コンテンツパフォーマンス分析レポートの生成"""
        try:
            logger.info("コンテンツパフォーマンス分析レポート生成開始")
            
            # GA4データ取得
            ga4_data = self.get_ga4_data_for_period(start_date, end_date)
            if ga4_data.empty:
                logger.error("GA4データが取得できませんでした")
                return
            
            # サイト別に分割
            sites_data = self.segment_data_by_site(ga4_data)
            
            report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'analysis_period': f"{start_date} - {end_date}",
                    'min_sessions_filter': min_sessions,
                    'analysis_type': 'content_performance_analyzer'
                },
                'sites': {}
            }
            
            # 各サイトの分析
            for site_name, site_data in sites_data.items():
                if site_data.empty:
                    continue
                
                logger.info(f"{site_name}のコンテンツパフォーマンス分析開始")
                
                # ページ別CVR分析
                page_stats = self.calculate_page_conversion_rates(site_data, site_name)
                
                # チャネル別パフォーマンス分析
                channel_performance = self.analyze_channel_performance(site_data, site_name)
                
                # 高パフォーマンスパターン分析
                high_performance_patterns = self.identify_high_performance_patterns(page_stats, site_name)
                
                # 改善機会分析
                improvement_opportunities = self.identify_improvement_opportunities(page_stats, site_name)
                
                site_report = {
                    'site_name': site_name,
                    'total_pages_analyzed': len(page_stats),
                    'page_performance': page_stats.to_dict('records') if not page_stats.empty else [],
                    'channel_performance': channel_performance,
                    'high_performance_patterns': high_performance_patterns,
                    'improvement_opportunities': improvement_opportunities,
                    'summary_metrics': {
                        'avg_conversion_rate': round(page_stats['conversion_rate'].mean(), 2) if not page_stats.empty else 0,
                        'total_sessions': int(site_data['sessions'].sum()),
                        'total_conversions': int(site_data['conversions'].sum()),
                        'high_cvr_pages_count': len(page_stats[page_stats['conversion_rate'] >= 5.0]) if not page_stats.empty else 0
                    }
                }
                
                report['sites'][site_name] = site_report
                
                # データ保存
                if not page_stats.empty:
                    filename = f'content_performance_{site_name}_{start_date.replace("-", "")}_{end_date.replace("-", "")}.csv'
                    self.api_integration.export_to_csv(page_stats, filename)
            
            # レポート保存
            report_file = f'data/processed/content_performance_{start_date.replace("-", "")}_{end_date.replace("-", "")}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # Markdownレポート生成
            self._generate_markdown_report(report, start_date, end_date)
            
            logger.info(f"コンテンツパフォーマンス分析レポート生成完了: {report_file}")
            
        except Exception as e:
            logger.error(f"コンテンツパフォーマンス分析レポート生成エラー: {e}")
    
    def _generate_markdown_report(self, report: Dict, start_date: str, end_date: str):
        """Markdownレポートの生成"""
        try:
            markdown = f"""# 📊 コンテンツパフォーマンス分析レポート

**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
**分析期間**: {start_date} - {end_date}
**分析方式**: GA4 API連携による包括的コンテンツ分析

## 📈 分析概要

このレポートは、GA4のデータを活用してコンテンツのパフォーマンスを分析し、改善機会を特定したものです。

### 分析対象サイト
"""
            
            for site_name, site_data in report['sites'].items():
                summary = site_data.get('summary_metrics', {})
                markdown += f"- **{site_name}**: {summary.get('total_pages_analyzed', 0)}ページ分析\n"
                markdown += f"  - 総セッション数: {summary.get('total_sessions', 0):,}\n"
                markdown += f"  - 総コンバージョン数: {summary.get('total_conversions', 0):,}\n"
                markdown += f"  - 平均CVR: {summary.get('avg_conversion_rate', 0):.2f}%\n"
                markdown += f"  - 高CVRページ数: {summary.get('high_cvr_pages_count', 0)}ページ\n\n"
            
            # 各サイトの詳細分析
            for site_name, site_data in report['sites'].items():
                markdown += f"## 🌐 {site_name.upper()}\n\n"
                
                # サマリーメトリクス
                summary = site_data.get('summary_metrics', {})
                markdown += f"### 📊 サマリーメトリクス\n\n"
                markdown += f"- **分析ページ数**: {site_data.get('total_pages_analyzed', 0)}ページ\n"
                markdown += f"- **平均CVR**: {summary.get('avg_conversion_rate', 0):.2f}%\n"
                markdown += f"- **高CVRページ数**: {summary.get('high_cvr_pages_count', 0)}ページ\n\n"
                
                # チャネル別パフォーマンス
                channel_perf = site_data.get('channel_performance', {})
                if channel_perf.get('channels'):
                    markdown += "### 🔄 流入チャネル別パフォーマンス\n\n"
                    markdown += "| チャネル | セッション数 | CVR | バウンス率 | セッション時間 | エンゲージメント率 |\n"
                    markdown += "|----------|------------|-----|------------|----------------|------------------|\n"
                    
                    for channel in channel_perf['channels'][:10]:
                        markdown += f"| {channel['channel']} | {channel['sessions']:,} | {channel['conversion_rate']}% | {channel['bounce_rate']}% | {channel['avg_session_duration']}秒 | {channel['engagement_rate']}% |\n"
                    markdown += "\n"
                
                # 高パフォーマンスパターン
                patterns = site_data.get('high_performance_patterns', {})
                if patterns.get('high_cvr_pages_count', 0) > 0:
                    markdown += "### 🏆 高パフォーマンスパターン\n\n"
                    markdown += f"- **高CVRページ数**: {patterns.get('high_cvr_pages_count', 0)}ページ\n"
                    markdown += f"- **平均CVR**: {patterns.get('avg_cvr_high_performers', 0):.2f}%\n"
                    markdown += f"- **平均バウンス率**: {patterns.get('avg_bounce_rate_high_performers', 0):.2f}%\n"
                    markdown += f"- **平均セッション時間**: {patterns.get('avg_session_duration_high_performers', 0):.1f}秒\n\n"
                    
                    # カテゴリ別パフォーマンス
                    if patterns.get('common_path_patterns'):
                        markdown += "#### 📂 カテゴリ別パフォーマンス\n\n"
                        markdown += "| カテゴリ | ページ数 | 平均CVR | 最高CVR |\n"
                        markdown += "|----------|----------|---------|----------|\n"
                        
                        for pattern in patterns['common_path_patterns'][:5]:
                            markdown += f"| {pattern['category']} | {pattern['page_count']} | {pattern['avg_cvr']}% | {pattern['max_cvr']}% |\n"
                        markdown += "\n"
                    
                    # パフォーマンスインサイト
                    if patterns.get('performance_insights'):
                        markdown += "#### 💡 パフォーマンスインサイト\n\n"
                        for insight in patterns['performance_insights']:
                            markdown += f"- {insight}\n"
                        markdown += "\n"
                
                # 改善機会
                opportunities = site_data.get('improvement_opportunities', {})
                if opportunities.get('high_priority'):
                    markdown += "### 🎯 改善機会分析\n\n"
                    markdown += f"#### 🔴 最優先改善（高トラフィック・低CVR）\n\n"
                    markdown += "| ページパス | セッション数 | 現在CVR | 改善余地 |\n"
                    markdown += "|------------|------------|---------|----------|\n"
                    
                    for page in opportunities['high_priority'][:10]:
                        improvement_potential = f"+{int(page['sessions'] * 0.02)} CV/月"
                        markdown += f"| {page['page_path'][:50]}... | {page['sessions']:,} | {page['conversion_rate']}% | {improvement_potential} |\n"
                    markdown += "\n"
                
                if opportunities.get('improvement_suggestions'):
                    markdown += "#### 💡 改善提案\n\n"
                    for suggestion in opportunities['improvement_suggestions'][:5]:
                        priority_emoji = "🔴" if suggestion['priority'] == 'high' else "🟡"
                        markdown += f"{priority_emoji} **{suggestion['page_path'][:40]}...**\n"
                        markdown += f"   - 現在CVR: {suggestion['current_cvr']}%\n"
                        markdown += f"   - 期待効果: {suggestion['potential_impact']}\n"
                        markdown += f"   - 推奨施策: {', '.join(suggestion['suggested_actions'][:2])}\n\n"
                
                markdown += "---\n\n"
            
            markdown += """## 📋 まとめ

### 主要な発見
- 高パフォーマンスページの共通パターンを特定
- 改善が必要なページの優先順位を明確化
- 流入チャネル別のパフォーマンス差を可視化

### 次のステップ
1. 最優先改善ページのCVR向上施策実施
2. 高パフォーマンスパターンの他ページへの展開
3. 低パフォーマンスチャネルの改善
4. 定期的なモニタリングと改善

---
*このレポートはコンテンツパフォーマンス分析ツールにより自動生成されました。*
"""
            
            # ファイル保存
            markdown_file = f'data/processed/content_performance_{start_date.replace("-", "")}_{end_date.replace("-", "")}.md'
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            logger.info(f"Markdownレポート生成完了: {markdown_file}")
            
        except Exception as e:
            logger.error(f"Markdownレポート生成エラー: {e}")

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='コンテンツパフォーマンス分析ツール')
    parser.add_argument('--start-date', required=True, help='分析開始日 (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='分析終了日 (YYYY-MM-DD)')
    parser.add_argument('--min-sessions', type=int, default=10, help='最小セッション数フィルター')
    
    args = parser.parse_args()
    
    print("=== コンテンツパフォーマンス分析ツール ===")
    print(f"分析期間: {args.start_date} - {args.end_date}")
    print(f"最小セッション数: {args.min_sessions}")
    print()
    
    analyzer = ContentPerformanceAnalyzer()
    analyzer.generate_content_performance_report(
        start_date=args.start_date,
        end_date=args.end_date,
        min_sessions=args.min_sessions
    )
    
    print("=== コンテンツパフォーマンス分析完了 ===")
    print(f"レポートファイル: data/processed/content_performance_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}.json")
    print(f"Markdownレポート: data/processed/content_performance_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}.md")

if __name__ == "__main__":
    main()







