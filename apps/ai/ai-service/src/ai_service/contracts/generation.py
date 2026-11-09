from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_service.contracts.conversation import AssistantAnswer
from ai_service.contracts.retrieval import RetrievedDocument


class AnswerGenerator(Protocol):
    async def generate(self, question: str, documents: list[RetrievedDocument]) -> AssistantAnswer:
        """Generate a grounded answer from the user's question and retrieved documents."""
        ...


class GeneratedAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_answer: bool
    content: str = Field(default="", max_length=12000)
    used_document_indices: list[int] = Field(default_factory=list[int])

    @model_validator(mode="after")
    def validate_answer(self) -> "GeneratedAnswerDraft":
        if self.can_answer and (not self.content.strip() or not self.used_document_indices):
            raise ValueError("An answer requires content and at least one supporting document.")

        if not self.can_answer and (self.content.strip() or self.used_document_indices):
            raise ValueError("An unsupported answer must not contain content or citations.")

        if len(self.used_document_indices) != len(set(self.used_document_indices)):
            raise ValueError("Document indices must be unique.")

        if any(index < 0 for index in self.used_document_indices):
            raise ValueError("Document indices cannot be negative.")

        return self
