# Claude LLM Proxy

無料LLMプロバイダーをClaude CodeのツールとしてMCP (Model Context Protocol) 経由で提供するプロキシサーバー。

## 対応プロバイダー

| プロバイダー | 無料枠 | モデル |
|-------------|--------|--------|
| Groq | 30 RPM, 1000 RPD | llama-3.3-70b-versatile |
| Gemini | 15 RPM, 1500 RPD | gemini-1.5-flash |
| OpenRouter | 20 RPM, 50 RPD | llama-3.1-8b-instruct:free |
| Cloudflare | 30 RPM, 150 RPD | llama-3.1-8b-instruct |
| Ollama | 無制限 | codellama:7b |

## セットアップ

### 1. Python環境を作成

```bash
cd ~/Projects/claude-llm-proxy
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. APIキーを設定

```bash
cp .env.example .env
# .envファイルを編集して各プロバイダーのAPIキーを設定
```

**APIキー取得先:**
- Groq: https://console.groq.com/keys
- Gemini: https://aistudio.google.com/apikey
- OpenRouter: https://openrouter.ai/keys
- Cloudflare: https://dash.cloudflare.com/profile/api-tokens

### 3. Ollama（オプション）

ローカルLLMを使用する場合:

```bash
brew install ollama
ollama serve
ollama pull codellama:7b
```

### 4. Claude Codeで使用

```bash
claude
/mcp
```

## 利用可能なツール

| ツール | 説明 |
|--------|------|
| `code_review` | コードレビュー（バグ、セキュリティ、改善点） |
| `generate_tests` | ユニットテスト生成 |
| `generate_docs` | ドキュメント生成 |
| `design_consult` | 設計相談 |
| `refactor_advice` | リファクタリング提案 |
| `llm_status` | プロバイダー状態確認 |

## アーキテクチャ

### ルーティング戦略

`IntelligentRouter`がタスク種別に応じて最適なプロバイダーを選択:

```
CODE_REVIEW     → groq > gemini > ollama
TEST_GENERATION → gemini > groq > ollama
DOCUMENTATION   → gemini > openrouter > ollama
DESIGN_CONSULT  → groq > openrouter > ollama
REFACTORING     → groq > gemini > ollama
```

優先プロバイダーがレート制限に達した場合、自動的に次のプロバイダーへフェイルオーバー。

### レート制限

`RateLimitTracker`が各プロバイダーのRPM（1分あたりリクエスト数）とRPD（1日あたりリクエスト数）を追跡し、制限超過を防止。

## ライセンス

MIT
