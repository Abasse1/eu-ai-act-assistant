from typing import Final

import httpx

from ingestion_worker.domain.documents import DocumentLanguage

CELEX: Final = "02024R1689-20260727"
CONSOLIDATION_DATE: Final = __import__("datetime").date(2026, 7, 27)


class EurLexSource:
    BASE_URL: Final = "https://eur-lex.europa.eu/legal-content"
    CELLAR_BASE_URL: Final = "https://publications.europa.eu/resource"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def document_url(self, language: DocumentLanguage) -> str:
        return f"{self.BASE_URL}/{language.upper()}/TXT/?uri=CELEX:{CELEX}"

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
