from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_ollama import ChatOllama
import uvicorn

from ai_service.agent.llm_generator import LLMAnswerGenerator
from ai_service.agent.llm_router import LLMRequestRouter
from ai_service.api.router import api_router
from ai_service.config import get_settings
from ai_service.logging_config import configure_logging
from ai_service.observability import configure_observability


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()

    try:
        model = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
        )

        app.state.request_router = LLMRequestRouter(model)
        app.state.answer_generator = LLMAnswerGenerator(
            model=model,
            language=settings.assistant_default_language,
        )

        yield
    finally:
        app.state.meter_provider.shutdown()
        app.state.tracer_provider.shutdown()
        app.state.logger_provider.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="EU AI Act Assistant - AI Service",
        description="AI orchestration and RAG (Retrieval-Augmented Generation) service.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api_router)
    configure_observability(app)

    return app


app = create_app()


def main() -> None:
    settings = get_settings()

    uvicorn.run(
        "ai_service.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_environment == "development",
        log_config=None,
    )


if __name__ == "__main__":
    main()
