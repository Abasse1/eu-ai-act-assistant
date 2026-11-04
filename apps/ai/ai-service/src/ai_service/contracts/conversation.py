from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class MessageInput(BaseModel):
    """
    Represents a message input in a conversation.
    """

    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        min_length=1, max_length=4000, description="The content of the message input."
    )


class Citation(BaseModel):
    """
    Represents a citation in a conversation.
    """

    model_config = ConfigDict(extra="forbid")

    reference: str
    passage: str
    article: str | None = None
    version: str
    source_url: HttpUrl
    withdrawn_at: datetime | None = None


class AssistantAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    citations: list[Citation] = Field(
        default_factory=list[Citation], description="List of citations associated with the answer."
    )
    disclaimer: str


class AssistantTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organisation_id: UUID
    user_id: UUID
    conversation_id: UUID
    message_id: UUID
    content: str = Field(min_length=1, max_length=4000)
