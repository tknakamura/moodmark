#!/usr/bin/env python3
"""
Google APIs統合システム
- Google Analytics 4 (GA4) API
- Google Search Console (GSC) API  
- Google Looker Studio API
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleAPIsIntegration:
    def __init__(self, credentials_file=None):
        """
        Google APIs統合クラスの初期化
        
        Args:
            credentials_file (str): サービスアカウントキーファイルのパス
        """
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE')
        self.credentials = None
        self.ga4_service = None
        self.gsc_service = None
        
        # 環境変数から設定を取得
        self.ga4_property_id = os.getenv('GA4_PROPERTY_ID')
        self.gsc_site_url = os.getenv('GSC_SITE_URL')
        
        self._authenticate()
    
    def _authenticate(self):
        """Google APIs認証"""
        try:
            if self.credentials_file and os.path.exists(self.credentials_file):
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=[
                        'https://www.googleapis.com/auth/analytics.readonly',
                        'https://www.googleapis.com/auth/webmasters.readonly',
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/bigquery'
                    ]
                )
            else:
                logger.warning("認証ファイルが見つかりません。環境変数を確認してください。")
                return
            
            # GA4 APIサービス構築
            self.ga4_service = build('analyticsdata', 'v1beta', credentials=self.credentials)
            
            # GSC APIサービス構築
            self.gsc_service = build('searchconsole', 'v1', credentials=self.credentials)
            
            logger.info("Google APIs認証完了")
            
        except Exception as e:
            logger.error(f"認証エラー: {e}")
    
    def get_ga4_data(self, date_range_days=30, metrics=None, dimensions=None):
        """
        GA4からデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            metrics (list): 取得するメトリクス
            dimensions (list): 取得するディメンション
        
        Returns:
            pd.DataFrame: GA4データ
        """
        if not self.ga4_service or not self.ga4_property_id:
            logger.error("GA4サービスまたはプロパティIDが設定されていません")
            return pd.DataFrame()
        
        # デフォルトメトリクス
        if not metrics:
            metrics = [
                'sessions',
                'users', 
                'pageviews',
                'bounceRate',
                'averageSessionDuration',
                'conversions',
                'totalRevenue'
            ]
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = [
                'date',
                'pagePath',
                'sourceMedium',
                'deviceCategory',
                'country'
            ]
        
        try:
            # 日付範囲の設定
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=date_range_days)).strftime('%Y-%m-%d')
            
            # GA4リクエスト作成
            request = {
                'requests': [{
                    'property': f'properties/{self.ga4_property_id}',
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'metrics': [{'name': metric} for metric in metrics],
                    'dimensions': [{'name': dimension} for dimension in dimensions],
                    'limit': 100000
                }]
            }
            
            # API呼び出し
            response = self.ga4_service.properties().batchRunReports(
                property=f'properties/{self.ga4_property_id}',
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
                                    # 数値に変換
                                    try:
                                        row_data[metric] = float(value)
                                    except ValueError:
                                        row_data[metric] = value
                            
                            data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GA4データ取得完了: {len(df)}行")
            return df
            
        except HttpError as e:
            logger.error(f"GA4 API エラー: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_gsc_data(self, date_range_days=30, dimensions=None, row_limit=25000):
        """
        Google Search Consoleからデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            dimensions (list): 取得するディメンション
            row_limit (int): 取得行数上限
        
        Returns:
            pd.DataFrame: GSCデータ
        """
        if not self.gsc_service or not self.gsc_site_url:
            logger.error("GSCサービスまたはサイトURLが設定されていません")
            return pd.DataFrame()
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = ['date', 'query', 'page', 'country', 'device']
        
        try:
            # 日付範囲の設定
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=date_range_days)).strftime('%Y-%m-%d')
            
            # GSCリクエスト作成
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': row_limit,
                'startRow': 0
            }
            
            # API呼び出し
            response = self.gsc_service.searchanalytics().query(
                siteUrl=self.gsc_site_url,
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
            logger.info(f"GSCデータ取得完了: {len(df)}行")
            return df
            
        except HttpError as e:
            logger.error(f"GSC API エラー: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GSCデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_top_pages_gsc(self, date_range_days=30, limit=100):
        """
        GSCから上位ページデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            limit (int): 取得件数
        
        Returns:
            pd.DataFrame: 上位ページデータ
        """
        gsc_data = self.get_gsc_data(
            date_range_days=date_range_days,
            dimensions=['page'],
            row_limit=limit
        )
        
        if gsc_data.empty:
            return pd.DataFrame()
        
        # ページ別で集計
        page_stats = gsc_data.groupby('page').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # CTRとポジションを計算し直し
        page_stats['ctr_calculated'] = (page_stats['clicks'] / page_stats['impressions'] * 100).round(2)
        page_stats['avg_position'] = page_stats['position'].round(2)
        
        # ソート（クリック数順）
        page_stats = page_stats.sort_values('clicks', ascending=False).reset_index(drop=True)
        
        return page_stats
    
    def get_top_queries_gsc(self, date_range_days=30, limit=100):
        """
        GSCから上位クエリデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            limit (int): 取得件数
        
        Returns:
            pd.DataFrame: 上位クエリデータ
        """
        gsc_data = self.get_gsc_data(
            date_range_days=date_range_days,
            dimensions=['query'],
            row_limit=limit
        )
        
        if gsc_data.empty:
            return pd.DataFrame()
        
        # クエリ別で集計
        query_stats = gsc_data.groupby('query').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()
        
        # CTRとポジションを計算し直し
        query_stats['ctr_calculated'] = (query_stats['clicks'] / query_stats['impressions'] * 100).round(2)
        query_stats['avg_position'] = query_stats['position'].round(2)
        
        # ソート（クリック数順）
        query_stats = query_stats.sort_values('clicks', ascending=False).reset_index(drop=True)
        
        return query_stats
    
    def export_to_csv(self, data, filename, output_dir='data/processed'):
        """
        データをCSVファイルにエクスポート
        
        Args:
            data (pd.DataFrame): エクスポートするデータ
            filename (str): ファイル名
            output_dir (str): 出力ディレクトリ
        """
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        try:
            data.to_csv(filepath, index=False, encoding='utf-8')
            logger.info(f"データをエクスポートしました: {filepath}")
        except Exception as e:
            logger.error(f"エクスポートエラー: {e}")
    
    def generate_summary_report(self, date_range_days=30):
        """
        統合サマリーレポートを生成
        
        Args:
            date_range_days (int): 取得する日数
        
        Returns:
            dict: サマリーレポート
        """
        logger.info("統合サマリーレポート生成開始")
        
        # GA4データ取得
        ga4_data = self.get_ga4_data(date_range_days)
        
        # GSCデータ取得
        gsc_pages = self.get_top_pages_gsc(date_range_days)
        gsc_queries = self.get_top_queries_gsc(date_range_days)
        
        # サマリー作成
        summary = {
            'report_date': datetime.now().isoformat(),
            'date_range_days': date_range_days,
            'ga4_summary': {},
            'gsc_summary': {},
            'recommendations': []
        }
        
        # GA4サマリー
        if not ga4_data.empty:
            summary['ga4_summary'] = {
                'total_sessions': ga4_data['sessions'].sum() if 'sessions' in ga4_data.columns else 0,
                'total_users': ga4_data['users'].sum() if 'users' in ga4_data.columns else 0,
                'total_pageviews': ga4_data['pageviews'].sum() if 'pageviews' in ga4_data.columns else 0,
                'avg_bounce_rate': ga4_data['bounceRate'].mean() if 'bounceRate' in ga4_data.columns else 0,
                'avg_session_duration': ga4_data['averageSessionDuration'].mean() if 'averageSessionDuration' in ga4_data.columns else 0,
                'total_conversions': ga4_data['conversions'].sum() if 'conversions' in ga4_data.columns else 0,
                'total_revenue': ga4_data['totalRevenue'].sum() if 'totalRevenue' in ga4_data.columns else 0
            }
        
        # GSCサマリー
        if not gsc_pages.empty:
            summary['gsc_summary'] = {
                'total_clicks': gsc_pages['clicks'].sum(),
                'total_impressions': gsc_pages['impressions'].sum(),
                'avg_ctr': gsc_pages['ctr_calculated'].mean(),
                'avg_position': gsc_pages['avg_position'].mean(),
                'top_pages_count': len(gsc_pages),
                'top_queries_count': len(gsc_queries) if not gsc_queries.empty else 0
            }
        
        # 推奨事項の生成
        if summary['gsc_summary'].get('avg_position', 0) > 10:
            summary['recommendations'].append("平均検索順位が10位以下です。SEO改善が必要です。")
        
        if summary['ga4_summary'].get('avg_bounce_rate', 0) > 0.6:
            summary['recommendations'].append("バウンス率が60%を超えています。コンテンツ改善が必要です。")
        
        if summary['gsc_summary'].get('avg_ctr', 0) < 2:
            summary['recommendations'].append("CTRが2%未満です。タイトルとメタディスクリプションの最適化が必要です。")
        
        logger.info("統合サマリーレポート生成完了")
        return summary

def main():
    """メイン実行関数"""
    # 環境変数の確認
    required_env_vars = ['GA4_PROPERTY_ID', 'GSC_SITE_URL']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        print("設定例:")
        print("export GA4_PROPERTY_ID='your-ga4-property-id'")
        print("export GSC_SITE_URL='https://isetan.mistore.jp/moodmarkgift/'")
        return
    
    # API統合インスタンス作成
    api = GoogleAPIsIntegration()
    
    # データ取得とレポート生成
    print("=== Google APIs統合分析開始 ===")
    
    # サマリーレポート生成
    summary = api.generate_summary_report(date_range_days=30)
    
    # 結果表示
    print("\n=== 統合サマリーレポート ===")
    print(f"レポート日時: {summary['report_date']}")
    print(f"分析期間: {summary['date_range_days']}日")
    
    print("\n--- GA4サマリー ---")
    for key, value in summary['ga4_summary'].items():
        print(f"{key}: {value:,.2f}" if isinstance(value, float) else f"{key}: {value:,}")
    
    print("\n--- GSCサマリー ---")
    for key, value in summary['gsc_summary'].items():
        print(f"{key}: {value:,.2f}" if isinstance(value, float) else f"{key}: {value:,}")
    
    if summary['recommendations']:
        print("\n--- 推奨事項 ---")
        for i, rec in enumerate(summary['recommendations'], 1):
            print(f"{i}. {rec}")
    
    # データエクスポート
    print("\n=== データエクスポート ===")
    
    # GA4データ
    ga4_data = api.get_ga4_data(date_range_days=30)
    if not ga4_data.empty:
        api.export_to_csv(ga4_data, f'ga4_data_{datetime.now().strftime("%Y%m%d")}.csv')
    
    # GSCページデータ
    gsc_pages = api.get_top_pages_gsc(date_range_days=30)
    if not gsc_pages.empty:
        api.export_to_csv(gsc_pages, f'gsc_pages_{datetime.now().strftime("%Y%m%d")}.csv')
    
    # GSCクエリデータ
    gsc_queries = api.get_top_queries_gsc(date_range_days=30)
    if not gsc_queries.empty:
        api.export_to_csv(gsc_queries, f'gsc_queries_{datetime.now().strftime("%Y%m%d")}.csv')
    
    # サマリーレポート保存
    with open(f'data/processed/summary_report_{datetime.now().strftime("%Y%m%d")}.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("分析完了！データをdata/processed/に保存しました。")

if __name__ == "__main__":
    main()
