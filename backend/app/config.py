from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://ecostream:password@localhost:5432/ecostream_db"
    secret_key: str = "changeme"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    groq_api_key: str = ""
    # Legacy / optional fallbacks
    openai_api_key: str = ""
    ollama_host: str = "http://localhost:11434"

    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_dir: str = "data/chroma_db"

    yolo_model_path: str = "ml-models/yolo/weights/best.pt"
    yolo_conf_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45

    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 10
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ("../.env", ".env")  # project root first, then current dir fallback
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
