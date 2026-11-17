from datetime import UTC, datetime

from pydantic import HttpUrl

from ingestion_worker.domain.documents import (
    DocumentLanguage,
    SourceDocument,
    StructuredLegalDocument,
)
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser
from ingestion_worker.infrastructure.parsing.formex_extractor import FormexExtractor
from ingestion_worker.infrastructure.sources.eur_lex import CELEX, CONSOLIDATION_DATE, EurLexSource


async def ingest_document(
    language: DocumentLanguage,
    source: EurLexSource,
    extractor: FormexExtractor,
    parser: EurLexParser,
) -> StructuredLegalDocument:
    archive = await source.fetch_formex(language)
    retrieved_at = datetime.now(UTC)

    files = extractor.extract(archive)

    document = SourceDocument(
        celex=CELEX,
        language=language,
        consolidation_date=CONSOLIDATION_DATE,
        source_url=HttpUrl(source.document_url(language)),
        retrieved_at=retrieved_at,
    )

    return parser.parse(
        xml_metadata=files.metadata_xml, xml_content=files.content_xml, document=document
    )
