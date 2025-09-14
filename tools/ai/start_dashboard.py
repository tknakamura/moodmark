#!/usr/bin/env python3
"""
MOO:D MARK IDEA 商品推奨ダッシュボード 起動スクリプト

ダッシュボードの起動と初期設定を行うスクリプト
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """依存関係のチェック"""
    print("📦 依存関係をチェック中...")
    
    required_packages = [
        'flask',
        'pandas',
        'numpy',
        'scikit-learn',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️  不足しているパッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ すべての依存関係が満たされています")
    return True

def setup_directories():
    """必要なディレクトリの作成"""
    print("\n📁 ディレクトリをセットアップ中...")
    
    directories = [
        'templates',
        'static/css',
        'static/js',
        'data/processed'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")

def check_data_files():
    """データファイルのチェック"""
    print("\n📊 データファイルをチェック中...")
    
    data_files = [
        'data/processed/articles.json',
        'data/processed/products.json'
    ]
    
    data_available = True
    
    for file_path in data_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ⚠️  {file_path} (サンプルデータで動作)")
            data_available = False
    
    if not data_available:
        print("\n💡 実際のデータファイルが見つかりません。")
        print("   サンプルデータでダッシュボードが起動します。")
        print("   本格運用時は、データファイルを準備してください。")
    
    return True

def start_dashboard():
    """ダッシュボードの起動"""
    print("\n🚀 ダッシュボードを起動中...")
    
    # ダッシュボードスクリプトのパス
    dashboard_script = Path(__file__).parent / 'product_dashboard.py'
    
    if not dashboard_script.exists():
        print(f"❌ ダッシュボードスクリプトが見つかりません: {dashboard_script}")
        return False
    
    try:
        # ダッシュボードを起動
        print("  🌐 ダッシュボードサーバーを起動中...")
        print("  📍 URL: http://localhost:5001")
        print("  ⏹️  停止: Ctrl+C")
        print("\n" + "="*50)
        
        # 少し待ってからブラウザを開く
        def open_browser():
            time.sleep(2)
            try:
                webbrowser.open('http://localhost:5001')
                print("🌐 ブラウザでダッシュボードを開きました")
            except Exception as e:
                print(f"⚠️  ブラウザの自動起動に失敗: {e}")
                print("手動で http://localhost:5001 にアクセスしてください")
        
        import threading
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
        
        # ダッシュボードを実行
        subprocess.run([sys.executable, str(dashboard_script)])
        
    except KeyboardInterrupt:
        print("\n\n⏹️  ダッシュボードを停止しました")
    except Exception as e:
        print(f"❌ ダッシュボードの起動に失敗: {e}")
        return False
    
    return True

def main():
    """メイン関数"""
    print("="*60)
    print("🎯 MOO:D MARK IDEA 商品推奨ダッシュボード")
    print("="*60)
    
    # 依存関係のチェック
    if not check_dependencies():
        print("\n❌ 依存関係のインストールが必要です")
        sys.exit(1)
    
    # ディレクトリのセットアップ
    setup_directories()
    
    # データファイルのチェック
    check_data_files()
    
    print("\n✅ セットアップが完了しました")
    
    # ダッシュボードの起動
    if not start_dashboard():
        print("\n❌ ダッシュボードの起動に失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    main()
