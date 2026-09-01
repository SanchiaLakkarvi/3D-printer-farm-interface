from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "3D Printer Farm Backend"
    app_env: str = "development"
    api_v1_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://printfarm:printfarm@localhost:5432/printfarm"

    # Auth: "fake" for tests/local without Supabase; "supabase" for real Auth.
    auth_adapter: str = "fake"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    jwt_secret_key: str = "replace-me-with-a-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:3000"

    file_storage_root: str = "./storage"
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB

    printer_adapter: str = "mock"
    mock_printer_base_url: str = "http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()
