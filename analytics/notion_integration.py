#!/usr/bin/env python3
"""
Notion API統合モジュール
- Notionワークスペースとの連携
- 分析レポートの自動送信
- データベース管理
- ページ作成・更新
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError

# ログ設定
logger = logging.getLogger(__name__)

class NotionIntegration:
    def __init__(self, config_path: str = 'config/notion_config.json'):
        """
        Notion統合クラスの初期化
        
        Args:
            config_path (str): 設定ファイルのパス
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.client = None
        self.database_id = None
        
        # Notion API認証
        self._authenticate()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルの読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"設定ファイルが見つかりません: {self.config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"設定ファイルの形式エラー: {e}")
            return {}
    
    def _authenticate(self) -> bool:
        """Notion API認証"""
        try:
            # 環境変数またはファイルからトークンを取得
            token = os.getenv('NOTION_TOKEN') or self.config.get('notion', {}).get('integration_token')
            
            if not token:
                logger.error("Notionトークンが設定されていません")
                return False
            
            # Notionクライアントの初期化
            self.client = Client(auth=token)
            
            # データベースIDの取得
            self.database_id = os.getenv('NOTION_DATABASE_ID') or self.config.get('notion', {}).get('database_id')
            
            # 接続テスト
            if self.database_id:
                self.client.databases.retrieve(database_id=self.database_id)
                logger.info("Notion API認証成功")
                return True
            else:
                logger.warning("データベースIDが設定されていません")
                return True  # データベースは後で作成可能
                
        except APIResponseError as e:
            logger.error(f"Notion API認証エラー: {e}")
            return False
        except Exception as e:
            logger.error(f"Notion認証に予期しないエラー: {e}")
            return False
    
    def create_analytics_database(self, parent_page_id: Optional[str] = None) -> Optional[str]:
        """
        分析レポート用データベースの作成
        
        Args:
            parent_page_id (str, optional): 親ページのID
            
        Returns:
            str: 作成されたデータベースID
        """
        try:
            if not self.client:
                logger.error("Notionクライアントが初期化されていません")
                return None
            
            # デフォルトのプロパティ設定（設定ファイルからは読み込まない）
            default_properties = {
                "Title": {"title": {}},
                "Report Date": {"date": {}},
                "Period": {"rich_text": {}},
                "Total Sessions": {"number": {"format": "number"}},
                "Total Users": {"number": {"format": "number"}},
                "Total Revenue (¥)": {"number": {"format": "number_with_commas"}},
                "CVR (%)": {"number": {"format": "percent"}},
                "AOV (¥)": {"number": {"format": "number_with_commas"}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Generated", "color": "blue"},
                            {"name": "Reviewed", "color": "yellow"},
                            {"name": "Actioned", "color": "green"}
                        ]
                    }
                },
                "Priority": {
                    "select": {
                        "options": [
                            {"name": "High", "color": "red"},
                            {"name": "Medium", "color": "yellow"},
                            {"name": "Low", "color": "gray"}
                        ]
                    }
                },
                "Tags": {
                    "multi_select": {
                        "options": [
                            {"name": "Weekly Report", "color": "blue"},
                            {"name": "Performance", "color": "green"},
                            {"name": "SEO", "color": "purple"},
                            {"name": "Mobile", "color": "orange"},
                            {"name": "Desktop", "color": "gray"}
                        ]
                    }
                }
            }
            
            # プロパティはデフォルトのみを使用
            final_properties = default_properties
            
            # 親ページの設定
            if not parent_page_id:
                parent_page_id = os.getenv('NOTION_PAGE_ID') or self.config.get('notion', {}).get('page_id')
            
            if not parent_page_id:
                logger.error("親ページIDが設定されていません")
                return None
            
            # データベース作成
            database = self.client.databases.create(
                parent={
                    "type": "page_id",
                    "page_id": parent_page_id
                },
                title=[
                    {
                        "type": "text",
                        "text": {
                            "content": "Analytics Reports - MOO-D MARK"
                        }
                    }
                ],
                properties=final_properties
            )
            
            database_id = database['id']
            logger.info(f"分析レポート用データベースを作成しました: {database_id}")
            
            # 設定ファイルにデータベースIDを保存
            self.database_id = database_id
            self._update_config('notion.database_id', database_id)
            
            return database_id
            
        except APIResponseError as e:
            logger.error(f"データベース作成エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"データベース作成に予期しないエラー: {e}")
            return None
    
    def _update_config(self, key_path: str, value: Any) -> bool:
        """設定ファイルの更新"""
        try:
            keys = key_path.split('.')
            config = self.config.copy()
            
            # ネストされたキーに値を設定
            current = config
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            
            # ファイルに保存
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.config = config
            return True
            
        except Exception as e:
            logger.error(f"設定更新エラー: {e}")
            return False
    
    def create_report_page(self, report_data: Dict[str, Any], report_content: str) -> Optional[str]:
        """
        分析レポートページの作成
        
        Args:
            report_data (dict): レポートのメタデータ
            report_content (str): レポートのMarkdown内容
            
        Returns:
            str: 作成されたページID
        """
        try:
            if not self.client or not self.database_id:
                logger.error("NotionクライアントまたはデータベースIDが設定されていません")
                return None
            
            # ページプロパティの構築
            properties = self._build_page_properties(report_data)
            
            # ページ内容の構築
            children = self._build_page_content(report_content, report_data)
            
            # ページ作成
            page = self.client.pages.create(
                parent={
                    "type": "database_id",
                    "database_id": self.database_id
                },
                properties=properties,
                children=children
            )
            
            page_id = page['id']
            logger.info(f"レポートページを作成しました: {page_id}")
            
            return page_id
            
        except APIResponseError as e:
            logger.error(f"ページ作成エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"ページ作成に予期しないエラー: {e}")
            return None
    
    def _build_page_properties(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """ページプロパティの構築"""
        summary = report_data.get('summary', {})
        
        # 日付の処理
        report_date = report_data.get('report_date', datetime.now().isoformat())
        if isinstance(report_date, str):
            try:
                report_date = datetime.fromisoformat(report_date.replace('Z', '+00:00'))
            except:
                report_date = datetime.now()
        
        # タイトルの生成
        period = report_data.get('period', '分析期間不明')
        title = f"📊 MOO-D MARK 分析レポート - {period}"
        
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Report Date": {
                "date": {
                    "start": report_date.strftime('%Y-%m-%d')
                }
            },
            "Period": {
                "rich_text": [
                    {
                        "text": {
                            "content": period
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": "Generated"
                }
            },
            "Priority": {
                "select": {
                    "name": "Medium"
                }
            },
            "Tags": {
                "multi_select": [
                    {"name": "Weekly Report"}
                ]
            }
        }
        
        # 数値データの追加
        if summary:
            if 'total_sessions' in summary:
                properties["Total Sessions"] = {
                    "number": summary['total_sessions']
                }
            
            if 'total_users' in summary:
                properties["Total Users"] = {
                    "number": summary['total_users']
                }
            
            if 'total_revenue' in summary:
                properties["Total Revenue (¥)"] = {
                    "number": round(summary['total_revenue'])
                }
            
            if 'purchase_cvr' in summary:
                properties["CVR (%)"] = {
                    "number": round(summary['purchase_cvr'], 4)
                }
            
            if 'avg_order_value' in summary:
                properties["AOV (¥)"] = {
                    "number": round(summary['avg_order_value'])
                }
        
        return properties
    
    def _build_page_content(self, report_content: str, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ページ内容の構築"""
        children = []
        
        # サマリー情報を追加
        summary = report_data.get('summary', {})
        if summary:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📊 主要指標サマリー"
                            }
                        }
                    ]
                }
            })
            
            # 主要指標のテーブル
            summary_text = self._format_summary_metrics(summary)
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary_text
                            }
                        }
                    ]
                }
            })
        
        # 推奨事項を追加
        recommendations = report_data.get('recommendations', [])
        if recommendations:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🎯 推奨事項"
                            }
                        }
                    ]
                }
            })
            
            for i, rec in enumerate(recommendations, 1):
                children.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": rec
                                }
                            }
                        ]
                    }
                })
        
        # 詳細レポートの追加（Markdown内容）
        if report_content:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📋 詳細レポート"
                            }
                        }
                    ]
                }
            })
            
            # Markdownを段落に分割して追加
            paragraphs = self._markdown_to_blocks(report_content)
            children.extend(paragraphs)
        
        return children
    
    def _format_summary_metrics(self, summary: Dict[str, Any]) -> str:
        """サマリー指標の整形"""
        metrics = []
        
        if 'total_sessions' in summary:
            metrics.append(f"📊 総セッション数: {summary['total_sessions']:,}")
        
        if 'total_users' in summary:
            metrics.append(f"👥 総ユーザー数: {summary['total_users']:,}")
        
        if 'total_revenue' in summary:
            metrics.append(f"💰 総売上: ¥{summary['total_revenue']:,.0f}")
        
        if 'purchase_cvr' in summary:
            metrics.append(f"📈 購入CVR: {summary['purchase_cvr']:.2%}")
        
        if 'avg_order_value' in summary:
            metrics.append(f"💳 平均注文単価: ¥{summary['avg_order_value']:,.0f}")
        
        if 'avg_bounce_rate' in summary:
            metrics.append(f"⚡ 平均直帰率: {summary['avg_bounce_rate']:.1%}")
        
        return "\n".join(metrics)
    
    def _markdown_to_blocks(self, markdown_content: str) -> List[Dict[str, Any]]:
        """MarkdownコンテンツをNotionブロックに変換（簡単な実装）"""
        blocks = []
        lines = markdown_content.split('\n')
        
        for line in lines[:50]:  # 最初の50行のみ処理（Notion APIの制限対応）
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith('# '):
                # 見出し1
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[2:]
                                }
                            }
                        ]
                    }
                })
            elif line.startswith('## '):
                # 見出し2
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[3:]
                                }
                            }
                        ]
                    }
                })
            elif line.startswith('### '):
                # 見出し3
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[4:]
                                }
                            }
                        ]
                    }
                })
            elif line.startswith('- '):
                # 箇条書き
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[2:]
                                }
                            }
                        ]
                    }
                })
            else:
                # 通常の段落
                if len(line) > 0:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": line[:2000]  # Notion APIの制限対応
                                    }
                                }
                            ]
                        }
                    })
        
        return blocks
    
    def update_report_status(self, page_id: str, status: str) -> bool:
        """レポートのステータスを更新"""
        try:
            if not self.client:
                logger.error("Notionクライアントが初期化されていません")
                return False
            
            self.client.pages.update(
                page_id=page_id,
                properties={
                    "Status": {
                        "select": {
                            "name": status
                        }
                    }
                }
            )
            
            logger.info(f"ページ {page_id} のステータスを {status} に更新しました")
            return True
            
        except APIResponseError as e:
            logger.error(f"ステータス更新エラー: {e}")
            return False
        except Exception as e:
            logger.error(f"ステータス更新に予期しないエラー: {e}")
            return False
    
    def search_reports_by_date(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """日付範囲でレポートを検索"""
        try:
            if not self.client or not self.database_id:
                logger.error("NotionクライアントまたはデータベースIDが設定されていません")
                return []
            
            query_result = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "and": [
                        {
                            "property": "Report Date",
                            "date": {
                                "on_or_after": start_date.strftime('%Y-%m-%d')
                            }
                        },
                        {
                            "property": "Report Date", 
                            "date": {
                                "on_or_before": end_date.strftime('%Y-%m-%d')
                            }
                        }
                    ]
                }
            )
            
            return query_result.get('results', [])
            
        except APIResponseError as e:
            logger.error(f"レポート検索エラー: {e}")
            return []
        except Exception as e:
            logger.error(f"レポート検索に予期しないエラー: {e}")
            return []
    
    def get_database_info(self) -> Optional[Dict[str, Any]]:
        """データベース情報の取得"""
        try:
            if not self.client or not self.database_id:
                logger.error("NotionクライアントまたはデータベースIDが設定されていません")
                return None
            
            database = self.client.databases.retrieve(database_id=self.database_id)
            return database
            
        except APIResponseError as e:
            logger.error(f"データベース情報取得エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"データベース情報取得に予期しないエラー: {e}")
            return None


def main():
    """テスト実行用のメイン関数"""
    print("=== Notion統合システムテスト ===")
    
    # Notion統合の初期化
    notion = NotionIntegration()
    
    if not notion.client:
        print("Notion認証に失敗しました")
        return
    
    print("Notion認証成功")
    
    # データベース情報の取得
    db_info = notion.get_database_info()
    if db_info:
        print(f"データベース: {db_info['title'][0]['plain_text']}")
    else:
        print("データベースが見つかりません。作成しますか？")
        # データベース作成のテスト
        # db_id = notion.create_analytics_database()
        # if db_id:
        #     print(f"新しいデータベースを作成しました: {db_id}")

if __name__ == "__main__":
    main()
