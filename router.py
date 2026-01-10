"""
インテリジェントルーター - タスク種別に応じて最適なLLMプロバイダーを選択
"""

from typing import Optional
from llm_clients import (
    GroqClient, GeminiClient, OpenRouterClient,
    CloudflareClient, OllamaClient,
)
from llm_clients.base import LLMResponse


class TaskType:
    """タスク種別の定義"""
    CODE_REVIEW = "code_review"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    DESIGN_CONSULT = "design_consult"
    REFACTORING = "refactoring"


# タスク種別ごとのプロバイダー優先順位
TASK_PROVIDER_PRIORITY = {
    TaskType.CODE_REVIEW: ["groq", "gemini", "ollama"],
    TaskType.TEST_GENERATION: ["gemini", "groq", "ollama"],
    TaskType.DOCUMENTATION: ["gemini", "openrouter", "ollama"],
    TaskType.DESIGN_CONSULT: ["groq", "openrouter", "ollama"],
    TaskType.REFACTORING: ["groq", "gemini", "ollama"],
}


class IntelligentRouter:
    """タスクに応じてLLMプロバイダーを選択するルーター"""

    def __init__(self):
        self.clients = {
            "groq": GroqClient(),
            "gemini": GeminiClient(),
            "openrouter": OpenRouterClient(),
            "cloudflare": CloudflareClient(),
            "ollama": OllamaClient(),
        }

    def get_available_providers(self) -> list[str]:
        """利用可能なプロバイダー一覧を取得"""
        return [
            name for name, client in self.clients.items()
            if client.is_available() and client.can_request()
        ]

    def get_provider_for_task(self, task_type: str) -> Optional[str]:
        """タスク種別に応じた最適なプロバイダーを取得"""
        priority = TASK_PROVIDER_PRIORITY.get(
            task_type,
            ["groq", "gemini", "openrouter", "cloudflare", "ollama"]
        )
        for provider in priority:
            client = self.clients.get(provider)
            if client and client.is_available() and client.can_request():
                return provider
        return None

    async def route_request(
        self,
        prompt: str,
        task_type: str,
        system: str = "",
        **kwargs
    ) -> LLMResponse:
        """
        リクエストを適切なプロバイダーにルーティング

        Args:
            prompt: ユーザープロンプト
            task_type: タスク種別
            system: システムプロンプト
            **kwargs: 追加パラメータ（temperature, max_tokensなど）

        Returns:
            LLMResponse: 生成結果
        """
        priority = TASK_PROVIDER_PRIORITY.get(
            task_type,
            ["groq", "gemini", "openrouter", "cloudflare", "ollama"]
        )
        errors = []

        for provider_name in priority:
            client = self.clients.get(provider_name)
            if not client:
                continue

            if not client.is_available():
                errors.append(f"{provider_name}: not configured")
                continue

            if not client.can_request():
                errors.append(f"{provider_name}: rate limited")
                continue

            response = await client.generate(prompt, system, **kwargs)
            if response.error:
                errors.append(f"{provider_name}: {response.error}")
                # レート制限エラーの場合は次のプロバイダーへ
                if "rate" in response.error.lower():
                    continue
            else:
                return response

        # 全プロバイダーが失敗した場合
        return LLMResponse(
            content="",
            model="",
            provider="none",
            error=f"All providers failed: {'; '.join(errors)}"
        )

    def get_status(self) -> dict:
        """全プロバイダーの状態を取得"""
        return {
            name: {
                "available": client.is_available(),
                "can_request": client.can_request(),
                "model": getattr(client, "model", "unknown")
            }
            for name, client in self.clients.items()
        }


# シングルトンインスタンス
router = IntelligentRouter()
