# Render.com環境変数設定手順

## 概要
Render.comで環境変数を設定する方法を説明します。

## 必要な環境変数

以下の環境変数を設定する必要があります：

1. `OPENAI_API_KEY` - OpenAI APIキー
2. `GOOGLE_CREDENTIALS_FILE` - Google認証情報ファイルのパス（通常は `config/google-credentials-474807.json`）
3. `GA4_PROPERTY_ID` - GA4プロパティID（例: `316302380`）
4. `GSC_SITE_URL` - GSCサイトURL（例: `https://isetan.mistore.jp/moodmark/`）

## 設定手順

### ステップ1: Render.comダッシュボードにアクセス

1. **ブラウザでRender.comにログイン**
   - URL: https://dashboard.render.com/
   - アカウントにログイン

2. **サービスを選択**
   - ダッシュボードから `moodmark-csv-to-html-converter` サービスをクリック

### ステップ2: 環境変数の設定

1. **左サイドバーから「Environment」をクリック**
   - または、サービスページの「Environment」タブをクリック

2. **「Add Environment Variable」ボタンをクリック**

3. **各環境変数を追加**

#### 環境変数1: OPENAI_API_KEY

- **Key**: `OPENAI_API_KEY`
- **Value**: あなたのOpenAI APIキー（例: `sk-...`）
- **重要**: APIキーは機密情報なので、他人に共有しないでください

#### 環境変数2: GOOGLE_CREDENTIALS_JSON（推奨）

- **Key**: `GOOGLE_CREDENTIALS_JSON`
- **Value**: Google認証ファイル（JSON）の内容をそのまま貼り付け
  - 認証ファイル（`config/google-credentials-474807.json`）を開く
  - ファイルの内容全体をコピー
  - 環境変数のValueに貼り付け（改行を含む完全なJSON）
  - **重要**: JSONの内容をそのまま貼り付けてください（1行にまとめる必要はありません）

**または**

#### 環境変数2: GOOGLE_CREDENTIALS_FILE（代替方法）

- **Key**: `GOOGLE_CREDENTIALS_FILE`
- **Value**: `config/google-credentials-474807.json`
- **注意**: この方法を使用する場合は、認証ファイルをリポジトリに含めるか、Render.comにアップロードする必要があります

#### 環境変数3: GA4_PROPERTY_ID

- **Key**: `GA4_PROPERTY_ID`
- **Value**: `316302380`

#### 環境変数4: GSC_SITE_URL_MOODMARK

- **Key**: `GSC_SITE_URL_MOODMARK`
- **Value**: `https://isetan.mistore.jp/moodmark/`
- **注意**: 後方互換性のため、`GSC_SITE_URL`も使用可能です（MOODMARKサイト用）

#### 環境変数5: GSC_SITE_URL_MOODMARKGIFT

- **Key**: `GSC_SITE_URL_MOODMARKGIFT`
- **Value**: `https://isetan.mistore.jp/moodmarkgift/`
- **注意**: MOODMARK GIFTサイトのデータを取得する場合は必須です

#### 環境変数6: PAGESPEED_INSIGHTS_API_KEY（オプション）

- **Key**: `PAGESPEED_INSIGHTS_API_KEY`
- **Value**: あなたのPage Speed Insights APIキー
- **注意**: この環境変数はオプションです。設定しない場合、Page Speed Insightsの分析はスキップされます
- **取得方法**:
  1. Google Cloud Consoleにアクセス
  2. プロジェクトを選択
  3. 「APIとサービス」→「ライブラリ」から「PageSpeed Insights API」を有効化
  4. 「認証情報」→「認証情報を作成」→「APIキー」を選択
  5. 作成されたAPIキーをコピー

#### 環境変数7: USE_PLAYWRIGHT（オプション、高度な機能）

**この機能について**

構造化データ（JSON-LDなど）は、HTMLに直接書かれている場合と、JavaScriptで動的に生成される場合があります。通常の解析では、HTMLに直接書かれている構造化データしか検出できません。JavaScriptで動的に生成される構造化データを検出するには、ブラウザでJavaScriptを実行する必要があります。

**設定方法**

1. **Key**: `USE_PLAYWRIGHT`
2. **Value**: `true` または `false`（デフォルト: `false`）
3. **使用する場合**: JavaScriptで動的に生成される構造化データを検出したい場合のみ `true` に設定
4. **使用しない場合**: 通常のHTML解析のみで十分な場合は設定不要（デフォルトの `false` のまま）

**設定手順（Playwrightを使用する場合）**

1. `requirements.txt`を開く
2. 以下の行のコメント（`#`）を外す：
   ```
   playwright>=1.40.0
   ```
3. Render.comの環境変数に `USE_PLAYWRIGHT=true` を追加
4. 変更をコミット・プッシュしてデプロイ
5. **デプロイが完了したことを確認**（Render.comのダッシュボードで確認）
6. Render.comのシェル（SSH）に接続し、以下を実行：
   
   **ステップ1**: Playwrightがインストールされているか確認
   ```bash
   python -m pip list | grep playwright
   ```
   
   **ステップ2**: もしPlaywrightがインストールされていない場合、手動でインストール
   ```bash
   python -m pip install playwright>=1.40.0
   ```
   
   **ステップ3**: Chromiumブラウザをインストール
   ```bash
   python -m playwright install chromium
   ```
   
   **注意**: 
   - `playwright`コマンドではなく、`python -m playwright`として実行してください
   - デプロイが完了していない場合、Playwrightがインストールされていない可能性があります
   - その場合は、ステップ2で手動インストールしてください

**注意事項**

- Playwrightを使用すると、ページ取得に時間がかかります（通常の2-3倍）
- Render.comの無料プランでは、メモリやCPUの制限があるため、エラーが発生する可能性があります
- ほとんどの場合、通常のHTML解析で十分です。JavaScriptで動的に生成される構造化データがある場合のみ使用してください

---

#### 環境変数8: USE_SELENIUM（オプション、高度な機能）

**この機能について**

USE_SELENIUMは、USE_PLAYWRIGHTの代替手段です。Playwrightが使用できない環境や、Seleniumを既に使用している場合に使用します。

**設定方法**

1. **Key**: `USE_SELENIUM`
2. **Value**: `true` または `false`（デフォルト: `false`）
3. **使用する場合**: Playwrightが使用できない場合、またはSeleniumを優先したい場合のみ `true` に設定
4. **推奨**: 通常はPlaywright（USE_PLAYWRIGHT）の使用を推奨します（より軽量で高速）

**設定手順（Seleniumを使用する場合）**

1. `requirements.txt`を開く
2. 以下の行のコメント（`#`）を外す：
   ```
   selenium>=4.15.0
   ```
3. Render.comの環境変数に `USE_SELENIUM=true` を追加
4. ChromeDriverの設定（環境変数9を参照）

**注意事項**

- USE_PLAYWRIGHTとUSE_SELENIUMは同時に設定しないでください（USE_PLAYWRIGHTが優先されます）
- Render.comの無料プランでは、ChromeDriverの設定が複雑で、エラーが発生する可能性が高いです
- 可能であれば、USE_PLAYWRIGHTの使用を推奨します

---

#### 環境変数9: CHROMEDRIVER_PATH（オプション、Selenium使用時のみ）

**この機能について**

Seleniumを使用する場合、Chromeブラウザを制御するためにChromeDriverが必要です。通常は自動検出されますが、見つからない場合は手動でパスを指定します。

**設定方法**

1. **Key**: `CHROMEDRIVER_PATH`
2. **Value**: ChromeDriverのパス（例: `/usr/local/bin/chromedriver`）
3. **使用する場合**: USE_SELENIUM=true に設定し、かつChromeDriverが自動検出されない場合のみ設定
4. **通常は不要**: 自動検出を試行するため、多くの場合設定不要です

**注意事項**

- USE_SELENIUMを使用しない場合は設定不要です
- Render.comの無料プランでは、ChromeDriverのインストールと設定が複雑です
- 可能であれば、USE_PLAYWRIGHTの使用を推奨します（ChromeDriverの設定が不要）

### ステップ3: Google認証情報ファイルの設定

Google認証情報ファイル（`config/google-credentials-474807.json`）をRender.comにアップロードする必要があります。

#### 方法1: Render.comのシェルを使用（推奨）

1. **Render.comダッシュボードで「Shell」タブをクリック**
2. **シェルを開く**
3. **以下のコマンドを実行**:

```bash
# ディレクトリを作成
mkdir -p config

# ファイルを作成（エディタを使用）
nano config/google-credentials-474807.json
```

4. **Google認証情報のJSONコンテンツを貼り付け**
   - ローカル環境の `config/google-credentials-474807.json` の内容をコピー
   - シェルのエディタに貼り付け
   - 保存（nanoの場合は `Ctrl+O` → `Enter` → `Ctrl+X`）

#### 方法2: GitHubリポジトリに追加（注意: セキュリティリスクあり）

**⚠️ 注意**: この方法は推奨されません。認証情報がGitHubに公開されるリスクがあります。

1. ローカル環境で `.gitignore` を確認
2. 必要に応じて `.gitignore` を更新
3. ファイルをコミットしてプッシュ

### ステップ4: デプロイの再実行

1. **環境変数を設定した後、「Manual Deploy」をクリック**
   - または、自動デプロイを待つ（数分かかる場合があります）

2. **デプロイの進行状況を確認**
   - 「Logs」タブでデプロイログを確認
   - エラーがないか確認

### ステップ5: 動作確認

1. **デプロイが完了したら、アプリケーションにアクセス**
   - URL: https://moodmark-csv-to-html-converter.onrender.com/

2. **AI分析チャットページにアクセス**
   - URL: https://moodmark-csv-to-html-converter.onrender.com/analytics_chat

3. **接続状態を確認**
   - サイドバーの「🔌 接続状態」セクションで、すべての接続が正常であることを確認

## トラブルシューティング

### 問題1: 環境変数が反映されない

**解決方法**:
- 環境変数を設定した後、必ずデプロイを再実行してください
- 環境変数のキー名が正確であることを確認してください（大文字小文字を区別）

### 問題2: Google認証情報ファイルが見つからない

**解決方法**:
- `GOOGLE_CREDENTIALS_FILE` 環境変数が正しく設定されているか確認
- ファイルパスが `config/google-credentials-474807.json` であることを確認
- Render.comのシェルでファイルが存在するか確認: `ls -la config/`

### 問題3: OpenAI APIキーが無効

**解決方法**:
- APIキーが正しくコピーされているか確認（前後の空白がないか）
- OpenAIのダッシュボードでAPIキーが有効であることを確認
- APIキーの使用制限に達していないか確認

## セキュリティのベストプラクティス

1. **APIキーを共有しない**
   - APIキーは機密情報です。GitHubや公開場所にコミットしないでください

2. **環境変数を使用**
   - 認証情報は環境変数として設定し、コードに直接書かないでください

3. **定期的にローテーション**
   - セキュリティのため、定期的にAPIキーを更新してください

## 参考リンク

- [Render.com環境変数のドキュメント](https://render.com/docs/environment-variables)
- [OpenAI APIキーの取得方法](https://platform.openai.com/api-keys)

