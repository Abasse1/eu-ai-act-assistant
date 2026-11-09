from typing import NotRequired, TypedDict

from ai_service.contracts.conversation import Citation
from ai_service.contracts.retrieval import RetrievedDocument
from ai_service.contracts.routing import RequestIntent
from ai_service.contracts.streaming import FieldEvent


class AssistantTurnState(TypedDict):
    organization_id: str
    user_id: str
    conversation_id: str
    message_id: str
    question: str

    retrieved_documents: NotRequired[list[RetrievedDocument]]
    answer: NotRequired[str]
    citations: NotRequired[list[Citation]]
    disclaimer: NotRequired[str]
    failure: NotRequired[FieldEvent]
    intent: NotRequired[RequestIntent]
