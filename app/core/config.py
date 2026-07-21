"""Configuración centralizada leída desde variables de entorno y .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Valores configurables del MVP con valores seguros para desarrollo local."""

    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    database_url: str = "sqlite:///./portoasiste.db"
    faiss_index_dir: Path = PROJECT_ROOT / "faiss_index"
    generated_pdfs_dir: Path = PROJECT_ROOT / "generated_pdfs"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte CORS_ORIGINS separado por comas a una lista para FastAPI."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_runtime_directories(self) -> None:
        """Crea directorios generados que no deben versionarse."""
        self.faiss_index_dir.mkdir(parents=True, exist_ok=True)
        self.generated_pdfs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Entrega una única instancia de configuración por proceso."""
    return Settings()
