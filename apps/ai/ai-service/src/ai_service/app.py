from fastapi import FastAPI

from ai_service.api.router import api_router
from ai_service.config import get_settings
from ai_service.lifespan import lifespan
from ai_service.logging_config import configure_logging
from ai_service.observability import configure_observability


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


app:FastAPI = create_app()
