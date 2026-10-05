import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # Google AI
    google_api_key: str
    chat_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"

    # PostgreSQL / Supabase
    db_host: str
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str
    db_password: str
    db_sslmode: str = "require"

    # Vector Store
    vector_table: str = "vector_store"
    vector_dimension: int = 3072
    top_k: int = 5
    similarity_threshold: float = 0.65

    # Server / Upload
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    max_upload_size_mb: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def connection_kwargs(self) -> dict:
        return {
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "sslmode": self.db_sslmode,
        }

@lru_cache()
def get_settings() -> Settings:
    return Settings()
