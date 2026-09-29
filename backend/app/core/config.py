import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Assimilate Automation Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & JWT
    JWT_SECRET_KEY: str = "assimilate-super-secret-jwt-key-2026-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database Configuration (Multi-Tenant Approach A)
    MASTER_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/assimilate_master_db"
    TENANT_TEMPLATE_DB_NAME: str = "tenant_template_db"
    TENANT_DATABASE_BASE_URL: str = "postgresql://postgres:postgres@localhost:5432/"

    # GitHub App Credentials
    GITHUB_APP_ID: str = "123456"
    GITHUB_APP_PRIVATE_KEY_PATH: str = "private-key.pem"
    GITHUB_WEBHOOK_SECRET: str = "default-webhook-secret-change-in-prod-min-32-chars"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v


settings = Settings()
