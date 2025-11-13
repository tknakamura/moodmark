#!/usr/bin/env python3
"""
SEO分析モジュール
ページコンテンツのスクレイピングとHTML/CSS解析機能
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SEOAnalyzer:
    """SEO分析クラス - ページコンテンツのスクレイピングと解析"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        初期化
        
        Args:
            base_url (str): ベースURL（相対URL解決用）
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def fetch_page(self, url: str, timeout: int = 30, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        ページを取得してBeautifulSoupオブジェクトを返す
        
        Args:
            url (str): 取得するURL
            timeout (int): タイムアウト（秒）
            
        Returns:
            BeautifulSoup: パースされたHTML、エラー時はNone
        """
        import time
        
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"ページ取得開始 (試行 {attempt}/{retries}): {url}")
                logger.info(f"  タイムアウト: {timeout}秒")
                
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                
                logger.info(f"ページ取得成功: ステータスコード {response.status_code}, サイズ {len(response.content)} bytes")
                response.encoding = response.apparent_encoding or 'utf-8'
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info(f"HTML解析成功: {len(soup.find_all())} 要素")
                return soup
                
            except requests.exceptions.Timeout as e:
                logger.warning(f"ページ取得タイムアウト (試行 {attempt}/{retries}) ({url}): {e}")
                if attempt < retries:
                    wait_time = attempt * 2  # 指数バックオフ
                    logger.info(f"  {wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"ページ取得タイムアウト: すべての試行が失敗しました ({url})")
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"ページ取得接続エラー (試行 {attempt}/{retries}) ({url}): {e}")
                if attempt < retries:
                    wait_time = attempt * 2
                    logger.info(f"  {wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"ページ取得接続エラー: すべての試行が失敗しました ({url})")
                    return None
                    
            except requests.exceptions.HTTPError as e:
                status_code = response.status_code if 'response' in locals() else 'N/A'
                logger.error(f"ページ取得HTTPエラー ({url}): ステータスコード {status_code}, {e}")
                # HTTPエラーは再試行しない（4xx, 5xxエラー）
                return None
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"ページ取得エラー (試行 {attempt}/{retries}) ({url}): {e}")
                if attempt < retries:
                    wait_time = attempt * 2
                    logger.info(f"  {wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"ページ取得エラー: すべての試行が失敗しました ({url})")
                    return None
                    
            except Exception as e:
                logger.error(f"予期しないエラー ({url}): {e}", exc_info=True)
                return None
        
        return None
    
    def analyze_page(self, url: str) -> Dict[str, Any]:
        """
        ページの包括的なSEO分析を実行
        
        Args:
            url (str): 分析するURL
            
        Returns:
            dict: SEO分析結果
        """
        logger.info(f"SEO分析開始: {url}")
        try:
            soup = self.fetch_page(url)
            if not soup:
                error_msg = 'ページの取得に失敗しました。URLが正しいか、ページがアクセス可能か確認してください。'
                logger.error(f"SEO分析失敗: {error_msg}")
                return {
                    'url': url,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                }
            
            logger.info("SEO分析の各セクションを実行中...")
            
            try:
                analysis = {
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'basic': self._analyze_basic_seo(soup),
                    'content': self._analyze_content(soup),
                    'technical': self._analyze_technical_seo(soup),
                    'performance': self._analyze_performance(soup, url),
                    'accessibility': self._analyze_accessibility(soup),
                    'structured_data': self._analyze_structured_data(soup),
                    'links': self._analyze_links(soup, url),
                    'images': self._analyze_images(soup),
                    'css': self._analyze_css(soup, url)
                }
                
                logger.info("SEO分析完了")
                logger.info(f"  基本SEO: ✓, コンテンツ: ✓, 技術的SEO: ✓, パフォーマンス: ✓")
                logger.info(f"  アクセシビリティ: ✓, 構造化データ: ✓, リンク: ✓, 画像: ✓, CSS: ✓")
                
                return analysis
            except Exception as e:
                logger.error(f"SEO分析中にエラーが発生しました: {e}", exc_info=True)
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"エラー詳細:\n{error_details}")
                return {
                    'url': url,
                    'error': f'SEO分析中にエラーが発生しました: {str(e)}',
                    'error_details': error_details,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"SEO分析で予期しないエラーが発生しました: {e}", exc_info=True)
            return {
                'url': url,
                'error': f'予期しないエラーが発生しました: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_basic_seo(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """基本的なSEO要素の分析"""
        # タイトルタグ
        title_tag = soup.find('title')
        title = title_tag.get_text().strip() if title_tag else ""
        title_length = len(title)
        
        # メタディスクリプション
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '').strip() if meta_desc else ""
        desc_length = len(description)
        
        # メタキーワード（非推奨だが確認）
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        keywords = meta_keywords.get('content', '').strip() if meta_keywords else ""
        
        # Canonical URL
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        canonical_url = canonical.get('href', '') if canonical else ""
        
        # Robots meta
        robots = soup.find('meta', attrs={'name': 'robots'})
        robots_content = robots.get('content', '') if robots else ""
        
        return {
            'title': title,
            'title_length': title_length,
            'title_optimal': 30 <= title_length <= 60,
            'description': description,
            'description_length': desc_length,
            'description_optimal': 120 <= desc_length <= 160,
            'keywords': keywords,
            'canonical_url': canonical_url,
            'robots': robots_content,
            'has_title': bool(title),
            'has_description': bool(description)
        }
    
    def _analyze_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """コンテンツ構造の分析"""
        # 見出しタグ（テキストを取得し、空でないもののみ）
        headings = {
            'h1': [h.get_text().strip() for h in soup.find_all('h1') if h.get_text().strip()],
            'h2': [h.get_text().strip() for h in soup.find_all('h2') if h.get_text().strip()],
            'h3': [h.get_text().strip() for h in soup.find_all('h3') if h.get_text().strip()],
            'h4': [h.get_text().strip() for h in soup.find_all('h4') if h.get_text().strip()],
            'h5': [h.get_text().strip() for h in soup.find_all('h5') if h.get_text().strip()],
            'h6': [h.get_text().strip() for h in soup.find_all('h6') if h.get_text().strip()]
        }
        
        # 見出し構造の階層チェック
        h1_count = len(headings['h1'])
        h2_count = len(headings['h2'])
        h3_count = len(headings['h3'])
        
        # 見出し構造の評価
        heading_structure_optimal = (
            h1_count == 1 and  # H1は1つ
            h2_count > 0 and   # H2が存在
            (h3_count == 0 or h2_count > 0)  # H3がある場合はH2も存在
        )
        
        # 本文テキスト
        # scriptとstyleタグを除去
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        word_count = len(text.split())
        char_count = len(text)
        
        # 段落
        paragraphs = soup.find_all('p')
        paragraph_count = len(paragraphs)
        
        # リスト
        lists = soup.find_all(['ul', 'ol'])
        list_count = len(lists)
        
        # H1の数（理想的には1つ）
        h1_count = len(headings['h1'])
        h1_optimal = h1_count == 1
        
        # 見出しテキストの品質評価
        heading_quality = self._analyze_heading_quality(headings)
        
        return {
            'headings': headings,
            'h1_count': h1_count,
            'h1_optimal': h1_optimal,
            'h2_count': len(headings['h2']),
            'h3_count': len(headings['h3']),
            'h4_count': len(headings['h4']),
            'h5_count': len(headings['h5']),
            'h6_count': len(headings['h6']),
            'heading_structure_optimal': heading_structure_optimal,
            'heading_quality': heading_quality,
            'word_count': word_count,
            'char_count': char_count,
            'paragraph_count': paragraph_count,
            'list_count': list_count,
            'content_length_optimal': word_count >= 300  # 最低300語推奨
        }
    
    def _analyze_heading_quality(self, headings: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        見出しテキストの品質評価
        
        Args:
            headings: 見出しテキストの辞書
            
        Returns:
            dict: 品質評価結果
        """
        quality = {
            'h2': {
                'total': len(headings['h2']),
                'optimal_length': 0,
                'too_short': [],
                'too_long': [],
                'duplicates': [],
                'length_stats': {}
            },
            'h3': {
                'total': len(headings['h3']),
                'optimal_length': 0,
                'too_short': [],
                'too_long': [],
                'duplicates': [],
                'length_stats': {}
            }
        }
        
        # H2の品質評価
        h2_lengths = []
        h2_texts = []
        for h2 in headings['h2']:
            length = len(h2)
            h2_lengths.append(length)
            h2_texts.append(h2)
            
            # 推奨範囲: 30-60文字
            if 30 <= length <= 60:
                quality['h2']['optimal_length'] += 1
            elif length < 30:
                quality['h2']['too_short'].append({'text': h2, 'length': length})
            else:
                quality['h2']['too_long'].append({'text': h2, 'length': length})
        
        # H2の重複チェック
        h2_counts = {}
        for h2 in h2_texts:
            h2_counts[h2] = h2_counts.get(h2, 0) + 1
        quality['h2']['duplicates'] = [text for text, count in h2_counts.items() if count > 1]
        
        # H2の長さ統計
        if h2_lengths:
            quality['h2']['length_stats'] = {
                'min': min(h2_lengths),
                'max': max(h2_lengths),
                'avg': sum(h2_lengths) / len(h2_lengths),
                'median': sorted(h2_lengths)[len(h2_lengths) // 2]
            }
        
        # H3の品質評価
        h3_lengths = []
        h3_texts = []
        for h3 in headings['h3']:
            length = len(h3)
            h3_lengths.append(length)
            h3_texts.append(h3)
            
            # 推奨範囲: 20-50文字
            if 20 <= length <= 50:
                quality['h3']['optimal_length'] += 1
            elif length < 20:
                quality['h3']['too_short'].append({'text': h3, 'length': length})
            else:
                quality['h3']['too_long'].append({'text': h3, 'length': length})
        
        # H3の重複チェック
        h3_counts = {}
        for h3 in h3_texts:
            h3_counts[h3] = h3_counts.get(h3, 0) + 1
        quality['h3']['duplicates'] = [text for text, count in h3_counts.items() if count > 1]
        
        # H3の長さ統計
        if h3_lengths:
            quality['h3']['length_stats'] = {
                'min': min(h3_lengths),
                'max': max(h3_lengths),
                'avg': sum(h3_lengths) / len(h3_lengths),
                'median': sorted(h3_lengths)[len(h3_lengths) // 2]
            }
        
        # キーワード分析（H1から主要キーワードを抽出）
        main_keywords = []
        if headings['h1']:
            h1_text = headings['h1'][0]
            # 簡単なキーワード抽出（2文字以上の単語）
            import re
            words = re.findall(r'\w{2,}', h1_text.lower())
            main_keywords = words[:5]  # 最初の5語を主要キーワードとする
        
        # H2/H3での主要キーワード含有率
        h2_keyword_coverage = 0
        h3_keyword_coverage = 0
        
        if main_keywords and headings['h2']:
            h2_with_keywords = sum(1 for h2 in headings['h2'] 
                                  if any(kw in h2.lower() for kw in main_keywords))
            h2_keyword_coverage = h2_with_keywords / len(headings['h2']) if headings['h2'] else 0
        
        if main_keywords and headings['h3']:
            h3_with_keywords = sum(1 for h3 in headings['h3'] 
                                  if any(kw in h3.lower() for kw in main_keywords))
            h3_keyword_coverage = h3_with_keywords / len(headings['h3']) if headings['h3'] else 0
        
        quality['keyword_analysis'] = {
            'main_keywords': main_keywords,
            'h2_keyword_coverage': h2_keyword_coverage,
            'h3_keyword_coverage': h3_keyword_coverage
        }
        
        # SEO最適化スコア計算（0-100）
        score = 0
        max_score = 100
        
        # H2の長さスコア（30点）
        if quality['h2']['total'] > 0:
            h2_length_score = (quality['h2']['optimal_length'] / quality['h2']['total']) * 30
            score += h2_length_score
        
        # H3の長さスコア（20点）
        if quality['h3']['total'] > 0:
            h3_length_score = (quality['h3']['optimal_length'] / quality['h3']['total']) * 20
            score += h3_length_score
        
        # 重複ペナルティ（20点）
        duplicate_penalty = min(20, len(quality['h2']['duplicates']) * 2 + len(quality['h3']['duplicates']) * 1)
        score -= duplicate_penalty
        
        # キーワード含有率スコア（30点）
        keyword_score = (h2_keyword_coverage * 0.6 + h3_keyword_coverage * 0.4) * 30
        score += keyword_score
        
        quality['seo_score'] = max(0, min(100, int(score)))
        
        return quality
    
    def _analyze_technical_seo(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """技術的SEO要素の分析"""
        # Open Graph
        og_tags = {}
        for og_tag in soup.find_all('meta', attrs={'property': re.compile(r'^og:')}):
            prop = og_tag.get('property', '')
            content = og_tag.get('content', '')
            og_tags[prop] = content
        
        # Twitter Card
        twitter_tags = {}
        for twitter_tag in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = twitter_tag.get('name', '')
            content = twitter_tag.get('content', '')
            twitter_tags[name] = content
        
        # Viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        has_viewport = viewport is not None
        
        # Charset
        charset = soup.find('meta', attrs={'charset': True})
        charset_value = charset.get('charset', '') if charset else ""
        if not charset_value:
            charset_meta = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
            if charset_meta:
                content = charset_meta.get('content', '')
                match = re.search(r'charset=([^;]+)', content)
                charset_value = match.group(1) if match else ""
        
        # Language
        html_tag = soup.find('html')
        lang = html_tag.get('lang', '') if html_tag else ""
        
        return {
            'open_graph': og_tags,
            'twitter_card': twitter_tags,
            'has_viewport': has_viewport,
            'charset': charset_value,
            'language': lang,
            'is_mobile_friendly': has_viewport
        }
    
    def _analyze_performance(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """パフォーマンス関連の分析"""
        # 外部リソース
        external_scripts = []
        external_stylesheets = []
        
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if src.startswith('http') and urlparse(src).netloc != urlparse(url).netloc:
                external_scripts.append(src)
        
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href.startswith('http') and urlparse(href).netloc != urlparse(url).netloc:
                external_stylesheets.append(href)
        
        # インラインスタイル
        inline_styles = soup.find_all(attrs={'style': True})
        inline_style_count = len(inline_styles)
        
        # 画像の遅延読み込み
        lazy_images = soup.find_all('img', attrs={'loading': 'lazy'})
        all_images = soup.find_all('img')
        lazy_loading_ratio = len(lazy_images) / len(all_images) if all_images else 0
        
        return {
            'external_scripts_count': len(external_scripts),
            'external_stylesheets_count': len(external_stylesheets),
            'inline_style_count': inline_style_count,
            'lazy_loading_images': len(lazy_images),
            'total_images': len(all_images),
            'lazy_loading_ratio': lazy_loading_ratio
        }
    
    def _analyze_accessibility(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """アクセシビリティの分析"""
        # 画像のalt属性
        images = soup.find_all('img')
        images_with_alt = [img for img in images if img.get('alt')]
        images_without_alt = [img for img in images if not img.get('alt')]
        
        # 空のalt属性（装飾画像用）
        images_with_empty_alt = [img for img in images if img.get('alt') == '']
        
        # リンクのテキスト
        links = soup.find_all('a', href=True)
        links_with_text = [link for link in links if link.get_text().strip()]
        links_without_text = [link for link in links if not link.get_text().strip()]
        
        # フォームのラベル
        inputs = soup.find_all(['input', 'textarea', 'select'])
        labels = soup.find_all('label')
        labeled_inputs = 0
        for input_tag in inputs:
            input_id = input_tag.get('id')
            if input_id:
                if soup.find('label', attrs={'for': input_id}):
                    labeled_inputs += 1
        
        return {
            'total_images': len(images),
            'images_with_alt': len(images_with_alt),
            'images_without_alt': len(images_without_alt),
            'images_with_empty_alt': len(images_with_empty_alt),
            'alt_coverage': len(images_with_alt) / len(images) if images else 0,
            'total_links': len(links),
            'links_with_text': len(links_with_text),
            'links_without_text': len(links_without_text),
            'total_inputs': len(inputs),
            'labeled_inputs': labeled_inputs,
            'label_coverage': labeled_inputs / len(inputs) if inputs else 0
        }
    
    def _analyze_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """構造化データの分析"""
        structured_data = []
        
        # JSON-LD
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                structured_data.append({
                    'type': 'json-ld',
                    'data': data
                })
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # マイクロデータ
        microdata_items = soup.find_all(attrs={'itemscope': True})
        microdata_types = []
        for item in microdata_items:
            itemtype = item.get('itemtype', '')
            if itemtype:
                microdata_types.append(itemtype)
        
        # RDFa
        rdfa_types = []
        for elem in soup.find_all(attrs={'typeof': True}):
            typeof = elem.get('typeof', '')
            if typeof:
                rdfa_types.append(typeof)
        
        return {
            'json_ld_count': len(json_ld_scripts),
            'json_ld_data': structured_data,
            'microdata_count': len(microdata_items),
            'microdata_types': list(set(microdata_types)),
            'rdfa_count': len(rdfa_types),
            'rdfa_types': list(set(rdfa_types)),
            'has_structured_data': len(structured_data) > 0 or len(microdata_items) > 0 or len(rdfa_types) > 0
        }
    
    def _analyze_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """リンクの分析"""
        links = soup.find_all('a', href=True)
        
        internal_links = []
        external_links = []
        nofollow_links = []
        
        base_domain = urlparse(base_url).netloc
        
        for link in links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            
            if not href:
                continue
            
            # 絶対URLに変換
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            
            is_nofollow = 'nofollow' in rel
            is_external = parsed.netloc and parsed.netloc != base_domain
            
            link_info = {
                'href': href,
                'absolute_url': absolute_url,
                'text': link.get_text().strip(),
                'is_external': is_external,
                'is_nofollow': is_nofollow
            }
            
            if is_nofollow:
                nofollow_links.append(link_info)
            
            if is_external:
                external_links.append(link_info)
            else:
                internal_links.append(link_info)
        
        return {
            'total_links': len(links),
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'nofollow_links': len(nofollow_links),
            'internal_links_list': internal_links[:10],  # 最初の10件
            'external_links_list': external_links[:10]
        }
    
    def _analyze_images(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """画像の分析"""
        images = soup.find_all('img')
        
        image_info = []
        for img in images:
            src = img.get('src', '') or img.get('data-src', '')
            alt = img.get('alt', '')
            width = img.get('width', '')
            height = img.get('height', '')
            loading = img.get('loading', '')
            
            image_info.append({
                'src': src,
                'alt': alt,
                'has_alt': bool(alt),
                'width': width,
                'height': height,
                'has_dimensions': bool(width and height),
                'loading': loading,
                'is_lazy': loading == 'lazy'
            })
        
        return {
            'total_images': len(images),
            'images_with_alt': sum(1 for img in image_info if img['has_alt']),
            'images_without_alt': sum(1 for img in image_info if not img['has_alt']),
            'images_with_dimensions': sum(1 for img in image_info if img['has_dimensions']),
            'lazy_loaded_images': sum(1 for img in image_info if img['is_lazy']),
            'image_details': image_info[:20]  # 最初の20件
        }
    
    def _analyze_css(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """CSSの分析"""
        # 外部CSS
        external_css = []
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if href:
                absolute_url = urljoin(base_url, href)
                external_css.append({
                    'href': href,
                    'absolute_url': absolute_url,
                    'media': link.get('media', 'all')
                })
        
        # インラインCSS
        style_tags = soup.find_all('style')
        inline_css_count = len(style_tags)
        inline_css_size = sum(len(tag.string or '') for tag in style_tags)
        
        # インラインスタイル属性
        elements_with_style = soup.find_all(attrs={'style': True})
        inline_style_count = len(elements_with_style)
        
        return {
            'external_css_count': len(external_css),
            'external_css': external_css,
            'inline_css_count': inline_css_count,
            'inline_css_size': inline_css_size,
            'inline_style_count': inline_style_count,
            'css_optimization_score': self._calculate_css_score(external_css, inline_css_count, inline_style_count)
        }
    
    def _calculate_css_score(self, external_css: List[Dict], inline_css_count: int, inline_style_count: int) -> float:
        """CSS最適化スコアを計算（0-100）"""
        score = 100
        
        # 外部CSSが多すぎる場合は減点
        if len(external_css) > 5:
            score -= min(20, (len(external_css) - 5) * 2)
        
        # インラインCSSが多い場合は減点
        if inline_css_count > 3:
            score -= min(20, (inline_css_count - 3) * 5)
        
        # インラインスタイルが多い場合は減点
        if inline_style_count > 50:
            score -= min(30, (inline_style_count - 50) * 0.3)
        
        return max(0, score)
    
    def generate_seo_report(self, url: str) -> str:
        """
        SEO分析レポートを生成（テキスト形式）
        
        Args:
            url (str): 分析するURL
            
        Returns:
            str: レポートテキスト
        """
        analysis = self.analyze_page(url)
        
        if 'error' in analysis:
            return f"エラー: {analysis['error']}"
        
        report_lines = []
        report_lines.append(f"=== SEO分析レポート ===")
        report_lines.append(f"URL: {url}")
        report_lines.append(f"分析日時: {analysis['timestamp']}")
        report_lines.append("")
        
        # 基本SEO
        basic = analysis['basic']
        report_lines.append("【基本SEO要素】")
        report_lines.append(f"タイトル: {basic['title']}")
        report_lines.append(f"タイトル長: {basic['title_length']}文字 ({'✓' if basic['title_optimal'] else '✗'} 最適)")
        report_lines.append(f"ディスクリプション: {basic['description'][:100]}...")
        report_lines.append(f"ディスクリプション長: {basic['description_length']}文字 ({'✓' if basic['description_optimal'] else '✗'} 最適)")
        report_lines.append("")
        
        # コンテンツ
        content = analysis['content']
        report_lines.append("【コンテンツ構造】")
        report_lines.append(f"H1数: {content['h1_count']} ({'✓' if content['h1_optimal'] else '✗'} 理想的には1つ)")
        report_lines.append(f"H2数: {content['h2_count']}")
        report_lines.append(f"文字数: {content['char_count']:,}")
        report_lines.append(f"語数: {content['word_count']:,}")
        report_lines.append("")
        
        # アクセシビリティ
        accessibility = analysis['accessibility']
        report_lines.append("【アクセシビリティ】")
        report_lines.append(f"画像alt属性カバレッジ: {accessibility['alt_coverage']:.1%}")
        report_lines.append(f"alt属性なし画像: {accessibility['images_without_alt']}件")
        report_lines.append("")
        
        # 構造化データ
        structured = analysis['structured_data']
        report_lines.append("【構造化データ】")
        report_lines.append(f"JSON-LD: {structured['json_ld_count']}件")
        report_lines.append(f"マイクロデータ: {structured['microdata_count']}件")
        report_lines.append("")
        
        # リンク
        links = analysis['links']
        report_lines.append("【リンク】")
        report_lines.append(f"内部リンク: {links['internal_links']}件")
        report_lines.append(f"外部リンク: {links['external_links']}件")
        report_lines.append("")
        
        return "\n".join(report_lines)

