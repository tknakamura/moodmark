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
from typing import Optional, Dict, List, Any
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
    
    def __init__(self, credentials_file=None, openai_api_key=None):
        """
        初期化
        
        Args:
            credentials_file (str): Google認証情報ファイルのパス
            openai_api_key (str): OpenAI APIキー
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
        
        # システムプロンプト
        self.system_prompt = """あなたはGoogle Analytics 4 (GA4)、Google Search Console (GSC)、およびSEO分析の専門家です。
ユーザーの質問に対して、提供されたデータを基に、わかりやすく、実用的なアドバイスを提供してください。

【SEO改善に関する回答の構造】
SEO改善に関する質問には、必ず以下の3段階の構造で回答してください：

1. 【現状分析】
   - 現在のSEO要素の状態を数値と共に明確に示す
   - タイトル、ディスクリプション、見出し構造、画像alt属性、構造化データなどの現状を分析
   - 最適値との比較を示す（例：タイトルは45文字で、最適範囲30-60文字内）
   - **重要**: H2/H3の見出しテキストが提供されている場合は、具体的な見出しテキストを列挙し、その内容を分析してください
   - 見出しテキストの品質評価（長さ、キーワード含有率、重複など）を具体的に示してください

2. 【課題整理】
   - 現状分析から見つかった問題点を整理
   - 優先度の高い課題から順に列挙
   - 各課題がSEOに与える影響を説明
   - **重要**: 見出しテキストの問題（長すぎる/短すぎる、重複、キーワード含有率の低さなど）を具体的に指摘してください

3. 【改善提案】
   - 各課題に対する具体的な改善方法を提示
   - 実装可能な具体的な改善案を提示（例：タイトルの改善案、ディスクリプションの改善案）
   - **重要**: 見出しテキストの改善提案では、具体的な見出しテキストの改善案を提示してください
   - 長すぎる見出しの短縮案、短すぎる見出しの拡充案、重複見出しの統合案などを具体的に示してください
   - キーワード含有率を向上させるための見出しテキストの改善案を提示してください
   - 優先順位をつけて改善すべき順序を提示

【コンテンツSEOにおける見出し構造の重要性】
- 見出し構造（H1、H2、H3）はコンテンツSEOにおいて極めて重要です
- 見出しテキストは検索エンジンがコンテンツの構造と内容を理解するための重要な手がかりです
- H2/H3の見出しテキストは、具体的に列挙し、その品質を評価してください
- 見出しテキストの長さ、キーワード含有率、重複などの問題を具体的に指摘し、改善案を提示してください

【データに基づいた回答の重要性】
- GSC/GA4データが提供されている場合は、必ずそのデータを使用して回答してください
- 年次比較データが提供されている場合は、昨年と今年の数値を比較して分析してください
- 特定ページのデータが提供されている場合は、そのページの具体的な数値を示してください
- データがない場合は、データが取得できなかった旨を明記してください

【一般的な回答の注意点】
- データは数値で正確に示す
- トレンドや変化を明確に説明する
- 専門用語を使う場合は簡潔に説明する
- 日本語で回答する
- SEO改善以外の質問でも、可能な限り構造化して回答する
- 見出しテキストが提供されている場合は、必ず具体的な見出しテキストを回答に含めてください
- GSC/GA4データが提供されている場合は、SEO分析だけでなく、実際のトラフィックデータも分析してください"""
    
    def _extract_date_range(self, question: str) -> int:
        """
        質問から日付範囲を抽出
        
        Args:
            question (str): ユーザーの質問
            
        Returns:
            int: 日数
        """
        question_lower = question.lower()
        
        if '今日' in question_lower or '本日' in question_lower:
            return 1
        elif '昨日' in question_lower:
            return 1
        elif '今週' in question_lower or 'この週' in question_lower:
            return 7
        elif '先週' in question_lower or '前週' in question_lower:
            return 7
        elif '今月' in question_lower or '今月' in question_lower:
            return 30
        elif '先月' in question_lower or '前月' in question_lower:
            return 30
        elif '過去' in question_lower:
            # "過去7日"のような表現を探す
            import re
            match = re.search(r'過去(\d+)日', question_lower)
            if match:
                return int(match.group(1))
        elif '最近' in question_lower:
            return 7
        
        # デフォルトは30日
        return 30
    
    def _get_ga4_summary(self, date_range_days: int) -> Dict[str, Any]:
        """
        GA4データのサマリーを取得
        
        Args:
            date_range_days (int): 日数
            
        Returns:
            dict: サマリーデータ
        """
        try:
            # 基本的なメトリクスを取得
            ga4_data = self.google_apis.get_ga4_data(
                date_range_days=date_range_days,
                metrics=['sessions', 'users', 'pageviews', 'bounceRate', 'averageSessionDuration'],
                dimensions=['date']
            )
            
            if ga4_data.empty:
                return {"error": "データが取得できませんでした"}
            
            summary = {
                "total_sessions": int(ga4_data['sessions'].sum()) if 'sessions' in ga4_data.columns else 0,
                "total_users": int(ga4_data['users'].sum()) if 'users' in ga4_data.columns else 0,
                "total_pageviews": int(ga4_data['pageviews'].sum()) if 'pageviews' in ga4_data.columns else 0,
                "avg_bounce_rate": float(ga4_data['bounceRate'].mean()) if 'bounceRate' in ga4_data.columns else 0,
                "avg_session_duration": float(ga4_data['averageSessionDuration'].mean()) if 'averageSessionDuration' in ga4_data.columns else 0,
                "date_range_days": date_range_days,
                "data_points": len(ga4_data)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"GA4データ取得エラー: {e}")
            return {"error": f"データ取得エラー: {str(e)}"}
    
    def _get_gsc_summary(self, date_range_days: int) -> Dict[str, Any]:
        """
        GSCデータのサマリーを取得
        
        Args:
            date_range_days (int): 日数
            
        Returns:
            dict: サマリーデータ
        """
        try:
            # ページ別データを取得
            gsc_pages = self.google_apis.get_top_pages_gsc(
                date_range_days=date_range_days,
                limit=50
            )
            
            # クエリ別データを取得
            gsc_queries = self.google_apis.get_top_queries_gsc(
                date_range_days=date_range_days,
                limit=50
            )
            
            summary = {
                "total_clicks": int(gsc_pages['clicks'].sum()) if not gsc_pages.empty else 0,
                "total_impressions": int(gsc_pages['impressions'].sum()) if not gsc_pages.empty else 0,
                "avg_ctr": float(gsc_pages['ctr_calculated'].mean()) if not gsc_pages.empty and 'ctr_calculated' in gsc_pages.columns else 0,
                "avg_position": float(gsc_pages['avg_position'].mean()) if not gsc_pages.empty and 'avg_position' in gsc_pages.columns else 0,
                "top_pages_count": len(gsc_pages),
                "top_queries_count": len(gsc_queries),
                "date_range_days": date_range_days
            }
            
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
    
    def _build_data_context(self, question: str) -> str:
        """
        質問に基づいてデータコンテキストを構築
        
        Args:
            question (str): ユーザーの質問
            
        Returns:
            str: データコンテキストの文字列
        """
        logger.info("=" * 60)
        logger.info("データコンテキスト構築開始")
        logger.info(f"質問: {question[:100]}...")
        
        date_range = self._extract_date_range(question)
        logger.info(f"抽出された日付範囲: {date_range}日")
        
        context_parts = []
        
        # URLを抽出
        urls = self._extract_urls(question)
        logger.info(f"抽出されたURL: {urls}")
        
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
            'オーガニック', '流入', '訪問', '来訪'
        ]) or needs_yearly_comparison or needs_page_specific_analysis
        
        # GSCデータが必要かどうかを判定
        needs_gsc = any(keyword in question_lower for keyword in [
            '検索', 'seo', 'クリック', 'インプレッション', 'ctr', 'ポジション', 
            '順位', 'キーワード', 'クエリ', '検索流入', 'オーガニック', '集客'
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
            for idx, url in enumerate(urls[:3], 1):  # 最大3つのURLまで
                logger.info(f"[{idx}/{min(len(urls), 3)}] SEO分析を開始: {url}")
                try:
                    # ページ取得開始
                    logger.info(f"  ステップ1: ページ取得を開始...")
                    seo_analysis = self.seo_analyzer.analyze_page(url)
                    
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
                        context_parts.append("")
                        
                        # リンク構造
                        links = seo_analysis.get('links', {})
                        context_parts.append("■ リンク構造")
                        context_parts.append(f"  内部リンク: {links.get('internal_links', 0)}件")
                        context_parts.append(f"  外部リンク: {links.get('external_links', 0)}件")
                        context_parts.append(f"  nofollowリンク: {links.get('nofollow_links', 0)}件")
                        context_parts.append("")
                        
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
                date_range_days=date_range
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
            page_gsc_data = self.google_apis.get_page_specific_gsc_data(
                page_url=urls[0],
                date_range_days=date_range
            )
            
            if 'error' not in page_gsc_data:
                context_parts.append(f"=== 特定ページのGSCデータ: {urls[0]} ===")
                context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"クリック数: {page_gsc_data.get('clicks', 0):,}")
                context_parts.append(f"インプレッション数: {page_gsc_data.get('impressions', 0):,}")
                context_parts.append(f"CTR: {page_gsc_data.get('ctr', 0):.2f}%")
                context_parts.append(f"平均検索順位: {page_gsc_data.get('avg_position', 0):.2f}位")
                context_parts.append("")
            elif 'error' in page_gsc_data:
                context_parts.append(f"⚠️ 特定ページのGSCデータ取得エラー: {page_gsc_data.get('error', 'Unknown error')}")
                context_parts.append("")
        
        if needs_ga4:
            ga4_summary = self._get_ga4_summary(date_range)
            if "error" not in ga4_summary:
                context_parts.append("=== Google Analytics 4 (GA4) データ ===")
                context_parts.append(f"期間: 過去{date_range}日間")
                context_parts.append(f"総セッション数: {ga4_summary['total_sessions']:,}")
                context_parts.append(f"総ユーザー数: {ga4_summary['total_users']:,}")
                context_parts.append(f"総ページビュー数: {ga4_summary['total_pageviews']:,}")
                context_parts.append(f"平均バウンス率: {ga4_summary['avg_bounce_rate']:.2%}")
                context_parts.append(f"平均セッション時間: {ga4_summary['avg_session_duration']:.2f}秒")
                context_parts.append("")
        
        if needs_gsc:
            gsc_summary = self._get_gsc_summary(date_range)
            if "error" not in gsc_summary:
                context_parts.append("=== Google Search Console (GSC) データ ===")
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
        
        if not context_parts:
            # デフォルトで両方のデータを取得
            logger.info("デフォルトデータ取得モード: GA4とGSCデータを取得")
            ga4_summary = self._get_ga4_summary(date_range)
            gsc_summary = self._get_gsc_summary(date_range)
            
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
        context_text = "\n".join(context_parts)
        logger.info(f"データコンテキスト構築完了")
        logger.info(f"  コンテキスト長: {len(context_text)}文字")
        logger.info(f"  コンテキスト行数: {len(context_parts)}行")
        
        if not context_text.strip():
            logger.warning("⚠️ データコンテキストが空です")
        else:
            # コンテキストのサマリーをログに記録
            has_seo_data = "SEO分析結果" in context_text
            has_ga4_data = "GA4" in context_text
            has_gsc_data = "GSC" in context_text
            logger.info(f"  含まれるデータ: SEO={has_seo_data}, GA4={has_ga4_data}, GSC={has_gsc_data}")
        
        logger.info("=" * 60)
        
        return context_text
    
    def ask(self, question: str, model: str = "gpt-4o-mini") -> str:
        """
        質問に対してAIが回答を生成
        
        Args:
            question (str): ユーザーの質問
            model (str): 使用するOpenAIモデル（デフォルト: gpt-4o-mini）
            
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
            data_context = self._build_data_context(question)
            
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

