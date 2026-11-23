from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = Field(default=8001, gt=0, le=65535)
    streamable_http_path: str = "/mcp"

    qdrant_url: str = "http://localhost:6333"
    qdrant_active_alias: str = "eu_ai_act_documents_active"
    qdrant_timeout: int = Field(default=30, gt=0)

    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    ollama_timeout: float = Field(default=120.0, gt=0)


settings = Settings()
