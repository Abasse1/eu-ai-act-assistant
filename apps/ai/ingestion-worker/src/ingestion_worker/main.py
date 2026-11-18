import asyncio
import logging

from ingestion_worker.application.index_document import index_document
from ingestion_worker.application.projection.legal_document_projector import LegalDocumentProjector
from ingestion_worker.bootstrap import build_dependencies
from ingestion_worker.config import settings
from ingestion_worker.domain.documents import DocumentLanguage
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    dependencies = build_dependencies()

    try:
        language: DocumentLanguage = settings.document_language

        logger.info(
            "Starting document indexing: language=%s",
            language,
        )

        indexed_count = await index_document(
            language=language,
            source=dependencies.eur_lex_source,
            extractor=dependencies.formex_extractor,
            parser=EurLexParser(),
            projector=LegalDocumentProjector(),
            embedding_generator=dependencies.embedding_generator,
            vector_indexer=dependencies.vector_indexer,
            collection_publisher=dependencies.collection_publisher,
        )

        logger.info(
            "Document indexing completed successfully: %d units indexed",
            indexed_count,
        )

    except Exception:
        logger.exception("Document indexing failed")
        raise

    finally:
        await dependencies.close()


if __name__ == "__main__":
    asyncio.run(main())
