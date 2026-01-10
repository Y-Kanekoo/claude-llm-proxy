"""
LLMクライアントの基底クラスとユーティリティ
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class LLMResponse:
    """LLMからのレスポンス"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None


class RateLimitTracker:
    """レート制限を追跡するクラス"""

    def __init__(self, rpm_limit: int, rpd_limit: int = 0):
        """
        Args:
            rpm_limit: 1分あたりのリクエスト上限
            rpd_limit: 1日あたりのリクエスト上限（0の場合は無制限）
        """
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.minute_requests: list[float] = []
        self.day_requests: list[float] = []

    def can_request(self) -> bool:
        """リクエスト可能かどうかを判定"""
        now = time.time()
        # 1分以内のリクエストをフィルタ
        self.minute_requests = [t for t in self.minute_requests if now - t < 60]
        # 1日以内のリクエストをフィルタ
        self.day_requests = [t for t in self.day_requests if now - t < 86400]

        if len(self.minute_requests) >= self.rpm_limit:
            return False
        if self.rpd_limit and len(self.day_requests) >= self.rpd_limit:
            return False
        return True

    def record_request(self):
        """リクエストを記録"""
        now = time.time()
        self.minute_requests.append(now)
        self.day_requests.append(now)

    def get_wait_time(self) -> float:
        """次のリクエストまでの待機時間を取得（秒）"""
        if not self.minute_requests:
            return 0
        oldest = min(self.minute_requests)
        return max(0, 60 - (time.time() - oldest))


class BaseLLMClient(ABC):
    """LLMクライアントの基底クラス"""
    provider_name: str = "base"

    def __init__(self):
        self.rate_tracker: Optional[RateLimitTracker] = None

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", **kwargs) -> LLMResponse:
        """テキスト生成を実行"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """プロバイダーが利用可能かどうかを判定"""
        pass

    def can_request(self) -> bool:
        """レート制限内でリクエスト可能かどうかを判定"""
        return self.rate_tracker.can_request() if self.rate_tracker else True

    def record_request(self):
        """リクエストを記録"""
        if self.rate_tracker:
            self.rate_tracker.record_request()
