from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseLLM(ABC):

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def stream(self, prompt: str) -> AsyncIterator[str]:
        raise NotImplementedError