
import math

from httpx import AsyncClient
from pydantic import BaseModel, ConfigDict

from mcp_server.application.ports.embedding_generator import EmbeddingGenerator


class OllamaEmbedResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    embeddings: list[list[float]]

class OllamaEmbeddingClient(EmbeddingGenerator):
    def __init__(self, client: AsyncClient, model: str) -> None:
        self._client = client
        self._model= model

    async def generate(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot generate an embedding for empty text.")

        response = await self._client.post(
            "api/embed",
            json={
                "model": self._model,
                "input": text,
                "truncate": True
            }
        )

        response.raise_for_status()

        payload = OllamaEmbedResponse.model_validate(response.json())

        if len(payload.embeddings) != 1:
            raise ValueError(
                f"Ollama returned {len(payload.embeddings)} embeddings "
                "for on point"
            )

        vector = payload.embeddings[0]

        if not vector or not all(math.isfinite(value) for value in vector):
            raise ValueError("Ollama returned an invalid embedding")

        return vector
    