#!/usr/bin/env python3
"""
SEO機会発見ツール
- 検索順位4-10位のクエリ抽出（順位向上で大幅トラフィック増が見込める）
- 高インプレッション・低CTRクエリの特定（タイトル/ディスクリプション改善候補）
- 競合に負けているクエリの分析
- 季節性・トレンド分析（前年同期比での機会発見）
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
        logging.FileHandler('logs/seo_opportunity_finder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SEOOpportunityFinder:
    def __init__(self):
        """SEO機会発見ツールの初期化"""
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
                'rowLimit': 25000,
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
    
    def find_ranking_improvement_opportunities(self, gsc_data: pd.DataFrame, site_name: str) -> List[Dict]:
        """検索順位4-10位のクエリを抽出（順位向上で大幅トラフィック増が見込める）"""
        try:
            if gsc_data.empty:
                return []
            
            # 順位4-10位のクエリをフィルタリング
            opportunities = gsc_data[
                (gsc_data['position'] >= 4.0) & 
                (gsc_data['position'] <= 10.0) &
                (gsc_data['impressions'] >= 100)  # 最低インプレッション数
            ].copy()
            
            if opportunities.empty:
                logger.warning(f"{site_name}: 順位改善機会が見つかりません")
                return []
            
            # インプレッション数でソート
            opportunities = opportunities.sort_values('impressions', ascending=False)
            
            # 結果を辞書形式に変換
            result = []
            for _, row in opportunities.head(50).iterrows():  # TOP50
                # 順位改善時の予想トラフィック増加を計算
                current_position = row['position']
                current_clicks = row['clicks']
                current_impressions = row['impressions']
                
                # 順位別CTRの推定値（業界平均）
                position_ctr_map = {
                    1: 0.30, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05,
                    6: 0.04, 7: 0.03, 8: 0.02, 9: 0.02, 10: 0.01
                }
                
                # 3位達成時の予想クリック数
                target_position = 3
                target_ctr = position_ctr_map.get(target_position, 0.10)
                predicted_clicks = current_impressions * target_ctr
                traffic_increase = predicted_clicks - current_clicks
                
                result.append({
                    'query': row['query'],
                    'page': row['page'],
                    'current_position': round(current_position, 1),
                    'current_clicks': int(current_clicks),
                    'current_impressions': int(current_impressions),
                    'current_ctr': round(row['ctr'] * 100, 2),
                    'target_position': target_position,
                    'predicted_traffic_increase': int(traffic_increase),
                    'priority_score': int(current_impressions * (10 - current_position)),  # 優先度スコア
                    'improvement_potential': 'high' if traffic_increase > 1000 else 'medium' if traffic_increase > 500 else 'low'
                })
            
            logger.info(f"{site_name}: 順位改善機会{len(result)}件を発見")
            return result
            
        except Exception as e:
            logger.error(f"{site_name}: 順位改善機会分析エラー: {e}")
            return []
    
    def find_ctr_improvement_opportunities(self, gsc_data: pd.DataFrame, site_name: str) -> List[Dict]:
        """高インプレッション・低CTRクエリの特定（タイトル/ディスクリプション改善候補）"""
        try:
            if gsc_data.empty:
                return []
            
            # 平均CTRを計算
            avg_ctr = gsc_data['ctr'].mean()
            
            # 高インプレッション・低CTRクエリをフィルタリング
            opportunities = gsc_data[
                (gsc_data['impressions'] >= 1000) &  # 高インプレッション
                (gsc_data['ctr'] < avg_ctr * 0.7) &  # 平均CTRの70%未満
                (gsc_data['position'] <= 10)  # 上位10位以内
            ].copy()
            
            if opportunities.empty:
                logger.warning(f"{site_name}: CTR改善機会が見つかりません")
                return []
            
            # インプレッション数でソート
            opportunities = opportunities.sort_values('impressions', ascending=False)
            
            # 結果を辞書形式に変換
            result = []
            for _, row in opportunities.head(30).iterrows():  # TOP30
                current_ctr = row['ctr']
                current_impressions = row['impressions']
                current_clicks = row['clicks']
                
                # CTR改善時の予想クリック増加
                target_ctr = avg_ctr * 1.2  # 平均CTRの120%を目標
                predicted_clicks = current_impressions * target_ctr
                click_increase = predicted_clicks - current_clicks
                
                result.append({
                    'query': row['query'],
                    'page': row['page'],
                    'current_ctr': round(current_ctr * 100, 2),
                    'current_clicks': int(current_clicks),
                    'current_impressions': int(current_impressions),
                    'current_position': round(row['position'], 1),
                    'target_ctr': round(target_ctr * 100, 2),
                    'predicted_click_increase': int(click_increase),
                    'improvement_potential': 'high' if click_increase > 500 else 'medium' if click_increase > 200 else 'low',
                    'suggested_actions': self._generate_ctr_improvement_suggestions(row['query'], row['position'])
                })
            
            logger.info(f"{site_name}: CTR改善機会{len(result)}件を発見")
            return result
            
        except Exception as e:
            logger.error(f"{site_name}: CTR改善機会分析エラー: {e}")
            return []
    
    def _generate_ctr_improvement_suggestions(self, query: str, position: float) -> List[str]:
        """CTR改善のための具体的な提案を生成"""
        suggestions = []
        
        if position <= 3:
            suggestions.append("タイトルタグに年号や最新性を追加")
            suggestions.append("ディスクリプションに価格帯や特徴を明記")
        elif position <= 6:
            suggestions.append("タイトルタグの最適化")
            suggestions.append("ディスクリプションの改善")
            suggestions.append("構造化データの追加")
        else:
            suggestions.append("コンテンツの充実")
            suggestions.append("内部リンクの強化")
            suggestions.append("ページ速度の最適化")
        
        # クエリに応じた具体的な提案
        if "プレゼント" in query:
            suggestions.append("ギフト感を演出する画像の追加")
        if "誕生日" in query or "クリスマス" in query:
            suggestions.append("季節性を強調したタイトル")
        if "男性" in query or "女性" in query:
            suggestions.append("性別に特化したコンテンツ")
        
        return suggestions[:3]  # 上位3つの提案
    
    def analyze_seasonal_trends(self, current_data: pd.DataFrame, previous_data: pd.DataFrame, site_name: str) -> Dict:
        """季節性・トレンド分析（前年同期比での機会発見）"""
        try:
            if current_data.empty or previous_data.empty:
                return {
                    'growing_queries': [],
                    'declining_queries': [],
                    'new_queries': [],
                    'trend_analysis': 'データ不足のため分析不可'
                }
            
            # クエリ別の集計
            current_queries = current_data.groupby('query').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            previous_queries = previous_data.groupby('query').agg({
                'clicks': 'sum',
                'impressions': 'sum',
                'ctr': 'mean',
                'position': 'mean'
            }).reset_index()
            
            # 前年データをキーとした辞書を作成
            previous_dict = {row['query']: row for _, row in previous_queries.iterrows()}
            
            growing_queries = []
            declining_queries = []
            new_queries = []
            
            for _, current_row in current_queries.iterrows():
                query = current_row['query']
                previous_row = previous_dict.get(query)
                
                if previous_row:
                    # 成長率を計算
                    clicks_growth = ((current_row['clicks'] - previous_row['clicks']) / previous_row['clicks'] * 100) if previous_row['clicks'] > 0 else 0
                    impressions_growth = ((current_row['impressions'] - previous_row['impressions']) / previous_row['impressions'] * 100) if previous_row['impressions'] > 0 else 0
                    
                    if clicks_growth > 50 and current_row['clicks'] > 100:  # 50%以上成長かつ100クリック以上
                        growing_queries.append({
                            'query': query,
                            'current_clicks': int(current_row['clicks']),
                            'previous_clicks': int(previous_row['clicks']),
                            'clicks_growth': round(clicks_growth, 1),
                            'current_impressions': int(current_row['impressions']),
                            'impressions_growth': round(impressions_growth, 1),
                            'current_position': round(current_row['position'], 1),
                            'previous_position': round(previous_row['position'], 1)
                        })
                    elif clicks_growth < -30 and previous_row['clicks'] > 100:  # 30%以上減少
                        declining_queries.append({
                            'query': query,
                            'current_clicks': int(current_row['clicks']),
                            'previous_clicks': int(previous_row['clicks']),
                            'clicks_growth': round(clicks_growth, 1),
                            'reason': '順位低下' if current_row['position'] > previous_row['position'] else '需要減少'
                        })
                else:
                    # 新規クエリ
                    if current_row['clicks'] > 50:  # 50クリック以上の新規クエリ
                        new_queries.append({
                            'query': query,
                            'clicks': int(current_row['clicks']),
                            'impressions': int(current_row['impressions']),
                            'position': round(current_row['position'], 1),
                            'ctr': round(current_row['ctr'] * 100, 2)
                        })
            
            # 成長クエリをクリック数でソート
            growing_queries.sort(key=lambda x: x['current_clicks'], reverse=True)
            declining_queries.sort(key=lambda x: x['clicks_growth'])
            new_queries.sort(key=lambda x: x['clicks'], reverse=True)
            
            logger.info(f"{site_name}: 成長クエリ{len(growing_queries)}件、減少クエリ{len(declining_queries)}件、新規クエリ{len(new_queries)}件を発見")
            
            return {
                'growing_queries': growing_queries[:20],  # TOP20
                'declining_queries': declining_queries[:20],  # TOP20
                'new_queries': new_queries[:20],  # TOP20
                'trend_analysis': f"成長クエリ{len(growing_queries)}件、減少クエリ{len(declining_queries)}件、新規クエリ{len(new_queries)}件"
            }
            
        except Exception as e:
            logger.error(f"{site_name}: 季節性トレンド分析エラー: {e}")
            return {
                'growing_queries': [],
                'declining_queries': [],
                'new_queries': [],
                'trend_analysis': f'分析エラー: {e}'
            }
    
    def compare_sites_performance(self, moodmark_data: pd.DataFrame, moodmarkgift_data: pd.DataFrame) -> Dict:
        """両サイトのパフォーマンス比較"""
        try:
            comparison = {
                'moodmark': self._calculate_site_metrics(moodmark_data, 'moodmark'),
                'moodmarkgift': self._calculate_site_metrics(moodmarkgift_data, 'moodmarkgift'),
                'comparison_insights': []
            }
            
            # 比較インサイトの生成
            moodmark_metrics = comparison['moodmark']
            moodmarkgift_metrics = comparison['moodmarkgift']
            
            if moodmark_metrics['total_clicks'] > moodmarkgift_metrics['total_clicks']:
                comparison['comparison_insights'].append({
                    'insight': 'moodmarkがmoodmarkgiftより多くのクリックを獲得',
                    'difference': f"{moodmark_metrics['total_clicks'] - moodmarkgift_metrics['total_clicks']:,}クリック",
                    'recommendation': 'moodmarkgiftのSEO強化を検討'
                })
            
            if moodmarkgift_metrics['avg_ctr'] > moodmark_metrics['avg_ctr']:
                comparison['comparison_insights'].append({
                    'insight': 'moodmarkgiftのCTRがmoodmarkより高い',
                    'difference': f"{moodmarkgift_metrics['avg_ctr'] - moodmark_metrics['avg_ctr']:.2f}%",
                    'recommendation': 'moodmarkgiftの成功パターンをmoodmarkに適用'
                })
            
            return comparison
            
        except Exception as e:
            logger.error(f"サイト比較分析エラー: {e}")
            return {}
    
    def _calculate_site_metrics(self, data: pd.DataFrame, site_name: str) -> Dict:
        """サイト別のメトリクス計算"""
        if data.empty:
            return {
                'total_clicks': 0,
                'total_impressions': 0,
                'avg_ctr': 0,
                'avg_position': 0,
                'top_queries_count': 0
            }
        
        return {
            'total_clicks': int(data['clicks'].sum()),
            'total_impressions': int(data['impressions'].sum()),
            'avg_ctr': round(data['ctr'].mean() * 100, 2),
            'avg_position': round(data['position'].mean(), 1),
            'top_queries_count': len(data[data['clicks'] > 10])
        }
    
    def generate_seo_opportunity_report(self, start_date: str, end_date: str, previous_start_date: str = None, previous_end_date: str = None):
        """SEO機会発見レポートの生成"""
        try:
            logger.info("SEO機会発見レポート生成開始")
            
            # サイト設定の取得
            sites = self.config.get('sites', {})
            if not sites:
                logger.error("サイト設定が見つかりません")
                return
            
            report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'current_period': f"{start_date} - {end_date}",
                    'previous_period': f"{previous_start_date} - {previous_end_date}" if previous_start_date else None,
                    'analysis_type': 'seo_opportunity_finder'
                },
                'sites': {}
            }
            
            # 各サイトの分析
            for site_key, site_config in sites.items():
                site_url = site_config.get('gsc_site_url')
                if not site_url:
                    continue
                
                logger.info(f"{site_key}のSEO機会分析開始")
                
                # 現在期間のデータ取得
                current_data = self.get_gsc_data_for_period(start_date, end_date, site_url)
                
                # 前年同期のデータ取得（提供されている場合）
                previous_data = pd.DataFrame()
                if previous_start_date and previous_end_date:
                    previous_data = self.get_gsc_data_for_period(previous_start_date, previous_end_date, site_url)
                
                # 各種分析の実行
                ranking_opportunities = self.find_ranking_improvement_opportunities(current_data, site_key)
                ctr_opportunities = self.find_ctr_improvement_opportunities(current_data, site_key)
                seasonal_trends = self.analyze_seasonal_trends(current_data, previous_data, site_key)
                
                site_report = {
                    'site_url': site_url,
                    'current_period_data': self._calculate_site_metrics(current_data, site_key),
                    'ranking_improvement_opportunities': ranking_opportunities,
                    'ctr_improvement_opportunities': ctr_opportunities,
                    'seasonal_trends': seasonal_trends,
                    'quick_wins': self._identify_quick_wins(ranking_opportunities, ctr_opportunities)
                }
                
                report['sites'][site_key] = site_report
                
                # データ保存
                if not current_data.empty:
                    filename = f'gsc_{site_key}_seo_analysis_{start_date.replace("-", "")}_{end_date.replace("-", "")}.csv'
                    self.api_integration.export_to_csv(current_data, filename)
            
            # サイト間比較
            if len(report['sites']) >= 2:
                moodmark_data = self.get_gsc_data_for_period(start_date, end_date, sites['moodmark']['gsc_site_url'])
                moodmarkgift_data = self.get_gsc_data_for_period(start_date, end_date, sites['moodmark_idea']['gsc_site_url'])
                report['site_comparison'] = self.compare_sites_performance(moodmark_data, moodmarkgift_data)
            
            # レポート保存
            report_file = f'data/processed/seo_opportunities_{start_date.replace("-", "")}_{end_date.replace("-", "")}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # Markdownレポート生成
            self._generate_markdown_report(report, start_date, end_date)
            
            logger.info(f"SEO機会発見レポート生成完了: {report_file}")
            
        except Exception as e:
            logger.error(f"SEO機会発見レポート生成エラー: {e}")
    
    def _identify_quick_wins(self, ranking_opportunities: List[Dict], ctr_opportunities: List[Dict]) -> List[Dict]:
        """即効性の高い施策を特定"""
        quick_wins = []
        
        # 順位改善機会から即効性の高いものを抽出
        for opp in ranking_opportunities[:10]:
            if opp['improvement_potential'] == 'high' and opp['predicted_traffic_increase'] > 1000:
                quick_wins.append({
                    'type': 'ranking_improvement',
                    'query': opp['query'],
                    'action': f"順位{opp['current_position']}位→{opp['target_position']}位への改善",
                    'expected_impact': f"+{opp['predicted_traffic_increase']}クリック/月",
                    'effort': 'medium',
                    'priority': 'high'
                })
        
        # CTR改善機会から即効性の高いものを抽出
        for opp in ctr_opportunities[:5]:
            if opp['improvement_potential'] == 'high' and opp['predicted_click_increase'] > 500:
                quick_wins.append({
                    'type': 'ctr_improvement',
                    'query': opp['query'],
                    'action': f"CTR{opp['current_ctr']}%→{opp['target_ctr']}%への改善",
                    'expected_impact': f"+{opp['predicted_click_increase']}クリック/月",
                    'effort': 'low',
                    'priority': 'high'
                })
        
        # 優先度でソート
        quick_wins.sort(key=lambda x: (x['priority'] == 'high', x['expected_impact']), reverse=True)
        
        return quick_wins[:10]  # TOP10
    
    def _generate_markdown_report(self, report: Dict, start_date: str, end_date: str):
        """Markdownレポートの生成"""
        try:
            markdown = f"""# 🔍 SEO機会発見レポート

**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
**分析期間**: {start_date} - {end_date}
**分析方式**: GSC API連携による包括的SEO分析

## 📊 分析概要

このレポートは、Google Search Consoleのデータを活用してSEO改善機会を特定したものです。

### 分析対象サイト
"""
            
            for site_key, site_data in report['sites'].items():
                site_url = site_data.get('site_url', '')
                metrics = site_data.get('current_period_data', {})
                markdown += f"- **{site_key}**: {site_url}\n"
                markdown += f"  - 総クリック数: {metrics.get('total_clicks', 0):,}\n"
                markdown += f"  - 総インプレッション数: {metrics.get('total_impressions', 0):,}\n"
                markdown += f"  - 平均CTR: {metrics.get('avg_ctr', 0):.2f}%\n"
                markdown += f"  - 平均検索順位: {metrics.get('avg_position', 0):.1f}位\n\n"
            
            # 各サイトの詳細分析
            for site_key, site_data in report['sites'].items():
                markdown += f"## 🌐 {site_key.upper()}\n\n"
                
                # 順位改善機会
                ranking_opps = site_data.get('ranking_improvement_opportunities', [])
                if ranking_opps:
                    markdown += "### 📈 順位改善機会（TOP10）\n\n"
                    markdown += "| 順位 | クエリ | 現在順位 | 現在クリック数 | 予想トラフィック増加 | 優先度 |\n"
                    markdown += "|------|--------|----------|----------------|---------------------|--------|\n"
                    
                    for i, opp in enumerate(ranking_opps[:10], 1):
                        priority_emoji = "🔴" if opp['improvement_potential'] == 'high' else "🟡" if opp['improvement_potential'] == 'medium' else "🟢"
                        markdown += f"| {i} | {opp['query']} | {opp['current_position']}位 | {opp['current_clicks']:,} | +{opp['predicted_traffic_increase']:,} | {priority_emoji} |\n"
                    markdown += "\n"
                
                # CTR改善機会
                ctr_opps = site_data.get('ctr_improvement_opportunities', [])
                if ctr_opps:
                    markdown += "### 🎯 CTR改善機会（TOP10）\n\n"
                    markdown += "| 順位 | クエリ | 現在CTR | 目標CTR | 予想クリック増加 | 推奨施策 |\n"
                    markdown += "|------|--------|---------|---------|------------------|----------|\n"
                    
                    for i, opp in enumerate(ctr_opps[:10], 1):
                        suggestions = ", ".join(opp.get('suggested_actions', [])[:2])
                        markdown += f"| {i} | {opp['query']} | {opp['current_ctr']}% | {opp['target_ctr']}% | +{opp['predicted_click_increase']:,} | {suggestions} |\n"
                    markdown += "\n"
                
                # 季節性トレンド
                trends = site_data.get('seasonal_trends', {})
                if trends.get('growing_queries'):
                    markdown += "### 📊 成長中のクエリ（TOP10）\n\n"
                    markdown += "| 順位 | クエリ | 現在クリック数 | 前年同期比 | 成長率 |\n"
                    markdown += "|------|--------|----------------|------------|--------|\n"
                    
                    for i, query in enumerate(trends['growing_queries'][:10], 1):
                        markdown += f"| {i} | {query['query']} | {query['current_clicks']:,} | {query['previous_clicks']:,} | +{query['clicks_growth']}% |\n"
                    markdown += "\n"
                
                # クイックウィン
                quick_wins = site_data.get('quick_wins', [])
                if quick_wins:
                    markdown += "### ⚡ 即効性の高い施策（TOP5）\n\n"
                    for i, win in enumerate(quick_wins[:5], 1):
                        effort_emoji = "🟢" if win['effort'] == 'low' else "🟡" if win['effort'] == 'medium' else "🔴"
                        markdown += f"{i}. **{win['query']}**\n"
                        markdown += f"   - 施策: {win['action']}\n"
                        markdown += f"   - 期待効果: {win['expected_impact']}\n"
                        markdown += f"   - 工数: {effort_emoji} {win['effort']}\n\n"
                
                markdown += "---\n\n"
            
            # サイト間比較
            if 'site_comparison' in report:
                comparison = report['site_comparison']
                markdown += "## 🔄 サイト間比較\n\n"
                
                if comparison.get('comparison_insights'):
                    markdown += "### 💡 比較インサイト\n\n"
                    for insight in comparison['comparison_insights']:
                        markdown += f"- **{insight['insight']}**: {insight['difference']}\n"
                        markdown += f"  - 推奨: {insight['recommendation']}\n\n"
            
            markdown += """## 📋 まとめ

### 主要な発見
- 順位改善機会の特定により、大幅なトラフィック増加が期待できる
- CTR改善により、既存のインプレッションをより効率的に活用可能
- 季節性トレンドの把握により、先手の施策実施が可能

### 次のステップ
1. 即効性の高い施策の優先実施
2. 順位改善のためのコンテンツ最適化
3. CTR改善のためのメタデータ最適化
4. 定期的なモニタリングと改善

---
*このレポートはSEO機会発見ツールにより自動生成されました。*
"""
            
            # ファイル保存
            markdown_file = f'data/processed/seo_opportunities_{start_date.replace("-", "")}_{end_date.replace("-", "")}.md'
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            logger.info(f"Markdownレポート生成完了: {markdown_file}")
            
        except Exception as e:
            logger.error(f"Markdownレポート生成エラー: {e}")

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SEO機会発見ツール')
    parser.add_argument('--start-date', required=True, help='分析開始日 (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='分析終了日 (YYYY-MM-DD)')
    parser.add_argument('--previous-start-date', help='前年同期開始日 (YYYY-MM-DD)')
    parser.add_argument('--previous-end-date', help='前年同期終了日 (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    print("=== SEO機会発見ツール ===")
    print(f"分析期間: {args.start_date} - {args.end_date}")
    if args.previous_start_date:
        print(f"前年同期間: {args.previous_start_date} - {args.previous_end_date}")
    print()
    
    finder = SEOOpportunityFinder()
    finder.generate_seo_opportunity_report(
        start_date=args.start_date,
        end_date=args.end_date,
        previous_start_date=args.previous_start_date,
        previous_end_date=args.previous_end_date
    )
    
    print("=== SEO機会発見分析完了 ===")
    print(f"レポートファイル: data/processed/seo_opportunities_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}.json")
    print(f"Markdownレポート: data/processed/seo_opportunities_{args.start_date.replace('-', '')}_{args.end_date.replace('-', '')}.md")

if __name__ == "__main__":
    main()







