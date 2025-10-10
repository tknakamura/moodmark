#!/usr/bin/env python3
"""
MOO:D MARK IDEA 商品推奨ダッシュボード（シンプル版）

軽量で動作するシンプルなダッシュボード
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
import json
from datetime import datetime
import random
import os

app = Flask(__name__)

# 静的ファイルのルーティング
@app.route('/static/<path:filename>')
def static_files(filename):
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    return send_from_directory(static_dir, filename)

# サンプル商品データ
SAMPLE_PRODUCTS = [
    {
        "id": "001",
        "name": "高級革財布 ブラック",
        "price": 8000,
        "category": "ファッション",
        "tags": ["革", "財布", "高級", "男性"],
        "description": "職人が手作りした本革の財布。長く使える高品質なアイテム。"
    },
    {
        "id": "002", 
        "name": "クリスマス限定 スイーツギフトセット",
        "price": 3500,
        "category": "食品",
        "tags": ["スイーツ", "クリスマス", "限定", "家族"],
        "description": "クリスマス限定の特別なスイーツギフトセット。"
    },
    {
        "id": "003",
        "name": "母の日特別 花束アレンジメント", 
        "price": 4500,
        "category": "花・植物",
        "tags": ["花束", "母の日", "感謝", "春"],
        "description": "母の日にぴったりの美しい花束アレンジメント。"
    },
    {
        "id": "004",
        "name": "高級腕時計 シンプルデザイン",
        "price": 25000,
        "category": "アクセサリー", 
        "tags": ["腕時計", "高級", "シンプル", "男性"],
        "description": "シンプルで上品なデザインの高級腕時計。"
    },
    {
        "id": "005",
        "name": "季節のフルーツギフト",
        "price": 2800,
        "category": "食品",
        "tags": ["フルーツ", "季節", "新鮮", "健康"],
        "description": "旬の美味しいフルーツを厳選したギフト。"
    }
]

# HTMLテンプレート
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>MOO:D MARK IDEA 商品推奨ダッシュボード</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="alternate icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='16' fill='%23ff322d'/><circle cx='12' cy='12' r='2' fill='white'/><circle cx='20' cy='12' r='2' fill='white'/><path d='M12 22C14 24 16 25 18 25C20 25 22 24 24 22' stroke='white' stroke-width='3' stroke-linecap='round'/></svg>">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .hero { background: linear-gradient(135deg, #ff322d, #d42823); color: white; padding: 2rem 0; }
        .card { border: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 1rem; }
        .product-card { border-left: 4px solid #ff322d; }
        .catch-copy { background: #fff5f5; padding: 1rem; border-radius: 8px; font-weight: 600; color: #ff322d; }
        .body-copy { background: #fff5f5; padding: 1rem; border-radius: 8px; white-space: pre-line; }
        .reason-tag { background: #ff322d; color: white; padding: 0.25rem 0.5rem; border-radius: 15px; font-size: 0.8rem; margin: 0.2rem; }
        .btn-primary:hover { background-color: #d42823 !important; border-color: #d42823 !important; }
        .btn-outline-secondary:hover { background-color: #ff322d !important; border-color: #ff322d !important; color: white !important; }
    </style>
</head>
<body>
    <div class="hero text-center">
        <h1><i class="fas fa-gift"></i> MOO:D MARK IDEA 商品推奨ダッシュボード</h1>
        <p>記事に最適な商品をAIが自動提案</p>
    </div>

    <div class="container mt-4">
        <div class="row">
            <!-- 入力フォーム -->
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-light">
                        <h5><i class="fas fa-edit"></i> 入力情報</h5>
                    </div>
                    <div class="card-body">
                        <form id="form">
                            <div class="mb-3">
                                <label class="form-label">記事のURL</label>
                                <input type="url" class="form-control" id="url" placeholder="https://example.com/article" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">ターゲットキーワード</label>
                                <textarea class="form-control" id="keywords" rows="3" placeholder="彼氏,誕生日プレゼント,男性ギフト,20代男性" required></textarea>
                                <small class="text-muted">
                                    <i class="fas fa-info-circle"></i> 複数のキーワードは <strong>カンマ（,）</strong> で区切って入力してください<br>
                                    例: 彼氏,誕生日プレゼント,男性ギフト,20代男性
                                </small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">ペルソナ</label>
                                <select class="form-select" id="persona" onchange="togglePersonaInput()">
                                    <option value="">選択してください</option>
                                    <option value="20代女性">20代女性</option>
                                    <option value="30代女性">30代女性</option>
                                    <option value="20代男性">20代男性</option>
                                    <option value="30代男性">30代男性</option>
                                    <option value="40代女性">40代女性</option>
                                    <option value="40代男性">40代男性</option>
                                    <option value="custom">カスタム（フリーテキスト）</option>
                                </select>
                                <input type="text" class="form-control mt-2" id="personaCustom" placeholder="例: 30代のビジネスパーソン、大学生、子育て中の母親" style="display:none;">
                                <small class="text-muted">カスタムを選択するとフリーテキスト入力ができます</small>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">提案商品数</label>
                                <input type="number" class="form-control" id="count" value="5" min="1" max="20" placeholder="1-20の範囲で入力">
                                <small class="text-muted">1-20件の範囲で入力してください</small>
                            </div>
                            <button type="submit" class="btn btn-primary w-100" style="background-color: #ff322d; border-color: #ff322d;">
                                <i class="fas fa-magic"></i> 商品を提案する
                            </button>
                            <button type="button" class="btn btn-outline-secondary w-100 mt-2" onclick="loadSample()" style="border-color: #ff322d; color: #ff322d;">
                                <i class="fas fa-flask"></i> サンプルデータ
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- 推奨結果 -->
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-light">
                        <h5><i class="fas fa-star"></i> 推奨商品</h5>
                    </div>
                    <div class="card-body">
                        <div id="loading" style="display:none;" class="text-center py-4">
                            <div class="spinner-border text-primary"></div>
                            <p>商品を分析中...</p>
                        </div>
                        <div id="error" style="display:none;" class="alert alert-danger"></div>
                        <div id="results"></div>
                        <div id="empty" class="text-center text-muted py-5">
                            <i class="fas fa-gift fa-3x mb-3"></i>
                            <p>入力情報を入力して「商品を提案する」ボタンをクリックしてください</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/js/all.min.js"></script>
    <script>
        function togglePersonaInput() {
            const select = document.getElementById('persona');
            const customInput = document.getElementById('personaCustom');
            
            if (select.value === 'custom') {
                customInput.style.display = 'block';
                customInput.required = true;
            } else {
                customInput.style.display = 'none';
                customInput.required = false;
            }
        }
        
        function getPersonaValue() {
            const select = document.getElementById('persona');
            const customInput = document.getElementById('personaCustom');
            
            if (select.value === 'custom') {
                return customInput.value.trim();
            }
            return select.value;
        }
        
        document.getElementById('form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const url = document.getElementById('url').value;
            const keywordsText = document.getElementById('keywords').value.trim();
            const keywords = keywordsText.split(',').map(k => k.trim()).filter(k => k.length > 0);
            const persona = getPersonaValue();
            const count = parseInt(document.getElementById('count').value);
            
            if (!url || !keywordsText || !persona) {
                showError('すべての項目を入力してください');
                return;
            }
            
            if (keywords.length === 0) {
                showError('キーワードが正しく入力されていません。カンマ区切りで複数のキーワードを入力してください。');
                return;
            }
            
            if (count < 1 || count > 20) {
                showError('提案商品数は1-20の範囲で入力してください');
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch('/api/recommend', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url, keywords, persona, count})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showResults(data.recommendations);
                } else {
                    showError(data.error || 'エラーが発生しました');
                }
            } catch (error) {
                showError('サーバーエラーが発生しました');
            }
        });
        
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('error').style.display = 'none';
            document.getElementById('results').innerHTML = '';
            document.getElementById('empty').style.display = 'none';
        }
        
        function showError(message) {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = 'block';
            document.getElementById('error').textContent = message;
            document.getElementById('results').innerHTML = '';
            document.getElementById('empty').style.display = 'none';
        }
        
        function showResults(recommendations) {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            document.getElementById('empty').style.display = 'none';
            
            const html = recommendations.map((rec, i) => `
                <div class="card product-card mb-3">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6><span class="badge bg-primary">${i+1}</span> ${rec.product_name}</h6>
                            <div class="text-end">
                                <div class="badge bg-success mb-1">信頼度: ${Math.round(rec.confidence * 100)}%</div>
                                <div class="fw-bold text-danger">¥${rec.price.toLocaleString()}</div>
                            </div>
                        </div>
                        
                        <div class="catch-copy mb-3">
                            <i class="fas fa-quote-left"></i> ${rec.catch_copy}
                        </div>
                        
                        <div class="body-copy mb-3">${rec.body_copy}</div>
                        
                        <div class="mb-3">
                            <strong>推奨理由:</strong><br>
                            ${rec.reasons.map(r => `<span class="reason-tag">${r}</span>`).join('')}
                        </div>
                        
                        <a href="${rec.product_url}" target="_blank" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-external-link-alt"></i> 商品ページを見る
                        </a>
                    </div>
                </div>
            `).join('');
            
            document.getElementById('results').innerHTML = html;
        }
        
        function loadSample() {
            document.getElementById('url').value = 'https://example.com/birthday-gifts-for-boyfriend';
            document.getElementById('keywords').value = '彼氏,誕生日プレゼント,男性ギフト,20代男性';
            document.getElementById('persona').value = '20代女性';
            document.getElementById('personaCustom').style.display = 'none';
            document.getElementById('count').value = '5';
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        
        url = data.get('url', '')
        keywords = data.get('keywords', [])
        persona = data.get('persona', '')
        count = data.get('count', 5)
        
        # 簡単なマッチングロジック
        matches = []
        for product in SAMPLE_PRODUCTS:
            score = 0
            reasons = []
            
            # キーワードマッチング
            for keyword in keywords:
                if any(keyword.lower() in tag.lower() for tag in product['tags']):
                    score += 0.4
                    reasons.append('キーワード一致')
                    break
            
            # ペルソナマッチング（改善版）
            persona_lower = persona.lower()
            
            # 年齢・性別マッチング
            if '男性' in persona_lower and any('男性' in tag for tag in product['tags']):
                score += 0.3
                reasons.append('ペルソナ一致')
            elif '女性' in persona_lower and any(tag in ['スイーツ', '花束', '可愛い'] for tag in product['tags']):
                score += 0.3
                reasons.append('ペルソナ一致')
            
            # カスタムペルソナのキーワードマッチング
            if 'ビジネス' in persona_lower and any(tag in ['ビジネス', '高級', 'シンプル'] for tag in product['tags']):
                score += 0.2
                reasons.append('ビジネス向け')
            elif '学生' in persona_lower and product['price'] < 5000:
                score += 0.2
                reasons.append('学生向け価格')
            elif '子育て' in persona_lower and any(tag in ['家族', '健康', '安全'] for tag in product['tags']):
                score += 0.2
                reasons.append('家族向け')
            
            # ランダム要素
            score += random.uniform(0.1, 0.3)
            
            if score > 0.3:
                matches.append({
                    'product': product,
                    'score': score,
                    'reasons': reasons
                })
        
        # スコア順でソート
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        # 推奨結果の生成
        recommendations = []
        for i, match in enumerate(matches[:count]):
            product = match['product']
            score = match['score']
            reasons = match['reasons'] if match['reasons'] else ['おすすめ商品']
            
            # キャッチコピー生成
            if any('誕生日' in k for k in keywords):
                catch_copy = f"【{persona}必見】{product['name']}で特別な誕生日を！¥{product['price']:,}の素敵なプレゼント"
            elif any('クリスマス' in k for k in keywords):
                catch_copy = f"【クリスマス限定】{product['name']}で最高のクリスマスを！¥{product['price']:,}ギフト"
            else:
                catch_copy = f"【{persona}におすすめ】{product['name']}で特別なギフト¥{product['price']:,}"
            
            # ボディコピー生成
            body_copy = f"""{product['name']}は、{product['description']}

【{persona}におすすめの理由】
• 特別なシーンに最適
• ¥{product['price']:,}の価格で高品質な商品
• ギフト包装にも対応可能

【商品の特徴】
• 厳選された素材と丁寧な仕上げ
• 長く愛用できるデザイン
• ギフトに最適なアイテム

{persona}にぴったりの{product['name']}をお選びください。"""
            
            recommendations.append({
                'product_name': product['name'],
                'product_id': product['id'],
                'catch_copy': catch_copy,
                'body_copy': body_copy,
                'product_url': f"https://isetan.mistore.jp/moodmark/products/{product['id']}",
                'reasons': reasons,
                'confidence': min(score, 1.0),
                'price': product['price'],
                'category': product['category']
            })
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'total_count': len(recommendations)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'products_count': len(SAMPLE_PRODUCTS)
    })

if __name__ == '__main__':
    print("🚀 商品推奨ダッシュボード（シンプル版）を起動中...")
    print("📍 URL: http://localhost:5003")
    print("⏹️  停止: Ctrl+C")
    
    app.run(
        host='0.0.0.0',
        port=5003,
        debug=False,
        threaded=True
    )

