from collections.abc import AsyncIterator

from backend.app.llm.base import BaseLLM


class LLMClient(BaseLLM):

    def __init__(self, provider: BaseLLM) -> None:
        self._provider = provider

    async def generate(self, prompt: str) -> str:
        return await self._provider.generate(prompt)

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        async for chunk in self._provider.stream(prompt):
            yield chunk
