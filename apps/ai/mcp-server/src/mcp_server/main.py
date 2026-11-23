import asyncio

import httpx
from qdrant_client import AsyncQdrantClient

from mcp_server.application.search_legal_document import SearchLegalDocuments
from mcp_server.config import settings
from mcp_server.infrastructure.ollama_embedding_client import OllamaEmbeddingClient
from mcp_server.infrastructure.qdrant_document_searcher import QdrantDocumentSearcher
from mcp_server.server import mcp
from mcp_server.tools.search_legal_documents import register_search_legal_documents_tools


async def run() -> None:
    async with httpx.AsyncClient(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout,
    ) as ollama_client:
        qdrant_client = AsyncQdrantClient(
            url=settings.qdrant_url,
            timeout=settings.qdrant_timeout,
        )

        try:
            embedding_generator = OllamaEmbeddingClient(
                client=ollama_client,
                model=settings.ollama_embedding_model,
            )

            document_searcher = QdrantDocumentSearcher(
                client=qdrant_client,
                collection_name=settings.qdrant_active_alias,
            )

            use_case = SearchLegalDocuments(
                embedding_generator=embedding_generator,
                document_searcher=document_searcher,
            )

            register_search_legal_documents_tools(
                server=mcp,
                use_case=use_case,
            )

            await mcp.run_streamable_http_async(
                host=settings.host,
                port=settings.port,
                streamable_http_path=settings.streamable_http_path,
            )
        finally:
            await qdrant_client.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()