from collections.abc import AsyncIterator
from collections.abc import AsyncIterator

from groq import AsyncGroq
from backend.app.core.config import settings
from backend.app.llm.base import BaseLLM


class GroqProvider(BaseLLM):
    """Groq implementation of the BaseLLM interface with fallback protection."""

    def __init__(self) -> None:
        self.api_key = settings.GROQ_API_KEY
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            self.client = None

    async def generate(self, prompt: str) -> str:
        if not self.client:
            return "Groq Service Notice: GROQ_API_KEY is not configured in environment."

        try:
            response = await self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as err:
            return f"Groq LLM Service Notice: Unable to generate response ({err})."

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        if not self.client:
            yield "Groq Service Notice: GROQ_API_KEY is not configured in environment."
            return

        try:
            stream = await self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as err:
            yield f"Groq LLM Service Notice: Streaming error ({err})."
