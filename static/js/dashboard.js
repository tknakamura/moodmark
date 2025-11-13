// MOO:D MARK IDEA 商品推奨ダッシュボード JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // DOM要素の取得
    const form = document.getElementById('recommendationForm');
    const loadingArea = document.getElementById('loadingArea');
    const errorArea = document.getElementById('errorArea');
    const recommendationsArea = document.getElementById('recommendationsArea');
    const resultCount = document.getElementById('resultCount');
    const submitBtn = document.getElementById('submitBtn');
    const loadSampleBtn = document.getElementById('loadSampleBtn');
    
    // システム状況の更新
    updateSystemStatus();
    
    // フォーム送信イベント
    form.addEventListener('submit', handleFormSubmit);
    
    // サンプルデータ読み込みイベント
    loadSampleBtn.addEventListener('click', loadSampleData);
    
    // システム状況を更新する関数
    async function updateSystemStatus() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            const engineStatus = document.getElementById('engineStatus');
            const dataStatus = document.getElementById('dataStatus');
            
            if (data.engine_initialized) {
                engineStatus.textContent = '正常';
                engineStatus.className = 'badge bg-success';
            } else {
                engineStatus.textContent = '異常';
                engineStatus.className = 'badge bg-danger';
            }
            
            if (data.data_processor_initialized) {
                dataStatus.textContent = '正常';
                dataStatus.className = 'badge bg-success';
            } else {
                dataStatus.textContent = '異常';
                dataStatus.className = 'badge bg-danger';
            }
        } catch (error) {
            console.error('システム状況の取得に失敗:', error);
        }
    }
    
    // フォーム送信処理
    async function handleFormSubmit(event) {
        event.preventDefault();
        
        // 入力値の取得
        const articleUrl = document.getElementById('articleUrl').value.trim();
        const targetKeywords = document.getElementById('targetKeywords').value.trim();
        const persona = document.getElementById('persona').value;
        const numRecommendations = document.getElementById('numRecommendations').value;
        
        // バリデーション
        if (!articleUrl || !targetKeywords || !persona) {
            showError('すべての必須項目を入力してください。');
            return;
        }
        
        // キーワードの配列化
        const keywords = targetKeywords.split(',').map(k => k.trim()).filter(k => k);
        
        if (keywords.length === 0) {
            showError('有効なキーワードを入力してください。');
            return;
        }
        
        // ローディング表示
        showLoading();
        
        try {
            // API呼び出し
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    article_url: articleUrl,
                    target_keywords: keywords,
                    persona: persona,
                    num_recommendations: parseInt(numRecommendations)
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '推奨の取得に失敗しました。');
            }
            
            // 結果の表示
            displayRecommendations(data);
            
        } catch (error) {
            console.error('推奨取得エラー:', error);
            showError(error.message);
        }
    }
    
    // ローディング表示
    function showLoading() {
        loadingArea.style.display = 'block';
        errorArea.style.display = 'none';
        recommendationsArea.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>分析中...';
    }
    
    // エラー表示
    function showError(message) {
        loadingArea.style.display = 'none';
        recommendationsArea.style.display = 'none';
        errorArea.style.display = 'block';
        document.getElementById('errorMessage').textContent = message;
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-magic me-2"></i>商品を提案する';
    }
    
    // 推奨結果の表示
    function displayRecommendations(data) {
        loadingArea.style.display = 'none';
        errorArea.style.display = 'none';
        recommendationsArea.style.display = 'block';
        
        const recommendations = data.recommendations || [];
        
        if (recommendations.length === 0) {
            recommendationsArea.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3 opacity-25"></i>
                    <p>推奨商品が見つかりませんでした。</p>
                    <p>入力条件を変更してお試しください。</p>
                </div>
            `;
            resultCount.style.display = 'none';
        } else {
            // 結果カウントの更新
            resultCount.textContent = `${recommendations.length}件`;
            resultCount.style.display = 'inline-block';
            
            // 推奨商品の表示
            const recommendationsHTML = recommendations.map((rec, index) => 
                createRecommendationCard(rec, index + 1)
            ).join('');
            
            recommendationsArea.innerHTML = `
                <div class="fade-in">
                    ${recommendationsHTML}
                </div>
            `;
        }
        
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-magic me-2"></i>商品を提案する';
    }
    
    // 推奨商品カードの作成
    function createRecommendationCard(recommendation, index) {
        const confidenceClass = getConfidenceClass(recommendation.confidence);
        const confidenceText = getConfidenceText(recommendation.confidence);
        
        return `
            <div class="recommendation-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-0">
                            <span class="badge bg-primary me-2">${index}</span>
                            ${recommendation.product_name}
                        </h6>
                        <small class="text-muted">${recommendation.product_id}</small>
                    </div>
                    <div class="text-end">
                        <div class="score-badge badge ${confidenceClass} mb-1">
                            信頼度: ${(recommendation.confidence * 100).toFixed(1)}%
                        </div>
                        <div class="price-badge">
                            ¥${recommendation.price.toLocaleString()}
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    <!-- キャッチコピー -->
                    <div class="catch-copy">
                        <i class="fas fa-quote-left me-2"></i>
                        ${recommendation.catch_copy}
                    </div>
                    
                    <!-- ボディコピー -->
                    <div class="body-copy">
                        ${recommendation.body_copy}
                    </div>
                    
                    <!-- 推奨理由 -->
                    <div class="recommendation-reasons">
                        <h6 class="mb-2">
                            <i class="fas fa-lightbulb me-1"></i>
                            推奨理由
                        </h6>
                        <div>
                            ${recommendation.recommendation_reasons.map(reason => 
                                `<span class="reason-tag">${reason}</span>`
                            ).join('')}
                        </div>
                    </div>
                    
                    <!-- 商品URL -->
                    <div class="product-url">
                        <a href="${recommendation.product_url}" target="_blank" class="btn btn-outline-primary btn-sm">
                            <i class="fas fa-external-link-alt me-1"></i>
                            商品ページを見る
                        </a>
                    </div>
                </div>
            </div>
        `;
    }
    
    // 信頼度に基づくクラスの取得
    function getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'bg-success';
        if (confidence >= 0.6) return 'bg-warning';
        return 'bg-danger';
    }
    
    // 信頼度に基づくテキストの取得
    function getConfidenceText(confidence) {
        if (confidence >= 0.8) return '高信頼度';
        if (confidence >= 0.6) return '中信頼度';
        return '低信頼度';
    }
    
    // サンプルデータの読み込み
    function loadSampleData() {
        document.getElementById('articleUrl').value = 'https://example.com/birthday-gifts-for-boyfriend';
        document.getElementById('targetKeywords').value = '彼氏,誕生日プレゼント,男性ギフト,20代男性';
        document.getElementById('persona').value = '20代女性';
        document.getElementById('numRecommendations').value = '5';
        
        // フォーカスを移動
        document.getElementById('submitBtn').focus();
    }
    
    // 定期的なシステム状況更新
    setInterval(updateSystemStatus, 30000); // 30秒ごと
    
    // キーボードショートカット
    document.addEventListener('keydown', function(event) {
        // Ctrl + Enter でフォーム送信
        if (event.ctrlKey && event.key === 'Enter') {
            if (!submitBtn.disabled) {
                form.dispatchEvent(new Event('submit'));
            }
        }
        
        // Ctrl + S でサンプルデータ読み込み
        if (event.ctrlKey && event.key === 's') {
            event.preventDefault();
            loadSampleData();
        }
    });
    
    // フォームの入力検証
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('input', function() {
            // リアルタイムバリデーション
            validateForm();
        });
    });
    
    // フォーム検証
    function validateForm() {
        const articleUrl = document.getElementById('articleUrl').value.trim();
        const targetKeywords = document.getElementById('targetKeywords').value.trim();
        const persona = document.getElementById('persona').value;
        
        const isValid = articleUrl && targetKeywords && persona;
        
        submitBtn.disabled = !isValid;
        
        if (isValid) {
            submitBtn.classList.remove('btn-secondary');
            submitBtn.classList.add('btn-primary');
        } else {
            submitBtn.classList.remove('btn-primary');
            submitBtn.classList.add('btn-secondary');
        }
    }
    
    // 初期検証
    validateForm();
    
    // コピー機能の追加
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('copy-btn')) {
            const text = event.target.getAttribute('data-copy');
            navigator.clipboard.writeText(text).then(() => {
                // 一時的にボタンテキストを変更
                const originalText = event.target.innerHTML;
                event.target.innerHTML = '<i class="fas fa-check me-1"></i>コピー完了';
                event.target.classList.add('btn-success');
                event.target.classList.remove('btn-outline-secondary');
                
                setTimeout(() => {
                    event.target.innerHTML = originalText;
                    event.target.classList.remove('btn-success');
                    event.target.classList.add('btn-outline-secondary');
                }, 2000);
            });
        }
    });
});










