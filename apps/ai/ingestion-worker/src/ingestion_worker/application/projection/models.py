from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ingestion_worker.domain.documents import DocumentLanguage

LegalContentUnitType = Literal["article", "subdivision", "annex_block", "table_row", "final"]


class LegalContentUnit(BaseModel):
    """A semantically meaningful and traceable legal content unit."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: LegalContentUnitType
    content: str
    article_number: str | None = None
    paragraph_number: str | None = None
    alinea_index: int | None = None
    subdivision_path: list[str] = Field(default_factory=list)
    annex_title: str | None = None
    language: DocumentLanguage
    celex: str
    consolidation_date: date
    source_url: HttpUrl
    metadata: dict[str, str] = Field(default_factory=dict)
