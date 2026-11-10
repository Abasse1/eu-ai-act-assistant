from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

DocumentLanguage = Literal["fr", "en"]


class LegalSubdivision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: str | None = None
    text: str
    list_type: str | None = None
    children: list["LegalSubdivision"] = Field(default_factory=list["LegalSubdivision"])


class LegalProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: str | None = None
    text: str | None
    subdivisions: list[LegalSubdivision] = Field(default_factory=list[LegalSubdivision])


class LegalArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: str
    title: str | None = None
    provisions: list[LegalProvision] = Field(default_factory=list[LegalProvision])


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celex: str
    language: DocumentLanguage
    consolidation_date: date
    source_url: HttpUrl
    content_xml: str
    retrieved_at: datetime


class StructuredLegalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celex: str
    language: DocumentLanguage
    consolidation_date: date
    source_url: HttpUrl
    articles: list[LegalArticle]
    retrieved_at: datetime
