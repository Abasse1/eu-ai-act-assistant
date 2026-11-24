from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

from ai_service.contracts.conversation import Language


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    log_level: str = "INFO"

    app_environment: Literal["development", "acceptance", "production"] = "development"

    otel_service_name: str = "EuAiAct.AI"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "http://grafana:3000"

    assistant_default_language: Language = "fr"

    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3:8b"
    ollama_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    mcp_server_url: str = "http://mcp-server:8001/mcp"

    prompt_injection_detector_model: str = '/opt/models/prompt-injection-guard-small'
    prompt_injection_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
