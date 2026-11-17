from typing import Protocol

from ingestion_worker.application.projection.models import LegalContentUnit
from ingestion_worker.domain.embeddings import Embedding


class EmbeddingGenerator(Protocol):
    async def generate(self, units: list[LegalContentUnit]) -> list[Embedding]: ...
