from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict

from ai_service.contracts.conversation import AssistantAnswer, Citation


class ContentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["content.delta"] = "content.delta"
    content: str


class CitationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["citation"] = "citation"
    citation: Citation


class CompletedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["completed"] = "completed"
    answer: AssistantAnswer


class FieldEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["field"] = "field"
    code: Literal["provider_unavailable", "processing_failed", "request_rejected"]
    message: str
    retryable: bool


StreamEvent = ContentEvent | CitationEvent | CompletedEvent | FieldEvent
