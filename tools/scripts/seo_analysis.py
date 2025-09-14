#!/usr/bin/env python3
"""
SEO分析スクリプト
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import time

class SEOAnalyzer:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def analyze_page(self, url):
        """ページのSEO分析を実行"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # メタデータの取得
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            meta_description = soup.find('meta', attrs={'name': 'description'})
            description = meta_description.get('content', '') if meta_description else ""
            
            # 見出しタグの分析
            headings = {
                'h1': [h.get_text().strip() for h in soup.find_all('h1')],
                'h2': [h.get_text().strip() for h in soup.find_all('h2')],
                'h3': [h.get_text().strip() for h in soup.find_all('h3')]
            }
            
            # 画像のalt属性チェック
            images = soup.find_all('img')
            images_without_alt = [img for img in images if not img.get('alt')]
            
            return {
                'url': url,
                'title': title_text,
                'description': description,
                'headings': headings,
                'images_without_alt': len(images_without_alt),
                'total_images': len(images),
                'status_code': response.status_code
            }
            
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'status_code': None
            }

if __name__ == "__main__":
    analyzer = SEOAnalyzer("https://isetan.mistore.jp/moodmarkgift/")
    
    # 分析対象URLのリスト
    urls = [
        "https://isetan.mistore.jp/moodmarkgift/",
        "https://isetan.mistore.jp/moodmark/"
    ]
    
    results = []
    for url in urls:
        print(f"Analyzing: {url}")
        result = analyzer.analyze_page(url)
        results.append(result)
        time.sleep(1)  # リクエスト間隔を空ける
    
    # 結果をDataFrameに変換
    df = pd.DataFrame(results)
    print(df)
    
    # CSVファイルに保存
    df.to_csv('seo_analysis_results.csv', index=False, encoding='utf-8')
    print("Analysis results saved to seo_analysis_results.csv")
