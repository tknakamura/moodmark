#!/usr/bin/env python3
"""
Google Looker Studio コネクタ
- データソースの自動更新
- レポートの自動生成
- ダッシュボードの管理
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)

class LookerStudioConnector:
    def __init__(self, credentials_file=None):
        """
        Looker Studio コネクタの初期化
        
        Args:
            credentials_file (str): サービスアカウントキーファイルのパス
        """
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE')
        self.credentials = None
        self.drive_service = None
        self.sheets_service = None
        
        # 環境変数から設定を取得
        self.dashboard_folder_id = os.getenv('LOOKER_STUDIO_FOLDER_ID')
        self.data_source_folder_id = os.getenv('DATA_SOURCE_FOLDER_ID')
        
        self._authenticate()
    
    def _authenticate(self):
        """Google APIs認証"""
        try:
            if self.credentials_file and os.path.exists(self.credentials_file):
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=[
                        'https://www.googleapis.com/auth/drive',
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/bigquery'
                    ]
                )
            else:
                logger.warning("認証ファイルが見つかりません。")
                return
            
            # Google Drive API
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            # Google Sheets API
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            logger.info("Looker Studio コネクタ認証完了")
            
        except Exception as e:
            logger.error(f"認証エラー: {e}")
    
    def create_data_source_sheet(self, data, sheet_name, folder_id=None):
        """
        データソース用のGoogle Sheetsを作成
        
        Args:
            data (pd.DataFrame): データ
            sheet_name (str): シート名
            folder_id (str): フォルダID
        
        Returns:
            str: 作成されたスプレッドシートID
        """
        try:
            # スプレッドシート作成
            spreadsheet_body = {
                'properties': {
                    'title': sheet_name,
                    'timeZone': 'Asia/Tokyo'
                }
            }
            
            if folder_id:
                spreadsheet_body['parents'] = [folder_id]
            
            spreadsheet = self.sheets_service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            spreadsheet_id = spreadsheet['spreadsheetId']
            
            # データをシートに書き込み
            self._write_data_to_sheet(spreadsheet_id, data)
            
            # フォルダに移動（指定されている場合）
            if folder_id:
                self._move_to_folder(spreadsheet_id, folder_id)
            
            logger.info(f"データソースシート作成完了: {sheet_name} (ID: {spreadsheet_id})")
            return spreadsheet_id
            
        except Exception as e:
            logger.error(f"データソースシート作成エラー: {e}")
            return None
    
    def _write_data_to_sheet(self, spreadsheet_id, data):
        """データをスプレッドシートに書き込み"""
        try:
            # ヘッダー行の準備
            headers = list(data.columns)
            values = [headers] + data.values.tolist()
            
            # データを書き込み
            body = {
                'values': values
            }
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"データ書き込み完了: {len(data)}行")
            
        except Exception as e:
            logger.error(f"データ書き込みエラー: {e}")
    
    def _move_to_folder(self, file_id, folder_id):
        """ファイルを指定フォルダに移動"""
        try:
            # ファイルの親フォルダを取得
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            previous_parents = ",".join(file.get('parents'))
            
            # ファイルを新しいフォルダに移動
            self.drive_service.files().update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            logger.info(f"ファイルをフォルダに移動: {file_id} -> {folder_id}")
            
        except Exception as e:
            logger.error(f"フォルダ移動エラー: {e}")
    
    def update_data_source(self, spreadsheet_id, data):
        """
        既存のデータソースを更新
        
        Args:
            spreadsheet_id (str): スプレッドシートID
            data (pd.DataFrame): 新しいデータ
        """
        try:
            # 既存のデータをクリア
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range='A:Z'
            ).execute()
            
            # 新しいデータを書き込み
            self._write_data_to_sheet(spreadsheet_id, data)
            
            logger.info(f"データソース更新完了: {spreadsheet_id}")
            
        except Exception as e:
            logger.error(f"データソース更新エラー: {e}")
    
    def create_dashboard_template(self, dashboard_name, data_sources):
        """
        ダッシュボードテンプレートを作成
        
        Args:
            dashboard_name (str): ダッシュボード名
            data_sources (list): データソース情報
        
        Returns:
            str: 作成されたダッシュボードID
        """
        try:
            # ダッシュボード用のスプレッドシートを作成
            dashboard_body = {
                'properties': {
                    'title': f"{dashboard_name}_Dashboard",
                    'timeZone': 'Asia/Tokyo'
                }
            }
            
            if self.dashboard_folder_id:
                dashboard_body['parents'] = [self.dashboard_folder_id]
            
            dashboard = self.sheets_service.spreadsheets().create(
                body=dashboard_body
            ).execute()
            
            dashboard_id = dashboard['spreadsheetId']
            
            # ダッシュボード設定シートを作成
            self._create_dashboard_config_sheet(dashboard_id, data_sources)
            
            logger.info(f"ダッシュボードテンプレート作成完了: {dashboard_name} (ID: {dashboard_id})")
            return dashboard_id
            
        except Exception as e:
            logger.error(f"ダッシュボードテンプレート作成エラー: {e}")
            return None
    
    def _create_dashboard_config_sheet(self, dashboard_id, data_sources):
        """ダッシュボード設定シートを作成"""
        try:
            # 設定データの準備
            config_data = {
                'data_sources': data_sources,
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # JSON形式でシートに書き込み
            config_sheet = {
                'properties': {
                    'title': 'Dashboard_Config',
                    'sheetType': 'GRID'
                }
            }
            
            # シートを追加
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=dashboard_id,
                body={
                    'requests': [{
                        'addSheet': config_sheet
                    }]
                }
            ).execute()
            
            # 設定データを書き込み
            config_values = [
                ['設定項目', '値'],
                ['データソース数', len(data_sources)],
                ['作成日時', config_data['created_at']],
                ['最終更新', config_data['last_updated']],
                ['バージョン', config_data['version']]
            ]
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=dashboard_id,
                range='Dashboard_Config!A1:B5',
                valueInputOption='RAW',
                body={'values': config_values}
            ).execute()
            
            logger.info("ダッシュボード設定シート作成完了")
            
        except Exception as e:
            logger.error(f"ダッシュボード設定シート作成エラー: {e}")
    
    def generate_looker_studio_instructions(self, data_sources, dashboard_id):
        """
        Looker Studio セットアップ手順を生成
        
        Args:
            data_sources (list): データソース情報
            dashboard_id (str): ダッシュボードID
        
        Returns:
            str: セットアップ手順
        """
        instructions = f"""
# Looker Studio セットアップ手順

## ダッシュボードID
{dashboard_id}

## データソース接続手順

### 1. Looker Studio にアクセス
- https://datastudio.google.com/ にアクセス
- 新しいレポートを作成

### 2. データソースの追加
"""
        
        for i, source in enumerate(data_sources, 1):
            instructions += f"""
#### データソース {i}: {source['name']}
- **スプレッドシートID**: {source['spreadsheet_id']}
- **説明**: {source['description']}
- **接続方法**: 
  1. データソース追加 → Google Sheets
  2. スプレッドシートID: {source['spreadsheet_id']}
  3. 接続を確認

"""
        
        instructions += f"""
### 3. レポートの作成
1. 上記データソースをすべて追加
2. 以下のチャートを作成:

#### 必須チャート
- **概要メトリクス**: セッション数、ユーザー数、ページビュー数
- **時系列グラフ**: 日別の主要メトリクス
- **ページ別パフォーマンス**: 上位ページのトラフィック
- **検索クエリ分析**: 上位検索クエリのクリック数・インプレッション数
- **デバイス別分析**: デバイスカテゴリ別のパフォーマンス
- **地理的分布**: 国別のトラフィック分布

#### 推奨チャート
- **コンバージョン分析**: コンバージョン率と収益
- **バウンス率分析**: ページ別バウンス率
- **検索順位分析**: 平均検索順位の推移
- **CTR分析**: クリック率の分析

### 4. 自動更新設定
1. 各データソースで「自動更新」を有効化
2. 更新頻度: 毎日
3. データの新鮮度: 24時間以内

### 5. 共有設定
1. レポートを共有可能に設定
2. 関係者に閲覧権限を付与
3. 定期レポート配信の設定

## 注意事項
- データソースは定期的に更新されます
- 新しいデータが追加された場合は、レポートを手動で更新してください
- パフォーマンスに問題がある場合は、データ量を確認してください
"""
        
        return instructions
    
    def create_automated_report_system(self, api_integration, report_config):
        """
        自動レポートシステムを作成
        
        Args:
            api_integration: GoogleAPIsIntegrationインスタンス
            report_config (dict): レポート設定
        
        Returns:
            dict: 作成されたレポート情報
        """
        try:
            logger.info("自動レポートシステム作成開始")
            
            # データ取得
            ga4_data = api_integration.get_ga4_data(
                date_range_days=report_config.get('date_range_days', 30)
            )
            
            gsc_pages = api_integration.get_top_pages_gsc(
                date_range_days=report_config.get('date_range_days', 30),
                limit=report_config.get('top_pages_limit', 100)
            )
            
            gsc_queries = api_integration.get_top_queries_gsc(
                date_range_days=report_config.get('date_range_days', 30),
                limit=report_config.get('top_queries_limit', 100)
            )
            
            # データソース作成
            data_sources = []
            
            if not ga4_data.empty:
                ga4_sheet_id = self.create_data_source_sheet(
                    ga4_data,
                    f"GA4_Data_{datetime.now().strftime('%Y%m%d')}",
                    self.data_source_folder_id
                )
                if ga4_sheet_id:
                    data_sources.append({
                        'name': 'GA4 Analytics Data',
                        'spreadsheet_id': ga4_sheet_id,
                        'description': 'Google Analytics 4の詳細データ'
                    })
            
            if not gsc_pages.empty:
                gsc_pages_sheet_id = self.create_data_source_sheet(
                    gsc_pages,
                    f"GSC_Pages_{datetime.now().strftime('%Y%m%d')}",
                    self.data_source_folder_id
                )
                if gsc_pages_sheet_id:
                    data_sources.append({
                        'name': 'GSC Pages Data',
                        'spreadsheet_id': gsc_pages_sheet_id,
                        'description': 'Google Search Consoleのページ別データ'
                    })
            
            if not gsc_queries.empty:
                gsc_queries_sheet_id = self.create_data_source_sheet(
                    gsc_queries,
                    f"GSC_Queries_{datetime.now().strftime('%Y%m%d')}",
                    self.data_source_folder_id
                )
                if gsc_queries_sheet_id:
                    data_sources.append({
                        'name': 'GSC Queries Data',
                        'spreadsheet_id': gsc_queries_sheet_id,
                        'description': 'Google Search Consoleのクエリ別データ'
                    })
            
            # ダッシュボードテンプレート作成
            dashboard_id = self.create_dashboard_template(
                f"MOOD_MARK_Analytics_{datetime.now().strftime('%Y%m%d')}",
                data_sources
            )
            
            # セットアップ手順生成
            instructions = self.generate_looker_studio_instructions(data_sources, dashboard_id)
            
            # 手順をファイルに保存
            instructions_file = f'data/processed/looker_studio_setup_{datetime.now().strftime("%Y%m%d")}.md'
            os.makedirs('data/processed', exist_ok=True)
            
            with open(instructions_file, 'w', encoding='utf-8') as f:
                f.write(instructions)
            
            result = {
                'dashboard_id': dashboard_id,
                'data_sources': data_sources,
                'instructions_file': instructions_file,
                'created_at': datetime.now().isoformat()
            }
            
            logger.info("自動レポートシステム作成完了")
            return result
            
        except Exception as e:
            logger.error(f"自動レポートシステム作成エラー: {e}")
            return {}

def main():
    """メイン実行関数"""
    print("=== Looker Studio コネクタテスト ===")
    
    # 環境変数の確認
    if not os.getenv('GOOGLE_CREDENTIALS_FILE'):
        print("GOOGLE_CREDENTIALS_FILE環境変数が設定されていません。")
        return
    
    # コネクタ初期化
    connector = LookerStudioConnector()
    
    if not connector.credentials:
        print("認証に失敗しました。")
        return
    
    print("Looker Studio コネクタ初期化完了")
    print("詳細な機能テストは、Google APIs統合システムと組み合わせて実行してください。")

if __name__ == "__main__":
    main()
