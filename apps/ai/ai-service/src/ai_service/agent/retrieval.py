from typing import Protocol

from ai_service.contracts.retrieval import RetrievedDocument


class DocumentRetriever(Protocol):
    async def retrieve(self, question: str) -> list[RetrievedDocument]:
        """Retrieve relevant regulatory passage for user question."""
        ...
