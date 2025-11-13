#!/usr/bin/env python3
"""
統合分析システム
- Google APIs統合
- Looker Studio連携
- 自動レポート生成
- リアルタイム監視
"""

import os
import json
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

# 相対インポートまたは絶対インポートを試みる
try:
    from .google_apis_integration import GoogleAPIsIntegration
    from .looker_studio_connector import LookerStudioConnector
    from .notion_integration import NotionIntegration
    from .notion_report_converter import NotionReportConverter
except ImportError:
    from google_apis_integration import GoogleAPIsIntegration
    from looker_studio_connector import LookerStudioConnector
    from notion_integration import NotionIntegration
    from notion_report_converter import NotionReportConverter

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analytics_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IntegratedAnalyticsSystem:
    def __init__(self):
        """統合分析システムの初期化"""
        self.api_integration = GoogleAPIsIntegration()
        self.looker_connector = LookerStudioConnector()
        self.notion_integration = None
        self.notion_converter = None
        self.is_running = False
        
        # 設定の読み込み
        self.config = self._load_config()
        
        # Notion統合の初期化
        self._initialize_notion_integration()
        
        # ログディレクトリの作成
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        config_file = 'config/analytics_config.json'
        
        default_config = {
            'data_collection': {
                'ga4_date_range_days': 30,
                'gsc_date_range_days': 30,
                'top_pages_limit': 100,
                'top_queries_limit': 100
            },
            'reporting': {
                'auto_report_enabled': True,
                'report_frequency': 'daily',
                'looker_studio_enabled': True
            },
            'alerts': {
                'performance_threshold': {
                    'bounce_rate': 0.7,
                    'avg_position': 10,
                    'ctr': 0.02
                },
                'email_notifications': False
            },
            'notion': {
                'enabled': True,
                'auto_sync': True,
                'sync_after_report_generation': True,
                'create_database_if_missing': True
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # デフォルト設定とマージ
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                # デフォルト設定を保存
                os.makedirs('config', exist_ok=True)
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            return default_config
    
    def _initialize_notion_integration(self):
        """Notion統合の初期化"""
        try:
            if not self.config.get('notion', {}).get('enabled', False):
                logger.info("Notion統合が無効です")
                return
            
            # Notion統合クラスの初期化
            self.notion_integration = NotionIntegration()
            self.notion_converter = NotionReportConverter()
            
            if self.notion_integration.client:
                logger.info("Notion統合が正常に初期化されました")
                
                # データベースの確認・作成
                if (self.config.get('notion', {}).get('create_database_if_missing', False) and
                    not self.notion_integration.database_id):
                    
                    database_id = self.notion_integration.create_analytics_database()
                    if database_id:
                        logger.info(f"新しいAnalyticsデータベースを作成しました: {database_id}")
            else:
                logger.warning("Notion認証に失敗しました。Notion連携は無効です。")
                self.notion_integration = None
                
        except Exception as e:
            logger.error(f"Notion統合初期化エラー: {e}")
            self.notion_integration = None
            self.notion_converter = None
    
    def collect_data(self):
        """データ収集の実行"""
        try:
            logger.info("データ収集開始")
            
            # GA4データ取得
            ga4_data = self.api_integration.get_ga4_data(
                date_range_days=self.config['data_collection']['ga4_date_range_days']
            )
            
            # GSCページデータ取得
            gsc_pages = self.api_integration.get_top_pages_gsc(
                date_range_days=self.config['data_collection']['gsc_date_range_days'],
                limit=self.config['data_collection']['top_pages_limit']
            )
            
            # GSCクエリデータ取得
            gsc_queries = self.api_integration.get_top_queries_gsc(
                date_range_days=self.config['data_collection']['gsc_date_range_days'],
                limit=self.config['data_collection']['top_queries_limit']
            )
            
            # データ保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if not ga4_data.empty:
                self.api_integration.export_to_csv(
                    ga4_data, 
                    f'ga4_data_{timestamp}.csv'
                )
            
            if not gsc_pages.empty:
                self.api_integration.export_to_csv(
                    gsc_pages, 
                    f'gsc_pages_{timestamp}.csv'
                )
            
            if not gsc_queries.empty:
                self.api_integration.export_to_csv(
                    gsc_queries, 
                    f'gsc_queries_{timestamp}.csv'
                )
            
            logger.info("データ収集完了")
            return {
                'ga4_data': ga4_data,
                'gsc_pages': gsc_pages,
                'gsc_queries': gsc_queries,
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"データ収集エラー: {e}")
            return None
    
    def generate_analytics_report(self, data):
        """分析レポートの生成"""
        try:
            logger.info("分析レポート生成開始")
            
            # サマリーレポート生成
            summary = self.api_integration.generate_summary_report(
                date_range_days=self.config['data_collection']['ga4_date_range_days']
            )
            
            # 詳細分析
            detailed_analysis = self._perform_detailed_analysis(data)
            
            # レポート統合
            report = {
                'summary': summary,
                'detailed_analysis': detailed_analysis,
                'generated_at': datetime.now().isoformat(),
                'system_status': 'healthy'
            }
            
            # レポート保存
            report_file = f'data/processed/analytics_report_{data["timestamp"]}.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分析レポート生成完了: {report_file}")
            
            # Notionに送信（設定が有効な場合）
            if (self.notion_integration and 
                self.config.get('notion', {}).get('sync_after_report_generation', False)):
                
                notion_page_id = self._sync_report_to_notion(report_file, report)
                if notion_page_id:
                    report['notion_page_id'] = notion_page_id
                    logger.info(f"レポートをNotionに送信しました: {notion_page_id}")
            
            return report
            
        except Exception as e:
            logger.error(f"分析レポート生成エラー: {e}")
            return None
    
    def _perform_detailed_analysis(self, data):
        """詳細分析の実行"""
        analysis = {
            'performance_analysis': {},
            'seo_analysis': {},
            'content_analysis': {},
            'recommendations': []
        }
        
        try:
            # パフォーマンス分析
            if not data['ga4_data'].empty:
                ga4_data = data['ga4_data']
                
                # セッション分析
                if 'sessions' in ga4_data.columns:
                    total_sessions = ga4_data['sessions'].sum()
                    analysis['performance_analysis']['total_sessions'] = total_sessions
                
                # バウンス率分析
                if 'bounceRate' in ga4_data.columns:
                    avg_bounce_rate = ga4_data['bounceRate'].mean()
                    analysis['performance_analysis']['avg_bounce_rate'] = avg_bounce_rate
                    
                    if avg_bounce_rate > self.config['alerts']['performance_threshold']['bounce_rate']:
                        analysis['recommendations'].append({
                            'type': 'performance',
                            'priority': 'high',
                            'message': f'バウンス率が{avg_bounce_rate:.2%}と高すぎます。コンテンツ改善が必要です。'
                        })
                
                # セッション時間分析
                if 'averageSessionDuration' in ga4_data.columns:
                    avg_duration = ga4_data['averageSessionDuration'].mean()
                    analysis['performance_analysis']['avg_session_duration'] = avg_duration
            
            # SEO分析
            if not data['gsc_pages'].empty:
                gsc_pages = data['gsc_pages']
                
                # 平均検索順位
                if 'avg_position' in gsc_pages.columns:
                    avg_position = gsc_pages['avg_position'].mean()
                    analysis['seo_analysis']['avg_position'] = avg_position
                    
                    if avg_position > self.config['alerts']['performance_threshold']['avg_position']:
                        analysis['recommendations'].append({
                            'type': 'seo',
                            'priority': 'high',
                            'message': f'平均検索順位が{avg_position:.1f}位と低すぎます。SEO改善が必要です。'
                        })
                
                # CTR分析
                if 'ctr_calculated' in gsc_pages.columns:
                    avg_ctr = gsc_pages['ctr_calculated'].mean()
                    analysis['seo_analysis']['avg_ctr'] = avg_ctr
                    
                    if avg_ctr < self.config['alerts']['performance_threshold']['ctr'] * 100:
                        analysis['recommendations'].append({
                            'type': 'seo',
                            'priority': 'medium',
                            'message': f'CTRが{avg_ctr:.2f}%と低すぎます。タイトルとメタディスクリプションの最適化が必要です。'
                        })
                
                # トップページ分析
                top_pages = gsc_pages.head(10)
                analysis['seo_analysis']['top_pages'] = top_pages.to_dict('records')
            
            # コンテンツ分析
            if not data['gsc_queries'].empty:
                gsc_queries = data['gsc_queries']
                
                # トップクエリ分析
                top_queries = gsc_queries.head(20)
                analysis['content_analysis']['top_queries'] = top_queries.to_dict('records')
                
                # キーワード分析
                keyword_analysis = self._analyze_keywords(gsc_queries)
                analysis['content_analysis']['keyword_analysis'] = keyword_analysis
            
            return analysis
            
        except Exception as e:
            logger.error(f"詳細分析エラー: {e}")
            return analysis
    
    def _analyze_keywords(self, gsc_queries):
        """キーワード分析"""
        try:
            if gsc_queries.empty:
                return {}
            
            # キーワードカテゴリの分析
            categories = {
                'gift_related': ['プレゼント', 'ギフト', '贈り物', 'プレゼント'],
                'occasion_related': ['誕生日', 'クリスマス', 'バレンタイン', '母の日', '父の日'],
                'person_related': ['彼氏', '彼女', '友達', '家族', '上司'],
                'product_related': ['スイーツ', 'コスメ', '花束', 'お酒']
            }
            
            keyword_analysis = {}
            
            for category, keywords in categories.items():
                category_data = gsc_queries[
                    gsc_queries['query'].str.contains('|'.join(keywords), case=False, na=False)
                ]
                
                if not category_data.empty:
                    keyword_analysis[category] = {
                        'total_clicks': category_data['clicks'].sum(),
                        'total_impressions': category_data['impressions'].sum(),
                        'avg_position': category_data['avg_position'].mean(),
                        'top_queries': category_data.head(5).to_dict('records')
                    }
            
            return keyword_analysis
            
        except Exception as e:
            logger.error(f"キーワード分析エラー: {e}")
            return {}
    
    def create_looker_studio_dashboard(self, data):
        """Looker Studioダッシュボードの作成"""
        try:
            if not self.config['reporting']['looker_studio_enabled']:
                logger.info("Looker Studio連携が無効です")
                return None
            
            logger.info("Looker Studioダッシュボード作成開始")
            
            # レポート設定
            report_config = {
                'date_range_days': self.config['data_collection']['ga4_date_range_days'],
                'top_pages_limit': self.config['data_collection']['top_pages_limit'],
                'top_queries_limit': self.config['data_collection']['top_queries_limit']
            }
            
            # ダッシュボード作成
            dashboard_info = self.looker_connector.create_automated_report_system(
                self.api_integration, 
                report_config
            )
            
            if dashboard_info:
                logger.info(f"Looker Studioダッシュボード作成完了: {dashboard_info['dashboard_id']}")
                return dashboard_info
            else:
                logger.warning("Looker Studioダッシュボード作成に失敗")
                return None
                
        except Exception as e:
            logger.error(f"Looker Studioダッシュボード作成エラー: {e}")
            return None
    
    def run_analysis_cycle(self):
        """分析サイクルの実行"""
        try:
            logger.info("=== 分析サイクル開始 ===")
            
            # データ収集
            data = self.collect_data()
            if not data:
                logger.error("データ収集に失敗しました")
                return
            
            # 分析レポート生成
            report = self.generate_analytics_report(data)
            if not report:
                logger.error("分析レポート生成に失敗しました")
                return
            
            # Looker Studioダッシュボード更新（必要に応じて）
            if self.config['reporting']['auto_report_enabled']:
                dashboard_info = self.create_looker_studio_dashboard(data)
            
            # アラートチェック
            self._check_alerts(report)
            
            logger.info("=== 分析サイクル完了 ===")
            
        except Exception as e:
            logger.error(f"分析サイクルエラー: {e}")
    
    def _check_alerts(self, report):
        """アラートチェック"""
        try:
            alerts = []
            
            # パフォーマンスアラート
            if 'detailed_analysis' in report:
                analysis = report['detailed_analysis']
                
                # 推奨事項のチェック
                if 'recommendations' in analysis:
                    for rec in analysis['recommendations']:
                        if rec.get('priority') == 'high':
                            alerts.append({
                                'type': 'high_priority',
                                'message': rec['message'],
                                'timestamp': datetime.now().isoformat()
                            })
            
            # アラートログ
            if alerts:
                logger.warning(f"アラート発生: {len(alerts)}件")
                for alert in alerts:
                    logger.warning(f"  - {alert['message']}")
                
                # アラートファイルに保存
                alert_file = f'data/processed/alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(alert_file, 'w', encoding='utf-8') as f:
                    json.dump(alerts, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"アラートチェックエラー: {e}")
    
    def _sync_report_to_notion(self, report_file: str, report_data: Dict[str, Any]) -> Optional[str]:
        """レポートをNotionに送信"""
        try:
            if not self.notion_integration or not self.notion_converter:
                logger.error("Notion統合が初期化されていません")
                return None
            
            logger.info("レポートのNotion送信開始")
            
            # 対応するMarkdownファイルを探す
            markdown_file = self._find_corresponding_markdown(report_file)
            
            # レポートをNotion形式に変換
            converted_report = self.notion_converter.convert_analysis_report(
                report_file, 
                markdown_file
            )
            
            if not converted_report:
                logger.error("レポート変換に失敗しました")
                return None
            
            # Markdownコンテンツの取得
            markdown_content = ""
            if markdown_file:
                with open(markdown_file, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
            
            # NotionページでのReporting
            page_id = self.notion_integration.create_report_page(
                converted_report, 
                markdown_content
            )
            
            if page_id:
                logger.info(f"Notionレポートページ作成成功: {page_id}")
                return page_id
            else:
                logger.error("Notionページ作成に失敗しました")
                return None
                
        except Exception as e:
            logger.error(f"Notion送信エラー: {e}")
            return None
    
    def _find_corresponding_markdown(self, json_file_path: str) -> Optional[str]:
        """対応するMarkdownファイルを探す"""
        try:
            # JSONファイル名から対応するMarkdownファイルを推測
            base_name = os.path.basename(json_file_path)
            
            # 一般的なMarkdownファイルの場所を検索
            markdown_locations = [
                'docs/analytics/',
                'data/processed/',
                os.path.dirname(json_file_path) + '/'
            ]
            
            # パターンマッチング用のキーワード
            if 'purchase' in base_name:
                keywords = ['purchase', 'moodmark', '7days', 'analysis']
            else:
                keywords = ['moodmark', '7days', 'analysis']
            
            # 各場所でMarkdownファイルを検索
            for location in markdown_locations:
                if os.path.exists(location):
                    for filename in os.listdir(location):
                        if filename.endswith('.md'):
                            # キーワードマッチング
                            matches = sum(1 for keyword in keywords if keyword in filename.lower())
                            if matches >= 2:  # 最低2つのキーワードがマッチした場合
                                markdown_path = os.path.join(location, filename)
                                logger.info(f"対応するMarkdownファイルを発見: {markdown_path}")
                                return markdown_path
            
            # 直接的なファイル名パターンもチェック
            markdown_patterns = [
                'docs/analytics/moodmark_7days_analysis_report.md',
                'docs/analytics/analysis_report.md',
                'data/processed/report.md'
            ]
            
            for pattern in markdown_patterns:
                if os.path.exists(pattern):
                    logger.info(f"標準Markdownファイルを使用: {pattern}")
                    return pattern
            
            logger.warning("対応するMarkdownファイルが見つかりません")
            return None
            
        except Exception as e:
            logger.error(f"Markdownファイル検索エラー: {e}")
            return None
    
    def create_notion_kpi_dashboard(self) -> Optional[str]:
        """Notion KPIダッシュボードの作成"""
        try:
            if not self.notion_integration:
                logger.error("Notion統合が初期化されていません")
                return None
            
            logger.info("Notion KPIダッシュボード作成開始")
            
            # 最新の分析データを取得
            data = self.collect_data()
            if not data:
                logger.error("データ収集に失敗しました")
                return None
            
            # KPIダッシュボード用のレポート生成
            kpi_report = self._generate_kpi_report(data)
            
            # Notionページの作成
            dashboard_page_id = self.notion_integration.create_report_page(
                kpi_report,
                self._format_kpi_dashboard_content(kpi_report)
            )
            
            if dashboard_page_id:
                logger.info(f"KPIダッシュボード作成完了: {dashboard_page_id}")
                return dashboard_page_id
            else:
                logger.error("KPIダッシュボード作成に失敗しました")
                return None
                
        except Exception as e:
            logger.error(f"KPIダッシュボード作成エラー: {e}")
            return None
    
    def _generate_kpi_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """KPI用レポートの生成"""
        return {
            'report_date': datetime.now().isoformat(),
            'period': 'KPI Dashboard',
            'site_url': 'https://isetan.mistore.jp/moodmark',
            'summary': data.get('ga4_data', pd.DataFrame()).to_dict('records')[0] if not data.get('ga4_data', pd.DataFrame()).empty else {},
            'recommendations': ['KPIダッシュボードの定期的な監視を推奨します。']
        }
    
    def _format_kpi_dashboard_content(self, kpi_report: Dict[str, Any]) -> str:
        """KPIダッシュボードのコンテンツ整形"""
        content = f"""
# 📈 MOO-D MARK KPIダッシュボード

**更新日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

## 主要指標

このダッシュボードは自動更新されます。最新のパフォーマンスデータを確認できます。

## 注意事項

- データは毎日自動更新されます
- 異常値を発見した場合は、詳細な分析レポートを確認してください
- 改善提案については、レコメンデーションセクションを参照してください
        """
        
        return content.strip()
    
    def start_scheduled_analysis(self):
        """スケジュール分析の開始"""
        try:
            logger.info("スケジュール分析開始")
            
            # スケジュール設定
            if self.config['reporting']['report_frequency'] == 'daily':
                schedule.every().day.at("09:00").do(self.run_analysis_cycle)
            elif self.config['reporting']['report_frequency'] == 'weekly':
                schedule.every().monday.at("09:00").do(self.run_analysis_cycle)
            elif self.config['reporting']['report_frequency'] == 'hourly':
                schedule.every().hour.do(self.run_analysis_cycle)
            
            # 初回実行
            self.run_analysis_cycle()
            
            self.is_running = True
            logger.info("スケジュール分析開始完了")
            
            # メインループ
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1分ごとにチェック
                
        except KeyboardInterrupt:
            logger.info("スケジュール分析停止")
            self.is_running = False
        except Exception as e:
            logger.error(f"スケジュール分析エラー: {e}")
            self.is_running = False
    
    def stop_scheduled_analysis(self):
        """スケジュール分析の停止"""
        self.is_running = False
        logger.info("スケジュール分析停止要求")

def main():
    """メイン実行関数"""
    print("=== 統合分析システム起動 ===")
    
    # システム初期化
    system = IntegratedAnalyticsSystem()
    
    # 環境チェック
    if not system.api_integration.credentials:
        print("Google APIs認証に失敗しました。認証ファイルを確認してください。")
        return
    
    if not system.looker_connector.credentials:
        print("Looker Studio認証に失敗しました。認証ファイルを確認してください。")
        return
    
    print("統合分析システム初期化完了")
    
    # 実行モード選択
    import sys
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == 'once':
            # 一回だけ実行
            system.run_analysis_cycle()
        elif mode == 'schedule':
            # スケジュール実行
            system.start_scheduled_analysis()
        else:
            print("使用法: python integrated_analytics_system.py [once|schedule]")
    else:
        # デフォルトは一回だけ実行
        system.run_analysis_cycle()

if __name__ == "__main__":
    main()
