
from typing import Protocol

from mcp_server.application.models.legal_document import DocumentLanguage, LegalDocumentSearchResult


class DocumentSearcher(Protocol):
    async def search(self, vector: list[float],
                     top_k: int,language: DocumentLanguage
                     ) -> list[LegalDocumentSearchResult]: ...