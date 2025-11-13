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
            # 方法1: 環境変数からJSONを直接読み込む（Render.com推奨）
            google_credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if google_credentials_json:
                try:
                    credentials_info = json.loads(google_credentials_json)
                    self.credentials = service_account.Credentials.from_service_account_info(
                        credentials_info,
                        scopes=[
                            'https://www.googleapis.com/auth/analytics.readonly',
                            'https://www.googleapis.com/auth/webmasters.readonly',
                            'https://www.googleapis.com/auth/drive',
                            'https://www.googleapis.com/auth/bigquery'
                        ]
                    )
                    logger.info("環境変数GOOGLE_CREDENTIALS_JSONから認証情報を読み込みました")
                except json.JSONDecodeError as e:
                    logger.error(f"GOOGLE_CREDENTIALS_JSONのJSON解析エラー: {e}")
                    return
                except Exception as e:
                    logger.error(f"環境変数からの認証情報読み込みエラー: {e}")
                    return
            # 方法2: 認証ファイルパスから読み込む
            elif self.credentials_file and os.path.exists(self.credentials_file):
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=[
                        'https://www.googleapis.com/auth/analytics.readonly',
                        'https://www.googleapis.com/auth/webmasters.readonly',
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/bigquery'
                    ]
                )
                logger.info(f"認証ファイルから認証情報を読み込みました: {self.credentials_file}")
            else:
                logger.warning("認証ファイルが見つかりません。環境変数を確認してください。")
                logger.warning("  - GOOGLE_CREDENTIALS_JSON: JSON形式の認証情報（推奨）")
                logger.warning(f"  - GOOGLE_CREDENTIALS_FILE: 認証ファイルのパス（現在: {self.credentials_file}）")
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
    
    def get_ga4_data_custom_range(self, start_date: str, end_date: str, metrics=None, dimensions=None):
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
            if 'reports' in response and len(response['reports']) > 0:
                report = response['reports'][0]
                if 'rows' in report:
                    for row in report['rows']:
                        row_data = {}
                        # ディメンション値
                        for i, dimension in enumerate(dimensions):
                            if i < len(row.get('dimensionValues', [])):
                                row_data[dimension] = row['dimensionValues'][i].get('value', '')
                        # メトリクス値
                        for i, metric in enumerate(metrics):
                            if i < len(row.get('metricValues', [])):
                                value = row['metricValues'][i].get('value', '0')
                                try:
                                    row_data[metric] = float(value)
                                except ValueError:
                                    row_data[metric] = 0
                        data.append(row_data)
            
            df = pd.DataFrame(data)
            logger.info(f"GA4データ取得完了（カスタム範囲）: {len(df)}行 ({start_date} ～ {end_date})")
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
        if not self.gsc_service:
            logger.error("GSCサービスが初期化されていません。認証ファイルを確認してください。")
            return pd.DataFrame()
        
        if not self.gsc_site_url:
            logger.error("GSCサイトURLが設定されていません。環境変数GSC_SITE_URLを確認してください。")
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
    
    def get_page_specific_gsc_data(self, page_url: str, date_range_days=30):
        """
        特定ページのGSCデータを取得
        
        Args:
            page_url (str): 分析するページのURL
            date_range_days (int): 取得する日数
            
        Returns:
            dict: ページのGSCデータ（クリック数、インプレッション数、CTR、平均順位など）
        """
        try:
            # GSCサービスが初期化されているか確認
            if not self.gsc_service:
                logger.error("GSCサービスが初期化されていません。認証ファイルを確認してください。")
                return {
                    'page_url': page_url,
                    'error': 'GSCサービスが初期化されていません。認証ファイル（GOOGLE_CREDENTIALS_FILE）を確認してください。'
                }
            
            # ページURLを正規化（サイトURLとの相対パスに変換）
            from urllib.parse import urlparse
            parsed_url = urlparse(page_url)
            page_path = parsed_url.path
            
            # GSCデータを取得（ページディメンションで）
            gsc_data = self.get_gsc_data(
                date_range_days=date_range_days,
                dimensions=['page', 'date'],
                row_limit=25000
            )
            
            if gsc_data.empty:
                logger.warning(f"ページ固有のGSCデータが見つかりませんでした: {page_path}")
                return {
                    'page_url': page_url,
                    'page_path': page_path,
                    'clicks': 0,
                    'impressions': 0,
                    'ctr': 0.0,
                    'avg_position': 0.0,
                    'error': 'GSCデータが取得できませんでした。認証ファイルまたは環境変数を確認してください。'
                }
            
            # 指定されたページのデータをフィルタリング
            # ページパスが完全一致または部分一致するものを検索
            page_data = gsc_data[
                gsc_data['page'].str.contains(page_path, case=False, na=False)
            ]
            
            if page_data.empty:
                logger.warning(f"ページ '{page_path}' のデータが見つかりませんでした")
                return {
                    'page_url': page_url,
                    'page_path': page_path,
                    'clicks': 0,
                    'impressions': 0,
                    'ctr': 0.0,
                    'avg_position': 0.0,
                    'error': f'ページ "{page_path}" のデータが見つかりませんでした'
                }
            
            # 集計
            total_clicks = page_data['clicks'].sum()
            total_impressions = page_data['impressions'].sum()
            avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
            avg_position = page_data['position'].mean()
            
            logger.info(f"ページ固有のGSCデータ取得完了: {page_path}")
            logger.info(f"  クリック数: {total_clicks:,}, インプレッション数: {total_impressions:,}")
            logger.info(f"  CTR: {avg_ctr:.2f}%, 平均順位: {avg_position:.2f}")
            
            return {
                'page_url': page_url,
                'page_path': page_path,
                'clicks': int(total_clicks),
                'impressions': int(total_impressions),
                'ctr': round(avg_ctr, 2),
                'avg_position': round(avg_position, 2),
                'date_range_days': date_range_days
            }
            
        except Exception as e:
            logger.error(f"ページ固有のGSCデータ取得エラー ({page_url}): {e}")
            return {
                'page_url': page_url,
                'error': f'データ取得エラー: {str(e)}'
            }
    
    def get_yearly_comparison_gsc(self, page_url: str = None, date_range_days=30):
        """
        年次比較用のGSCデータを取得（今年と昨年の同じ期間）
        
        Args:
            page_url (str): 分析するページのURL（オプション、指定されない場合は全体）
            date_range_days (int): 比較する期間の日数
            
        Returns:
            dict: 今年と昨年のGSCデータの比較
        """
        try:
            from datetime import datetime, timedelta
            
            # 今年の期間
            this_year_end = datetime.now()
            this_year_start = this_year_end - timedelta(days=date_range_days)
            
            # 昨年の同じ期間
            last_year_end = datetime(this_year_end.year - 1, this_year_end.month, this_year_end.day)
            last_year_start = last_year_end - timedelta(days=date_range_days)
            
            logger.info(f"年次比較データ取得: 今年 {this_year_start.strftime('%Y-%m-%d')} ～ {this_year_end.strftime('%Y-%m-%d')}")
            logger.info(f"                  昨年 {last_year_start.strftime('%Y-%m-%d')} ～ {last_year_end.strftime('%Y-%m-%d')}")
            
            # GSCサービスが初期化されているか確認
            if not self.gsc_service:
                logger.error("GSCサービスが初期化されていません。年次比較データを取得できません。")
                return {
                    'error': 'GSCサービスが初期化されていません。認証ファイル（GOOGLE_CREDENTIALS_FILE）を確認してください。'
                }
            
            # 今年のデータ取得
            if page_url:
                this_year_data = self.get_page_specific_gsc_data(page_url, date_range_days)
                # エラーが含まれている場合は、エラーを返す
                if 'error' in this_year_data:
                    return {
                        'error': this_year_data.get('error', '今年のデータ取得エラー')
                    }
            else:
                gsc_data = self.get_gsc_data(date_range_days=date_range_days, dimensions=['page'])
                if not gsc_data.empty:
                    this_year_data = {
                        'clicks': int(gsc_data['clicks'].sum()),
                        'impressions': int(gsc_data['impressions'].sum()),
                        'ctr': round((gsc_data['clicks'].sum() / gsc_data['impressions'].sum() * 100) if gsc_data['impressions'].sum() > 0 else 0, 2),
                        'avg_position': round(gsc_data['position'].mean(), 2)
                    }
                else:
                    logger.warning("今年のGSCデータが取得できませんでした（空のDataFrame）")
                    return {
                        'error': '今年のGSCデータが取得できませんでした。認証ファイルまたは環境変数を確認してください。'
                    }
            
            # 昨年のデータ取得（カスタム日付範囲で取得）
            last_year_gsc_data = self._get_gsc_data_custom_range(
                start_date=last_year_start.strftime('%Y-%m-%d'),
                end_date=last_year_end.strftime('%Y-%m-%d'),
                page_url=page_url
            )
            
            if page_url and 'error' not in last_year_gsc_data:
                last_year_data = last_year_gsc_data
            elif not page_url and not last_year_gsc_data.empty:
                last_year_data = {
                    'clicks': int(last_year_gsc_data['clicks'].sum()),
                    'impressions': int(last_year_gsc_data['impressions'].sum()),
                    'ctr': round((last_year_gsc_data['clicks'].sum() / last_year_gsc_data['impressions'].sum() * 100) if last_year_gsc_data['impressions'].sum() > 0 else 0, 2),
                    'avg_position': round(last_year_gsc_data['position'].mean(), 2)
                }
            else:
                last_year_data = {'clicks': 0, 'impressions': 0, 'ctr': 0.0, 'avg_position': 0.0}
            
            # 比較計算
            clicks_change = this_year_data.get('clicks', 0) - last_year_data.get('clicks', 0)
            clicks_change_pct = (clicks_change / last_year_data.get('clicks', 1) * 100) if last_year_data.get('clicks', 0) > 0 else 0
            
            impressions_change = this_year_data.get('impressions', 0) - last_year_data.get('impressions', 0)
            impressions_change_pct = (impressions_change / last_year_data.get('impressions', 1) * 100) if last_year_data.get('impressions', 0) > 0 else 0
            
            ctr_change = this_year_data.get('ctr', 0) - last_year_data.get('ctr', 0)
            position_change = this_year_data.get('avg_position', 0) - last_year_data.get('avg_position', 0)
            
            comparison = {
                'this_year': {
                    'period': f"{this_year_start.strftime('%Y-%m-%d')} ～ {this_year_end.strftime('%Y-%m-%d')}",
                    'clicks': this_year_data.get('clicks', 0),
                    'impressions': this_year_data.get('impressions', 0),
                    'ctr': this_year_data.get('ctr', 0.0),
                    'avg_position': this_year_data.get('avg_position', 0.0)
                },
                'last_year': {
                    'period': f"{last_year_start.strftime('%Y-%m-%d')} ～ {last_year_end.strftime('%Y-%m-%d')}",
                    'clicks': last_year_data.get('clicks', 0),
                    'impressions': last_year_data.get('impressions', 0),
                    'ctr': last_year_data.get('ctr', 0.0),
                    'avg_position': last_year_data.get('avg_position', 0.0)
                },
                'changes': {
                    'clicks': clicks_change,
                    'clicks_change_pct': round(clicks_change_pct, 1),
                    'impressions': impressions_change,
                    'impressions_change_pct': round(impressions_change_pct, 1),
                    'ctr': round(ctr_change, 2),
                    'position': round(position_change, 2)
                }
            }
            
            logger.info(f"年次比較完了:")
            logger.info(f"  クリック数: {this_year_data.get('clicks', 0):,} ({clicks_change:+,}, {clicks_change_pct:+.1f}%)")
            logger.info(f"  インプレッション数: {this_year_data.get('impressions', 0):,} ({impressions_change:+,}, {impressions_change_pct:+.1f}%)")
            
            return comparison
            
        except Exception as e:
            logger.error(f"年次比較データ取得エラー: {e}", exc_info=True)
            return {
                'error': f'年次比較データ取得エラー: {str(e)}'
            }
    
    def _get_gsc_data_custom_range(self, start_date: str, end_date: str, page_url: str = None):
        """
        カスタム日付範囲でGSCデータを取得（内部メソッド）
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            page_url (str): ページURL（オプション）
            
        Returns:
            pd.DataFrame or dict: GSCデータ
        """
        if not self.gsc_service:
            error_msg = 'GSCサービスが初期化されていません。認証ファイル（GOOGLE_CREDENTIALS_FILE）を確認してください。'
            logger.error(error_msg)
            return pd.DataFrame() if not page_url else {'error': error_msg}
        
        if not self.gsc_site_url:
            error_msg = 'GSCサイトURLが設定されていません。環境変数GSC_SITE_URLを確認してください。'
            logger.error(error_msg)
            return pd.DataFrame() if not page_url else {'error': error_msg}
        
        try:
            dimensions = ['page', 'date'] if page_url else ['page']
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': 25000,
                'startRow': 0
            }
            
            response = self.gsc_service.searchanalytics().query(
                siteUrl=self.gsc_site_url,
                body=request
            ).execute()
            
            data = []
            if 'rows' in response:
                for row in response['rows']:
                    row_data = {
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    }
                    
                    for i, dimension in enumerate(dimensions):
                        if i < len(row.get('keys', [])):
                            row_data[dimension] = row['keys'][i]
                    data.append(row_data)
            
            df = pd.DataFrame(data)
            
            if page_url:
                # ページURLでフィルタリング
                from urllib.parse import urlparse
                parsed_url = urlparse(page_url)
                page_path = parsed_url.path
                page_data = df[df['page'].str.contains(page_path, case=False, na=False)]
                
                if page_data.empty:
                    return {'error': f'ページ "{page_path}" のデータが見つかりませんでした'}
                
                total_clicks = page_data['clicks'].sum()
                total_impressions = page_data['impressions'].sum()
                return {
                    'clicks': int(total_clicks),
                    'impressions': int(total_impressions),
                    'ctr': round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2),
                    'avg_position': round(page_data['position'].mean(), 2)
                }
            
            return df
            
        except Exception as e:
            logger.error(f"カスタム日付範囲のGSCデータ取得エラー: {e}")
            return pd.DataFrame() if not page_url else {'error': str(e)}
    
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
