from qdrant_client import AsyncQdrantClient, models

from ingestion_worker.application.indexing.vector_indexer import VectorIndexer
from ingestion_worker.application.projection.models import LegalContentUnit
from ingestion_worker.domain.embeddings import Embedding


class QdrantVectorIndexer(VectorIndexer):
    def __init__(self, client: AsyncQdrantClient, batch_size: int = 128) -> None:
        if batch_size < 1:
            raise ValueError("Batch size must be greater than zero")

        self._client = client
        self._batch_size = batch_size

    async def create_collection(self, collection_name: str, vector_size: int) -> None:
        if vector_size < 1:
            raise ValueError("Vector size must be greater than zero")

        if await self._client.collection_exists(collection_name):
            raise ValueError(f"Collection already exists: {collection_name}")

        await self._client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    async def upsert(
        self,
        collection_name: str,
        units: list[LegalContentUnit],
        embeddings: list[Embedding],
    ) -> None:
        if len(units) != len(embeddings):
            raise ValueError(f"Received {len(units)} units but {len(embeddings)} embeddings")

        if not units:
            return

        units_by_id = {unit.id: unit for unit in units}

        if len(units_by_id) != len(units):
            raise ValueError("Duplicate legal content unit IDs detected")

        embedding_ids = [embedding.unit_id for embedding in embeddings]

        if len(set(embedding_ids)) != len(embedding_ids):
            raise ValueError("Duplicate embedding IDs detected")

        if set(units_by_id) != set(embedding_ids):
            raise ValueError("Units and embeddings do not have matching IDs")

        vector_size = len(embeddings[0].vector)

        if vector_size == 0:
            raise ValueError("Embedding vectors must not be empty")

        if any(len(embedding.vector) != vector_size for embedding in embeddings):
            raise ValueError("Inconsistent embedding dimensions")

        for start in range(0, len(embeddings), self._batch_size):
            batch = embeddings[start : start + self._batch_size]

            points = [
                models.PointStruct(
                    id=unit.id,
                    vector=embedding.vector,
                    payload={
                        "content": unit.content,
                        "type": unit.type,
                        "article_number": unit.article_number,
                        "paragraph_number": unit.paragraph_number,
                        "alinea_index": unit.alinea_index,
                        "subdivision_path": unit.subdivision_path,
                        "annex_title": unit.annex_title,
                        "language": unit.language,
                        "celex": unit.celex,
                        "consolidation_date": unit.consolidation_date.isoformat(),
                        "source_url": str(unit.source_url),
                        "metadata": unit.metadata,
                    },
                )
                for embedding in batch
                for unit in [units_by_id[embedding.unit_id]]
            ]

            await self._client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True,
            )

    async def count(self, collection_name: str) -> int:
        result = await self._client.count(
            collection_name=collection_name,
            exact=True,
        )
        return result.count

    async def delete_collection(self, collection_name: str) -> None:
        if await self._client.collection_exists(collection_name):
            await self._client.delete_collection(collection_name=collection_name)
