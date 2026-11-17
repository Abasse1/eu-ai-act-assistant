from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INGESTION_")

    ollama_base_url: str = "http://ollama:11434"
    ollama_embedding_model: str = "qwen3-embedding"
    embedding_batch_size: int = 32
    embedding_timeout: float = 120.0

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "eu_ai_act_documenrts"
    qdrant_timeout: float = 30.0


settings = Settings()
