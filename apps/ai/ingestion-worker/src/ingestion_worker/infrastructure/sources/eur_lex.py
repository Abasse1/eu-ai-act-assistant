from datetime import UTC, date, datetime
from typing import Final

import httpx
from pydantic import HttpUrl

from ingestion_worker.domain.documents import DocumentLanguage, SourceDocument

CELEX: Final = "02024R1689-20260727"
CONSOLIDATION_DATE: Final = date(2026, 7, 27)


class EurLexSource:
    BASE_URL: Final = "https://eur-lex.europa.eu/legal-content"
    CELLAR_BASE_URL: Final = "https://publications.europa.eu/resource"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch(self, language: DocumentLanguage) -> SourceDocument:
        url = f"{self.BASE_URL}/{language.upper()}/TXT/HTML/"
        response = await self._client.get(url, params={"uri": f"CELEX:{CELEX}"})
        response.raise_for_status()

        content_html = response.text
        if not content_html.strip():
            raise ValueError(f"EUR-Lex returned an empty document for language '{language}'.")

        return SourceDocument(
            celex=CELEX,
            language=language,
            consolidation_date=CONSOLIDATION_DATE,
            source_url=HttpUrl(str(response.url)),
            content_xml=content_html,
            retrieved_at=datetime.now(UTC),
        )

    async def fetch_formex(self, language: DocumentLanguage) -> bytes:
        response = await self._client.get(
            f"{self.CELLAR_BASE_URL}/celex/{CELEX}",
            headers={
                "Accept": "application/zip;mtype=fmx4",
                "Accept-Language": "eng" if language == "en" else "fra",
            },
            follow_redirects=True,
        )
        response.raise_for_status()

        if not response.content:
            raise ValueError(f"Cellar returned an empty Formex document for '{language}'.")

        return response.content
