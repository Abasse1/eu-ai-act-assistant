from typing import Protocol

from ai_service.contracts.conversation import AssistantAnswer
from ai_service.contracts.retrieval import RetrievedDocument


class AnswerGenerator(Protocol):
    async def generate(self, question: str, documents: list[RetrievedDocument]) -> AssistantAnswer:
        """Generate a grounded answer from the user's question and retrieved documents."""
        ...
