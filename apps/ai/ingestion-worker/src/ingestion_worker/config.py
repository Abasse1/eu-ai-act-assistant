from pydantic_settings import BaseSettings, SettingsConfigDict

from ingestion_worker.domain.documents import DocumentLanguage


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INGESTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://ollama:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    embedding_batch_size: int = 32
    embedding_timeout: float = 120.0

    qdrant_url: str = "http://qdrant:6333"
    qdrant_active_alias: str = "eu_ai_act_documents_active"
    qdrant_timeout: int = 30

    eur_lex_timeout: int = 30
    document_language: DocumentLanguage = "fr"


settings = Settings()
