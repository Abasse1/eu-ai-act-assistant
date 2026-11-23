from typing import Any

from mcp.server import MCPServer

from mcp_server.application.models.legal_document import DocumentLanguage
from mcp_server.application.search_legal_document import (
    SearchLegalDocumentRequest,
    SearchLegalDocuments,
)


def register_search_legal_documents_tools(
    server: MCPServer,
    use_case: SearchLegalDocuments,
) -> None:
    @server.tool(
        name="search_legal_documents",
        description=(
            "Search the European Union AI Act using semantic search. "
            "Returns relevant legal passages with their references, "
            "consolidation date and source URL."
        ),
        structured_output=True,
    )
    async def search_legal_documents(
        query: str,
        top_k: int = 5,
        language: DocumentLanguage = "fr",
    ) -> list[dict[str, Any]]:
        request = SearchLegalDocumentRequest(
            query=query,
            top_k=top_k,
            language=language,
        )

        results = await use_case.execute(request=request)

        return [result.model_dump(mode="json") for result in results]