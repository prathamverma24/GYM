from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "AthleteOS API"
    api_prefix: str = "/api/v1"
    web_origin: str = "http://localhost:3000"
    database_url: str = "sqlite:///./athleteos.db"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = "local-development-secret-change-before-deploy"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 168
    auto_create_db: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

