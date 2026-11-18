from ingestion_worker.application.embeddings.generate_embeddings import EmbeddingGenerator
from ingestion_worker.application.indexing.collection_naming import create_collection_name
from ingestion_worker.application.indexing.collection_publisher import CollectionPublisher
from ingestion_worker.application.indexing.validate_collection import validate_collection
from ingestion_worker.application.indexing.vector_indexer import VectorIndexer
from ingestion_worker.application.ingest_document import ingest_document
from ingestion_worker.application.projection.legal_document_projector import LegalDocumentProjector
from ingestion_worker.application.projection.models import LegalContentUnit
from ingestion_worker.domain.documents import DocumentLanguage
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser
from ingestion_worker.infrastructure.parsing.formex_extractor import FormexExtractor
from ingestion_worker.infrastructure.sources.eur_lex import EurLexSource


async def index_document(
    language: DocumentLanguage,
    source: EurLexSource,
    extractor: FormexExtractor,
    parser: EurLexParser,
    projector: LegalDocumentProjector,
    embedding_generator: EmbeddingGenerator,
    vector_indexer: VectorIndexer,
    collection_publisher: CollectionPublisher,
) -> int:
    document = await ingest_document(
        language=language,
        extractor=extractor,
        source=source,
        parser=parser,
    )

    units = projector.project(document=document)
    _validate_units(units)

    first_unit = units[0]

    collection_name = create_collection_name(
        celex=first_unit.celex,
        consolidation_date=first_unit.consolidation_date,
        language=first_unit.language,
    )

    vector_size: int | None = None
    indexed_count = 0

    async for batch in embedding_generator.generate(units):
        if len(batch.units) != len(batch.embeddings):
            raise RuntimeError(
                "Embedding count does not match batch unit count"
            )

        if not batch.embeddings:
            raise RuntimeError("Embedding generator returned an empty batch")

        if vector_size is None:
            vector_size = len(batch.embeddings[0].vector)

            if vector_size == 0:
                raise RuntimeError("Embedding vectors must not be empty")

            await vector_indexer.create_collection(
                collection_name=collection_name,
                vector_size=vector_size,
            )

        if any(len(embedding.vector) != vector_size for embedding in batch.embeddings):
            raise RuntimeError("Inconsistent embedding dimensions")

        await vector_indexer.upsert(
            collection_name=collection_name,
            units=batch.units,
            embeddings=batch.embeddings,
        )

        indexed_count += len(batch.units)

    if indexed_count != len(units):
        raise RuntimeError(
            f"Incomplete embedding generation: "
            f"expected {len(units)} units, generated {indexed_count}"
        )

    await validate_collection(
        indexer=vector_indexer,
        collection_name=collection_name,
        expected_count=len(units),
    )

    await collection_publisher.publish(collection_name)

    return indexed_count


def _validate_units(units: list[LegalContentUnit]) -> None:
    if not units:
        raise ValueError("Document projection produced no legal content unit")

    first_unit = units[0]

    for unit in units[1:]:
        if unit.celex != first_unit.celex:
            raise ValueError("Projected units contain multiple CELEX identifiers")
        if unit.language != first_unit.language:
            raise ValueError("Projected units contain multiple languages")
        if unit.consolidation_date != first_unit.consolidation_date:
            raise ValueError("Projected units contain multiple consolidation dates")