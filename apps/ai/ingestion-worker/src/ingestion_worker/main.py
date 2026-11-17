import asyncio

import httpx

from ingestion_worker.application.ingest_document import (
    ingest_document as ingest_document_use_case,
)
from ingestion_worker.domain.documents import DocumentLanguage, LegalDivision
from ingestion_worker.infrastructure.parsing.eur_lex_parser import EurLexParser
from ingestion_worker.infrastructure.parsing.formex_extractor import FormexExtractor
from ingestion_worker.infrastructure.sources.eur_lex import EurLexSource

async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        source = EurLexSource(client)
        extractor = FormexExtractor()
        parser = EurLexParser()

        languages: tuple[DocumentLanguage, ...] = ("fr", "en")

        for language in languages:
            document = await ingest_document_use_case(
                language=language,
                source=source,
                extractor=extractor,
                parser=parser,
            )
            print(f"\n=== {document.language.upper()} STRUCTURE ===")

            top_level_divisions = [
                item for item in document.body if isinstance(item, LegalDivision)
            ]

            nested_divisions = [
                child
                for division in top_level_divisions
                for child in division.children
                if isinstance(child, LegalDivision)
            ]

            print(f"Top-level divisions: {len(top_level_divisions)}")
            print(f"Nested divisions: {len(nested_divisions)}")
            print(f"Total articles: {len(document.articles)}")

            for division in top_level_divisions:
                print(f"\n{division.title} (level={division.level})")

                for child in division.children:
                    if isinstance(child, LegalDivision):
                        print(f"  {child.title} (level={child.level})")


if __name__ == "__main__":
    asyncio.run(main())
