from collections.abc import AsyncIterator

from groq import AsyncGroq
from backend.app.core.config import settings
from backend.app.llm.base import BaseLLM


class GroqProvider(BaseLLM):
    """Groq implementation of the BaseLLM interface."""

    def __init__(self) -> None:
        self.client = AsyncGroq(
            api_key=settings.GROQ_API_KEY
        )

    async def generate(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return response.choices[0].message.content or ""

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            stream=True,
        )

        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
