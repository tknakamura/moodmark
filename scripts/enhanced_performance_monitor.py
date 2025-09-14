#!/usr/bin/env python3
"""
強化版パフォーマンス監視スクリプト
"""

import requests
import time
import json
from datetime import datetime
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class EnhancedPerformanceMonitor:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        
        # リトライ戦略の設定
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # ヘッダーの設定
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def measure_page_performance(self, url):
        """ページのパフォーマンスを詳細測定"""
        start_time = time.time()
        
        try:
            print(f"測定開始: {url}")
            
            # タイムアウト設定
            response = self.session.get(url, timeout=30)
            end_time = time.time()
            
            load_time = end_time - start_time
            
            # レスポンスヘッダーから詳細情報を取得
            response_headers = dict(response.headers)
            
            result = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'load_time': round(load_time, 3),
                'status_code': response.status_code,
                'content_length': len(response.content),
                'response_time': round(load_time, 3),
                'server': response_headers.get('Server', 'Unknown'),
                'content_type': response_headers.get('Content-Type', 'Unknown'),
                'cache_control': response_headers.get('Cache-Control', 'Unknown'),
                'last_modified': response_headers.get('Last-Modified', 'Unknown'),
                'etag': response_headers.get('ETag', 'Unknown'),
                'error': None
            }
            
            print(f"✅ 成功: {url} - {load_time:.3f}秒")
            return result
            
        except requests.exceptions.Timeout:
            end_time = time.time()
            load_time = end_time - start_time
            result = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'load_time': None,
                'status_code': None,
                'content_length': None,
                'response_time': round(load_time, 3),
                'error': 'Timeout (30秒)'
            }
            print(f"⏰ タイムアウト: {url}")
            return result
            
        except requests.exceptions.ConnectionError as e:
            end_time = time.time()
            load_time = end_time - start_time
            result = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'load_time': None,
                'status_code': None,
                'content_length': None,
                'response_time': round(load_time, 3),
                'error': f'Connection Error: {str(e)[:100]}'
            }
            print(f"🔌 接続エラー: {url}")
            return result
            
        except requests.exceptions.HTTPError as e:
            end_time = time.time()
            load_time = end_time - start_time
            result = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'load_time': None,
                'status_code': e.response.status_code if e.response else None,
                'content_length': None,
                'response_time': round(load_time, 3),
                'error': f'HTTP Error: {str(e)[:100]}'
            }
            print(f"🚫 HTTPエラー: {url}")
            return result
            
        except Exception as e:
            end_time = time.time()
            load_time = end_time - start_time
            result = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'load_time': None,
                'status_code': None,
                'content_length': None,
                'response_time': round(load_time, 3),
                'error': f'Unexpected Error: {str(e)[:100]}'
            }
            print(f"❌ 予期しないエラー: {url}")
            return result
    
    def run_monitoring(self, urls, interval=300):
        """継続的な監視を実行"""
        while True:
            for url in urls:
                result = self.measure_page_performance(url)
                self.results.append(result)
                time.sleep(2)  # リクエスト間隔を空ける
            
            time.sleep(interval)

def main():
    monitor = EnhancedPerformanceMonitor()
    
    urls = [
        "https://isetan.mistore.jp/moodmarkgift/",
        "https://isetan.mistore.jp/moodmark/"
    ]
    
    print("=== パフォーマンス監視開始 ===")
    print()
    
    # 一度だけ実行
    for url in urls:
        result = monitor.measure_page_performance(url)
        monitor.results.append(result)
        time.sleep(2)  # リクエスト間隔を空ける
    
    print()
    print("=== 監視結果サマリー ===")
    
    # 結果をCSVに保存
    df = pd.DataFrame(monitor.results)
    df.to_csv('enhanced_performance_monitoring.csv', index=False, encoding='utf-8')
    
    # 結果サマリーを表示
    for idx, row in df.iterrows():
        print(f"【{row['url'].split('/')[-2]}】")
        if row['error']:
            print(f"❌ エラー: {row['error']}")
        else:
            print(f"✅ 読み込み時間: {row['load_time']}秒")
            print(f"📊 ステータス: {row['status_code']}")
            print(f"📦 コンテンツサイズ: {row['content_length']:,}バイト")
            print(f"🖥️ サーバー: {row.get('server', 'Unknown')}")
        print("-" * 40)
    
    print(f"\n詳細結果を enhanced_performance_monitoring.csv に保存しました。")

if __name__ == "__main__":
    main()
