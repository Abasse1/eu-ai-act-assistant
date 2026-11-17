import httpx
from pydantic import BaseModel, ConfigDict

from ingestion_worker.application.embeddings.generate_embeddings import EmbeddingGenerator
from ingestion_worker.application.projection.models import LegalContentUnit
from ingestion_worker.domain.embeddings import Embedding


class OllamaEmbedResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    embeddings: list[list[float]]


class OllamaEmbeddingGenerator(EmbeddingGenerator):
    def __init__(self, client: httpx.AsyncClient, model: str, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero.")

        self._client = client
        self._model = model
        self.batch_size = batch_size

    async def generate(self, units: list[LegalContentUnit]) -> list[Embedding]:
        if not units:
            return []

        if any(not unit.content.strip() for unit in units):
            raise ValueError("Cannot generate embedding for empty legal centent")

        results: list[Embedding] = []
        expected_dimmension: int | None = None

        for start in range(0, len(units), self.batch_size):
            batch = units[start : start + self.batch_size]

            response = await self._client.post(
                "/api/embed",
                json={"model": self._model, "input": [unit for unit in batch], "truncate": False},
            )

            response.raise_for_status()

            payload = OllamaEmbedResponse.model_validate(response.json())

            if len(payload.embeddings) != len(batch):
                raise ValueError(
                    f"Ollama returned {len(payload.embeddings)} embeddings "
                    f"for {len(batch)} input units"
                )

            for unit, vector in zip(batch, payload.embeddings, strict=True):
                if not vector:
                    raise ValueError(f"Ollama returned an empty embedding for unit {unit.id}")

                if expected_dimmension is None:
                    expected_dimmension = len(vector)
                elif len(vector) != expected_dimmension:
                    raise ValueError(
                        f"Inconsistent embedding dimension: expected "
                        f"{expected_dimmension}, received {len(vector)}"
                    )

                results.append(Embedding(unit_id=unit.id, model=self._model, vector=vector))

        return results
