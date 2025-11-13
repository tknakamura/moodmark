#!/usr/bin/env python3
"""
OAuth 2.0を使用したGoogle APIs統合システム
- Google Analytics 4 (GA4) API
- Google Search Console (GSC) API  
- ユーザー認証方式（サービスアカウントではなくOAuth 2.0）
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth 2.0スコープ
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly'
]

class OAuthGoogleAPIsIntegration:
    def __init__(self, credentials_path='config/oauth_credentials.json', token_path='config/token.json'):
        """
        OAuth 2.0を使用したGoogle APIs統合クラスの初期化
        
        Args:
            credentials_path (str): OAuth 2.0クライアント認証情報ファイルのパス
            token_path (str): 保存されたトークンファイルのパス
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.credentials = None
        self.ga4_service = None
        self.gsc_service = None
        
        # 設定の読み込み
        self.config = self._load_config()
        
        # GA4プロパティIDとGSCサイトURLを設定から取得
        self.ga4_property_id = self.config.get('sites', {}).get('moodmark', {}).get('ga4_property_id')
        self.gsc_site_url = self.config.get('sites', {}).get('moodmark', {}).get('gsc_site_url')
        
        # 認証
        self._authenticate()
    
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
    
    def _authenticate(self):
        """OAuth 2.0認証"""
        try:
            # 既存のトークンをロード
            if os.path.exists(self.token_path):
                self.credentials = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            
            # トークンが無効または存在しない場合、新しく取得
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("トークンをリフレッシュしています...")
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"OAuth認証情報ファイルが見つかりません: {self.credentials_path}")
                        logger.error("Google Cloud ConsoleでOAuth 2.0クライアントIDを作成し、JSONファイルをダウンロードしてください。")
                        return
                    
                    logger.info("OAuth 2.0認証フローを開始します...")
                    logger.info("ブラウザが開きます。Googleアカウントでログインしてください。")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                
                # トークンを保存
                with open(self.token_path, 'w', encoding='utf-8') as token:
                    token.write(self.credentials.to_json())
                logger.info(f"トークンを保存しました: {self.token_path}")
            
            # GA4 APIサービス構築
            self.ga4_service = build('analyticsdata', 'v1beta', credentials=self.credentials)
            
            # GSC APIサービス構築
            self.gsc_service = build('searchconsole', 'v1', credentials=self.credentials)
            
            logger.info("Google APIs認証完了")
            
        except Exception as e:
            logger.error(f"認証エラー: {e}")
    
    def get_ga4_data(self, date_range_days=30, metrics=None, dimensions=None, property_id=None):
        """
        GA4からデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            metrics (list): 取得するメトリクス
            dimensions (list): 取得するディメンション
            property_id (str): GA4プロパティID（指定しない場合は設定から取得）
        
        Returns:
            pd.DataFrame: GA4データ
        """
        if not self.ga4_service:
            logger.error("GA4サービスが初期化されていません")
            return pd.DataFrame()
        
        # プロパティIDの決定
        prop_id = property_id or self.ga4_property_id
        if not prop_id:
            logger.error("GA4プロパティIDが設定されていません")
            return pd.DataFrame()
        
        # デフォルトメトリクス
        if not metrics:
            metrics = [
                'sessions',
                'totalUsers',
                'screenPageViews',
                'bounceRate',
                'averageSessionDuration',
                'conversions'
            ]
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = [
                'date',
                'pagePath',
                'sessionDefaultChannelGrouping',
                'deviceCategory'
            ]
        
        try:
            # 日付範囲の設定
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=date_range_days)).strftime('%Y-%m-%d')
            
            logger.info(f"GA4データ取得: {start_date} 〜 {end_date}")
            logger.info(f"プロパティID: {prop_id}")
            
            # GA4リクエスト作成
            request_body = {
                'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
                'metrics': [{'name': metric} for metric in metrics],
                'dimensions': [{'name': dimension} for dimension in dimensions],
                'limit': 10000
            }
            
            # API呼び出し
            response = self.ga4_service.properties().runReport(
                property=f'properties/{prop_id}',
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
            if e.resp.status == 403:
                logger.error("権限エラー: GA4プロパティへのアクセス権限を確認してください")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_gsc_data(self, date_range_days=30, dimensions=None, row_limit=25000, site_url=None):
        """
        Google Search Consoleからデータを取得
        
        Args:
            date_range_days (int): 取得する日数
            dimensions (list): 取得するディメンション
            row_limit (int): 取得行数上限
            site_url (str): サイトURL（指定しない場合は設定から取得）
        
        Returns:
            pd.DataFrame: GSCデータ
        """
        if not self.gsc_service:
            logger.error("GSCサービスが初期化されていません")
            return pd.DataFrame()
        
        # サイトURLの決定
        url = site_url or self.gsc_site_url
        if not url:
            logger.error("GSCサイトURLが設定されていません")
            return pd.DataFrame()
        
        # デフォルトディメンション
        if not dimensions:
            dimensions = ['date', 'query', 'page', 'country', 'device']
        
        try:
            # 日付範囲の設定（GSCは3日前までのデータしか取得できない）
            end_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=date_range_days + 3)).strftime('%Y-%m-%d')
            
            logger.info(f"GSCデータ取得: {start_date} 〜 {end_date}")
            logger.info(f"サイトURL: {url}")
            
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
                siteUrl=url,
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
            if e.resp.status == 403:
                logger.error("権限エラー: Search Consoleプロパティへのアクセス権限を確認してください")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"GSCデータ取得エラー: {e}")
            return pd.DataFrame()
    
    def get_summary_report(self, date_range_days=30):
        """
        サマリーレポートを生成
        
        Args:
            date_range_days (int): 取得する日数
        
        Returns:
            dict: サマリーレポート
        """
        logger.info("サマリーレポート生成開始")
        
        # GA4データ取得
        ga4_data = self.get_ga4_data(date_range_days)
        
        # GSCデータ取得
        gsc_data = self.get_gsc_data(date_range_days)
        
        # サマリー作成
        summary = {
            'report_date': datetime.now().isoformat(),
            'date_range_days': date_range_days,
            'site_url': self.gsc_site_url,
            'ga4_property_id': self.ga4_property_id,
            'ga4_summary': {},
            'gsc_summary': {}
        }
        
        # GA4サマリー
        if not ga4_data.empty:
            summary['ga4_summary'] = {
                'total_sessions': int(ga4_data['sessions'].sum()) if 'sessions' in ga4_data.columns else 0,
                'total_users': int(ga4_data['totalUsers'].sum()) if 'totalUsers' in ga4_data.columns else 0,
                'total_pageviews': int(ga4_data['screenPageViews'].sum()) if 'screenPageViews' in ga4_data.columns else 0,
                'avg_bounce_rate': float(ga4_data['bounceRate'].mean()) if 'bounceRate' in ga4_data.columns else 0,
                'avg_session_duration': float(ga4_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in ga4_data.columns else 0,
                'total_conversions': int(ga4_data['conversions'].sum()) if 'conversions' in ga4_data.columns else 0,
                'data_rows': len(ga4_data)
            }
        
        # GSCサマリー
        if not gsc_data.empty:
            summary['gsc_summary'] = {
                'total_clicks': int(gsc_data['clicks'].sum()),
                'total_impressions': int(gsc_data['impressions'].sum()),
                'avg_ctr': float(gsc_data['ctr'].mean() * 100),
                'avg_position': float(gsc_data['position'].mean()),
                'data_rows': len(gsc_data)
            }
        
        logger.info("サマリーレポート生成完了")
        return summary
    
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
            data.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"データをエクスポートしました: {filepath}")
        except Exception as e:
            logger.error(f"エクスポートエラー: {e}")


def main():
    """メイン実行関数"""
    print("=== OAuth 2.0 Google APIs統合分析開始 ===\n")
    
    # API統合インスタンス作成
    api = OAuthGoogleAPIsIntegration()
    
    if not api.credentials:
        print("❌ 認証に失敗しました。")
        print("以下を確認してください：")
        print("1. config/oauth_credentials.json が存在するか")
        print("2. Google Cloud ConsoleでOAuth 2.0クライアントIDを作成したか")
        print("3. GA4プロパティへのアクセス権限があるか")
        return
    
    # サマリーレポート生成
    print("📊 データ取得中...\n")
    summary = api.get_summary_report(date_range_days=30)
    
    # 結果表示
    print("=" * 60)
    print("統合サマリーレポート")
    print("=" * 60)
    print(f"レポート日時: {summary['report_date']}")
    print(f"分析期間: {summary['date_range_days']}日")
    print(f"サイトURL: {summary['site_url']}")
    print(f"GA4プロパティID: {summary['ga4_property_id']}")
    
    print("\n--- GA4サマリー ---")
    if summary['ga4_summary']:
        for key, value in summary['ga4_summary'].items():
            print(f"  {key}: {value:,}")
    else:
        print("  データがありません")
    
    print("\n--- GSCサマリー ---")
    if summary['gsc_summary']:
        for key, value in summary['gsc_summary'].items():
            print(f"  {key}: {value:,.2f}")
    else:
        print("  データがありません")
    
    # データエクスポート
    print("\n=== データエクスポート ===")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # GA4データ
    ga4_data = api.get_ga4_data(date_range_days=30)
    if not ga4_data.empty:
        api.export_to_csv(ga4_data, f'ga4_data_oauth_{timestamp}.csv')
        print(f"✅ GA4データをエクスポートしました")
    
    # GSCデータ
    gsc_data = api.get_gsc_data(date_range_days=30)
    if not gsc_data.empty:
        api.export_to_csv(gsc_data, f'gsc_data_oauth_{timestamp}.csv')
        print(f"✅ GSCデータをエクスポートしました")
    
    # サマリーレポート保存
    summary_file = f'data/processed/summary_report_oauth_{timestamp}.json'
    os.makedirs('data/processed', exist_ok=True)
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ サマリーレポートを保存しました: {summary_file}")
    
    print("\n✨ 分析完了！")


if __name__ == "__main__":
    main()


