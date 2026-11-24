import uvicorn

from ai_service.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "ai_service.app:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.app_environment == "development",
        log_config=None,
    )


if __name__ == "__main__":
    main()
