from typing import NotRequired, TypedDict

from ai_service.contracts.conversation import Citation
from ai_service.contracts.streaming import FieldEvent


class AssistantTurnState(TypedDict):
    organisation_id: str
    user_id: str
    conversation_id: str
    message_id: str
    sanitized_question: str

    retrieved_citations: NotRequired[list[Citation]]
    answer: NotRequired[str]
    citations: NotRequired[list[Citation]]
    failure: NotRequired[FieldEvent]
