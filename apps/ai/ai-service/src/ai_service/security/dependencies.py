from langgraph.graph.state import CompiledStateGraph
from wrapt import lru_cache

from ai_service.agent.retrieval import DocumentRetriever
from ai_service.agent.state import AssistantTurnState
from ai_service.application.langgraph_assistant_turn import LangGraphAssistantTurnProcessor
from ai_service.application.ports.assistant_turn import AssistantTurnProcessor
from ai_service.application.ports.tool_provider import ToolProvider
from ai_service.infrastructure.mcp.mcp_document_retriever import McpDocumentRetriever
from ai_service.infrastructure.mcp.mcp_tool_provider import McpToolProvider
from ai_service.privacy.pii import PiiAnonymizer, PiiProtectionService
from ai_service.security.huggingface_detector import HuggingFacePromptInjectionDetector
from ai_service.application.ports.prompt_injection import PromptInjectionDetector


@lru_cache(maxsize=1)
def get_prompt_injection_detector(model_name: str,threshold: float = 0.85) -> PromptInjectionDetector:
    return HuggingFacePromptInjectionDetector(model_name,threshold)


@lru_cache(maxsize=1)
def get_pii_protection_service() -> PiiAnonymizer:
    return PiiProtectionService()

def get_tool_provider(server_url: str) -> ToolProvider:
    return McpToolProvider(server_url)

def get_mcp_document_retriever(tool_provider: ToolProvider) -> DocumentRetriever:
    return McpDocumentRetriever(tool_provider)


def get_langgraph_assistant_turn_processor(
    graph: CompiledStateGraph[
        AssistantTurnState,
        None,
        AssistantTurnState,
        AssistantTurnState,
    ],
) -> AssistantTurnProcessor:
    return LangGraphAssistantTurnProcessor(graph)
