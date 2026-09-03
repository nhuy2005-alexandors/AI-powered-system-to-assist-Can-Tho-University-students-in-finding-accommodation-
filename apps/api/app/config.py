from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    database_url: str = "postgresql+psycopg://nckh:nckh@db:5432/nckh"
    redis_url: str = "redis://redis:6379/0"

    # bật scheduler crawler trong app (tắt mặc định: dev/test không tự crawl ra mạng)
    crawler_enabled: bool = False

    # auth (Sprint 1.9). Secret THẬT đặt trong .env, KHÔNG commit.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    google_client_id: str = ""  # bắt buộc khi dùng Google login

    ors_api_key: str = ""  # OpenRouteService — route time/geometry; rỗng = tắt routing

    # Room-service AI. `auto`: Qwen local -> Gemini nếu có khóa -> template grounded.
    chatbot_embedding_model: str = "intfloat/multilingual-e5-small"
    chatbot_confidence_threshold: float = 0.65
    chatbot_max_results: int = 5
    chatbot_llm_provider: Literal["auto", "qwen", "gemini", "template"] = "auto"
    chatbot_llm_timeout_seconds: float = 120.0

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Không ghi khóa thật vào source; chỉ đặt GEMINI_API_KEY trong .env/runtime.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.7-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    risk_auto_assess: bool = True
    risk_auto_assess_limit: int = 1000


settings = Settings()
