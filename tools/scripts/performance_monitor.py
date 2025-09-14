#!/usr/bin/env python3
"""
パフォーマンス監視スクリプト
"""

import requests
import time
import json
from datetime import datetime
import pandas as pd

class PerformanceMonitor:
    def __init__(self):
        self.results = []
    
    def measure_page_performance(self, url):
        """ページのパフォーマンスを測定"""
        start_time = time.time()
        
        try:
            response = requests.get(url)
            end_time = time.time()
            
            load_time = end_time - start_time
            
            return {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'load_time': load_time,
                'status_code': response.status_code,
                'content_length': len(response.content),
                'response_headers': dict(response.headers)
            }
            
        except Exception as e:
            return {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'load_time': None
            }
    
    def run_monitoring(self, urls, interval=300):
        """継続的な監視を実行"""
        while True:
            for url in urls:
                result = self.measure_page_performance(url)
                self.results.append(result)
                print(f"Measured {url}: {result.get('load_time', 'error')}s")
            
            time.sleep(interval)

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    
    urls = [
        "https://isetan.mistore.jp/moodmarkgift/",
        "https://isetan.mistore.jp/moodmark/"
    ]
    
    # 一度だけ実行
    for url in urls:
        result = monitor.measure_page_performance(url)
        monitor.results.append(result)
        print(f"Performance: {url} - {result.get('load_time', 'error')}s")
    
    # 結果をCSVに保存
    df = pd.DataFrame(monitor.results)
    df.to_csv('performance_monitoring.csv', index=False, encoding='utf-8')
    print("Performance monitoring results saved to performance_monitoring.csv")
