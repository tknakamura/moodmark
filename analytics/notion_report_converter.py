#!/usr/bin/env python3
"""
Notion レポート変換モジュール
- 分析レポートのNotion形式変換
- Markdownコンテンツの最適化
- テンプレート管理
- データフォーマット調整
"""

import os
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class NotionReportConverter:
    def __init__(self, config_path: str = 'config/notion_config.json'):
        """
        Notionレポート変換クラスの初期化
        
        Args:
            config_path (str): 設定ファイルのパス
        """
        self.config_path = config_path
        self.config = self._load_config()
        
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
    
    def convert_analysis_report(self, json_file_path: str, markdown_file_path: str = None) -> Dict[str, Any]:
        """
        分析レポートをNotion用に変換
        
        Args:
            json_file_path (str): JSONレポートファイルのパス
            markdown_file_path (str, optional): Markdownレポートファイルのパス
            
        Returns:
            dict: Notion用に変換されたレポートデータ
        """
        try:
            # JSONデータの読み込み
            with open(json_file_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Markdownデータの読み込み
            markdown_content = ""
            if markdown_file_path and os.path.exists(markdown_file_path):
                with open(markdown_file_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
            
            # Notion用に変換
            converted_report = {
                'metadata': self._extract_metadata(report_data),
                'summary': self._format_summary(report_data.get('summary', {})),
                'recommendations': self._format_recommendations(report_data.get('recommendations', [])),
                'content': self._optimize_markdown_for_notion(markdown_content),
                'kpi_metrics': self._extract_kpi_metrics(report_data),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"レポート変換完了: {json_file_path}")
            return converted_report
            
        except Exception as e:
            logger.error(f"レポート変換エラー: {e}")
            return {}
    
    def _extract_metadata(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """メタデータの抽出"""
        metadata = {
            'report_date': report_data.get('report_date', datetime.now().isoformat()),
            'period': report_data.get('period', '期間不明'),
            'site_url': report_data.get('site_url', ''),
            'conversion_definition': report_data.get('conversion_definition', ''),
            'report_type': 'weekly_analysis'  # デフォルト
        }
        
        # 日付の正規化
        if isinstance(metadata['report_date'], str):
            try:
                dt = datetime.fromisoformat(metadata['report_date'].replace('Z', '+00:00'))
                metadata['report_date'] = dt
            except:
                metadata['report_date'] = datetime.now()
        
        return metadata
    
    def _format_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """サマリーデータの整形"""
        formatted = {}
        
        # 数値データの正規化とフォーマット
        numeric_fields = {
            'total_sessions': ('セッション数', 'number'),
            'total_users': ('ユーザー数', 'number'),
            'total_pageviews': ('ページビュー数', 'number'),
            'total_purchases': ('購入数', 'number'),
            'total_revenue': ('売上', 'currency'),
            'purchase_cvr': ('購入CVR', 'percentage'),
            'avg_order_value': ('平均注文単価', 'currency'),
            'avg_bounce_rate': ('平均直帰率', 'percentage'),
            'avg_session_duration': ('平均セッション時間', 'duration')
        }
        
        for field, (label, format_type) in numeric_fields.items():
            if field in summary:
                value = summary[field]
                formatted[field] = {
                    'label': label,
                    'value': value,
                    'formatted_value': self._format_value(value, format_type),
                    'type': format_type
                }
        
        return formatted
    
    def _format_value(self, value: Any, format_type: str) -> str:
        """値のフォーマット"""
        if value is None:
            return "N/A"
        
        try:
            if format_type == 'currency':
                return f"¥{value:,.0f}"
            elif format_type == 'percentage':
                if value > 1:  # 100を超える値は既にパーセント表示と仮定
                    return f"{value:.2f}%"
                else:  # 1以下の値は小数として扱い、パーセントに変換
                    return f"{value * 100:.2f}%"
            elif format_type == 'number':
                return f"{value:,}"
            elif format_type == 'duration':
                # 秒数を時間:分:秒に変換
                hours = int(value // 3600)
                minutes = int((value % 3600) // 60)
                seconds = int(value % 60)
                if hours > 0:
                    return f"{hours}時間{minutes}分{seconds}秒"
                elif minutes > 0:
                    return f"{minutes}分{seconds}秒"
                else:
                    return f"{seconds}秒"
            else:
                return str(value)
        except:
            return str(value)
    
    def _format_recommendations(self, recommendations: List[str]) -> List[Dict[str, Any]]:
        """推奨事項の整形"""
        formatted_recs = []
        
        for i, rec in enumerate(recommendations):
            # 優先度の推定
            priority = self._estimate_priority(rec)
            
            # カテゴリの推定
            category = self._estimate_category(rec)
            
            formatted_recs.append({
                'id': f"rec_{i+1}",
                'content': rec,
                'priority': priority,
                'category': category,
                'status': 'open',
                'estimated_impact': self._estimate_impact(rec)
            })
        
        return formatted_recs
    
    def _estimate_priority(self, recommendation: str) -> str:
        """推奨事項の優先度を推定"""
        high_keywords = ['緊急', '重要', 'CVR', '売上', '購入', '必須', '即座']
        medium_keywords = ['改善', '最適化', '強化', '検討']
        
        rec_lower = recommendation.lower()
        
        if any(keyword in rec_lower for keyword in high_keywords):
            return 'High'
        elif any(keyword in rec_lower for keyword in medium_keywords):
            return 'Medium'
        else:
            return 'Low'
    
    def _estimate_category(self, recommendation: str) -> str:
        """推奨事項のカテゴリを推定"""
        categories = {
            'モバイル': ['モバイル', 'スマホ', 'mobile'],
            'デスクトップ': ['デスクトップ', 'PC', 'desktop'],
            'SEO': ['検索', 'SEO', 'キーワード', '検索順位'],
            'CVR改善': ['CVR', '購入', 'コンバージョン', '購入率'],
            'UX改善': ['UX', 'UI', 'ユーザー', 'フォーム', '導線'],
            '広告': ['広告', 'ディスプレイ', 'リターゲティング'],
            'パフォーマンス': ['パフォーマンス', '速度', '読み込み']
        }
        
        rec_lower = recommendation.lower()
        
        for category, keywords in categories.items():
            if any(keyword.lower() in rec_lower for keyword in keywords):
                return category
        
        return 'その他'
    
    def _estimate_impact(self, recommendation: str) -> str:
        """推奨事項の影響度を推定"""
        high_impact_keywords = ['売上増加', 'CVR改善', '購入数', '2倍', '50%']
        medium_impact_keywords = ['改善', '最適化', '向上']
        
        rec_lower = recommendation.lower()
        
        if any(keyword in rec_lower for keyword in high_impact_keywords):
            return 'High'
        elif any(keyword in rec_lower for keyword in medium_impact_keywords):
            return 'Medium'
        else:
            return 'Low'
    
    def _optimize_markdown_for_notion(self, markdown_content: str) -> Dict[str, Any]:
        """MarkdownコンテンツをNotion用に最適化"""
        if not markdown_content:
            return {'sections': [], 'word_count': 0}
        
        # セクションに分割
        sections = self._split_into_sections(markdown_content)
        
        # Notion制限に合わせて最適化
        optimized_sections = []
        for section in sections:
            optimized_section = self._optimize_section_for_notion(section)
            if optimized_section:
                optimized_sections.append(optimized_section)
        
        return {
            'sections': optimized_sections,
            'word_count': len(markdown_content),
            'section_count': len(optimized_sections)
        }
    
    def _split_into_sections(self, content: str) -> List[Dict[str, str]]:
        """コンテンツをセクションに分割"""
        sections = []
        current_section = {'title': '', 'content': '', 'level': 0}
        
        lines = content.split('\n')
        
        for line in lines:
            # 見出しの検出
            if line.startswith('#'):
                # 前のセクションを保存
                if current_section['content'].strip():
                    sections.append(current_section.copy())
                
                # 新しいセクション開始
                level = len(re.match(r'^#+', line).group())
                title = line.lstrip('#').strip()
                
                current_section = {
                    'title': title,
                    'content': '',
                    'level': level
                }
            else:
                # コンテンツに追加
                current_section['content'] += line + '\n'
        
        # 最後のセクションを追加
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _optimize_section_for_notion(self, section: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """セクションをNotion用に最適化"""
        title = section['title']
        content = section['content'].strip()
        level = section['level']
        
        if not content:
            return None
        
        # Notion APIの制限に合わせてコンテンツを分割
        max_block_length = 2000
        content_blocks = []
        
        # 段落単位で分割
        paragraphs = content.split('\n\n')
        current_block = ""
        
        for paragraph in paragraphs:
            if len(current_block + paragraph) > max_block_length:
                if current_block:
                    content_blocks.append(current_block.strip())
                current_block = paragraph
            else:
                if current_block:
                    current_block += '\n\n' + paragraph
                else:
                    current_block = paragraph
        
        if current_block:
            content_blocks.append(current_block.strip())
        
        return {
            'title': title,
            'level': level,
            'content_blocks': content_blocks,
            'block_count': len(content_blocks)
        }
    
    def _extract_kpi_metrics(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """KPI指標の抽出"""
        summary = report_data.get('summary', {})
        kpi_metrics = []
        
        # 主要KPIの定義
        kpi_definitions = [
            {
                'name': 'Total Sessions',
                'key': 'total_sessions',
                'label': '総セッション数',
                'target': None,
                'format': 'number'
            },
            {
                'name': 'Total Revenue',
                'key': 'total_revenue', 
                'label': '総売上',
                'target': None,
                'format': 'currency'
            },
            {
                'name': 'Purchase CVR',
                'key': 'purchase_cvr',
                'label': '購入CVR',
                'target': 0.01,  # 1%目標
                'format': 'percentage'
            },
            {
                'name': 'AOV',
                'key': 'avg_order_value',
                'label': '平均注文単価',
                'target': 6000,  # ¥6,000目標
                'format': 'currency'
            },
            {
                'name': 'Bounce Rate',
                'key': 'avg_bounce_rate',
                'label': '平均直帰率',
                'target': 0.3,  # 30%以下目標
                'format': 'percentage'
            }
        ]
        
        for kpi_def in kpi_definitions:
            if kpi_def['key'] in summary:
                value = summary[kpi_def['key']]
                
                # 目標との比較
                status = 'neutral'
                if kpi_def['target'] is not None:
                    if kpi_def['key'] == 'avg_bounce_rate':
                        # 直帰率は低い方が良い
                        status = 'good' if value <= kpi_def['target'] else 'poor'
                    else:
                        # その他は高い方が良い
                        status = 'good' if value >= kpi_def['target'] else 'poor'
                
                kpi_metrics.append({
                    'name': kpi_def['name'],
                    'label': kpi_def['label'],
                    'value': value,
                    'formatted_value': self._format_value(value, kpi_def['format']),
                    'target': kpi_def['target'],
                    'status': status,
                    'format': kpi_def['format']
                })
        
        return kpi_metrics
    
    def create_executive_summary(self, converted_report: Dict[str, Any]) -> str:
        """エグゼクティブサマリーの作成"""
        summary = converted_report.get('summary', {})
        recommendations = converted_report.get('recommendations', [])
        
        # 主要指標の抽出
        key_metrics = []
        if 'total_revenue' in summary:
            key_metrics.append(f"売上: {summary['total_revenue']['formatted_value']}")
        if 'purchase_cvr' in summary:
            key_metrics.append(f"CVR: {summary['purchase_cvr']['formatted_value']}")
        if 'total_sessions' in summary:
            key_metrics.append(f"セッション: {summary['total_sessions']['formatted_value']}")
        
        # 優先度の高い推奨事項
        high_priority_recs = [rec for rec in recommendations if rec.get('priority') == 'High']
        
        # エグゼクティブサマリーの構築
        exec_summary = "## 📊 エグゼクティブサマリー\n\n"
        
        if key_metrics:
            exec_summary += "### 主要指標\n"
            exec_summary += " | ".join(key_metrics) + "\n\n"
        
        if high_priority_recs:
            exec_summary += "### 重要な改善点\n"
            for i, rec in enumerate(high_priority_recs[:3], 1):  # 上位3つ
                exec_summary += f"{i}. {rec['content']}\n"
            exec_summary += "\n"
        
        return exec_summary
    
    def generate_notion_tags(self, converted_report: Dict[str, Any]) -> List[str]:
        """Notion用タグの生成"""
        tags = ["Weekly Report"]
        
        # レポートタイプに基づくタグ
        metadata = converted_report.get('metadata', {})
        if metadata.get('report_type'):
            tags.append(metadata['report_type'].replace('_', ' ').title())
        
        # 推奨事項のカテゴリからタグを生成
        recommendations = converted_report.get('recommendations', [])
        categories = set()
        for rec in recommendations:
            if rec.get('category'):
                categories.add(rec['category'])
        
        # 主要カテゴリのみ追加（最大3つ）
        for category in list(categories)[:3]:
            if category not in tags:
                tags.append(category)
        
        return tags


def main():
    """テスト実行用のメイン関数"""
    print("=== Notionレポート変換システムテスト ===")
    
    # コンバーターの初期化
    converter = NotionReportConverter()
    
    # テストデータファイルの検索
    test_files = [
        'data/processed/analysis_report_purchase_7days_20251011_173000.json',
        'docs/analytics/moodmark_7days_analysis_report.md'
    ]
    
    json_file = None
    md_file = None
    
    for file_path in test_files:
        if os.path.exists(file_path):
            if file_path.endswith('.json'):
                json_file = file_path
            elif file_path.endswith('.md'):
                md_file = file_path
    
    if json_file:
        print(f"テストファイル: {json_file}")
        
        # レポート変換のテスト
        converted = converter.convert_analysis_report(json_file, md_file)
        
        if converted:
            print("レポート変換成功")
            print(f"サマリー指標数: {len(converted.get('summary', {}))}")
            print(f"推奨事項数: {len(converted.get('recommendations', []))}")
            print(f"KPI指標数: {len(converted.get('kpi_metrics', []))}")
            
            # エグゼクティブサマリーのテスト
            exec_summary = converter.create_executive_summary(converted)
            print(f"エグゼクティブサマリー: {len(exec_summary)} 文字")
            
            # タグ生成のテスト
            tags = converter.generate_notion_tags(converted)
            print(f"生成タグ: {tags}")
        else:
            print("レポート変換に失敗しました")
    else:
        print("テスト用のJSONファイルが見つかりません")

if __name__ == "__main__":
    main()
