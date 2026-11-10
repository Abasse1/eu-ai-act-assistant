import httpx

from ingestion_worker.infrastructure.sources.eur_lex import EurLexSource


async def fetch_formex_documents() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        source = EurLexSource(client)

        for language in ("fr", "en"):
            content = await source.fetch_formex(language)
            print(f"{language.upper()} Formex size: {len(content)} bytes")
            print(f"Header: {content[:100]!r}")
