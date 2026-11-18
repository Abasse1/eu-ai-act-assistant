import httpx
from qdrant_client import AsyncQdrantClient

from ingestion_worker.application.embeddings.generate_embeddings import EmbeddingGenerator
from ingestion_worker.application.indexing.collection_publisher import CollectionPublisher
from ingestion_worker.application.indexing.vector_indexer import VectorIndexer
from ingestion_worker.config import settings
from ingestion_worker.infrastructure.embeddings.ollama_embedding_generator import (
    OllamaEmbeddingGenerator,
)
from ingestion_worker.infrastructure.indexing.qdrant_collection_publisher import (
    QdrantCollectionPublisher,
)
from ingestion_worker.infrastructure.indexing.qdrant_vector_indexer import QdrantVectorIndexer
from ingestion_worker.infrastructure.parsing.formex_extractor import FormexExtractor
from ingestion_worker.infrastructure.sources.eur_lex import EurLexSource


class Dependencies:
    def __init__(
        self,
        ollama_http_client: httpx.AsyncClient,
        eur_lex_http_client: httpx.AsyncClient,
        qdrant_client: AsyncQdrantClient,
        embedding_generator: EmbeddingGenerator,
        vector_indexer: VectorIndexer,
        collection_publisher: CollectionPublisher,
        eur_lex_source: EurLexSource,
        formex_extractor: FormexExtractor,
    ) -> None:
        self.ollama_http_client = ollama_http_client
        self.eur_lex_http_client = eur_lex_http_client
        self.qdrant_client = qdrant_client
        self.embedding_generator = embedding_generator
        self.vector_indexer = vector_indexer
        self.collection_publisher = collection_publisher
        self.eur_lex_source = eur_lex_source
        self.formex_extractor = formex_extractor

    async def close(self) -> None:
        await self.ollama_http_client.aclose()
        await self.eur_lex_http_client.aclose()
        await self.qdrant_client.close()


def build_dependencies() -> Dependencies:
    print(f"voici la configuration chargé: {settings.model_dump()}\n\n")
    ollama_http_client = httpx.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=settings.embedding_timeout,
    )

    eur_lex_http_client = httpx.AsyncClient(
        timeout=settings.eur_lex_timeout,
    )

    qdrant_client = AsyncQdrantClient(
        url=settings.qdrant_url,
        timeout=settings.qdrant_timeout,
    )

    return Dependencies(
        ollama_http_client=ollama_http_client,
        eur_lex_http_client=eur_lex_http_client,
        qdrant_client=qdrant_client,
        embedding_generator=OllamaEmbeddingGenerator(
            client=ollama_http_client,
            model=settings.ollama_embedding_model,
            batch_size=settings.embedding_batch_size,
        ),
        vector_indexer=QdrantVectorIndexer(
            client=qdrant_client,
        ),
        collection_publisher=QdrantCollectionPublisher(
            client=qdrant_client,
            active_alias=settings.qdrant_active_alias,
        ),
        eur_lex_source=EurLexSource(
            client=eur_lex_http_client,
        ),
        formex_extractor=FormexExtractor(),
    )
