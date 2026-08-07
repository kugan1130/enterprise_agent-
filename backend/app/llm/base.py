from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseLLM(ABC):
    """Abstract interface for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate a complete response."""
        raise NotImplementedError

    @abstractmethod
    def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream the model response."""
        raise NotImplementedError