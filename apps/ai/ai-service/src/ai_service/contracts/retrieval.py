from pydantic import BaseModel, ConfigDict, Field

from ai_service.contracts.conversation import Citation


class RetrievedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation: Citation
    score: float = Field(ge=0.0, le=1.0)


class RetrievalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[RetrievedDocument] = Field(default_factory=list[RetrievedDocument])
