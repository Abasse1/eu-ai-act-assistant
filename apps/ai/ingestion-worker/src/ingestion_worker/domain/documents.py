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


class LegalAlinea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = None
    subdivisions: list[LegalSubdivision] = Field(default_factory=list[LegalSubdivision])


class LegalProvision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: str | None = None
    alineas: list[LegalAlinea] = Field(default_factory=list[LegalAlinea])


class LegalArticle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: str
    title: str | None = None
    provisions: list[LegalProvision] = Field(default_factory=list[LegalProvision])


class LegalDivision(BaseModel):
    """A chapter or section containing other divisions or legal articles."""

    model_config = ConfigDict(extra="forbid")

    title: str
    level: int
    children: list["LegalDivision | LegalArticle"] = Field(
        default_factory=list["LegalDivision | LegalArticle"]
    )


class LegalBlock(BaseModel):
    """A generic Formex element used to preserve annex and final-section structures."""

    model_config = ConfigDict(extra="forbid")

    element: str
    text: str | None = None
    number: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict[str, str])
    children: list["LegalBlock"] = Field(default_factory=list["LegalBlock"])


class LegalAnnex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    blocks: list[LegalBlock] = Field(default_factory=list[LegalBlock])


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celex: str
    language: DocumentLanguage
    consolidation_date: date
    source_url: HttpUrl
    retrieved_at: datetime


class StructuredLegalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    celex: str
    title: str
    document_type: str
    language: DocumentLanguage
    consolidation_date: date
    source_url: HttpUrl
    body: list[LegalDivision | LegalArticle] = Field(
        default_factory=list[LegalDivision | LegalArticle]
    )
    annexes: list[LegalAnnex] = Field(default_factory=list[LegalAnnex])
    final: LegalBlock | None = None
    retrieved_at: datetime

    @property
    def articles(self) -> list[LegalArticle]:
        """Return all articles in their original document order."""
        articles: list[LegalArticle] = []

        def collect(items: list[LegalDivision | LegalArticle]) -> None:
            for item in items:
                if isinstance(item, LegalArticle):
                    articles.append(item)
                else:
                    collect(item.children)

        collect(self.body)
        return articles
