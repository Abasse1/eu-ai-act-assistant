import logging
import time
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel, ConfigDict

from ingestion_worker.application.embeddings.generate_embeddings import EmbeddingGenerator
from ingestion_worker.application.projection.models import GeneratedEmbeddingBatch, LegalContentUnit
from ingestion_worker.domain.embeddings import Embedding

logger = logging.getLogger(__name__)


class OllamaEmbedResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    embeddings: list[list[float]]


class OllamaEmbeddingGenerator(EmbeddingGenerator):
    def __init__(
        self,
        client: httpx.AsyncClient,
        model: str,
        batch_size: int = 32,
    ) -> None:
        if batch_size < 1:
            raise ValueError("Batch size must be greater than zero")

        self._client = client
        self._model = model
        self._batch_size = batch_size

    async def generate(
        self,
        units: list[LegalContentUnit],
    ) -> AsyncIterator[GeneratedEmbeddingBatch]:
        if not units:
            return

        if any(not unit.content.strip() for unit in units):
            raise ValueError("Cannot generate embeddings for empty legal content")

        expected_dimension: int | None = None
        total_batches = (len(units) + self._batch_size - 1) // self._batch_size

        for start in range(0, len(units), self._batch_size):
            batch_number = start // self._batch_size + 1
            batch = units[start : start + self._batch_size]
            started_at = time.perf_counter()

            response = await self._client.post(
                "/api/embed",
                json={
                    "model": self._model,
                    "input": [unit.content for unit in batch],
                    "truncate": True,
                },
            )
            response.raise_for_status()

            payload = OllamaEmbedResponse.model_validate(response.json())

            if len(payload.embeddings) != len(batch):
                raise ValueError(
                    f"Ollama returned {len(payload.embeddings)} embeddings "
                    f"for {len(batch)} input units"
                )

            embeddings: list[Embedding] = []

            for unit, vector in zip(batch, payload.embeddings, strict=True):
                if not vector:
                    raise ValueError(
                        f"Ollama returned an empty embedding for unit {unit.id}"
                    )

                dimension = len(vector)

                if expected_dimension is None:
                    expected_dimension = dimension
                elif dimension != expected_dimension:
                    raise ValueError(
                        f"Inconsistent embedding dimension: expected "
                        f"{expected_dimension}, received {dimension}"
                    )

                embeddings.append(
                    Embedding(
                        unit_id=unit.id,
                        model=self._model,
                        vector=vector,
                    )
                )

            duration = time.perf_counter() - started_at

            logger.info(
                "Embedding batch %d/%d completed: %d units in %.2fs",
                batch_number,
                total_batches,
                len(batch),
                duration,
            )

            yield GeneratedEmbeddingBatch(
                units=batch,
                embeddings=embeddings,
            )

        logger.info(
            "Embedding generation completed: %d units, %d batches",
            len(units),
            total_batches,
        )