from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RequestIntent = Literal["regulatory_question", "registry_action", "clarification", "out_of_scope"]


class RequestRoutingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: RequestIntent
    reasoning: str = Field(min_length=1, max_length=500)
