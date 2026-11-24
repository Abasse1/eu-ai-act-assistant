from collections.abc import Mapping
from typing import cast
from unittest.mock import AsyncMock

import pytest

from ai_service.contracts.tool_call_result import ToolCallResult
from ai_service.infrastructure.mcp.mcp_document_retriever import McpDocumentRetriever


@pytest.mark.anyio
async def test_retrieve_maps_mcp_results_to_retrieved_documents() -> None:
    tool_provider = AsyncMock()

    tool_provider.call_tool.return_value = ToolCallResult(
        is_error=False,
        structured_content=cast(
            Mapping[str, object],
            {
                "result": [
                    {
                        "id": "d11f8a43-8162-5e9d-a0e0-1b2bf50348e8",
                        "type": "article",
                        "content": "Contenu de l'article 50, paragraphe 6.",
                        "score": 0.80436486,
                        "article_number": "50",
                        "paragraph_number": "6.",
                        "alinea_index": 1,
                        "subdivision_path": [],
                        "annex_title": None,
                        "celex": "02024R1689-20260727",
                        "consolidation_date": "2026-07-27",
                        "source_url": "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02024R1689-20260727",
                        "language": "fr",
                        "metadata": {},
                    }
                ]
            },
        ),
    )

    retriever = McpDocumentRetriever(tool_provider)

    documents = await retriever.retrieve("Quelles sont les obligations de transparence ?")

    assert len(documents) == 1
    assert documents[0].citation.reference == "Article 50, paragraphe 6."
    assert documents[0].citation.article == "50"
    assert documents[0].citation.version == "2026-07-27"
    assert documents[0].score == pytest.approx(0.80436486)

    tool_provider.call_tool.assert_awaited_once_with(
        "search_legal_documents",
        {"query": "Quelles sont les obligations de transparence ?"},
    )
