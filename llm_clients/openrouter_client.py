"""
OpenRouter LLMクライアント
"""

import os
import time
import httpx
from .base import BaseLLMClient, LLMResponse, RateLimitTracker


class OpenRouterClient(BaseLLMClient):
    """OpenRouter APIクライアント"""
    provider_name = "openrouter"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "meta-llama/llama-3.1-8b-instruct:free"
        self.rate_tracker = RateLimitTracker(rpm_limit=20, rpd_limit=50)

    def is_available(self) -> bool:
        """APIキーが設定されているかを確認"""
        return bool(self.api_key)

    async def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """OpenRouter APIでテキスト生成"""
        if not self.is_available():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="OpenRouter API key not configured"
            )

        if not self.can_request():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="Rate limited"
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://github.com/claude-llm-proxy"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_tokens": kwargs.get("max_tokens", 4096)
                    }
                )
                response.raise_for_status()
                data = response.json()

                self.record_request()
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    model=self.model,
                    provider=self.provider_name,
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                    latency_ms=(time.time() - start) * 1000
                )
        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error=str(e)
            )
