"""
Google Gemini LLMクライアント
"""

import os
import time
import httpx
from .base import BaseLLMClient, LLMResponse, RateLimitTracker


class GeminiClient(BaseLLMClient):
    """Gemini APIクライアント"""
    provider_name = "gemini"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = "gemini-1.5-flash"
        self.rate_tracker = RateLimitTracker(rpm_limit=15, rpd_limit=1500)

    def is_available(self) -> bool:
        """APIキーが設定されているかを確認"""
        return bool(self.api_key)

    async def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """Gemini APIでテキスト生成"""
        if not self.is_available():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="Gemini API key not configured"
            )

        if not self.can_request():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="Rate limited"
            )

        base_url = "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base_url}/models/{self.model}:generateContent?key={self.api_key}"

        # Geminiはsystemプロンプトをユーザープロンプトに結合
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        contents = [{"role": "user", "parts": [{"text": full_prompt}]}]

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "maxOutputTokens": kwargs.get("max_tokens", 4096)
                    }
                })
                response.raise_for_status()
                data = response.json()

                self.record_request()
                candidates = data.get("candidates", [])
                content = ""
                if candidates:
                    content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider=self.provider_name,
                    tokens_used=data.get("usageMetadata", {}).get("totalTokenCount", 0),
                    latency_ms=(time.time() - start) * 1000
                )
        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error=str(e)
            )
