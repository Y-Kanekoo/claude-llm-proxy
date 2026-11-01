"""
Ollama ローカルLLMクライアント
"""

import os
import time

import httpx

from .base import BaseLLMClient, LLMResponse


class OllamaClient(BaseLLMClient):
    """Ollama ローカルLLMクライアント"""
    provider_name = "ollama"

    def __init__(self):
        super().__init__()
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = "codellama:7b"
        self.rate_tracker = None  # ローカル実行のためレート制限なし

    def is_available(self) -> bool:
        """Ollamaサーバーが起動しているかを確認"""
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:  # noqa: BLE001 - 接続できない理由を問わず「利用不可」と判定するための意図的な捕捉
            return False

    def list_models(self) -> list[str]:
        """利用可能なモデル一覧を取得"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    return [m["name"] for m in response.json().get("models", [])]
        except Exception:  # noqa: BLE001, S110 - モデル一覧の取得失敗は理由を問わず空一覧として扱う（従来どおり）
            pass
        return []

    async def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """Ollamaでテキスト生成"""
        if not self.is_available():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="Ollama not running. Start: ollama serve"
            )

        # モデルの存在確認
        model = kwargs.get("model", self.model)
        available = self.list_models()
        if model not in available:
            # フォールバック: codellama:7b または最初の利用可能なモデル
            if "codellama:7b" in available:
                model = "codellama:7b"
            elif available:
                model = available[0]
            else:
                return LLMResponse(
                    content="",
                    model=self.model,
                    provider=self.provider_name,
                    error="No models. Run: ollama pull codellama:7b"
                )

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get("temperature", 0.7),
                            "num_predict": kwargs.get("max_tokens", 4096)
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data.get("response", ""),
                    model=model,
                    provider=self.provider_name,
                    tokens_used=data.get("eval_count", 0),
                    latency_ms=(time.time() - start) * 1000
                )
        except Exception as e:  # noqa: BLE001 - 想定外の例外も含めエラー応答に変換し、ルーターが次のプロバイダーへ切り替えるための意図的な捕捉
            return LLMResponse(
                content="",
                model=model,
                provider=self.provider_name,
                error=str(e)
            )
