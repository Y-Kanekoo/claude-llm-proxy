"""
Cloudflare Workers AI LLMクライアント
"""

import os
import time
import httpx
from .base import BaseLLMClient, LLMResponse, RateLimitTracker


class CloudflareClient(BaseLLMClient):
    """Cloudflare Workers AI APIクライアント"""
    provider_name = "cloudflare"

    def __init__(self):
        super().__init__()
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.model = "@cf/meta/llama-3.1-8b-instruct"
        self.rate_tracker = RateLimitTracker(rpm_limit=30, rpd_limit=150)

    def is_available(self) -> bool:
        """認証情報が設定されているかを確認"""
        return bool(self.account_id and self.api_token)

    async def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """Cloudflare Workers AI APIでテキスト生成"""
        if not self.is_available():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="Cloudflare credentials not configured"
            )

        if not self.can_request():
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error="Rate limited"
            )

        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{self.model}"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json={
                        "messages": messages,
                        "max_tokens": kwargs.get("max_tokens", 2048)
                    }
                )
                response.raise_for_status()
                data = response.json()

                self.record_request()
                return LLMResponse(
                    content=data.get("result", {}).get("response", ""),
                    model=self.model,
                    provider=self.provider_name,
                    latency_ms=(time.time() - start) * 1000
                )
        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                provider=self.provider_name,
                error=str(e)
            )
