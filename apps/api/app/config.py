from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


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

    # Internal mobility lane. No live Google request is enabled by this foundation.
    mobility_enabled: bool = False
    mobility_database_url: SecretStr = SecretStr("")  # independent read-only catalog target
    google_live_enabled: bool = False
    google_server_api_key: SecretStr = SecretStr("")


settings = Settings()
