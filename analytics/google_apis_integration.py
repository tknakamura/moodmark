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
from typing import Dict, Any
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
        
        # analytics_config.jsonから設定を読み込む
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'analytics_config.json')
        self.site_configs = {}
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    sites = config.get('sites', {})
                    # サイト設定を読み込む
                    for site_key, site_config in sites.items():
                        # キーを正規化（moodmark_idea -> moodmarkgift）
                        normalized_key = 'moodmarkgift' if site_key == 'moodmark_idea' else site_key
                        self.site_configs[normalized_key] = {
                            'ga4_property_id': site_config.get('ga4_property_id'),
                            'gsc_site_url': site_config.get('gsc_site_url')
                        }
                    logger.info(f"analytics_config.jsonから設定を読み込みました: {list(self.site_configs.keys())}")
        except Exception as e:
            logger.warning(f"analytics_config.jsonの読み込みエラー: {e}")
        
        # 複数GSCサイトURLの読み込み
        self.gsc_site_urls = {
            'moodmark': os.getenv('GSC_SITE_URL_MOODMARK') or os.getenv('GSC_SITE_URL') or 'https://isetan.mistore.jp/moodmark/',
            'moodmarkgift': os.getenv('GSC_SITE_URL_MOODMARKGIFT') or 'https://isetan.mistore.jp/moodmarkgift/'
        }
        # 後方互換性のため、既存のgsc_site_urlも保持
        self.gsc_site_url = self.gsc_site_urls.get('moodmark')
        
        # 複数GA4プロパティIDの読み込み
        self.ga4_property_ids = {}
        for site_key in ['moodmark', 'moodmarkgift']:
            # 環境変数から取得を試行
            env_key = f'GA4_PROPERTY_ID_{site_key.upper()}'
            property_id = os.getenv(env_key)
            # 環境変数がない場合はconfigから取得
            if not property_id and site_key in self.site_configs:
                property_id = self.site_configs[site_key].get('ga4_property_id')
            # それでもない場合はデフォルトの環境変数を使用
            if not property_id:
                property_id = os.getenv('GA4_PROPERTY_ID')
            self.ga4_property_ids[site_key] = property_id
            logger.info(f"GA4プロパティID ({site_key}): {property_id}")
        
        # デフォルトのプロパティIDを設定（環境変数またはmoodmarkの設定）
        if not self.ga4_property_id:
            self.ga4_property_id = self.ga4_property_ids.get('moodmark')
        
        self.pagespeed_api_key = os.getenv('PAGESPEED_INSIGHTS_API_KEY')
        
        self._authenticate()
    
    def set_site(self, site_name: str):
        """
        サイト名に応じてGSCサイトURLを設定
        （GA4プロパティIDは共通のため、ページパスフィルタで切り分けます）
        
        Args:
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
        """
        # 正規化（moodmark_idea -> moodmarkgift）
        normalized_site = 'moodmarkgift' if site_name == 'moodmark_idea' else site_name
        
        # GSCサイトURLを設定
        if normalized_site in self.gsc_site_urls:
            self.gsc_site_url = self.gsc_site_urls[normalized_site]
            logger.info(f"GSCサイトURLを設定: {normalized_site} -> {self.gsc_site_url}")
        else:
            logger.warning(f"サイト '{normalized_site}' のGSCサイトURLが見つかりません。デフォルトを使用します。")
        
        # GA4プロパティIDは共通のため変更しない（ページパスフィルタで切り分け）
        logger.info(f"GA4プロパティID（共通）: {self.ga4_property_id}, サイト: {normalized_site}（ページパスフィルタで切り分け）")
    
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
            # 方法1.5: GOOGLE_CREDENTIALS_FILEにJSONが設定されている場合のフォールバック
            elif self.credentials_file and self.credentials_file.strip().startswith('{'):
                # GOOGLE_CREDENTIALS_FILEにJSONが設定されている場合
                logger.warning("GOOGLE_CREDENTIALS_FILEにJSONが設定されています。GOOGLE_CREDENTIALS_JSON環境変数の使用を推奨します。")
                try:
                    credentials_info = json.loads(self.credentials_file)
                    self.credentials = service_account.Credentials.from_service_account_info(
                        credentials_info,
                        scopes=[
                            'https://www.googleapis.com/auth/analytics.readonly',
                            'https://www.googleapis.com/auth/webmasters.readonly',
                            'https://www.googleapis.com/auth/drive',
                            'https://www.googleapis.com/auth/bigquery'
                        ]
                    )
                    logger.info("GOOGLE_CREDENTIALS_FILEからJSON形式の認証情報を読み込みました（フォールバック）")
                except json.JSONDecodeError as e:
                    logger.error(f"GOOGLE_CREDENTIALS_FILEのJSON解析エラー: {e}")
                    return
                except Exception as e:
                    logger.error(f"GOOGLE_CREDENTIALS_FILEからの認証情報読み込みエラー: {e}")
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
            logger.error(f"認証エラー: {e}", exc_info=True)
            # エラーの詳細をログに記録
            if hasattr(e, 'args') and e.args:
                logger.error(f"  エラー詳細: {e.args}")
            logger.error(f"  認証情報の読み込みに失敗しました。環境変数を確認してください。")
    
    def check_authentication_status(self) -> Dict[str, Any]:
        """
        認証状態を確認し、診断情報を返す
        
        Returns:
            dict: 認証状態の診断結果
        """
        status = {
            'authenticated': False,
            'ga4_service_initialized': False,
            'gsc_service_initialized': False,
            'credentials_loaded': False,
            'ga4_property_id_set': False,
            'gsc_site_url_set': False,
            'errors': [],
            'warnings': [],
            'diagnostics': {}
        }
        
        # 環境変数の確認
        google_credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        google_credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
        
        status['diagnostics']['GOOGLE_CREDENTIALS_JSON_set'] = bool(google_credentials_json)
        status['diagnostics']['GOOGLE_CREDENTIALS_FILE_set'] = bool(google_credentials_file)
        
        # GOOGLE_CREDENTIALS_FILEにJSONが設定されている場合の検出
        if google_credentials_file and google_credentials_file.strip().startswith('{'):
            status['errors'].append('GOOGLE_CREDENTIALS_FILEにJSONの内容が設定されています。GOOGLE_CREDENTIALS_JSON環境変数を使用してください。')
            status['diagnostics']['credentials_file_contains_json'] = True
            status['diagnostics']['suggested_fix'] = 'GOOGLE_CREDENTIALS_FILEの値をGOOGLE_CREDENTIALS_JSON環境変数に移動してください'
        
        # 認証情報の確認
        if self.credentials:
            status['credentials_loaded'] = True
            status['authenticated'] = True
            status['diagnostics']['credentials_type'] = 'loaded'
        else:
            status['errors'].append('認証情報が読み込まれていません')
            # 環境変数の確認
            if not google_credentials_json and not google_credentials_file:
                status['errors'].append('GOOGLE_CREDENTIALS_JSONまたはGOOGLE_CREDENTIALS_FILEが設定されていません')
                status['diagnostics']['credentials_type'] = 'none'
            elif google_credentials_json:
                try:
                    json.loads(google_credentials_json)
                    status['diagnostics']['credentials_type'] = 'GOOGLE_CREDENTIALS_JSON'
                    status['diagnostics']['json_valid'] = True
                    status['warnings'].append('GOOGLE_CREDENTIALS_JSONは設定されていますが、認証情報が読み込まれていません。認証処理でエラーが発生した可能性があります。')
                except json.JSONDecodeError as e:
                    status['errors'].append(f'GOOGLE_CREDENTIALS_JSONのJSON形式が不正です: {str(e)}')
                    status['diagnostics']['credentials_type'] = 'GOOGLE_CREDENTIALS_JSON'
                    status['diagnostics']['json_valid'] = False
            elif google_credentials_file:
                status['diagnostics']['credentials_type'] = 'GOOGLE_CREDENTIALS_FILE'
                if os.path.exists(google_credentials_file):
                    status['diagnostics']['file_exists'] = True
                    status['warnings'].append('GOOGLE_CREDENTIALS_FILEは存在しますが、認証情報が読み込まれていません。認証処理でエラーが発生した可能性があります。')
                else:
                    status['errors'].append(f'認証ファイルが見つかりません: {google_credentials_file}')
                    status['diagnostics']['file_exists'] = False
        
        # GA4サービスの確認
        if self.ga4_service:
            status['ga4_service_initialized'] = True
        else:
            status['warnings'].append('GA4サービスが初期化されていません')
        
        # GSCサービスの確認
        if self.gsc_service:
            status['gsc_service_initialized'] = True
        else:
            status['warnings'].append('GSCサービスが初期化されていません')
        
        # GA4プロパティIDの確認
        if self.ga4_property_id:
            status['ga4_property_id_set'] = True
        else:
            status['errors'].append('GA4_PROPERTY_IDが設定されていません')
        
        # GSCサイトURLの確認
        status['gsc_site_urls'] = {}
        for site_name, site_url in self.gsc_site_urls.items():
            if site_url:
                status['gsc_site_urls'][site_name] = True
            else:
                status['gsc_site_urls'][site_name] = False
                status['warnings'].append(f'GSC_SITE_URL_{site_name.upper()}が設定されていません')
        
        # 後方互換性のため
        if self.gsc_site_url:
            status['gsc_site_url_set'] = True
        else:
            status['errors'].append('GSC_SITE_URLが設定されていません')
        
        # 全体の認証状態
        if status['authenticated'] and status['ga4_service_initialized'] and status['gsc_service_initialized']:
            status['overall_status'] = 'success'
        elif len(status['errors']) > 0:
            status['overall_status'] = 'error'
        else:
            status['overall_status'] = 'warning'
        
        return status
    
    def test_ga4_connection(self) -> Dict[str, Any]:
        """
        GA4 APIへの接続をテスト
        
        Returns:
            dict: テスト結果
        """
        result = {
            'success': False,
            'message': '',
            'error': None,
            'data_sample': None
        }
        
        if not self.ga4_service:
            result['error'] = 'GA4サービスが初期化されていません'
            result['message'] = '認証が完了していない可能性があります。環境変数を確認してください。'
            return result
        
        if not self.ga4_property_id:
            result['error'] = 'GA4プロパティIDが設定されていません'
            result['message'] = '環境変数GA4_PROPERTY_IDを設定してください。'
            return result
        
        try:
            # 過去7日間の簡単なデータ取得を試行
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            request = {
                'requests': [{
                    'property': f'properties/{self.ga4_property_id}',
                    'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                    'metrics': [{'name': 'sessions'}],
                    'dimensions': [{'name': 'date'}],
                    'limit': 10
                }]
            }
            
            logger.info(f"GA4接続テスト開始: プロパティID={self.ga4_property_id}")
            response = self.ga4_service.properties().batchRunReports(
                property=f'properties/{self.ga4_property_id}',
                body=request
            ).execute()
            
            # レスポンスの確認
            if 'reports' in response and len(response['reports']) > 0:
                report = response['reports'][0]
                row_count = len(report.get('rows', []))
                result['success'] = True
                result['message'] = f'GA4接続成功: {row_count}件のデータを取得しました'
                result['data_sample'] = {
                    'row_count': row_count,
                    'date_range': f'{start_date} ～ {end_date}'
                }
                logger.info(f"GA4接続テスト成功: {row_count}件のデータを取得")
            else:
                result['error'] = 'データが取得できませんでした'
                result['message'] = 'API接続は成功しましたが、データが返されませんでした。'
                logger.warning("GA4接続テスト: データが取得できませんでした")
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            result['error'] = f'GA4 API エラー: {error_reason}'
            result['message'] = f'GA4 APIへの接続に失敗しました: {error_reason}'
            logger.error(f"GA4接続テストエラー: {error_reason}")
        except Exception as e:
            result['error'] = f'接続エラー: {str(e)}'
            result['message'] = f'GA4への接続中にエラーが発生しました: {str(e)}'
            logger.error(f"GA4接続テストエラー: {e}", exc_info=True)
        
        return result
    
    def test_gsc_connection(self, site_name='moodmark') -> Dict[str, Any]:
        """
        GSC APIへの接続をテスト
        
        Args:
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
        
        Returns:
            dict: テスト結果
        """
        result = {
            'success': False,
            'message': '',
            'error': None,
            'data_sample': None,
            'site_name': site_name
        }
        
        if not self.gsc_service:
            result['error'] = 'GSCサービスが初期化されていません'
            result['message'] = '認証が完了していない可能性があります。環境変数を確認してください。'
            return result
        
        # サイトURLの取得
        gsc_site_url = self.gsc_site_urls.get(site_name)
        if not gsc_site_url:
            result['error'] = f'GSCサイトURLが設定されていません（サイト: {site_name}）'
            result['message'] = f'環境変数GSC_SITE_URL_{site_name.upper()}またはGSC_SITE_URLを設定してください。'
            return result
        
        try:
            # 過去7日間の簡単なデータ取得を試行
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['date'],
                'rowLimit': 10
            }
            
            logger.info(f"GSC接続テスト開始: サイト={site_name}, URL={gsc_site_url}")
            response = self.gsc_service.searchanalytics().query(
                siteUrl=gsc_site_url,
                body=request
            ).execute()
            
            # レスポンスの確認
            row_count = len(response.get('rows', []))
            result['success'] = True
            result['message'] = f'GSC接続成功 ({site_name}): {row_count}件のデータを取得しました'
            result['data_sample'] = {
                'row_count': row_count,
                'date_range': f'{start_date} ～ {end_date}'
            }
            logger.info(f"GSC接続テスト成功 ({site_name}): {row_count}件のデータを取得")
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            result['error'] = f'GSC API エラー: {error_reason}'
            result['message'] = f'GSC APIへの接続に失敗しました ({site_name}): {error_reason}'
            logger.error(f"GSC接続テストエラー ({site_name}): {error_reason}")
        except Exception as e:
            result['error'] = f'接続エラー: {str(e)}'
            result['message'] = f'GSCへの接続中にエラーが発生しました ({site_name}): {str(e)}'
            logger.error(f"GSC接続テストエラー ({site_name}): {e}", exc_info=True)
        
        return result
    
    def get_pagespeed_insights(self, url: str, strategy: str = 'mobile') -> Dict[str, Any]:
        """
        Page Speed Insights APIからパフォーマンスデータを取得
        
        Args:
            url (str): 分析するURL
            strategy (str): 分析戦略 ('mobile' または 'desktop')
            
        Returns:
            dict: Page Speed Insightsの結果
        """
        if not self.pagespeed_api_key:
            logger.warning("PAGESPEED_INSIGHTS_API_KEYが設定されていません")
            return {
                'error': 'PAGESPEED_INSIGHTS_API_KEYが設定されていません',
                'url': url
            }
        
        try:
            import requests
            
            api_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
            params = {
                'url': url,
                'key': self.pagespeed_api_key,
                'strategy': strategy,
                'category': ['PERFORMANCE', 'ACCESSIBILITY', 'BEST_PRACTICES', 'SEO']
            }
            
            logger.info(f"Page Speed Insights API呼び出し: {url} (strategy: {strategy})")
            # Page Speed Insights APIは処理に時間がかかるため、タイムアウトを60秒に設定
            response = requests.get(api_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # データを整形
            result = {
                'url': url,
                'strategy': strategy,
                'fetchTime': data.get('loadingExperience', {}).get('metrics', {}).get('FIRST_CONTENTFUL_PAINT_MS', {}).get('percentile', 0),
                'lighthouseResult': {}
            }
            
            if 'lighthouseResult' in data:
                lhr = data['lighthouseResult']
                result['lighthouseResult'] = {
                    'categories': {},
                    'audits': {}
                }
                
                # カテゴリスコア
                if 'categories' in lhr:
                    for category_name, category_data in lhr['categories'].items():
                        result['lighthouseResult']['categories'][category_name] = {
                            'score': category_data.get('score', 0) * 100 if category_data.get('score') else 0,
                            'title': category_data.get('title', '')
                        }
                
                # 主要な監査項目
                if 'audits' in lhr:
                    important_audits = [
                        'first-contentful-paint',
                        'largest-contentful-paint',
                        'total-blocking-time',
                        'cumulative-layout-shift',
                        'speed-index',
                        'interactive',
                        'server-response-time'
                    ]
                    
                    for audit_key in important_audits:
                        if audit_key in lhr['audits']:
                            audit = lhr['audits'][audit_key]
                            result['lighthouseResult']['audits'][audit_key] = {
                                'title': audit.get('title', ''),
                                'description': audit.get('description', ''),
                                'score': audit.get('score'),
                                'numericValue': audit.get('numericValue'),
                                'displayValue': audit.get('displayValue', ''),
                                'details': audit.get('details', {})
                            }
            
            # Core Web Vitals
            if 'loadingExperience' in data:
                loading_exp = data['loadingExperience']
                result['coreWebVitals'] = {}
                
                if 'metrics' in loading_exp:
                    metrics = loading_exp['metrics']
                    
                    # LCP (Largest Contentful Paint)
                    if 'LARGEST_CONTENTFUL_PAINT_MS' in metrics:
                        lcp = metrics['LARGEST_CONTENTFUL_PAINT_MS']
                        result['coreWebVitals']['LCP'] = {
                            'percentile': lcp.get('percentile', 0),
                            'category': lcp.get('category', 'UNKNOWN')
                        }
                    
                    # FID (First Input Delay)
                    if 'FIRST_INPUT_DELAY_MS' in metrics:
                        fid = metrics['FIRST_INPUT_DELAY_MS']
                        result['coreWebVitals']['FID'] = {
                            'percentile': fid.get('percentile', 0),
                            'category': fid.get('category', 'UNKNOWN')
                        }
                    
                    # CLS (Cumulative Layout Shift)
                    if 'CUMULATIVE_LAYOUT_SHIFT_SCORE' in metrics:
                        cls = metrics['CUMULATIVE_LAYOUT_SHIFT_SCORE']
                        result['coreWebVitals']['CLS'] = {
                            'percentile': cls.get('percentile', 0),
                            'category': cls.get('category', 'UNKNOWN')
                        }
            
            logger.info(f"Page Speed Insights取得成功: {url}")
            return result
            
        except Exception as e:
            import requests
            if isinstance(e, requests.exceptions.RequestException):
                logger.error(f"Page Speed Insights APIリクエストエラー ({url}): {e}")
                return {
                    'error': f'APIリクエストエラー: {str(e)}',
                    'url': url
                }
            else:
                logger.error(f"Page Speed Insights取得エラー ({url}): {e}", exc_info=True)
                return {
                    'error': f'予期しないエラー: {str(e)}',
                    'url': url
                }
    
    def get_ga4_data(self, date_range_days=30, metrics=None, dimensions=None, site_name=None):
        """
        GA4からデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            metrics (list): 取得するメトリクス
            dimensions (list): 取得するディメンション
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')、指定された場合はページパスでフィルタリング
        
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
                'activeUsers',  # GA4 APIでは 'users' ではなく 'activeUsers' を使用
                'screenPageViews',  # GA4 APIでは 'pageviews' ではなく 'screenPageViews' を使用
                'bounceRate',
                'averageSessionDuration',
                'conversions',
                'totalRevenue',
                'purchaseRevenue'
            ]
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = [
                'date',
                'pagePath',
                'sourceMedium',
                'deviceCategory',
                'country',
                'sessionDefaultChannelGroup'
            ]
        
        try:
            # 日付範囲の設定
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=date_range_days)).strftime('%Y-%m-%d')
            
            # サイト名に応じてページパスフィルタを設定
            dimension_filter = None
            if site_name:
                # 正規化（moodmark_idea -> moodmarkgift）
                normalized_site = 'moodmarkgift' if site_name == 'moodmark_idea' else site_name
                if normalized_site == 'moodmark':
                    page_path_prefix = '/moodmark'
                elif normalized_site == 'moodmarkgift':
                    page_path_prefix = '/moodmarkgift'
                else:
                    page_path_prefix = None
                
                if page_path_prefix:
                    # pagePathディメンションが含まれていない場合は追加
                    if 'pagePath' not in dimensions:
                        dimensions.append('pagePath')
                        logger.info(f"pagePathディメンションを追加（フィルタ用）")
                    
                    dimension_filter = {
                        'filter': {
                            'fieldName': 'pagePath',
                            'stringFilter': {
                                'matchType': 'BEGINS_WITH',
                                'value': page_path_prefix
                            }
                        }
                    }
                    logger.info(f"ページパスフィルタを適用: {normalized_site} -> {page_path_prefix}")
            
            # GA4リクエスト作成
            request_body = {
                'property': f'properties/{self.ga4_property_id}',
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [{'name': metric} for metric in metrics],
                'dimensions': [{'name': dimension} for dimension in dimensions],
                'limit': 100000
            }
            
            # ページパスフィルタを追加
            if dimension_filter:
                request_body['dimensionFilter'] = dimension_filter
            
            request = {
                'requests': [request_body]
            }
            
            # API呼び出し
            logger.info(f"GA4 API呼び出し開始: プロパティID={self.ga4_property_id}, 期間={start_date}～{end_date}, ディメンション={dimensions}, サイト={site_name}")
            try:
                response = self.ga4_service.properties().batchRunReports(
                    property=f'properties/{self.ga4_property_id}',
                    body=request
                ).execute()
                logger.info(f"GA4 API呼び出し完了: レスポンス受信")
            except Exception as api_error:
                logger.error(f"GA4 API呼び出しエラー: {api_error}", exc_info=True)
                raise
            
            # データの変換
            logger.info(f"GA4データ変換開始: レスポンス処理中...")
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
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            error_code = error_details.get('error', {}).get('code', 'N/A')
            logger.error(f"GA4 API エラー (コード: {error_code}): {error_reason}")
            logger.error(f"  プロパティID: {self.ga4_property_id}")
            logger.error(f"  エラー詳細: {error_details}")
            
            # よくあるエラーの原因をログに記録
            if error_code == 403:
                logger.error("  考えられる原因: サービスアカウントにGA4へのアクセス権限がありません")
                logger.error("  解決方法: GA4プロパティでサービスアカウントに閲覧者以上の権限を付与してください")
            elif error_code == 400:
                logger.error("  考えられる原因: プロパティIDが無効です")
                logger.error("  解決方法: GA4_PROPERTY_ID環境変数を確認してください")
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}", exc_info=True)
            logger.error(f"  プロパティID: {self.ga4_property_id}")
            return pd.DataFrame()
    
    def get_ga4_data_custom_range(self, start_date: str, end_date: str, metrics=None, dimensions=None, site_name=None):
        """
        カスタム日付範囲でGA4データを取得
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            metrics (list): 取得するメトリクス
            dimensions (list): 取得するディメンション
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')、指定された場合はページパスでフィルタリング
        
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
                'activeUsers',  # GA4 APIでは 'users' ではなく 'activeUsers' を使用
                'screenPageViews',  # GA4 APIでは 'pageviews' ではなく 'screenPageViews' を使用
                'bounceRate',
                'averageSessionDuration',
                'conversions',
                'totalRevenue',
                'purchaseRevenue'
            ]
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = [
                'date',
                'pagePath',
                'sourceMedium',
                'deviceCategory',
                'country',
                'sessionDefaultChannelGroup'
            ]
        
        try:
            # サイト名に応じてページパスフィルタを設定
            dimension_filter = None
            if site_name:
                # 正規化（moodmark_idea -> moodmarkgift）
                normalized_site = 'moodmarkgift' if site_name == 'moodmark_idea' else site_name
                if normalized_site == 'moodmark':
                    page_path_prefix = '/moodmark'
                elif normalized_site == 'moodmarkgift':
                    page_path_prefix = '/moodmarkgift'
                else:
                    page_path_prefix = None
                
                if page_path_prefix:
                    # pagePathディメンションが含まれていない場合は追加
                    if 'pagePath' not in dimensions:
                        dimensions.append('pagePath')
                        logger.info(f"pagePathディメンションを追加（フィルタ用）")
                    
                    dimension_filter = {
                        'filter': {
                            'fieldName': 'pagePath',
                            'stringFilter': {
                                'matchType': 'BEGINS_WITH',
                                'value': page_path_prefix
                            }
                        }
                    }
                    logger.info(f"ページパスフィルタを適用: {normalized_site} -> {page_path_prefix}")
            
            # GA4リクエスト作成
            request_body = {
                'property': f'properties/{self.ga4_property_id}',
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [{'name': metric} for metric in metrics],
                'dimensions': [{'name': dimension} for dimension in dimensions],
                'limit': 100000
            }
            
            # ページパスフィルタを追加
            if dimension_filter:
                request_body['dimensionFilter'] = dimension_filter
            
            request = {
                'requests': [request_body]
            }
            
            # API呼び出し
            logger.info(f"GA4 API呼び出し開始: プロパティID={self.ga4_property_id}, 期間={start_date}～{end_date}, ディメンション={dimensions}, サイト={site_name}")
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
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            error_code = error_details.get('error', {}).get('code', 'N/A')
            logger.error(f"GA4 API エラー (コード: {error_code}): {error_reason}")
            logger.error(f"  プロパティID: {self.ga4_property_id}")
            logger.error(f"  エラー詳細: {error_details}")
            
            # よくあるエラーの原因をログに記録
            if error_code == 403:
                logger.error("  考えられる原因: サービスアカウントにGA4へのアクセス権限がありません")
                logger.error("  解決方法: GA4プロパティでサービスアカウントに閲覧者以上の権限を付与してください")
            elif error_code == 400:
                logger.error("  考えられる原因: プロパティIDが無効です")
                logger.error("  解決方法: GA4_PROPERTY_ID環境変数を確認してください")
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}", exc_info=True)
            logger.error(f"  プロパティID: {self.ga4_property_id}")
            return pd.DataFrame()
    
    def get_page_specific_ga4_data(self, page_url: str, date_range_days=30, start_date: str = None, end_date: str = None):
        """
        特定ページのGA4データを取得
        
        Args:
            page_url (str): 分析するページのURL
            date_range_days (int): 取得する日数（start_date/end_dateが指定されていない場合に使用）
            start_date (str): 開始日 (YYYY-MM-DD形式、オプション)
            end_date (str): 終了日 (YYYY-MM-DD形式、オプション)
            
        Returns:
            dict: ページのGA4データ（セッション数、ユーザー数、ページビュー数、バウンス率、セッション時間など）
        """
        try:
            # GA4サービスが初期化されているか確認
            if not self.ga4_service or not self.ga4_property_id:
                logger.error("GA4サービスまたはプロパティIDが設定されていません")
                return {
                    'page_url': page_url,
                    'error': 'GA4サービスが初期化されていません。認証ファイルまたは環境変数を確認してください。'
                }
            
            # ページURLを正規化（サイトURLとの相対パスに変換）
            from urllib.parse import urlparse
            parsed_url = urlparse(page_url)
            page_path = parsed_url.path
            
            # カスタム日付範囲が指定されている場合はそれを使用、そうでなければdate_range_daysを使用
            # 個別ページのデータ取得では、dateディメンションを削除してデータ量を削減（タイムアウト回避）
            if start_date and end_date:
                logger.info(f"カスタム日付範囲でGA4データを取得: {start_date} ～ {end_date}, ページ: {page_path}")
                logger.info(f"  最適化: dateディメンションを除外してデータ量を削減")
                ga4_data = self.get_ga4_data_custom_range(
                    start_date=start_date,
                    end_date=end_date,
                    metrics=['sessions', 'activeUsers', 'screenPageViews', 'bounceRate', 'averageSessionDuration'],
                    dimensions=['pagePath']  # dateディメンションを削除してデータ量を削減
                )
                logger.info(f"GA4データ取得完了（カスタム範囲）: {len(ga4_data)}行")
            else:
                logger.info(f"GA4データを取得: 期間={date_range_days}日, ページ: {page_path}")
                logger.info(f"  最適化: dateディメンションを除外してデータ量を削減")
                ga4_data = self.get_ga4_data(
                    date_range_days=date_range_days,
                    metrics=['sessions', 'activeUsers', 'screenPageViews', 'bounceRate', 'averageSessionDuration'],
                    dimensions=['pagePath']  # dateディメンションを削除してデータ量を削減
                )
                logger.info(f"GA4データ取得完了: {len(ga4_data)}行")
            
            # ga4_dataが空の場合
            if ga4_data.empty:
                logger.warning(f"ページ固有のGA4データが見つかりませんでした: {page_path}")
                return {
                    'page_url': page_url,
                    'page_path': page_path,
                    'sessions': 0,
                    'users': 0,
                    'pageviews': 0,
                    'bounce_rate': 0.0,
                    'avg_session_duration': 0.0,
                    'error': 'GA4データが取得できませんでした。認証ファイルまたは環境変数を確認してください。'
                }
            
            # 指定されたページのデータをフィルタリング
            # ページパスが完全一致または部分一致するものを検索
            page_data = ga4_data[
                ga4_data['pagePath'].str.contains(page_path, case=False, na=False)
            ]
            
            if page_data.empty:
                logger.warning(f"ページ '{page_path}' のGA4データが見つかりませんでした")
                return {
                    'page_url': page_url,
                    'page_path': page_path,
                    'sessions': 0,
                    'users': 0,
                    'pageviews': 0,
                    'bounce_rate': 0.0,
                    'avg_session_duration': 0.0,
                    'error': f'ページ "{page_path}" のGA4データが見つかりませんでした'
                }
            
            # 集計
            total_sessions = page_data['sessions'].sum() if 'sessions' in page_data.columns else 0
            total_users = page_data['activeUsers'].sum() if 'activeUsers' in page_data.columns else 0
            total_pageviews = page_data['screenPageViews'].sum() if 'screenPageViews' in page_data.columns else 0
            avg_bounce_rate = page_data['bounceRate'].mean() if 'bounceRate' in page_data.columns else 0.0
            avg_session_duration = page_data['averageSessionDuration'].mean() if 'averageSessionDuration' in page_data.columns else 0.0
            
            logger.info(f"ページ固有のGA4データ取得完了: {page_path}")
            logger.info(f"  セッション数: {total_sessions:,}, ユーザー数: {total_users:,}, PV: {total_pageviews:,}")
            logger.info(f"  バウンス率: {avg_bounce_rate:.2f}%, 平均セッション時間: {avg_session_duration:.2f}秒")
            
            return {
                'page_url': page_url,
                'page_path': page_path,
                'sessions': int(total_sessions),
                'users': int(total_users),
                'pageviews': int(total_pageviews),
                'bounce_rate': round(avg_bounce_rate, 2),
                'avg_session_duration': round(avg_session_duration, 2),
                'date_range_days': date_range_days,
                'is_page_specific': True
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"ページ固有のGA4データ取得エラー ({page_url}): {error_msg}", exc_info=True)
            
            # タイムアウトエラーの場合、より詳細なメッセージを返す
            if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                return {
                    'page_url': page_url,
                    'error': f'GA4データ取得がタイムアウトしました。データ量が多いため、処理に時間がかかっています。他のデータ（GSC、SEO分析）で分析を続行します。',
                    'timeout': True
                }
            
            return {
                'page_url': page_url,
                'error': f'データ取得エラー: {error_msg}'
            }
    
    def get_gsc_data(self, date_range_days=30, dimensions=None, row_limit=25000, site_name='moodmark'):
        """
        Google Search Consoleからデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            dimensions (list): 取得するディメンション
            row_limit (int): 取得行数上限
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
        
        Returns:
            pd.DataFrame: GSCデータ
        """
        if not self.gsc_service:
            logger.error("GSCサービスが初期化されていません。認証ファイルを確認してください。")
            return pd.DataFrame()
        
        # サイトURLの取得
        gsc_site_url = self.gsc_site_urls.get(site_name)
        if not gsc_site_url:
            logger.error(f"GSCサイトURLが設定されていません（サイト: {site_name}）。環境変数を確認してください。")
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
            logger.info(f"GSCデータ取得: サイト={site_name}, URL={gsc_site_url}, 期間={date_range_days}日")
            response = self.gsc_service.searchanalytics().query(
                siteUrl=gsc_site_url,
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
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            logger.error(f"GSC API エラー: {error_reason}")
            logger.error(f"  エラー詳細: {error_details}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GSCデータ取得エラー: {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_top_pages_gsc(self, date_range_days=30, limit=100, site_name='moodmark'):
        """
        GSCから上位ページデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            limit (int): 取得件数
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
        
        Returns:
            pd.DataFrame: 上位ページデータ
        """
        gsc_data = self.get_gsc_data(
            date_range_days=date_range_days,
            dimensions=['page'],
            row_limit=limit,
            site_name=site_name
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
    
    def get_top_queries_gsc(self, date_range_days=30, limit=100, site_name='moodmark'):
        """
        GSCから上位クエリデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            limit (int): 取得件数
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
        
        Returns:
            pd.DataFrame: 上位クエリデータ
        """
        gsc_data = self.get_gsc_data(
            date_range_days=date_range_days,
            dimensions=['query'],
            row_limit=limit,
            site_name=site_name
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
    
    def get_page_specific_gsc_data(self, page_url: str, date_range_days=30, site_name='moodmark', start_date: str = None, end_date: str = None):
        """
        特定ページのGSCデータを取得
        
        Args:
            page_url (str): 分析するページのURL
            date_range_days (int): 取得する日数（start_date/end_dateが指定されていない場合に使用）
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
            start_date (str): 開始日 (YYYY-MM-DD形式、オプション)
            end_date (str): 終了日 (YYYY-MM-DD形式、オプション)
            
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
            
            # カスタム日付範囲が指定されている場合はそれを使用、そうでなければdate_range_daysを使用
            if start_date and end_date:
                logger.info(f"カスタム日付範囲でGSCデータを取得: {start_date} ～ {end_date}")
                result = self._get_gsc_data_custom_range(
                    start_date=start_date,
                    end_date=end_date,
                    page_url=page_url,
                    site_name=site_name
                )
                # _get_gsc_data_custom_rangeはpage_urlが指定されている場合はdictを返す
                if isinstance(result, dict):
                    return result
                # DataFrameが返された場合（通常は発生しないが念のため）
                gsc_data = result
            else:
                # GSCデータを取得（ページディメンションで）
                gsc_data = self.get_gsc_data(
                    date_range_days=date_range_days,
                    dimensions=['page', 'date'],
                    row_limit=25000,
                    site_name=site_name
                )
            
            # gsc_dataがDataFrameの場合の処理
            if hasattr(gsc_data, 'empty') and gsc_data.empty:
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
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            error_code = error_details.get('error', {}).get('code', e.resp.status if hasattr(e, 'resp') else 'N/A')
            logger.error(f"GSC API エラー (コード: {error_code}): {error_reason}")
            logger.error(f"  エラー詳細: {error_details}")
            return {
                'page_url': page_url,
                'error': f'GSC API エラー: {error_reason}',
                'error_code': error_code
            }
        except Exception as e:
            logger.error(f"ページ固有のGSCデータ取得エラー ({page_url}): {e}")
            return {
                'page_url': page_url,
                'error': f'データ取得エラー: {str(e)}'
            }
    
    def get_yearly_comparison_gsc(self, page_url: str = None, date_range_days=30, site_name='moodmark'):
        """
        年次比較用のGSCデータを取得（今年と昨年の同じ期間）
        
        Args:
            page_url (str): 分析するページのURL（オプション、指定されない場合は全体）
            date_range_days (int): 比較する期間の日数
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
            
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
                this_year_data = self.get_page_specific_gsc_data(page_url, date_range_days, site_name=site_name)
                # エラーが含まれている場合は、エラーを返す
                if 'error' in this_year_data:
                    return {
                        'error': this_year_data.get('error', '今年のデータ取得エラー')
                    }
            else:
                gsc_data = self.get_gsc_data(date_range_days=date_range_days, dimensions=['page'], site_name=site_name)
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
                page_url=page_url,
                site_name=site_name
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
    
    def _get_gsc_data_custom_range(self, start_date: str, end_date: str, page_url: str = None, site_name='moodmark'):
        """
        カスタム日付範囲でGSCデータを取得（内部メソッド）
        
        Args:
            start_date (str): 開始日 (YYYY-MM-DD)
            end_date (str): 終了日 (YYYY-MM-DD)
            page_url (str): ページURL（オプション）
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
            
        Returns:
            pd.DataFrame or dict: GSCデータ
        """
        if not self.gsc_service:
            error_msg = 'GSCサービスが初期化されていません。認証ファイル（GOOGLE_CREDENTIALS_FILE）を確認してください。'
            logger.error(error_msg)
            return pd.DataFrame() if not page_url else {'error': error_msg}
        
        # サイトURLの取得
        gsc_site_url = self.gsc_site_urls.get(site_name)
        if not gsc_site_url:
            error_msg = f'GSCサイトURLが設定されていません（サイト: {site_name}）。環境変数を確認してください。'
            logger.error(error_msg)
            return pd.DataFrame() if not page_url else {'error': error_msg}
        
        try:
            # page_urlが指定されている場合は、ページパスを抽出
            page_path = None
            if page_url:
                from urllib.parse import urlparse
                parsed_url = urlparse(page_url)
                page_path = parsed_url.path
            
            dimensions = ['page', 'date'] if page_url else ['page']
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': 25000,
                'startRow': 0
            }
            
            logger.info(f"GSCデータ取得（カスタム範囲）: サイト={site_name}, URL={gsc_site_url}, 期間={start_date} ～ {end_date}, ページ={page_path or '全体'}")
            response = self.gsc_service.searchanalytics().query(
                siteUrl=gsc_site_url,
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
            
            if page_url and page_path:
                # ページURLでフィルタリング
                page_data = df[df['page'].str.contains(page_path, case=False, na=False)]
                
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
                
                total_clicks = page_data['clicks'].sum()
                total_impressions = page_data['impressions'].sum()
                avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
                avg_position = page_data['position'].mean()
                
                logger.info(f"ページ固有のGSCデータ取得完了（カスタム範囲）: {page_path}")
                logger.info(f"  クリック数: {total_clicks:,}, インプレッション数: {total_impressions:,}")
                logger.info(f"  CTR: {avg_ctr:.2f}%, 平均順位: {avg_position:.2f}")
                
                return {
                    'page_url': page_url,
                    'page_path': page_path,
                    'clicks': int(total_clicks),
                    'impressions': int(total_impressions),
                    'ctr': round(avg_ctr, 2),
                    'avg_position': round(avg_position, 2),
                    'start_date': start_date,
                    'end_date': end_date
                }
            
            return df
            
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8')) if e.content else {}
            error_reason = error_details.get('error', {}).get('message', str(e))
            error_code = error_details.get('error', {}).get('code', e.resp.status if hasattr(e, 'resp') else 'N/A')
            logger.error(f"GSC API エラー (コード: {error_code}): {error_reason}")
            logger.error(f"  エラー詳細: {error_details}")
            if page_url:
                return {
                    'error': f'GSC API エラー: {error_reason}',
                    'error_code': error_code
                }
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"カスタム日付範囲のGSCデータ取得エラー: {e}")
            if page_url:
                return {'error': str(e)}
            return pd.DataFrame()
    
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
                'total_users': ga4_data['activeUsers'].sum() if 'activeUsers' in ga4_data.columns else 0,  # GA4 APIでは 'activeUsers' を使用
                'total_pageviews': ga4_data['screenPageViews'].sum() if 'screenPageViews' in ga4_data.columns else 0,  # GA4 APIでは 'screenPageViews' を使用
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
