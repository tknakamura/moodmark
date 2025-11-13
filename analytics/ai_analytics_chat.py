#!/usr/bin/env python3
"""
GA4/GSC AI分析チャット統合モジュール
OpenAI APIを使用してGA4/GSCデータを分析し、自然言語で回答を生成
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Generator
import logging

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from analytics.google_apis_integration import GoogleAPIsIntegration
from analytics.seo_analyzer import SEOAnalyzer

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIAnalyticsChat:
    """GA4/GSCデータを分析するAIチャットクラス"""
    
    def __init__(self, credentials_file=None, openai_api_key=None, default_site_name='moodmark'):
        """
        初期化
        
        Args:
            credentials_file (str): Google認証情報ファイルのパス
            openai_api_key (str): OpenAI APIキー
            default_site_name (str): デフォルトのサイト名 ('moodmark' または 'moodmarkgift')
        """
        # OpenAI APIキーの取得
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI APIキーが設定されていません。環境変数OPENAI_API_KEYを設定してください。")
        
        # OpenAIクライアントの初期化
        if OpenAI is None:
            raise ImportError("openaiパッケージがインストールされていません。pip install openai を実行してください。")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # Google APIs統合の初期化
        self.google_apis = GoogleAPIsIntegration(credentials_file=credentials_file)
        
        # SEO分析の初期化
        self.seo_analyzer = SEOAnalyzer()
        
        # デフォルトサイト名
        self.default_site_name = default_site_name
        
        # システムプロンプト
        self.system_prompt = """あなたはGoogle Analytics 4 (GA4)、Google Search Console (GSC)、およびSEO分析の専門家です。
ユーザーの質問に対して、提供されたデータを基に、わかりやすく、実用的なアドバイスを提供してください。

【質問の意図を理解し、適切に回答する】
- 質問の種類（SEO改善、商品提案、データ分析、年次比較など）を自動的に判断してください
- 質問の意図に応じて、適切な回答形式と含めるべき情報を柔軟に選択してください
- 例：
  * 商品提案の質問 → 商品カテゴリ、具体的な商品名、掲載理由を提案
  * SEO改善の質問 → 現状分析、課題整理、改善提案の3段階構造
  * データ分析の質問 → 数値の説明、トレンド分析、インサイト
  * 年次比較の質問 → 昨年と今年の比較、増減率、原因分析

【データの活用】
- 提供されたデータ（GA4、GSC、SEO分析）を最大限に活用してください
- データがない場合は、その旨を明記してください
- データ取得エラーがある場合は、エラーの内容を説明してください
- データ取得状態が「✗ 取得失敗」と表示されている場合は、そのデータは利用できないことを理解してください

【回答の構造】
- 質問の種類に応じて、適切な構造で回答してください
- 数値は必ず具体的に示してください
- 専門用語を使う場合は簡潔に説明してください
- 日本語で回答してください

【SEO改善に関する回答の構造】
SEO改善に関する質問には、以下の3段階の構造で回答することを推奨します：

1. 【現状分析】
   - 現在のSEO要素の状態を数値と共に明確に示す
   - タイトル、ディスクリプション、見出し構造、画像alt属性、構造化データなどの現状を分析
   - 最適値との比較を示す（例：タイトルは45文字で、最適範囲30-60文字内）
   - H2/H3の見出しテキストが提供されている場合は、具体的な見出しテキストを列挙し、その内容を分析してください
   - 見出しテキストの品質評価（長さ、キーワード含有率、重複など）を具体的に示してください

2. 【課題整理】
   - 現状分析から見つかった問題点を整理
   - 優先度の高い課題から順に列挙
   - 各課題がSEOに与える影響を説明

3. 【改善提案】
   - 各課題に対する具体的な改善方法を提示
   - 実装可能な具体的な改善案を提示（例：タイトルの改善案、ディスクリプションの改善案）
   - 見出しテキストの改善提案では、具体的な見出しテキストの改善案を提示してください
   - 優先順位をつけて改善すべき順序を提示

【コンテンツSEOにおける見出し構造の重要性】
- 見出し構造（H1、H2、H3）はコンテンツSEOにおいて極めて重要です
- 見出しテキストは検索エンジンがコンテンツの構造と内容を理解するための重要な手がかりです
- H2/H3の見出しテキストは、具体的に列挙し、その品質を評価してください
- 見出しテキストの長さ、キーワード含有率、重複などの問題を具体的に指摘し、改善案を提示してください"""
    
    def _extract_date_range(self, question: str) -> tuple:
        """
        質問から日付範囲を抽出
        
        Args:
            question (str): ユーザーの質問
            
        Returns:
            tuple: (start_date, end_date, date_range_days) または (None, None, date_range_days)
                   start_date, end_dateは 'YYYY-MM-DD' 形式、特定の月が指定されている場合は設定される
        """
        import re
        from datetime import datetime, timedelta
        question_lower = question.lower()
        
        # 特定の年月を抽出（例: "2025年10月"）
        year_month_match = re.search(r'(\d{4})年\s*(\d{1,2})月', question)
        if year_month_match:
            year = int(year_month_match.group(1))
            month = int(year_month_match.group(2))
            
            # その月の最初の日と最後の日を計算
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            
            start_date = datetime(year, month, 1)
            end_date = next_month - timedelta(days=1)
            
            date_range_days = (end_date - start_date).days + 1
            
            logger.info(f"特定の月を検出: {year}年{month}月 ({start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')})")
            return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), date_range_days)
        
        # 特定の日付範囲を抽出（例: "11/1-11/7", "11月1日-11月7日"）
        # パターン1: "11/1-11/7" 形式
        date_range_match = re.search(r'(\d{1,2})/(\d{1,2})\s*[-~～]\s*(\d{1,2})/(\d{1,2})', question)
        if date_range_match:
            start_month = int(date_range_match.group(1))
            start_day = int(date_range_match.group(2))
            end_month = int(date_range_match.group(3))
            end_day = int(date_range_match.group(4))
            current_year = datetime.now().year
            
            try:
                start_date = datetime(current_year, start_month, start_day)
                end_date = datetime(current_year, end_month, end_day)
                
                if end_date < start_date:
                    # 年をまたぐ場合（例: 12/25-1/5）
                    end_date = datetime(current_year + 1, end_month, end_day)
                
                date_range_days = (end_date - start_date).days + 1
                
                logger.info(f"特定の日付範囲を検出: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
                return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), date_range_days)
            except ValueError as e:
                logger.warning(f"日付範囲の解析エラー: {e}")
        
        # パターン2: "11月1日-11月7日" 形式
        date_range_match2 = re.search(r'(\d{1,2})月\s*(\d{1,2})日\s*[-~～]\s*(\d{1,2})月\s*(\d{1,2})日', question)
        if date_range_match2:
            start_month = int(date_range_match2.group(1))
            start_day = int(date_range_match2.group(2))
            end_month = int(date_range_match2.group(3))
            end_day = int(date_range_match2.group(4))
            current_year = datetime.now().year
            
            try:
                start_date = datetime(current_year, start_month, start_day)
                end_date = datetime(current_year, end_month, end_day)
                
                if end_date < start_date:
                    end_date = datetime(current_year + 1, end_month, end_day)
                
                date_range_days = (end_date - start_date).days + 1
                
                logger.info(f"特定の日付範囲を検出（日本語形式）: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
                return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), date_range_days)
            except ValueError as e:
                logger.warning(f"日付範囲の解析エラー: {e}")
        
        # 特定の月を抽出（例: "10月" - 今年を仮定）
        month_match = re.search(r'(\d{1,2})月', question_lower)
        if month_match and '年' not in question_lower:
            month = int(month_match.group(1))
            current_year = datetime.now().year
            
            if month == 12:
                next_month = datetime(current_year + 1, 1, 1)
            else:
                next_month = datetime(current_year, month + 1, 1)
            
            start_date = datetime(current_year, month, 1)
            end_date = next_month - timedelta(days=1)
            
            date_range_days = (end_date - start_date).days + 1
            
            logger.info(f"特定の月を検出（今年）: {current_year}年{month}月 ({start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')})")
            return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), date_range_days)
        
        # 相対的な日付範囲
        if '今日' in question_lower or '本日' in question_lower:
            return (None, None, 1)
        elif '昨日' in question_lower:
            yesterday = datetime.now() - timedelta(days=1)
            return (yesterday.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d'), 1)
        elif '今週' in question_lower or 'この週' in question_lower:
            return (None, None, 7)
        elif '先週' in question_lower or '前週' in question_lower:
            return (None, None, 7)
        elif '今月' in question_lower:
            # 今月の最初の日から今日まで
            today = datetime.now()
            start_of_month = datetime(today.year, today.month, 1)
            days = (today - start_of_month).days + 1
            return (start_of_month.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), days)
        elif '先月' in question_lower or '前月' in question_lower:
            # 先月の最初の日から最後の日まで
            today = datetime.now()
            if today.month == 1:
                last_month = datetime(today.year - 1, 12, 1)
            else:
                last_month = datetime(today.year, today.month - 1, 1)
            
            if last_month.month == 12:
                next_month = datetime(last_month.year + 1, 1, 1)
            else:
                next_month = datetime(last_month.year, last_month.month + 1, 1)
            
            end_of_last_month = next_month - timedelta(days=1)
            days = (end_of_last_month - last_month).days + 1
            
            return (last_month.strftime('%Y-%m-%d'), end_of_last_month.strftime('%Y-%m-%d'), days)
        elif '過去' in question_lower:
            # "過去7日"のような表現を探す
            match = re.search(r'過去(\d+)日', question_lower)
            if match:
                return (None, None, int(match.group(1)))
        elif '最近' in question_lower:
            return (None, None, 7)
        
        # デフォルトは30日
        return (None, None, 30)
    
    def _get_ga4_summary(self, date_range_days: int, start_date: str = None, end_date: str = None, page_url: str = None) -> Dict[str, Any]:
        """
        GA4データのサマリーを取得
        
        Args:
            date_range_days (int): 日数
            start_date (str): 開始日 (YYYY-MM-DD形式、オプション)
            end_date (str): 終了日 (YYYY-MM-DD形式、オプション)
            page_url (str): ページURL（オプション、指定された場合は個別ページのデータを取得）
            
        Returns:
            dict: サマリーデータ
        """
        try:
            # 個別ページのデータを取得する場合
            if page_url:
                logger.info(f"個別ページのGA4データ取得開始: URL={page_url}, 期間={date_range_days}日" + (f" ({start_date} ～ {end_date})" if start_date and end_date else ""))
                page_data = self.google_apis.get_page_specific_ga4_data(
                    page_url=page_url,
                    date_range_days=date_range_days,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if 'error' in page_data:
                    error_msg = page_data.get('error', 'Unknown error')
                    is_timeout = page_data.get('timeout', False)
                    logger.warning(f"個別ページのGA4データ取得エラー: {error_msg}")
                    
                    # タイムアウトの場合は、エラーメッセージをより詳細に
                    if is_timeout:
                        return {
                            "error": error_msg,
                            "total_sessions": 0,
                            "total_users": 0,
                            "total_pageviews": 0,
                            "avg_bounce_rate": 0.0,
                            "avg_session_duration": 0.0,
                            "is_page_specific": True,
                            "timeout": True
                        }
                    
                    return {
                        "error": error_msg,
                        "total_sessions": 0,
                        "total_users": 0,
                        "total_pageviews": 0,
                        "avg_bounce_rate": 0.0,
                        "avg_session_duration": 0.0,
                        "is_page_specific": True
                    }
                
                # 個別ページのデータを返す
                summary = {
                    "total_sessions": page_data.get('sessions', 0),
                    "total_users": page_data.get('users', 0),
                    "total_pageviews": page_data.get('pageviews', 0),
                    "avg_bounce_rate": page_data.get('bounce_rate', 0.0),
                    "avg_session_duration": page_data.get('avg_session_duration', 0.0),
                    "date_range_days": date_range_days,
                    "is_page_specific": True,
                    "page_url": page_url,
                    "page_path": page_data.get('page_path', '')
                }
                
                logger.info(f"個別ページのGA4サマリー: セッション={summary['total_sessions']:,}, ユーザー={summary['total_users']:,}, PV={summary['total_pageviews']:,}")
                return summary
            
            # サイト全体のデータを取得する場合
            logger.info(f"GA4データ取得開始: 期間={date_range_days}日" + (f" ({start_date} ～ {end_date})" if start_date and end_date else ""))
            
            # 基本的なメトリクスを取得
            # GA4 APIでは 'users' ではなく 'activeUsers'、'pageviews' ではなく 'screenPageViews' を使用
            if start_date and end_date:
                ga4_data = self.google_apis.get_ga4_data_custom_range(
                    start_date=start_date,
                    end_date=end_date,
                    metrics=['sessions', 'activeUsers', 'screenPageViews', 'bounceRate', 'averageSessionDuration'],
                    dimensions=['date']
                )
            else:
                ga4_data = self.google_apis.get_ga4_data(
                    date_range_days=date_range_days,
                    metrics=['sessions', 'activeUsers', 'screenPageViews', 'bounceRate', 'averageSessionDuration'],
                    dimensions=['date']
                )
            
            logger.info(f"GA4データ取得完了: {len(ga4_data)}行")
            
            if ga4_data.empty:
                logger.warning("GA4データが空です。認証状態とAPI接続を確認してください。")
                logger.warning(f"  GA4プロパティID: {self.google_apis.ga4_property_id}")
                logger.warning(f"  GA4サービス初期化: {self.google_apis.ga4_service is not None}")
                
                # より詳細なエラーメッセージ
                error_msg = "GA4データが取得できませんでした。"
                if not self.google_apis.ga4_property_id:
                    error_msg += " GA4_PROPERTY_ID環境変数が設定されていません。"
                elif not self.google_apis.ga4_service:
                    error_msg += " GA4サービスが初期化されていません。認証情報を確認してください。"
                else:
                    error_msg += " サービスアカウントにGA4へのアクセス権限がない可能性があります。"
                    error_msg += " GA4プロパティでサービスアカウントに閲覧者以上の権限を付与してください。"
                
                return {
                    "error": error_msg,
                    "total_sessions": 0,
                    "total_users": 0,
                    "total_pageviews": 0,
                    "avg_bounce_rate": 0.0,
                    "avg_session_duration": 0.0,
                    "is_page_specific": False
                }
            
            summary = {
                "total_sessions": int(ga4_data['sessions'].sum()) if 'sessions' in ga4_data.columns else 0,
                "total_users": int(ga4_data['activeUsers'].sum()) if 'activeUsers' in ga4_data.columns else 0,  # GA4 APIでは 'activeUsers' を使用
                "total_pageviews": int(ga4_data['screenPageViews'].sum()) if 'screenPageViews' in ga4_data.columns else 0,  # GA4 APIでは 'screenPageViews' を使用
                "avg_bounce_rate": float(ga4_data['bounceRate'].mean()) if 'bounceRate' in ga4_data.columns else 0,
                "avg_session_duration": float(ga4_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in ga4_data.columns else 0,
                "date_range_days": date_range_days,
                "data_points": len(ga4_data),
                "is_page_specific": False
            }
            
            logger.info(f"GA4サマリー: セッション={summary['total_sessions']:,}, ユーザー={summary['total_users']:,}, PV={summary['total_pageviews']:,}")
            
            return summary
            
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return {"error": f"データ取得エラー: {str(e)}"}
    
    def _get_gsc_summary(self, date_range_days: int, start_date: str = None, end_date: str = None, site_name: str = 'moodmark') -> Dict[str, Any]:
        """
        GSCデータのサマリーを取得
        
        Args:
            date_range_days (int): 日数
            start_date (str): 開始日 (YYYY-MM-DD形式、オプション)
            end_date (str): 終了日 (YYYY-MM-DD形式、オプション)
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')
            
        Returns:
            dict: サマリーデータ
        """
        try:
            logger.info(f"GSCデータ取得開始: サイト={site_name}, 期間={date_range_days}日" + (f" ({start_date} ～ {end_date})" if start_date and end_date else ""))
            
            # GSCデータを取得
            if start_date and end_date:
                gsc_data = self.google_apis._get_gsc_data_custom_range(
                    start_date=start_date,
                    end_date=end_date,
                    site_name=site_name
                )
            else:
                gsc_data = self.google_apis.get_gsc_data(
                    date_range_days=date_range_days,
                    dimensions=['date', 'page', 'query'],
                    site_name=site_name
                )
            
            logger.info(f"GSCデータ取得完了: {len(gsc_data)}行")
            
            if gsc_data.empty:
                logger.warning(f"GSCデータが空です（サイト: {site_name}）。認証状態とAPI接続を確認してください。")
                return {
                    "error": f"GSCデータが取得できませんでした（サイト: {site_name}）。認証状態とAPI接続を確認してください。",
                    "total_clicks": 0,
                    "total_impressions": 0,
                    "avg_ctr": 0.0,
                    "avg_position": 0.0
                }
            
            # ページ別データを取得（取得済みのgsc_dataから集計して重複取得を避ける）
            if 'page' in gsc_data.columns:
                gsc_pages = gsc_data.groupby('page').agg({
                    'clicks': 'sum',
                    'impressions': 'sum',
                    'ctr': 'mean',
                    'position': 'mean'
                }).reset_index()
                # CTRを計算し直し
                gsc_pages['ctr_calculated'] = (gsc_pages['clicks'] / gsc_pages['impressions'] * 100).round(2)
                gsc_pages['avg_position'] = gsc_pages['position'].round(2)
                gsc_pages = gsc_pages.sort_values('clicks', ascending=False).head(50)
            else:
                # pageカラムがない場合は空のDataFrameを返す
                import pandas as pd
                gsc_pages = pd.DataFrame()
            
            # クエリ別データを取得（取得済みのgsc_dataから集計して重複取得を避ける）
            if 'query' in gsc_data.columns:
                gsc_queries = gsc_data.groupby('query').agg({
                    'clicks': 'sum',
                    'impressions': 'sum',
                    'ctr': 'mean',
                    'position': 'mean'
                }).reset_index()
                # CTRを計算し直し
                gsc_queries['ctr_calculated'] = (gsc_queries['clicks'] / gsc_queries['impressions'] * 100).round(2)
                gsc_queries['avg_position'] = gsc_queries['position'].round(2)
                gsc_queries = gsc_queries.sort_values('clicks', ascending=False).head(50)
            else:
                # queryカラムがない場合は空のDataFrameを返す
                import pandas as pd
                gsc_queries = pd.DataFrame()
            
            # サマリー計算（gsc_dataから直接計算して正確性を向上）
            total_clicks = int(gsc_data['clicks'].sum()) if not gsc_data.empty else 0
            total_impressions = int(gsc_data['impressions'].sum()) if not gsc_data.empty else 0
            avg_ctr = float((total_clicks / total_impressions * 100)) if total_impressions > 0 else 0.0
            avg_position = float(gsc_data['position'].mean()) if not gsc_data.empty else 0.0
            
            summary = {
                "total_clicks": total_clicks,
                "total_impressions": total_impressions,
                "avg_ctr": round(avg_ctr, 2),
                "avg_position": round(avg_position, 2),
                "top_pages_count": len(gsc_pages),
                "top_queries_count": len(gsc_queries),
                "date_range_days": date_range_days
            }
            
            logger.info(f"GSCサマリー: クリック={summary['total_clicks']:,}, インプレッション={summary['total_impressions']:,}, CTR={summary['avg_ctr']:.2f}%")
            
            # トップページとトップクエリの情報
            if not gsc_pages.empty:
                summary["top_pages"] = gsc_pages.head(10).to_dict('records')
            if not gsc_queries.empty:
                summary["top_queries"] = gsc_queries.head(10).to_dict('records')
            
            return summary
            
        except Exception as e:
            logger.error(f"GSCデータ取得エラー: {e}")
            return {"error": f"データ取得エラー: {str(e)}"}
    
    def _extract_urls(self, text: str) -> List[str]:
        """
        テキストからURLを抽出し、正規化する
        
        Args:
            text (str): テキスト
            
        Returns:
            list: 正規化されたURLのリスト
        """
        import re
        from urllib.parse import urlparse, urlunparse
        
        # URLパターン（より包括的）
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        # URLの正規化
        normalized_urls = []
        for url in urls:
            try:
                parsed = urlparse(url)
                # 末尾のスラッシュを統一（パスがある場合は保持、ルートの場合は追加）
                path = parsed.path.rstrip('/') or '/'
                if parsed.path and not parsed.path.endswith('/'):
                    path = parsed.path
                
                # 正規化されたURLを構築
                normalized = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    path,
                    parsed.params,
                    parsed.query,
                    ''  # fragmentは削除
                ))
                normalized_urls.append(normalized)
                logger.info(f"URL抽出・正規化: {url} -> {normalized}")
            except Exception as e:
                logger.warning(f"URL正規化エラー ({url}): {e}")
                normalized_urls.append(url)  # 正規化に失敗した場合は元のURLを使用
        
        if normalized_urls:
            logger.info(f"抽出されたURL数: {len(normalized_urls)}")
            for i, url in enumerate(normalized_urls, 1):
                logger.info(f"  {i}. {url}")
        else:
            logger.info("URLは抽出されませんでした")
        
        return normalized_urls
    
    def _detect_site_from_url(self, url: str) -> str:
        """
        URLからサイト名を自動判定
        
        Args:
            url (str): ページURL
            
        Returns:
            str: サイト名 ('moodmark' または 'moodmarkgift')
        """
        if '/moodmarkgift/' in url:
            return 'moodmarkgift'
        elif '/moodmark/' in url:
            return 'moodmark'
        else:
            return self.default_site_name
    
    def _build_data_context(self, question: str, site_name: str = None, progress_callback=None, timeout: int = 300) -> str:
        """
        質問に基づいてデータコンテキストを構築
        
        Args:
            question (str): ユーザーの質問
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')、Noneの場合は自動判定またはデフォルトを使用
            progress_callback: 進捗コールバック関数（オプション）
            timeout (int): タイムアウト時間（秒）、デフォルトは300秒（5分）
            
        Returns:
            str: データコンテキストの文字列
        """
        import time
        start_time = time.time()
        
        def check_timeout():
            """タイムアウトチェック"""
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"データコンテキスト構築がタイムアウトしました（{timeout}秒）")
            return elapsed
        
        logger.info("=" * 60)
        logger.info("データコンテキスト構築開始")
        logger.info(f"質問: {question[:100]}...")
        
        date_range_result = self._extract_date_range(question)
        if isinstance(date_range_result, tuple) and len(date_range_result) == 3:
            start_date, end_date, date_range_days = date_range_result
            date_range = date_range_days
            logger.info(f"抽出された日付範囲: {date_range}日")
            if start_date and end_date:
                logger.info(f"  開始日: {start_date}, 終了日: {end_date}")
        else:
            # 後方互換性のため
            date_range = date_range_result if isinstance(date_range_result, int) else 30
            start_date, end_date = None, None
            logger.info(f"抽出された日付範囲: {date_range}日")
        
        context_parts = []
        
        # データ取得状態を追跡
        data_status = {
            'seo_analysis': False,
            'ga4_data': False,
            'gsc_data': False,
            'gsc_page_specific': False
        }
        
        # URLを抽出
        urls = self._extract_urls(question)
        logger.info(f"抽出されたURL: {urls}")
        
        # サイト名の決定（URLから自動判定、または指定された値、またはデフォルト）
        if site_name is None:
            if urls:
                # URLから自動判定
                site_name = self._detect_site_from_url(urls[0])
                logger.info(f"URLからサイトを自動判定: {site_name}")
            else:
                # デフォルトを使用
                site_name = self.default_site_name
                logger.info(f"デフォルトサイトを使用: {site_name}")
        else:
            logger.info(f"指定されたサイトを使用: {site_name}")
        
        # SEO分析が必要かどうかを判定
        question_lower = question.lower()
        needs_seo_analysis = any(keyword in question_lower for keyword in [
            'seo', 'タイトル', 'ディスクリプション', '見出し', 'メタ', 'alt', 
            '構造化データ', 'スクレイピング', 'html', 'css', 'ページ分析', 
            'コンテンツ分析', '改善提案', '最適化'
        ]) or len(urls) > 0
        
        # 年次比較が必要かどうかを判定
        needs_yearly_comparison = any(keyword in question_lower for keyword in [
            '昨年', '今年', '前年', '前年比', 'yoy', 'year over year', '比較',
            '比べて', '対比', '変化', '増減', '推移', 'トレンド'
        ])
        
        # 特定ページの分析が必要かどうかを判定
        needs_page_specific_analysis = len(urls) > 0
        
        # GA4データが必要かどうかを判定
        needs_ga4 = any(keyword in question_lower for keyword in [
            'トラフィック', 'セッション', 'ユーザー', 'ページビュー', 'バウンス', 
            '滞在時間', 'コンバージョン', '売上', '収益', 'アクセス', '集客',
            'オーガニック', '流入', '訪問', '来訪', '月間', '数値', 'レポート',
            'report', 'データ', '統計', '分析', 'パフォーマンス', '実績',
            'ページ分析', 'ページの分析', '分析して', '分析してください'
        ]) or needs_yearly_comparison or needs_page_specific_analysis
        
        # GSCデータが必要かどうかを判定
        needs_gsc = any(keyword in question_lower for keyword in [
            '検索', 'seo', 'クリック', 'インプレッション', 'ctr', 'ポジション', 
            '順位', 'キーワード', 'クエリ', '検索流入', 'オーガニック', '集客',
            '月間', '数値', 'レポート', 'report', 'データ', '統計', '分析'
        ]) or needs_yearly_comparison or needs_page_specific_analysis
        
        # SEO分析を実行（URLが含まれている場合、またはSEO関連の質問の場合）
        if needs_seo_analysis:
            if not urls:
                logger.warning("SEO分析が必要と判定されましたが、URLが抽出されませんでした")
                logger.info("  質問内容: " + question[:200])
                context_parts.append("⚠️ SEO分析を実行するには、URLを指定してください。")
                context_parts.append("例: 「このページのSEO改善点は？ https://example.com/page」")
                context_parts.append("")
        
        if needs_seo_analysis and urls:
            logger.info(f"SEO分析が必要と判定されました。URL数: {len(urls)}")
            if progress_callback:
                progress_callback("[STEP] 🔍 SEO分析を実行中...\n")
            for idx, url in enumerate(urls[:3], 1):  # 最大3つのURLまで
                logger.info(f"[{idx}/{min(len(urls), 3)}] SEO分析を開始: {url}")
                try:
                    # ページ取得開始
                    logger.info(f"  ステップ1: ページ取得を開始...")
                    # JavaScript実行環境の使用を環境変数で制御
                    use_js = os.getenv('USE_SELENIUM', 'false').lower() == 'true' or os.getenv('USE_PLAYWRIGHT', 'false').lower() == 'true'
                    seo_analysis = self.seo_analyzer.analyze_page(url, use_js=use_js)
                    
                    # 分析結果の検証
                    if 'error' in seo_analysis:
                        error_msg = seo_analysis.get('error', 'Unknown error')
                        logger.error(f"  SEO分析エラー: {error_msg}")
                        
                        # エラー情報を詳細に記録
                        context_parts.append(f"⚠️ SEO分析エラー ({url})")
                        context_parts.append(f"エラー内容: {error_msg}")
                        
                        # エラーの種類に応じた詳細情報
                        if 'タイムアウト' in error_msg or 'timeout' in error_msg.lower():
                            context_parts.append("")
                            context_parts.append("【エラー詳細】")
                            context_parts.append("ページの取得がタイムアウトしました。")
                            context_parts.append("考えられる原因:")
                            context_parts.append("- サーバーの応答が遅い")
                            context_parts.append("- ネットワーク接続の問題")
                            context_parts.append("- ページが重い（大量のリソースを読み込んでいる）")
                            context_parts.append("")
                            context_parts.append("【対処方法】")
                            context_parts.append("- サーバーのパフォーマンスを確認")
                            context_parts.append("- ページの読み込み速度を最適化")
                            context_parts.append("- ネットワーク接続を確認")
                        elif '接続' in error_msg or 'Connection' in error_msg:
                            context_parts.append("")
                            context_parts.append("【エラー詳細】")
                            context_parts.append("ページへの接続に失敗しました。")
                            context_parts.append("考えられる原因:")
                            context_parts.append("- URLが正しくない")
                            context_parts.append("- ページが存在しない")
                            context_parts.append("- サーバーがダウンしている")
                            context_parts.append("- ファイアウォールやセキュリティ設定でブロックされている")
                            context_parts.append("")
                            context_parts.append("【対処方法】")
                            context_parts.append("- URLが正しいか確認")
                            context_parts.append("- ブラウザで直接アクセスして確認")
                            context_parts.append("- サーバーの状態を確認")
                        
                        context_parts.append("")
                        context_parts.append("注意: ページ取得に失敗したため、実際のHTMLコンテンツの分析はできませんでした。")
                        context_parts.append("GSCデータ（クリック数、インプレッション数など）のみに基づいて分析を行います。")
                        context_parts.append("")
                        continue
                    
                    # 分析結果のサマリーをログに記録
                    basic = seo_analysis.get('basic', {})
                    content = seo_analysis.get('content', {})
                    logger.info(f"  ステップ2: 分析完了")
                    logger.info(f"    タイトル: {basic.get('title', 'N/A')[:50]}...")
                    logger.info(f"    タイトル長: {basic.get('title_length', 0)}文字")
                    logger.info(f"    H1数: {content.get('h1_count', 0)}")
                    logger.info(f"    文字数: {content.get('char_count', 0):,}")
                    
                    if 'error' not in seo_analysis:
                        data_status['seo_analysis'] = True
                        context_parts.append(f"=== SEO分析結果: {url} ===")
                        context_parts.append("")
                        
                        # 【現状分析】セクション
                        context_parts.append("【現状分析】")
                        
                        # 基本SEO
                        basic = seo_analysis.get('basic', {})
                        context_parts.append("■ 基本SEO要素")
                        context_parts.append(f"  タイトル: {basic.get('title', 'N/A')}")
                        context_parts.append(f"  タイトル長: {basic.get('title_length', 0)}文字 (最適範囲: 30-60文字) {'✓ 最適' if basic.get('title_optimal') else '✗ 要改善'}")
                        context_parts.append(f"  ディスクリプション: {basic.get('description', 'N/A')[:150]}...")
                        context_parts.append(f"  ディスクリプション長: {basic.get('description_length', 0)}文字 (最適範囲: 120-160文字) {'✓ 最適' if basic.get('description_optimal') else '✗ 要改善'}")
                        context_parts.append(f"  Canonical URL: {basic.get('canonical_url', 'N/A')}")
                        context_parts.append("")
                        
                        # コンテンツ構造
                        content = seo_analysis.get('content', {})
                        headings = content.get('headings', {})
                        context_parts.append("■ コンテンツ構造")
                        context_parts.append(f"  H1数: {content.get('h1_count', 0)} (理想的には1つ) {'✓ 最適' if content.get('h1_optimal') else '✗ 要改善'}")
                        
                        # H1の見出しテキスト
                        if headings.get('h1'):
                            context_parts.append(f"  H1見出し:")
                            for h1 in headings['h1'][:3]:  # 最大3つまで
                                context_parts.append(f"    - {h1}")
                        
                        context_parts.append(f"  H2数: {content.get('h2_count', 0)}")
                        # H2の見出しテキスト（コンテンツSEOで重要）
                        if headings.get('h2'):
                            context_parts.append(f"  H2見出し（全{len(headings['h2'])}個）:")
                            for idx, h2 in enumerate(headings['h2'], 1):
                                context_parts.append(f"    {idx}. {h2}")
                        
                        context_parts.append(f"  H3数: {content.get('h3_count', 0)}")
                        # H3の見出しテキスト（コンテンツSEOで重要）
                        if headings.get('h3'):
                            context_parts.append(f"  H3見出し（全{len(headings['h3'])}個）:")
                            for idx, h3 in enumerate(headings['h3'], 1):
                                context_parts.append(f"    {idx}. {h3}")
                        
                        context_parts.append(f"  文字数: {content.get('char_count', 0):,}文字")
                        context_parts.append(f"  語数: {content.get('word_count', 0):,}語 (推奨: 300語以上) {'✓' if content.get('content_length_optimal') else '✗'}")
                        
                        # 見出し構造の評価
                        h1_count = content.get('h1_count', 0)
                        h2_count = content.get('h2_count', 0)
                        h3_count = content.get('h3_count', 0)
                        
                        context_parts.append("")
                        context_parts.append("■ 見出し構造の評価")
                        if h1_count == 1 and h2_count > 0:
                            context_parts.append("  見出し階層: ✓ 適切（H1 → H2 → H3の階層構造）")
                        elif h1_count == 0:
                            context_parts.append("  見出し階層: ✗ H1が見つかりません（要改善）")
                        elif h1_count > 1:
                            context_parts.append("  見出し階層: ✗ H1が複数あります（要改善）")
                        elif h2_count == 0:
                            context_parts.append("  見出し階層: ⚠ H2が見つかりません（H1の下にH2を追加推奨）")
                        else:
                            context_parts.append("  見出し階層: ✓ 基本的な構造は適切")
                        
                        # 見出しテキストの品質評価
                        heading_quality = content.get('heading_quality', {})
                        if heading_quality:
                            context_parts.append("")
                            context_parts.append("■ 見出しテキストの品質評価")
                            
                            # SEOスコア
                            seo_score = heading_quality.get('seo_score', 0)
                            context_parts.append(f"  SEO最適化スコア: {seo_score}/100")
                            
                            # H2の品質評価
                            h2_quality = heading_quality.get('h2', {})
                            if h2_quality.get('total', 0) > 0:
                                context_parts.append("")
                                context_parts.append("  【H2見出しの品質】")
                                context_parts.append(f"    総数: {h2_quality['total']}個")
                                context_parts.append(f"    最適な長さ（30-60文字）: {h2_quality.get('optimal_length', 0)}個")
                                
                                if h2_quality.get('too_short'):
                                    context_parts.append(f"    短すぎる見出し（30文字未満）: {len(h2_quality['too_short'])}個")
                                    for item in h2_quality['too_short'][:5]:  # 最大5個まで
                                        context_parts.append(f"      - 「{item['text']}」 ({item['length']}文字)")
                                
                                if h2_quality.get('too_long'):
                                    context_parts.append(f"    長すぎる見出し（60文字超）: {len(h2_quality['too_long'])}個")
                                    for item in h2_quality['too_long'][:5]:  # 最大5個まで
                                        context_parts.append(f"      - 「{item['text']}」 ({item['length']}文字)")
                                
                                if h2_quality.get('duplicates'):
                                    context_parts.append(f"    重複見出し: {len(h2_quality['duplicates'])}個")
                                    for dup in h2_quality['duplicates'][:3]:  # 最大3個まで
                                        context_parts.append(f"      - 「{dup}」")
                                
                                if h2_quality.get('length_stats'):
                                    stats = h2_quality['length_stats']
                                    context_parts.append(f"    長さ統計: 最小{stats['min']}文字、最大{stats['max']}文字、平均{stats['avg']:.1f}文字")
                            
                            # H3の品質評価
                            h3_quality = heading_quality.get('h3', {})
                            if h3_quality.get('total', 0) > 0:
                                context_parts.append("")
                                context_parts.append("  【H3見出しの品質】")
                                context_parts.append(f"    総数: {h3_quality['total']}個")
                                context_parts.append(f"    最適な長さ（20-50文字）: {h3_quality.get('optimal_length', 0)}個")
                                
                                if h3_quality.get('too_short'):
                                    context_parts.append(f"    短すぎる見出し（20文字未満）: {len(h3_quality['too_short'])}個")
                                    for item in h3_quality['too_short'][:5]:  # 最大5個まで
                                        context_parts.append(f"      - 「{item['text']}」 ({item['length']}文字)")
                                
                                if h3_quality.get('too_long'):
                                    context_parts.append(f"    長すぎる見出し（50文字超）: {len(h3_quality['too_long'])}個")
                                    for item in h3_quality['too_long'][:5]:  # 最大5個まで
                                        context_parts.append(f"      - 「{item['text']}」 ({item['length']}文字)")
                                
                                if h3_quality.get('duplicates'):
                                    context_parts.append(f"    重複見出し: {len(h3_quality['duplicates'])}個")
                                    for dup in h3_quality['duplicates'][:3]:  # 最大3個まで
                                        context_parts.append(f"      - 「{dup}」")
                                
                                if h3_quality.get('length_stats'):
                                    stats = h3_quality['length_stats']
                                    context_parts.append(f"    長さ統計: 最小{stats['min']}文字、最大{stats['max']}文字、平均{stats['avg']:.1f}文字")
                            
                            # キーワード分析
                            keyword_analysis = heading_quality.get('keyword_analysis', {})
                            if keyword_analysis.get('main_keywords'):
                                context_parts.append("")
                                context_parts.append("  【キーワード分析】")
                                context_parts.append(f"    主要キーワード: {', '.join(keyword_analysis['main_keywords'])}")
                                context_parts.append(f"    H2でのキーワード含有率: {keyword_analysis.get('h2_keyword_coverage', 0):.1%}")
                                context_parts.append(f"    H3でのキーワード含有率: {keyword_analysis.get('h3_keyword_coverage', 0):.1%}")
                        
                        context_parts.append("")
                        context_parts.append("上記の見出しテキストの品質評価を基に、具体的な改善提案を提示してください。")
                        context_parts.append("特に、長すぎる/短すぎる見出し、重複見出し、キーワード含有率の改善について具体的な改善案を提示してください。")
                        context_parts.append("")
                        
                        # アクセシビリティ
                        accessibility = seo_analysis.get('accessibility', {})
                        context_parts.append("■ アクセシビリティ")
                        context_parts.append(f"  画像alt属性カバレッジ: {accessibility.get('alt_coverage', 0):.1%}")
                        context_parts.append(f"  alt属性なし画像: {accessibility.get('images_without_alt', 0)}件 / 総画像数: {accessibility.get('total_images', 0)}件")
                        context_parts.append(f"  リンクテキストなし: {accessibility.get('links_without_text', 0)}件 / 総リンク数: {accessibility.get('total_links', 0)}件")
                        context_parts.append("")
                        
                        # 構造化データ
                        structured = seo_analysis.get('structured_data', {})
                        context_parts.append("■ 構造化データ")
                        context_parts.append(f"  JSON-LD: {structured.get('json_ld_count', 0)}件")
                        context_parts.append(f"  マイクロデータ: {structured.get('microdata_count', 0)}件")
                        context_parts.append(f"  RDFa: {structured.get('rdfa_count', 0)}件")
                        context_parts.append(f"  構造化データの有無: {'✓ あり' if structured.get('has_structured_data') else '✗ なし（追加推奨）'}")
                        
                        # スキーマタイプの詳細
                        schema_types = structured.get('schema_types', [])
                        if schema_types:
                            context_parts.append(f"  検出されたスキーマタイプ: {', '.join(schema_types)}")
                            context_parts.append(f"  総スキーマ数: {structured.get('total_schemas', 0)}")
                        
                        # スキーマ詳細
                        schema_details = structured.get('schema_details', [])
                        if schema_details:
                            context_parts.append("")
                            context_parts.append("  【スキーマ詳細】")
                            for i, detail in enumerate(schema_details[:5], 1):  # 最大5個まで
                                schema_type = detail.get('schema_type', 'Unknown')
                                properties = detail.get('properties', {})
                                context_parts.append(f"    {i}. {schema_type}")
                                if properties:
                                    prop_list = ', '.join(properties.keys())
                                    context_parts.append(f"       プロパティ: {prop_list}")
                        
                        # 品質評価
                        quality = structured.get('quality_score', {})
                        if quality:
                            context_parts.append("")
                            context_parts.append(f"  品質スコア: {quality.get('score', 0)}/{quality.get('max_score', 100)}")
                            if quality.get('issues'):
                                context_parts.append("  【課題】")
                                for issue in quality['issues']:
                                    context_parts.append(f"    - {issue}")
                            if quality.get('recommendations'):
                                context_parts.append("  【推奨事項】")
                                for rec in quality['recommendations']:
                                    context_parts.append(f"    - {rec}")
                        
                        # JavaScriptで動的に生成される可能性の警告
                        if structured.get('potential_js_structured_data'):
                            context_parts.append("")
                            context_parts.append("  ⚠️ 注意: JavaScriptで構造化データが動的に生成されている可能性があります")
                            context_parts.append("    現在の解析方法では、JavaScriptで動的に生成される構造化データは検出できません")
                            context_parts.append("    より正確な分析には、JavaScript実行環境（Selenium/Playwright）が必要です")
                        
                        context_parts.append("")
                        
                        # リンク構造
                        links = seo_analysis.get('links', {})
                        context_parts.append("■ リンク構造")
                        context_parts.append(f"  内部リンク: {links.get('internal_links', 0)}件")
                        context_parts.append(f"  外部リンク: {links.get('external_links', 0)}件")
                        context_parts.append(f"  nofollowリンク: {links.get('nofollow_links', 0)}件")
                        context_parts.append("")
                        
                        # Page Speed Insightsデータを取得
                        # 注意: 処理時間が長いため（モバイル+デスクトップで約90秒）、無効化しています
                        # 必要に応じて、以下のコメントを外して有効化できます
                        # logger.info(f"  ステップ3: Page Speed Insightsデータ取得を開始...")
                        # try:
                        #     psi_data_mobile = self.google_apis.get_pagespeed_insights(url, strategy='mobile')
                        #     psi_data_desktop = self.google_apis.get_pagespeed_insights(url, strategy='desktop')
                        #     
                        #     if 'error' not in psi_data_mobile or 'error' not in psi_data_desktop:
                        #         context_parts.append("")
                        #         context_parts.append("=== Page Speed Insights分析結果 ===")
                        #         context_parts.append("")
                        #         
                        #         # モバイル結果
                        #         if 'error' not in psi_data_mobile:
                        #             context_parts.append("【モバイルパフォーマンス】")
                        #             lhr_mobile = psi_data_mobile.get('lighthouseResult', {})
                        #             categories_mobile = lhr_mobile.get('categories', {})
                        #             
                        #             if 'performance' in categories_mobile:
                        #                 perf_score = categories_mobile['performance'].get('score', 0)
                        #                 context_parts.append(f"  パフォーマンススコア: {perf_score:.0f}/100")
                        #             
                        #             if 'accessibility' in categories_mobile:
                        #                 acc_score = categories_mobile['accessibility'].get('score', 0)
                        #                 context_parts.append(f"  アクセシビリティスコア: {acc_score:.0f}/100")
                        #             
                        #             if 'best-practices' in categories_mobile:
                        #                 bp_score = categories_mobile['best-practices'].get('score', 0)
                        #                 context_parts.append(f"  ベストプラクティススコア: {bp_score:.0f}/100")
                        #             
                        #             if 'seo' in categories_mobile:
                        #                 seo_score = categories_mobile['seo'].get('score', 0)
                        #                 context_parts.append(f"  SEOスコア: {seo_score:.0f}/100")
                        #             
                        #             # Core Web Vitals
                        #             cwv_mobile = psi_data_mobile.get('coreWebVitals', {})
                        #             if cwv_mobile:
                        #                 context_parts.append("")
                        #                 context_parts.append("  【Core Web Vitals】")
                        #                 if 'LCP' in cwv_mobile:
                        #                     lcp = cwv_mobile['LCP']
                        #                     context_parts.append(f"    LCP (Largest Contentful Paint): {lcp.get('percentile', 0):.0f}ms ({lcp.get('category', 'UNKNOWN')})")
                        #                 if 'FID' in cwv_mobile:
                        #                     fid = cwv_mobile['FID']
                        #                     context_parts.append(f"    FID (First Input Delay): {fid.get('percentile', 0):.0f}ms ({fid.get('category', 'UNKNOWN')})")
                        #                 if 'CLS' in cwv_mobile:
                        #                     cls = cwv_mobile['CLS']
                        #                     context_parts.append(f"    CLS (Cumulative Layout Shift): {cls.get('percentile', 0):.3f} ({cls.get('category', 'UNKNOWN')})")
                        #             
                        #             # 主要な監査項目
                        #             audits_mobile = lhr_mobile.get('audits', {})
                        #             if audits_mobile:
                        #                 context_parts.append("")
                        #                 context_parts.append("  【主要なパフォーマンス指標】")
                        #                 if 'first-contentful-paint' in audits_mobile:
                        #                     fcp = audits_mobile['first-contentful-paint']
                        #                     context_parts.append(f"    FCP (First Contentful Paint): {fcp.get('displayValue', 'N/A')}")
                        #                 if 'largest-contentful-paint' in audits_mobile:
                        #                     lcp_audit = audits_mobile['largest-contentful-paint']
                        #                     context_parts.append(f"    LCP (Largest Contentful Paint): {lcp_audit.get('displayValue', 'N/A')}")
                        #                 if 'total-blocking-time' in audits_mobile:
                        #                     tbt = audits_mobile['total-blocking-time']
                        #                     context_parts.append(f"    TBT (Total Blocking Time): {tbt.get('displayValue', 'N/A')}")
                        #                 if 'cumulative-layout-shift' in audits_mobile:
                        #                     cls_audit = audits_mobile['cumulative-layout-shift']
                        #                     context_parts.append(f"    CLS (Cumulative Layout Shift): {cls_audit.get('displayValue', 'N/A')}")
                        #                 if 'speed-index' in audits_mobile:
                        #                     si = audits_mobile['speed-index']
                        #                     context_parts.append(f"    Speed Index: {si.get('displayValue', 'N/A')}")
                        #         
                        #         # デスクトップ結果
                        #         if 'error' not in psi_data_desktop:
                        #             context_parts.append("")
                        #             context_parts.append("【デスクトップパフォーマンス】")
                        #             lhr_desktop = psi_data_desktop.get('lighthouseResult', {})
                        #             categories_desktop = lhr_desktop.get('categories', {})
                        #             
                        #             if 'performance' in categories_desktop:
                        #                 perf_score = categories_desktop['performance'].get('score', 0)
                        #                 context_parts.append(f"  パフォーマンススコア: {perf_score:.0f}/100")
                        #             
                        #             if 'accessibility' in categories_desktop:
                        #                 acc_score = categories_desktop['accessibility'].get('score', 0)
                        #                 context_parts.append(f"  アクセシビリティスコア: {acc_score:.0f}/100")
                        #             
                        #             if 'best-practices' in categories_desktop:
                        #                 bp_score = categories_desktop['best-practices'].get('score', 0)
                        #                 context_parts.append(f"  ベストプラクティススコア: {bp_score:.0f}/100")
                        #             
                        #             if 'seo' in categories_desktop:
                        #                 seo_score = categories_desktop['seo'].get('score', 0)
                        #                 context_parts.append(f"  SEOスコア: {seo_score:.0f}/100")
                        #         
                        #         context_parts.append("")
                        #         logger.info(f"  ステップ3: Page Speed Insightsデータ取得完了")
                        #     else:
                        #         # エラーが発生した場合でも、エラーメッセージをコンテキストに含める
                        #         error_msg_mobile = psi_data_mobile.get('error', 'Unknown error')
                        #         error_msg_desktop = psi_data_desktop.get('error', 'Unknown error')
                        #         logger.warning(f"  Page Speed Insightsデータ取得エラー: モバイル={error_msg_mobile}, デスクトップ={error_msg_desktop}")
                        #         context_parts.append("")
                        #         context_parts.append("=== Page Speed Insights分析結果 ===")
                        #         context_parts.append("⚠️ Page Speed Insightsデータの取得に失敗しました")
                        #         context_parts.append(f"  モバイル: {error_msg_mobile}")
                        #         context_parts.append(f"  デスクトップ: {error_msg_desktop}")
                        #         context_parts.append("  他のデータ（GA4、GSC、SEO分析）で分析を続行します。")
                        #         context_parts.append("")
                        # except Exception as e:
                        #     # 例外が発生した場合でも、エラーメッセージをコンテキストに含める
                        #     logger.warning(f"  Page Speed Insightsデータ取得エラー: {e}")
                        #     context_parts.append("")
                        #     context_parts.append("=== Page Speed Insights分析結果 ===")
                        #     context_parts.append("⚠️ Page Speed Insightsデータの取得中にエラーが発生しました")
                        #     context_parts.append(f"  エラー内容: {str(e)}")
                        #     context_parts.append("  他のデータ（GA4、GSC、SEO分析）で分析を続行します。")
                        #     context_parts.append("")
                        
                        # Page Speed Insightsは無効化されています（処理時間短縮のため）
                        logger.info(f"  ステップ3: Page Speed Insightsデータ取得をスキップ（処理時間短縮のため無効化）")
                        
                        # 技術的SEO
                        technical = seo_analysis.get('technical', {})
                        context_parts.append("■ 技術的SEO")
                        context_parts.append(f"  Open Graph: {'✓ あり' if technical.get('open_graph') else '✗ なし'}")
                        context_parts.append(f"  Twitter Card: {'✓ あり' if technical.get('twitter_card') else '✗ なし'}")
                        context_parts.append(f"  モバイル対応: {'✓ あり' if technical.get('is_mobile_friendly') else '✗ なし'}")
                        context_parts.append("")
                        
                        # パフォーマンス
                        performance = seo_analysis.get('performance', {})
                        context_parts.append("■ パフォーマンス")
                        context_parts.append(f"  外部スクリプト: {performance.get('external_scripts_count', 0)}件")
                        context_parts.append(f"  外部スタイルシート: {performance.get('external_stylesheets_count', 0)}件")
                        context_parts.append(f"  遅延読み込み画像: {performance.get('lazy_loading_images', 0)}件 / 総画像数: {performance.get('total_images', 0)}件")
                        context_parts.append("")
                        
                        context_parts.append("上記の現状分析結果を基に、【課題整理】と【改善提案】を提示してください。")
                        context_parts.append("")
                        
                        # データコンテキストの検証
                        logger.info(f"  ステップ3: データコンテキスト構築完了")
                        logger.info(f"    コンテキスト行数: {len(context_parts)}")
                        
                except Exception as e:
                    logger.error(f"SEO分析で例外が発生しました ({url}): {e}", exc_info=True)
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"エラー詳細:\n{error_details}")
                    context_parts.append(f"❌ SEO分析エラー ({url})")
                    context_parts.append(f"エラー内容: {str(e)}")
                    context_parts.append("ページの取得または解析中にエラーが発生しました。URLが正しいか、ページがアクセス可能か確認してください。")
                    context_parts.append("")
        
        # 年次比較データの取得
        if needs_yearly_comparison:
            logger.info("年次比較データを取得中...")
            page_url_for_comparison = urls[0] if urls else None
            yearly_comparison = self.google_apis.get_yearly_comparison_gsc(
                page_url=page_url_for_comparison,
                date_range_days=date_range,
                site_name=site_name
            )
            
            if 'error' in yearly_comparison:
                error_msg = yearly_comparison.get('error', 'Unknown error')
                logger.error(f"年次比較データ取得エラー: {error_msg}")
                context_parts.append("=== 年次比較データ（GSC） ===")
                context_parts.append("")
                context_parts.append(f"❌ エラー: {error_msg}")
                context_parts.append("")
                context_parts.append("【対処方法】")
                context_parts.append("1. Render.comの環境変数を確認してください:")
                context_parts.append("   - GOOGLE_CREDENTIALS_FILE: Google認証ファイルのパス（例: config/google-credentials-474807.json）")
                context_parts.append("   - GSC_SITE_URL: GSCサイトURL（例: https://isetan.mistore.jp/moodmark/）")
                context_parts.append("2. 認証ファイルが正しくアップロードされているか確認してください")
                context_parts.append("3. サービスアカウントにGSCへのアクセス権限があるか確認してください")
                context_parts.append("")
                context_parts.append("⚠️ データが取得できないため、年次比較分析は実行できません。")
                context_parts.append("上記のエラーメッセージを確認し、設定を修正してください。")
                context_parts.append("")
            else:
                context_parts.append("=== 年次比較データ（GSC） ===")
                context_parts.append("")
                context_parts.append("【今年のデータ】")
                this_year = yearly_comparison.get('this_year', {})
                context_parts.append(f"期間: {this_year.get('period', 'N/A')}")
                context_parts.append(f"クリック数: {this_year.get('clicks', 0):,}")
                context_parts.append(f"インプレッション数: {this_year.get('impressions', 0):,}")
                context_parts.append(f"CTR: {this_year.get('ctr', 0):.2f}%")
                context_parts.append(f"平均検索順位: {this_year.get('avg_position', 0):.2f}位")
                context_parts.append("")
                
                context_parts.append("【昨年のデータ（同じ期間）】")
                last_year = yearly_comparison.get('last_year', {})
                context_parts.append(f"期間: {last_year.get('period', 'N/A')}")
                context_parts.append(f"クリック数: {last_year.get('clicks', 0):,}")
                context_parts.append(f"インプレッション数: {last_year.get('impressions', 0):,}")
                context_parts.append(f"CTR: {last_year.get('ctr', 0):.2f}%")
                context_parts.append(f"平均検索順位: {last_year.get('avg_position', 0):.2f}位")
                context_parts.append("")
                
                context_parts.append("【変化率】")
                changes = yearly_comparison.get('changes', {})
                context_parts.append(f"クリック数: {changes.get('clicks', 0):+,} ({changes.get('clicks_change_pct', 0):+.1f}%)")
                context_parts.append(f"インプレッション数: {changes.get('impressions', 0):+,} ({changes.get('impressions_change_pct', 0):+.1f}%)")
                context_parts.append(f"CTR: {changes.get('ctr', 0):+.2f}%ポイント")
                context_parts.append(f"平均検索順位: {changes.get('position', 0):+.2f}位")
                context_parts.append("")
                context_parts.append("上記の年次比較データを基に、昨年と比べて今年のオーガニック集客がどう変化したかを分析してください。")
                context_parts.append("")
        
        # 特定ページのGSCデータ取得
        if needs_page_specific_analysis and urls:
            logger.info(f"特定ページのGSCデータを取得中: {urls[0]}")
            if progress_callback:
                progress_callback("[STEP] 📊 GSCデータを取得中...\n")
            page_gsc_data = self.google_apis.get_page_specific_gsc_data(
                page_url=urls[0],
                date_range_days=date_range,
                site_name=site_name,
                start_date=start_date,
                end_date=end_date
            )
            
            if 'error' not in page_gsc_data:
                step_elapsed = time.time() - step_start_time
                logger.info(f"特定ページのGSCデータ取得完了: {step_elapsed:.2f}秒")
                if step_elapsed > 5.0:
                    logger.warning(f"⚠️ 特定ページのGSCデータ取得に時間がかかりました: {step_elapsed:.2f}秒")
                
                data_status['gsc_page_specific'] = True
                clicks = page_gsc_data.get('clicks', 0)
                impressions = page_gsc_data.get('impressions', 0)
                
                context_parts.append(f"=== 特定ページのGSCデータ: {urls[0]} ===")
                if start_date and end_date:
                    context_parts.append(f"期間: {start_date} ～ {end_date}")
                else:
                    context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"クリック数: {clicks:,}")
                context_parts.append(f"インプレッション数: {impressions:,}")
                context_parts.append(f"CTR: {page_gsc_data.get('ctr', 0):.2f}%")
                context_parts.append(f"平均検索順位: {page_gsc_data.get('avg_position', 0):.2f}位")
                
                # データが0の場合も明示的に表示
                if clicks == 0 and impressions == 0:
                    context_parts.append("")
                    context_parts.append("⚠️ 注意: この期間、このページのGSCデータが0件です。")
                    context_parts.append("   - ページがまだインデックスされていない可能性があります")
                    context_parts.append("   - 指定された期間に検索トラフィックがなかった可能性があります")
                    context_parts.append("   - ページURLが正しいか確認してください")
                
                context_parts.append("")
            elif 'error' in page_gsc_data:
                error_msg = page_gsc_data.get('error', 'Unknown error')
                error_code = page_gsc_data.get('error_code', '')
                logger.warning(f"特定ページのGSCデータ取得エラー: {error_msg}")
                context_parts.append(f"=== 特定ページのGSCデータ: {urls[0]} ===")
                context_parts.append(f"❌ エラー: {error_msg}")
                context_parts.append("")
                
                # 403エラーの場合、より詳細な説明を追加
                if error_code == 403 or '403' in str(error_msg) or 'permission' in str(error_msg).lower() or 'forbidden' in str(error_msg).lower():
                    context_parts.append("【GSC権限エラーの対処方法】")
                    context_parts.append(f"1. Google Search Consoleで、サイト '{site_name}' のプロパティを開く")
                    context_parts.append("2. 設定 > ユーザーと権限 に移動")
                    context_parts.append("3. サービスアカウントのメールアドレスを追加し、'所有者'または'編集者'権限を付与")
                    # サービスアカウントのメールアドレスを取得
                    try:
                        if self.google_apis.credentials and hasattr(self.google_apis.credentials, 'service_account_email'):
                            service_account_email = self.google_apis.credentials.service_account_email
                            context_parts.append(f"4. サービスアカウントのメールアドレス: {service_account_email}")
                        elif self.google_apis.credentials and hasattr(self.google_apis.credentials, '_service_account_email'):
                            service_account_email = self.google_apis.credentials._service_account_email
                            context_parts.append(f"4. サービスアカウントのメールアドレス: {service_account_email}")
                        else:
                            context_parts.append("4. サービスアカウントのメールアドレスは認証情報から取得できませんでした")
                    except Exception as e:
                        logger.debug(f"サービスアカウントメールアドレスの取得エラー: {e}")
                        context_parts.append("4. サービスアカウントのメールアドレスは認証情報から取得できませんでした")
                    context_parts.append("")
                else:
                    context_parts.append("【考えられる原因】")
                    context_parts.append("- ページがまだGSCに登録されていない")
                    context_parts.append("- 指定された期間にデータが存在しない")
                    context_parts.append("- ページURLが正しくない")
                    context_parts.append("- GSC APIの認証エラー")
                    context_parts.append("")
        
        if needs_ga4:
            import time
            step_start_time = time.time()
            check_timeout()  # タイムアウトチェック
            logger.info(f"GA4データが必要と判定されました。取得を開始...")
            if progress_callback:
                progress_callback("[STEP] 📈 GA4データを取得中...\n")
            # URLが指定されている場合は個別ページのデータを取得
            page_url_for_ga4 = urls[0] if urls else None
            ga4_summary = self._get_ga4_summary(date_range, start_date, end_date, page_url=page_url_for_ga4)
            
            step_elapsed = time.time() - step_start_time
            logger.info(f"GA4データ取得完了: {step_elapsed:.2f}秒")
            if step_elapsed > 5.0:
                logger.warning(f"⚠️ GA4データ取得に時間がかかりました: {step_elapsed:.2f}秒")
            
            if "error" not in ga4_summary:
                data_status['ga4_data'] = True
                is_page_specific = ga4_summary.get('is_page_specific', False)
                if is_page_specific:
                    logger.info(f"個別ページのGA4データ取得成功: セッション={ga4_summary['total_sessions']:,}, ユーザー={ga4_summary['total_users']:,}, PV={ga4_summary['total_pageviews']:,}")
                    context_parts.append(f"=== 個別ページのGoogle Analytics 4 (GA4) データ: {page_url_for_ga4} ===")
                else:
                    logger.info(f"GA4データ取得成功: セッション={ga4_summary['total_sessions']:,}, ユーザー={ga4_summary['total_users']:,}, PV={ga4_summary['total_pageviews']:,}")
                    context_parts.append("=== Google Analytics 4 (GA4) データ（サイト全体） ===")
                if start_date and end_date:
                    context_parts.append(f"期間: {start_date} ～ {end_date}")
                else:
                    context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"総セッション数: {ga4_summary['total_sessions']:,}")
                context_parts.append(f"総ユーザー数: {ga4_summary['total_users']:,}")
                context_parts.append(f"総ページビュー数: {ga4_summary['total_pageviews']:,}")
                context_parts.append(f"平均バウンス率: {ga4_summary['avg_bounce_rate']:.2%}")
                context_parts.append(f"平均セッション時間: {ga4_summary['avg_session_duration']:.2f}秒")
                context_parts.append("")
            else:
                # エラーが発生した場合もコンテキストに含める
                error_msg = ga4_summary.get('error', 'Unknown error')
                is_timeout = ga4_summary.get('timeout', False)
                logger.warning(f"GA4データ取得エラー: {error_msg}")
                
                context_parts.append("=== Google Analytics 4 (GA4) データ ===")
                if is_timeout:
                    context_parts.append(f"⚠️ タイムアウト: {error_msg}")
                    context_parts.append("GA4データの取得に時間がかかりすぎたため、タイムアウトしました。")
                    context_parts.append("他のデータ（GSC、SEO分析）で分析を続行します。")
                else:
                    context_parts.append(f"❌ エラー: {error_msg}")
                    context_parts.append("GA4データが取得できませんでした。認証状態とAPI接続を確認してください。")
                context_parts.append("")
        else:
            logger.info("GA4データは不要と判定されました（キーワードマッチなし、URLなし、年次比較なし）")
        
        if needs_gsc:
            import time
            step_start_time = time.time()
            check_timeout()  # タイムアウトチェック
            if progress_callback and not (needs_page_specific_analysis and urls):  # 特定ページのGSCデータ取得と重複しない場合のみ
                progress_callback("[STEP] 📊 GSCデータを取得中...\n")
            gsc_summary = self._get_gsc_summary(date_range, start_date, end_date, site_name=site_name)
            
            step_elapsed = time.time() - step_start_time
            logger.info(f"GSCデータ（サイト全体）取得完了: {step_elapsed:.2f}秒")
            if step_elapsed > 5.0:
                logger.warning(f"⚠️ GSCデータ取得に時間がかかりました: {step_elapsed:.2f}秒")
            if "error" not in gsc_summary:
                data_status['gsc_data'] = True
                context_parts.append("=== Google Search Console (GSC) データ ===")
                if start_date and end_date:
                    context_parts.append(f"期間: {start_date} ～ {end_date}")
                else:
                    context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"総クリック数: {gsc_summary['total_clicks']:,}")
                context_parts.append(f"総インプレッション数: {gsc_summary['total_impressions']:,}")
                context_parts.append(f"平均CTR: {gsc_summary['avg_ctr']:.2f}%")
                context_parts.append(f"平均検索順位: {gsc_summary['avg_position']:.2f}位")
                
                if 'top_pages' in gsc_summary and gsc_summary['top_pages']:
                    context_parts.append("\n【トップページ（クリック数順）】")
                    for i, page in enumerate(gsc_summary['top_pages'][:5], 1):
                        context_parts.append(f"{i}. {page.get('page', 'N/A')}: クリック数 {page.get('clicks', 0):,}, インプレッション数 {page.get('impressions', 0):,}")
                
                if 'top_queries' in gsc_summary and gsc_summary['top_queries']:
                    context_parts.append("\n【トップ検索クエリ（クリック数順）】")
                    for i, query in enumerate(gsc_summary['top_queries'][:5], 1):
                        context_parts.append(f"{i}. {query.get('query', 'N/A')}: クリック数 {query.get('clicks', 0):,}, インプレッション数 {query.get('impressions', 0):,}")
                context_parts.append("")
            else:
                # エラーが発生した場合もコンテキストに含める
                error_msg = gsc_summary.get('error', 'Unknown error')
                error_code = gsc_summary.get('error_code', '')
                logger.warning(f"GSCデータ取得エラー: {error_msg}")
                context_parts.append("=== Google Search Console (GSC) データ ===")
                context_parts.append(f"❌ エラー: {error_msg}")
                context_parts.append(f"GSCデータが取得できませんでした（サイト: {site_name}）。")
                
                # 403エラーの場合、より詳細な説明を追加
                if error_code == 403 or '403' in str(error_msg) or 'permission' in str(error_msg).lower() or 'forbidden' in str(error_msg).lower():
                    context_parts.append("")
                    context_parts.append("【GSC権限エラーの対処方法】")
                    context_parts.append(f"1. Google Search Consoleで、サイト '{site_name}' のプロパティを開く")
                    context_parts.append("2. 設定 > ユーザーと権限 に移動")
                    context_parts.append("3. サービスアカウントのメールアドレスを追加し、'所有者'または'編集者'権限を付与")
                    # サービスアカウントのメールアドレスを取得
                    try:
                        if self.google_apis.credentials and hasattr(self.google_apis.credentials, 'service_account_email'):
                            service_account_email = self.google_apis.credentials.service_account_email
                            context_parts.append(f"4. サービスアカウントのメールアドレス: {service_account_email}")
                        elif self.google_apis.credentials and hasattr(self.google_apis.credentials, '_service_account_email'):
                            service_account_email = self.google_apis.credentials._service_account_email
                            context_parts.append(f"4. サービスアカウントのメールアドレス: {service_account_email}")
                        else:
                            context_parts.append("4. サービスアカウントのメールアドレスは認証情報から取得できませんでした")
                    except Exception as e:
                        logger.debug(f"サービスアカウントメールアドレスの取得エラー: {e}")
                        context_parts.append("4. サービスアカウントのメールアドレスは認証情報から取得できませんでした")
                    context_parts.append("")
                else:
                    context_parts.append("認証状態とAPI接続を確認してください。")
                    context_parts.append("")
        
        if not context_parts:
            # デフォルトで両方のデータを取得
            logger.info("デフォルトデータ取得モード: GA4とGSCデータを取得")
            ga4_summary = self._get_ga4_summary(date_range)
            gsc_summary = self._get_gsc_summary(date_range, site_name=site_name)
            
            if "error" not in ga4_summary:
                context_parts.append("=== Google Analytics 4 (GA4) データ ===")
                context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"総セッション数: {ga4_summary['total_sessions']:,}")
                context_parts.append(f"総ユーザー数: {ga4_summary['total_users']:,}")
                context_parts.append(f"総ページビュー数: {ga4_summary['total_pageviews']:,}")
                context_parts.append("")
            
            if "error" not in gsc_summary:
                context_parts.append("=== Google Search Console (GSC) データ ===")
                context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"総クリック数: {gsc_summary['total_clicks']:,}")
                context_parts.append(f"総インプレッション数: {gsc_summary['total_impressions']:,}")
                context_parts.append(f"平均CTR: {gsc_summary['avg_ctr']:.2f}%")
                context_parts.append(f"平均検索順位: {gsc_summary['avg_position']:.2f}位")
                context_parts.append("")
        
        # データコンテキストの検証
        total_elapsed = time.time() - start_time
        context_text = "\n".join(context_parts)
        logger.info(f"データコンテキスト構築完了")
        logger.info(f"  総処理時間: {total_elapsed:.2f}秒")
        logger.info(f"  コンテキスト長: {len(context_text)}文字")
        logger.info(f"  コンテキスト行数: {len(context_parts)}行")
        
        if not context_text.strip():
            logger.warning("⚠️ データコンテキストが空です")
        else:
            # データ取得状態をログに記録（正確な判定）
            has_gsc_data_success = data_status.get('gsc_data', False) or data_status.get('gsc_page_specific', False)
            logger.info(f"  含まれるデータ: SEO={data_status['seo_analysis']}, GA4={data_status['ga4_data']}, GSC={has_gsc_data_success}")
        
        if total_elapsed > 10.0:
            logger.warning(f"⚠️ データコンテキスト構築に時間がかかりました: {total_elapsed:.2f}秒")
        
        logger.info("=" * 60)
        
        return context_text
    
    def ask(self, question: str, model: str = "gpt-4o-mini", site_name: str = None) -> str:
        """
        質問に対してAIが回答を生成
        
        Args:
            question (str): ユーザーの質問
            model (str): 使用するOpenAIモデル（デフォルト: gpt-4o-mini）
            site_name (str): サイト名 ('moodmark' または 'moodmarkgift')、Noneの場合は自動判定またはデフォルトを使用
            
        Returns:
            str: AIの回答
        """
        try:
            logger.info("=" * 60)
            logger.info("AI回答生成開始")
            logger.info(f"質問: {question[:100]}...")
            logger.info(f"モデル: {model}")
            
            # データコンテキストを構築
            logger.info("データコンテキストを構築中...")
            data_context = self._build_data_context(question, site_name=site_name)
            
            if not data_context or not data_context.strip():
                logger.warning("データコンテキストが空です")
                return "申し訳ございませんが、データを取得できませんでした。設定を確認してください。"
            
            logger.info(f"データコンテキスト構築完了: {len(data_context)}文字")
            
            # SEO関連の質問かどうかを判定
            question_lower = question.lower()
            is_seo_question = any(keyword in question_lower for keyword in [
                'seo', 'タイトル', 'ディスクリプション', '見出し', 'メタ', 'alt', 
                '構造化データ', 'スクレイピング', 'html', 'css', 'ページ分析', 
                'コンテンツ分析', '改善提案', '最適化', '改善点', '課題'
            ]) or len(self._extract_urls(question)) > 0
            
            # 年次比較が要求されているかどうかを判定
            question_lower = question.lower()
            is_yearly_comparison = any(keyword in question_lower for keyword in [
                '昨年', '今年', '前年', '前年比', 'yoy', 'year over year', '比較',
                '比べて', '対比', '変化', '増減', '推移', 'トレンド'
            ])
            
            # プロンプトを構築
            if is_yearly_comparison:
                user_prompt = f"""以下のデータを基に、ユーザーの質問に回答してください。

**重要**: 年次比較データが提供されている場合は、必ず昨年と今年の数値を比較して分析してください。
- クリック数、インプレッション数、CTR、平均検索順位の変化を具体的に示してください
- 増減率を計算して、改善しているか悪化しているかを明確に示してください
- 変化の原因を推測し、改善提案を提示してください

質問: {question}

データ:
{data_context}

回答には以下を含めてください:
- 昨年と今年の数値の比較
- 増減率の計算
- 変化の分析と原因の推測
- 改善提案（該当する場合）
- わかりやすい日本語で説明"""
            elif is_seo_question:
                user_prompt = f"""以下のSEO分析データを基に、ユーザーの質問に回答してください。

{data_context}

ユーザーの質問: {question}

【回答形式】
必ず以下の3段階の構造で回答してください：

1. 【現状分析】
   - 現在のSEO要素の状態を数値と共に明確に示す
   - 最適値との比較を示す
   - 各要素の現状を整理

2. 【課題整理】
   - 現状分析から見つかった問題点を優先度順に整理
   - 各課題がSEOに与える影響を説明
   - 緊急度・重要度を考慮

3. 【改善提案】
   - 各課題に対する具体的な改善方法を提示
   - 実装可能な具体的な改善案を提示（例：タイトルの改善案、ディスクリプションの改善案）
   - 優先順位をつけて改善すべき順序を提示
   - 可能であれば、改善前後の比較も示す

わかりやすい日本語で、具体的な数値と共に説明してください。"""
            else:
                user_prompt = f"""以下のデータを基に、ユーザーの質問に回答してください。

{data_context}

ユーザーの質問: {question}

回答は以下の点を含めてください：
- データの要約
- 重要な数値の説明
- 改善提案やアドバイス（該当する場合）
- わかりやすい日本語で説明"""
            
            # OpenAI APIを呼び出し
            logger.info(f"OpenAI APIを呼び出し中... (モデル: {model})")
            logger.info(f"プロンプト長: {len(user_prompt)}文字")
            
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                answer = response.choices[0].message.content
                logger.info(f"回答を生成しました: {len(answer)}文字")
                logger.info("=" * 60)
                
                return answer
                
            except Exception as api_error:
                logger.error(f"OpenAI API呼び出しエラー: {api_error}", exc_info=True)
                raise api_error
            
        except Exception as e:
            logger.error(f"AI回答生成エラー: {e}", exc_info=True)
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"エラー詳細:\n{error_details}")
            raise  # エラーを再発生させて、UI側で処理
    
    def ask_stream(self, question: str, model: str = "gpt-4o-mini", site_name: str = None, conversation_history: List[Dict] = None) -> Generator[str, None, str]:
        """
        AIに質問してストリーミング応答を取得（ジェネレータ）
        
        Args:
            question (str): ユーザーの質問
            model (str): 使用するモデル名
            site_name (str): サイト名（'moodmark' または 'moodmarkgift'）
            conversation_history (List[Dict]): 会話履歴（オプション）
        
        Yields:
            str: ストリーミング応答のチャンク
        
        Returns:
            str: 完全な応答（エラー時は部分応答）
        """
        try:
            # データ取得の進捗をyield（待機時間中のストレス軽減のため）
            yield "[STEP] データ取得を開始しています...\n\n"
            
            # URLを抽出して、どのステップが必要か判定
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, question)
            question_lower = question.lower()
            
            # SEO分析が必要か判定
            needs_seo_analysis = any(keyword in question_lower for keyword in [
                'seo', 'タイトル', 'ディスクリプション', '見出し', 'メタ', 'alt', 
                '構造化データ', 'スクレイピング', 'html', 'css', 'ページ分析', 
                'コンテンツ分析', '改善提案', '最適化'
            ]) or len(urls) > 0
            
            # GA4/GSCデータが必要か判定
            needs_ga4 = any(keyword in question_lower for keyword in [
                'トラフィック', 'セッション', 'ユーザー', 'ページビュー', 'バウンス', 
                '滞在時間', 'コンバージョン', '売上', '収益', 'アクセス', '集客',
                'オーガニック', '流入', '訪問', '来訪', '月間', '数値', 'レポート',
                'report', 'データ', '統計', '分析', 'パフォーマンス', '実績',
                'ページ分析', 'ページの分析', '分析して', '分析してください'
            ]) or len(urls) > 0
            
            needs_gsc = any(keyword in question_lower for keyword in [
                '検索', 'seo', 'クリック', 'インプレッション', 'ctr', 'ポジション', 
                '順位', 'キーワード', 'クエリ', '検索流入', 'オーガニック', '集客',
                '月間', '数値', 'レポート', 'report', 'データ', '統計', '分析'
            ]) or len(urls) > 0
            
            # 進捗メッセージのキュー（yieldするため）
            progress_queue = []
            
            # 進捗コールバック関数を定義
            def progress_callback(message: str):
                """進捗メッセージをキューに追加"""
                progress_queue.append(message)
            
            # 各ステップの開始をyield
            if needs_seo_analysis and urls:
                yield "[STEP] 🔍 SEO分析を実行中...\n"
            
            if needs_gsc:
                yield "[STEP] 📊 GSCデータを取得中...\n"
            
            if needs_ga4:
                yield "[STEP] 📈 GA4データを取得中...\n"
            
            # データコンテキストを構築（進捗コールバック付き）
            data_context = self._build_data_context(question, site_name=site_name, progress_callback=progress_callback)
            
            # キューに蓄積された進捗メッセージをyield
            for msg in progress_queue:
                yield msg
            
            # データ取得完了を通知
            yield "[STEP] ✅ データ取得完了\n\n"
            yield "[STEP] 🤖 AI分析を開始しています...\n\n"
            
            # 会話履歴をコンテキストに含める（オプション）
            conversation_context = ""
            if conversation_history and len(conversation_history) > 0:
                conversation_context = "\n=== 会話履歴 ===\n"
                # 直近の2-3件の会話をコンテキストに含める
                for msg in conversation_history[-3:]:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    # 長すぎる場合は省略
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    conversation_context += f"{role}: {content_preview}\n"
                conversation_context += "\n"
            
            # シンプルで柔軟なプロンプトに統一
            user_prompt = f"""以下のデータを基に、ユーザーの質問に回答してください。

{conversation_context}データ:
{data_context}

ユーザーの質問: {question}

質問の意図を理解し、適切な回答形式と含めるべき情報を選択して回答してください。
- 提供されたデータを最大限に活用してください
- データがない場合は、その旨を明記してください
- 質問の種類に応じて、適切な構造で回答してください
- 数値は必ず具体的に示してください
- わかりやすい日本語で説明してください"""
            
            # OpenAI APIをストリーミングモードで呼び出し
            logger.info(f"OpenAI APIをストリーミングモードで呼び出し中... (モデル: {model})")
            logger.info(f"プロンプト長: {len(user_prompt)}文字")
            
            full_answer = ""  # 完全な応答を蓄積
            
            try:
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True  # ストリーミングを有効化
                )
                
                # ストリーミング応答を処理
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_answer += content
                        yield content
                
                logger.info(f"ストリーミング応答を生成しました: {len(full_answer)}文字")
                logger.info("=" * 60)
                
                # 完全な応答を返す（ジェネレータの戻り値として）
                return full_answer
                
            except Exception as api_error:
                logger.error(f"OpenAI APIストリーミング呼び出しエラー: {api_error}", exc_info=True)
                # 部分的な応答があれば返す
                if full_answer:
                    yield f"\n\n⚠️ エラーが発生しました: {str(api_error)}"
                    return full_answer
                raise api_error
            
        except Exception as e:
            logger.error(f"AIストリーミング応答生成エラー: {e}", exc_info=True)
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"エラー詳細:\n{error_details}")
            # エラーメッセージをyieldしてから再発生
            yield f"\n\n❌ エラーが発生しました: {str(e)}"
            raise  # エラーを再発生させて、UI側で処理
    
    def get_available_models(self) -> List[str]:
        """
        利用可能なOpenAIモデルのリストを取得
        
        Returns:
            list: モデル名のリスト
        """
        return [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]

