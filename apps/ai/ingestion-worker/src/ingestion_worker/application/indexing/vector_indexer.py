from typing import Protocol

from ingestion_worker.application.projection.models import LegalContentUnit
from ingestion_worker.domain.embeddings import Embedding


class VectorIndexer(Protocol):
    async def create_collection(self, collection_name: str, vector_size: int) -> None: ...

    async def upsert(
        self, collection_name: str, units: list[LegalContentUnit], embeddings: list[Embedding]
    ) -> None: ...

    async def count(self, collection_name: str) -> int: ...

    async def delete_collection(self, collection_name: str) -> None: ...
