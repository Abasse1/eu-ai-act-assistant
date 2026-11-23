from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp_server.application.models.legal_document import (
    DocumentLanguage,
    LegalDocumentSearchResult,
)
from mcp_server.application.ports.document_searcher import DocumentSearcher
from mcp_server.application.ports.embedding_generator import EmbeddingGenerator


class SearchLegalDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    language: DocumentLanguage = "fr"

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError("Search query must contain at least 3 characters")

        return value


class SearchLegalDocuments:
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        document_searcher: DocumentSearcher,
    ) -> None:
        self._embedding_generator = embedding_generator
        self._document_searcher = document_searcher

    async def execute(
        self,
        request: SearchLegalDocumentRequest,
    ) -> list[LegalDocumentSearchResult]:
        vector = await self._embedding_generator.generate(request.query)

        return await self._document_searcher.search(
            vector=vector,
            top_k=request.top_k,
            language=request.language,
        )