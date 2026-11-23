
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentLanguage = Literal["fr","en"]

class LegalDocumentSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    content: str
    score: float
    article_number: str | None = None
    paragraph_number: str | None = None
    alinea_index: int | None = None
    subdivision_path: list[str] = Field(default_factory=list)
    annex_title: str | None = None
    celex: str
    consolidation_date: date
    source_url: str
    language: DocumentLanguage
    metadata: dict[str, str] = Field(default_factory=dict)
