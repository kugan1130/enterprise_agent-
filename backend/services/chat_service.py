from app.llm.base import BaseLLM


class ChatService:
    """
    Handles chat-related business logic.

    The service does not know which LLM provider
    is being used. It only depends on the BaseLLM
    interface.
    """

    def __init__(self, llm: BaseLLM) -> None:
        """
        Store the LLM implementation.

        Args:
            llm: Any object implementing BaseLLM.
        """
        self._llm = llm

    async def ask(self, prompt: str) -> str:
        """
        Send a user prompt to the LLM and
        return the generated response.

        Args:
            prompt: User input.

        Returns:
            Model response.
        """
        response = await self._llm.generate(prompt)

        return response