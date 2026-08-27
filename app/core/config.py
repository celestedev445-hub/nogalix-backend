from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Nogalix"
    app_env: str = "local"
    app_debug: bool = True
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    frontend_urls: str = "http://localhost:3000,http://127.0.0.1:3000"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_database: str = "nogalix"
    db_username: str = "root"
    db_password: str = ""

    auth_token_ttl_minutes: int = 1440

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    cloudinary_url: str = ""
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder_prefix: str = "nogalix"

    mail_host: str = ""
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_from_address: str = "contact@nogalix.com"
    mail_from_name: str = "Nogalix"
    contact_to_email: str = "contact@nogalix.com"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    gemini_enabled: bool = False
    gemini_max_output_tokens: int = 512

    assistant_name: str = "Noga"
    admin_emails: str = ""

    @property
    def database_url(self) -> str:
        password = self.db_password or ""
        auth = self.db_username
        if password:
            auth = f"{self.db_username}:{password}"
        return (
            f"mysql+pymysql://{auth}@{self.db_host}:{self.db_port}/"
            f"{self.db_database}?charset=utf8mb4"
        )

    @property
    def cors_origins(self) -> List[str]:
        raw = self.frontend_urls or self.frontend_url
        origins = [item.strip() for item in raw.split(",") if item.strip()]
        if self.app_env.lower() in {"local", "development", "dev", "test"}:
            defaults = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
            for item in defaults:
                if item not in origins:
                    origins.append(item)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
