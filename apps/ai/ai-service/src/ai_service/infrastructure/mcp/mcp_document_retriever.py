from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from ai_service.agent.retrieval import DocumentRetriever
from ai_service.application.ports.tool_provider import ToolProvider
from ai_service.contracts.conversation import Citation
from ai_service.contracts.retrieval import RetrievedDocument


class McpLegalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    content: str
    score: float = Field(ge=0.0, le=1.0)
    article_number: str | None = None
    paragraph_number: str | None = None
    alinea_index: int | None = None
    subdivision_path: list[str] = Field(default_factory=list[str])
    annex_title: str | None = None
    celex: str
    consolidation_date: str
    source_url: HttpUrl
    language: str
    metadata: Mapping[str, object] = Field(default_factory=dict)


class McpSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: list[McpLegalDocument]


class McpDocumentRetriever(DocumentRetriever):
    _TOOL_NAME = "search_legal_documents"

    def __init__(self, tool_provider: ToolProvider) -> None:
        self._tool_provider = tool_provider

    async def retrieve(self, question: str) -> list[RetrievedDocument]:
        result = await self._tool_provider.call_tool(
            self._TOOL_NAME,
            {"query": question},
        )

        if result.is_error:
            raise RuntimeError("MCP legal document search failed.")

        if result.structured_content is None:
            raise RuntimeError("MCP legal document search returned no structured content.")

        response = McpSearchResponse.model_validate(result.structured_content)

        return [self._to_retrieved_document(document) for document in response.result]

    @staticmethod
    def _to_retrieved_document(document: McpLegalDocument) -> RetrievedDocument:
        citation = Citation(
            document_title=None,
            reference=McpDocumentRetriever._build_reference(document),
            passage=document.content,
            article=document.article_number,
            version=document.consolidation_date,
            source_url=document.source_url,
            withdrawn_at=None,
        )

        return RetrievedDocument(
            citation=citation,
            score=document.score,
        )

    @staticmethod
    def _build_reference(document: McpLegalDocument) -> str:
        parts: list[str] = []

        if document.article_number:
            parts.append(f"Article {document.article_number}")

        if document.paragraph_number:
            parts.append(f"paragraphe {document.paragraph_number}")

        parts.extend(document.subdivision_path)

        if not parts and document.annex_title:
            parts.append(document.annex_title)

        if not parts:
            parts.append(document.celex)

        return ", ".join(parts)
