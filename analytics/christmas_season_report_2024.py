#!/usr/bin/env python3
"""
2024年クリスマスシーズンレポート生成システム
- 2024年11-12月のクリスマス関連キーワード分析
- GA4・GSC API連携によるデータ取得
- クリスマス期間のパフォーマンス分析
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# 相対インポートまたは絶対インポートを試みる
try:
    from .google_apis_integration import GoogleAPIsIntegration
except ImportError:
    from google_apis_integration import GoogleAPIsIntegration

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/christmas_season_report.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChristmasSeasonReportGenerator:
    def __init__(self, credentials_file=None):
        """
        クリスマスシーズンレポート生成クラスの初期化
        
        Args:
            credentials_file (str): サービスアカウントキーファイルのパス
        """
        self.api_integration = GoogleAPIsIntegration(credentials_file)
        self.christmas_keywords = self._define_christmas_keywords()
        self.report_period = {
            'start_date': '2024-11-01',
            'end_date': '2024-12-31'
        }
        
        # ログディレクトリの作成
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
        os.makedirs('data/christmas_2024', exist_ok=True)
    
    def _define_christmas_keywords(self) -> Dict[str, List[str]]:
        """クリスマス関連キーワードの定義"""
        return {
            'christmas_core': [
                'クリスマス', 'christmas', 'Xmas', 'クリスマスプレゼント',
                'クリスマスギフト', 'クリスマス プレゼント', 'クリスマス ギフト'
            ],
            'gift_related': [
                'プレゼント', 'ギフト', '贈り物', 'プレゼント クリスマス',
                'ギフト クリスマス', 'クリスマス お菓子', 'クリスマス スイーツ'
            ],
            'occasion_related': [
                'クリスマス 誕生日', 'クリスマス イブ', 'サンタクロース',
                'クリスマス ケーキ', 'クリスマス ディナー', 'クリスマス パーティー'
            ],
            'recipient_related': [
                'クリスマス 彼氏', 'クリスマス 彼女', 'クリスマス 家族',
                'クリスマス 友達', 'クリスマス 子供', 'クリスマス 恋人'
            ],
            'product_related': [
                'クリスマス コスメ', 'クリスマス 花束', 'クリスマス お酒',
                'クリスマス アクセサリー', 'クリスマス 雑貨', 'クリスマス 食品'
            ]
        }
    
    def get_christmas_gsc_data(self) -> Dict[str, pd.DataFrame]:
        """
        クリスマス関連キーワードのGSCデータを取得
        
        Returns:
            Dict[str, pd.DataFrame]: カテゴリ別のGSCデータ
        """
        logger.info("クリスマス関連キーワードのGSCデータ取得開始")
        
        christmas_data = {}
        
        try:
            # 全期間のGSCデータを取得
            gsc_data = self._get_custom_gsc_data(
                start_date=self.report_period['start_date'],
                end_date=self.report_period['end_date']
            )
            
            if gsc_data.empty:
                logger.warning("GSCデータが取得できませんでした")
                return christmas_data
            
            # カテゴリ別にフィルタリング
            for category, keywords in self.christmas_keywords.items():
                filtered_data = self._filter_data_by_keywords(gsc_data, keywords)
                if not filtered_data.empty:
                    christmas_data[category] = filtered_data
                    logger.info(f"{category}: {len(filtered_data)}件のデータを取得")
            
            return christmas_data
            
        except Exception as e:
            logger.error(f"クリスマスGSCデータ取得エラー: {e}")
            return christmas_data
    
    def _get_custom_gsc_data(self, start_date: str, end_date: str, 
                           dimensions: List[str] = None, row_limit: int = 25000) -> pd.DataFrame:
        """
        カスタム日付範囲でGSCデータを取得
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            dimensions (list): 取得するディメンション
            row_limit (int): 取得行数上限
        
        Returns:
            pd.DataFrame: GSCデータ
        """
        if not self.api_integration.gsc_service:
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
            response = self.api_integration.gsc_service.searchanalytics().query(
                siteUrl=self.api_integration.gsc_site_url,
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
    
    def _filter_data_by_keywords(self, data: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
        """
        キーワードリストでデータをフィルタリング
        
        Args:
            data (pd.DataFrame): フィルタリングするデータ
            keywords (list): フィルタリングキーワード
        
        Returns:
            pd.DataFrame: フィルタリングされたデータ
        """
        if data.empty or 'query' not in data.columns:
            return pd.DataFrame()
        
        # キーワードパターンを作成
        keyword_pattern = '|'.join(keywords)
        
        # クエリ列でフィルタリング
        filtered_data = data[
            data['query'].str.contains(keyword_pattern, case=False, na=False)
        ].copy()
        
        return filtered_data
    
    def get_christmas_ga4_data(self) -> Dict[str, Any]:
        """
        クリスマス期間のGA4データを取得
        
        Returns:
            Dict[str, Any]: GA4データとサマリー
        """
        logger.info("クリスマス期間のGA4データ取得開始")
        
        try:
            # カスタム日付範囲でGA4データを取得
            ga4_data = self._get_custom_ga4_data(
                start_date=self.report_period['start_date'],
                end_date=self.report_period['end_date']
            )
            
            if ga4_data.empty:
                logger.warning("GA4データが取得できませんでした")
                return {}
            
            # サマリー統計の計算
            summary = self._calculate_ga4_summary(ga4_data)
            
            # 日別トレンドの計算
            daily_trends = self._calculate_daily_trends(ga4_data)
            
            # デバイス別分析
            device_analysis = self._analyze_by_device(ga4_data)
            
            # トラフィックソース分析
            traffic_analysis = self._analyze_traffic_sources(ga4_data)
            
            return {
                'raw_data': ga4_data,
                'summary': summary,
                'daily_trends': daily_trends,
                'device_analysis': device_analysis,
                'traffic_analysis': traffic_analysis
            }
            
        except Exception as e:
            logger.error(f"クリスマスGA4データ取得エラー: {e}")
            return {}
    
    def _get_custom_ga4_data(self, start_date: str, end_date: str,
                           metrics: List[str] = None, dimensions: List[str] = None) -> pd.DataFrame:
        """
        カスタム日付範囲でGA4データを取得
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            metrics (list): 取得するメトリクス
            dimensions (list): 取得するディメンション
        
        Returns:
            pd.DataFrame: GA4データ
        """
        if not self.api_integration.ga4_service:
            logger.error("GA4サービスが初期化されていません")
            return pd.DataFrame()
        
        # デフォルトメトリクス
        if not metrics:
            metrics = [
                'sessions', 'users', 'pageviews', 'bounceRate',
                'averageSessionDuration', 'conversions', 'totalRevenue'
            ]
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = [
                'date', 'pagePath', 'sourceMedium', 'deviceCategory', 'country'
            ]
        
        try:
            # GA4リクエスト作成
            request = {
                'requests': [{
                    'property': f'properties/{self.api_integration.ga4_property_id}',
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'metrics': [{'name': metric} for metric in metrics],
                    'dimensions': [{'name': dimension} for dimension in dimensions],
                    'limit': 100000
                }]
            }
            
            # API呼び出し
            response = self.api_integration.ga4_service.properties().batchRunReports(
                property=f'properties/{self.api_integration.ga4_property_id}',
                body=request
            ).execute()
            
            # データの変換
            data = []
            if 'reports' in response:
                for report in response['reports']:
                    if 'rows' in report:
                        for row in report['rows']:
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
            logger.info(f"GA4データ取得完了: {len(df)}行 ({start_date} - {end_date})")
            return df
            
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return pd.DataFrame()
    
    def _calculate_ga4_summary(self, ga4_data: pd.DataFrame) -> Dict[str, Any]:
        """GA4データのサマリー統計を計算"""
        if ga4_data.empty:
            return {}
        
        summary = {}
        
        # 基本メトリクス
        if 'sessions' in ga4_data.columns:
            summary['total_sessions'] = int(ga4_data['sessions'].sum())
        if 'users' in ga4_data.columns:
            summary['total_users'] = int(ga4_data['users'].sum())
        if 'pageviews' in ga4_data.columns:
            summary['total_pageviews'] = int(ga4_data['pageviews'].sum())
        if 'bounceRate' in ga4_data.columns:
            summary['avg_bounce_rate'] = float(ga4_data['bounceRate'].mean())
        if 'averageSessionDuration' in ga4_data.columns:
            summary['avg_session_duration'] = float(ga4_data['averageSessionDuration'].mean())
        if 'conversions' in ga4_data.columns:
            summary['total_conversions'] = int(ga4_data['conversions'].sum())
        if 'totalRevenue' in ga4_data.columns:
            summary['total_revenue'] = float(ga4_data['totalRevenue'].sum())
        
        return summary
    
    def _calculate_daily_trends(self, ga4_data: pd.DataFrame) -> pd.DataFrame:
        """日別トレンドを計算"""
        if ga4_data.empty or 'date' not in ga4_data.columns:
            return pd.DataFrame()
        
        # 日別で集計
        daily_data = ga4_data.groupby('date').agg({
            'sessions': 'sum',
            'users': 'sum',
            'pageviews': 'sum',
            'bounceRate': 'mean',
            'averageSessionDuration': 'mean',
            'conversions': 'sum',
            'totalRevenue': 'sum'
        }).reset_index()
        
        # 日付をdatetimeに変換
        daily_data['date'] = pd.to_datetime(daily_data['date'])
        
        return daily_data.sort_values('date')
    
    def _analyze_by_device(self, ga4_data: pd.DataFrame) -> pd.DataFrame:
        """デバイス別分析"""
        if ga4_data.empty or 'deviceCategory' not in ga4_data.columns:
            return pd.DataFrame()
        
        device_data = ga4_data.groupby('deviceCategory').agg({
            'sessions': 'sum',
            'users': 'sum',
            'pageviews': 'sum',
            'bounceRate': 'mean',
            'averageSessionDuration': 'mean',
            'conversions': 'sum',
            'totalRevenue': 'sum'
        }).reset_index()
        
        # セッション数でソート
        return device_data.sort_values('sessions', ascending=False)
    
    def _analyze_traffic_sources(self, ga4_data: pd.DataFrame) -> pd.DataFrame:
        """トラフィックソース分析"""
        if ga4_data.empty or 'sourceMedium' not in ga4_data.columns:
            return pd.DataFrame()
        
        traffic_data = ga4_data.groupby('sourceMedium').agg({
            'sessions': 'sum',
            'users': 'sum',
            'pageviews': 'sum',
            'bounceRate': 'mean',
            'averageSessionDuration': 'mean',
            'conversions': 'sum',
            'totalRevenue': 'sum'
        }).reset_index()
        
        # セッション数でソート
        return traffic_data.sort_values('sessions', ascending=False)
    
    def analyze_christmas_keywords(self, gsc_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        クリスマスキーワードの詳細分析
        
        Args:
            gsc_data (Dict[str, pd.DataFrame]): カテゴリ別GSCデータ
        
        Returns:
            Dict[str, Any]: 分析結果
        """
        logger.info("クリスマスキーワード分析開始")
        
        analysis = {
            'category_summary': {},
            'top_performing_keywords': {},
            'keyword_trends': {},
            'opportunities': []
        }
        
        try:
            # カテゴリ別サマリー
            for category, data in gsc_data.items():
                if data.empty:
                    continue
                
                category_summary = {
                    'total_clicks': int(data['clicks'].sum()),
                    'total_impressions': int(data['impressions'].sum()),
                    'avg_ctr': float(data['ctr'].mean()),
                    'avg_position': float(data['position'].mean()),
                    'keyword_count': len(data)
                }
                
                analysis['category_summary'][category] = category_summary
                
                # トップパフォーマンスキーワード
                top_keywords = data.nlargest(10, 'clicks')[['query', 'clicks', 'impressions', 'ctr', 'position']]
                analysis['top_performing_keywords'][category] = top_keywords.to_dict('records')
            
            # 機会分析
            analysis['opportunities'] = self._identify_opportunities(gsc_data)
            
            return analysis
            
        except Exception as e:
            logger.error(f"クリスマスキーワード分析エラー: {e}")
            return analysis
    
    def _identify_opportunities(self, gsc_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """SEO機会の特定"""
        opportunities = []
        
        try:
            for category, data in gsc_data.items():
                if data.empty:
                    continue
                
                # 高インプレッション・低CTRキーワード
                high_imp_low_ctr = data[
                    (data['impressions'] > data['impressions'].quantile(0.75)) &
                    (data['ctr'] < data['ctr'].quantile(0.25))
                ]
                
                if not high_imp_low_ctr.empty:
                    opportunities.append({
                        'type': 'CTR改善機会',
                        'category': category,
                        'keywords': high_imp_low_ctr.head(5)[['query', 'impressions', 'ctr', 'position']].to_dict('records'),
                        'description': f'{category}カテゴリでCTR改善の機会があります'
                    })
                
                # 10-20位のキーワード
                ranking_opportunities = data[
                    (data['position'] >= 10) & (data['position'] <= 20)
                ]
                
                if not ranking_opportunities.empty:
                    opportunities.append({
                        'type': '順位上昇機会',
                        'category': category,
                        'keywords': ranking_opportunities.head(5)[['query', 'clicks', 'position']].to_dict('records'),
                        'description': f'{category}カテゴリで順位上昇の機会があります'
                    })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"機会分析エラー: {e}")
            return opportunities
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """
        包括的なクリスマスシーズンレポートを生成
        
        Returns:
            Dict[str, Any]: 包括的レポート
        """
        logger.info("包括的クリスマスシーズンレポート生成開始")
        
        try:
            # データ取得
            gsc_data = self.get_christmas_gsc_data()
            ga4_data = self.get_christmas_ga4_data()
            
            # 分析実行
            keyword_analysis = self.analyze_christmas_keywords(gsc_data)
            
            # レポート統合
            comprehensive_report = {
                'report_metadata': {
                    'title': '2024年クリスマスシーズンレポート',
                    'period': f"{self.report_period['start_date']} - {self.report_period['end_date']}",
                    'generated_at': datetime.now().isoformat(),
                    'site_url': self.api_integration.gsc_site_url
                },
                'gsc_data': gsc_data,
                'ga4_data': ga4_data,
                'keyword_analysis': keyword_analysis,
                'recommendations': self._generate_recommendations(keyword_analysis, ga4_data)
            }
            
            # レポート保存
            self._save_report(comprehensive_report)
            
            logger.info("包括的クリスマスシーズンレポート生成完了")
            return comprehensive_report
            
        except Exception as e:
            logger.error(f"包括的レポート生成エラー: {e}")
            return {}
    
    def _generate_recommendations(self, keyword_analysis: Dict[str, Any], 
                                ga4_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """推奨事項の生成"""
        recommendations = []
        
        try:
            # キーワード分析からの推奨事項
            for category, summary in keyword_analysis.get('category_summary', {}).items():
                if summary['avg_position'] > 15:
                    recommendations.append({
                        'type': 'SEO改善',
                        'priority': 'high',
                        'category': category,
                        'message': f'{category}カテゴリの平均順位が{summary["avg_position"]:.1f}位です。コンテンツ最適化が必要です。'
                    })
                
                if summary['avg_ctr'] < 2.0:
                    recommendations.append({
                        'type': 'CTR改善',
                        'priority': 'medium',
                        'category': category,
                        'message': f'{category}カテゴリのCTRが{summary["avg_ctr"]:.2f}%です。タイトル最適化が必要です。'
                    })
            
            # GA4データからの推奨事項
            if 'summary' in ga4_data:
                summary = ga4_data['summary']
                if summary.get('avg_bounce_rate', 0) > 0.7:
                    recommendations.append({
                        'type': 'UX改善',
                        'priority': 'high',
                        'message': f'バウンス率が{summary["avg_bounce_rate"]:.2%}と高すぎます。ページ改善が必要です。'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"推奨事項生成エラー: {e}")
            return recommendations
    
    def _save_report(self, report: Dict[str, Any]):
        """レポートの保存"""
        try:
            # JSON形式で保存
            report_file = f'data/christmas_2024/christmas_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            # サマリーレポートも生成
            self._generate_summary_markdown(report)
            
            logger.info(f"レポート保存完了: {report_file}")
            
        except Exception as e:
            logger.error(f"レポート保存エラー: {e}")
    
    def _generate_summary_markdown(self, report: Dict[str, Any]):
        """サマリーレポートのMarkdown生成"""
        try:
            markdown_content = self._format_report_as_markdown(report)
            
            markdown_file = f'data/christmas_2024/christmas_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"サマリーレポート保存完了: {markdown_file}")
            
        except Exception as e:
            logger.error(f"サマリーレポート生成エラー: {e}")
    
    def _format_report_as_markdown(self, report: Dict[str, Any]) -> str:
        """レポートをMarkdown形式でフォーマット"""
        metadata = report.get('report_metadata', {})
        ga4_data = report.get('ga4_data', {})
        keyword_analysis = report.get('keyword_analysis', {})
        recommendations = report.get('recommendations', [])
        
        content = f"""# {metadata.get('title', 'クリスマスシーズンレポート')}

**期間**: {metadata.get('period', 'N/A')}  
**生成日時**: {metadata.get('generated_at', 'N/A')}  
**サイトURL**: {metadata.get('site_url', 'N/A')}

## 📊 概要

### GA4パフォーマンス
"""
        
        # GA4サマリー
        if 'summary' in ga4_data:
            summary = ga4_data['summary']
            content += f"""
- **総セッション数**: {summary.get('total_sessions', 0):,}
- **総ユーザー数**: {summary.get('total_users', 0):,}
- **総ページビュー**: {summary.get('total_pageviews', 0):,}
- **平均バウンス率**: {summary.get('avg_bounce_rate', 0):.2%}
- **平均セッション時間**: {summary.get('avg_session_duration', 0):.1f}秒
- **総コンバージョン数**: {summary.get('total_conversions', 0):,}
- **総収益**: ¥{summary.get('total_revenue', 0):,.0f}
"""
        
        # キーワード分析
        content += "\n## 🔍 クリスマス関連キーワード分析\n"
        
        for category, summary in keyword_analysis.get('category_summary', {}).items():
            content += f"""
### {category.replace('_', ' ').title()}
- **総クリック数**: {summary.get('total_clicks', 0):,}
- **総インプレッション数**: {summary.get('total_impressions', 0):,}
- **平均CTR**: {summary.get('avg_ctr', 0):.2f}%
- **平均順位**: {summary.get('avg_position', 0):.1f}位
- **キーワード数**: {summary.get('keyword_count', 0)}個
"""
        
        # 推奨事項
        if recommendations:
            content += "\n## 💡 推奨事項\n"
            for i, rec in enumerate(recommendations, 1):
                priority_emoji = "🔴" if rec.get('priority') == 'high' else "🟡"
                content += f"{i}. {priority_emoji} **{rec.get('type', 'N/A')}**: {rec.get('message', 'N/A')}\n"
        
        content += f"""
## 📈 今後のアクション

1. **高優先度のSEO改善**を実施
2. **CTR改善**のためのタイトル最適化
3. **ユーザー体験向上**のためのページ改善
4. **定期監視**による継続的な改善

---
*このレポートは自動生成されました。詳細な分析データはJSONファイルをご確認ください。*
"""
        
        return content

def main():
    """メイン実行関数"""
    print("=== 2024年クリスマスシーズンレポート生成開始 ===")
    
    # 環境変数の確認
    required_env_vars = ['GA4_PROPERTY_ID', 'GSC_SITE_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        print("設定例:")
        print("export GA4_PROPERTY_ID='316302380'")
        print("export GSC_SITE_URL='https://isetan.mistore.jp/moodmarkgift/'")
        return
    
    # レポート生成器の初期化
    report_generator = ChristmasSeasonReportGenerator('config/google-credentials.json')
    
    # 包括的レポート生成
    report = report_generator.generate_comprehensive_report()
    
    if report:
        print("\n=== レポート生成完了 ===")
        print(f"レポート期間: {report['report_metadata']['period']}")
        print(f"生成日時: {report['report_metadata']['generated_at']}")
        
        # サマリー表示
        if 'ga4_data' in report and 'summary' in report['ga4_data']:
            summary = report['ga4_data']['summary']
            print(f"\n--- GA4サマリー ---")
            print(f"総セッション数: {summary.get('total_sessions', 0):,}")
            print(f"総ユーザー数: {summary.get('total_users', 0):,}")
            print(f"総ページビュー: {summary.get('total_pageviews', 0):,}")
        
        # キーワード分析サマリー
        if 'keyword_analysis' in report and 'category_summary' in report['keyword_analysis']:
            print(f"\n--- キーワード分析サマリー ---")
            for category, cat_summary in report['keyword_analysis']['category_summary'].items():
                print(f"{category}: {cat_summary.get('total_clicks', 0):,}クリック")
        
        # 推奨事項
        if 'recommendations' in report and report['recommendations']:
            print(f"\n--- 推奨事項 ---")
            for i, rec in enumerate(report['recommendations'][:5], 1):
                print(f"{i}. {rec.get('message', 'N/A')}")
        
        print(f"\n詳細レポートは data/christmas_2024/ に保存されました。")
    else:
        print("レポート生成に失敗しました。ログを確認してください。")

if __name__ == "__main__":
    main()
