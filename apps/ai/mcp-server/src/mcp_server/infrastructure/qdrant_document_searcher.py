from qdrant_client import AsyncQdrantClient, models

from mcp_server.application.models.legal_document import (
    DocumentLanguage,
    LegalDocumentSearchResult,
)
from mcp_server.application.ports.document_searcher import DocumentSearcher


class QdrantDocumentSearcher(DocumentSearcher):
    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
    ) -> None:
        self._client = client
        self._collection_name = collection_name

    async def search(
        self,
        vector: list[float],
        top_k: int,
        language: DocumentLanguage,
    ) -> list[LegalDocumentSearchResult]:
        if not vector:
            raise ValueError("Search vector must not be empty.")

        response = await self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="language",
                        match=models.MatchValue(value=language),
                    ),
                ],
            ),
            limit=top_k,
            with_payload=True,
        )

        results: list[LegalDocumentSearchResult] = []

        for point in response.points:
            if point.payload is None:
                raise ValueError(
                    f"Qdrant returned point {point.id} without a payload."
                )

            results.append(
                LegalDocumentSearchResult.model_validate(
                    {
                        **point.payload,
                        "id": str(point.id),
                        "score": point.score,
                    }
                )
            )

        return results