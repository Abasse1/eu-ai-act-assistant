from typing import Protocol

from ai_service.contracts.conversation import AssistantAnswer
from ai_service.contracts.retrieval import RetrievedDocument


class AnswerGenerator(Protocol):
    async def generator(self, question: str, documents: list[RetrievedDocument]) -> AssistantAnswer:
        """Generate a ground answer from the user's question and retrieved documents."""
        ...


class InvalidAnswerCitationError(ValueError):
    """Raised when an answer rerefence a citation absent from retrieved documents."""


def validate_answer_citations(answer: AssistantAnswer, documents: list[RetrievedDocument]) -> None:
    avalable_citations = [document.citation for document in documents]

    for citation in answer.citations:
        if citation not in avalable_citations:
            raise InvalidAnswerCitationError(
                f"Generated answer contains an unsupported citation: {citation.reference}"
            )
