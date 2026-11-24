from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from langchain_ollama import ChatOllama

from ai_service.agent.graph import build_assistant_graph
from ai_service.agent.llm_generator import LLMAnswerGenerator
from ai_service.agent.llm_router import LLMRequestRouter
from ai_service.config import get_settings
from ai_service.security.dependencies import (
    get_langgraph_assistant_turn_processor,
    get_mcp_document_retriever,
    get_pii_protection_service,
    get_prompt_injection_detector,
    get_tool_provider,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()

    try:
        model = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
        )

        request_router = LLMRequestRouter(model)
        answer_generator = LLMAnswerGenerator(
            model=model,
            language=settings.assistant_default_language,
        )

        pii_service = get_pii_protection_service()
        injection_detector = get_prompt_injection_detector(settings.prompt_injection_detector_model
                                                           ,settings.prompt_injection_threshold)

        async with AsyncExitStack() as exit_stack:
            tool_provider = await exit_stack.enter_async_context(
                get_tool_provider(settings.mcp_server_url)
            )

            document_retriever = get_mcp_document_retriever(tool_provider)
            assistant_graph = build_assistant_graph(
                pii_service=pii_service,
                injection_detector=injection_detector,
                language=settings.assistant_default_language,
                router=request_router,
                retriever=document_retriever,
                answer_generator=answer_generator,
            )

            app.state.request_router = request_router
            app.state.answer_generator = answer_generator
            app.state.document_retriever = document_retriever
            app.state.assistant_turn_processor = get_langgraph_assistant_turn_processor(
                assistant_graph
            )

            yield
    finally:
        app.state.meter_provider.shutdown()
        app.state.tracer_provider.shutdown()
        app.state.logger_provider.shutdown()
