from pydantic import BaseModel, ConfigDict


class Embedding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    unit_id: str
    model: str
    vector: list[float]
