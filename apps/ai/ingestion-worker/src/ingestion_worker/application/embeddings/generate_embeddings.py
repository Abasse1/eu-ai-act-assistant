from typing import AsyncIterator, Protocol

from ingestion_worker.application.projection.models import GeneratedEmbeddingBatch, LegalContentUnit


class EmbeddingGenerator(Protocol):
     def generate(self, units: list[LegalContentUnit]) -> AsyncIterator[GeneratedEmbeddingBatch]: ...
