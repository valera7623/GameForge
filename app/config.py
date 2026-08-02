"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "AI Game Dev Toolkit"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gamedev:gamedev@postgres:5432/gamedev"
    DATABASE_URL_SYNC: str = "postgresql://gamedev:gamedev@postgres:5432/gamedev"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60

    # AI providers (OpenAI via ProxyAPI by default)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.proxyapi.ru/openai/v1"
    OPENAI_MODEL: str = "gpt-4o"
    STABILITY_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    USE_MOCK_AI: bool = True  # fallback when keys missing

    # Upscale / Music providers
    REALESRGAN_URL: str = ""  # e.g. http://realesrgan:8080
    REPLICATE_API_TOKEN: str = ""
    MUSICGEN_MODEL: str = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837932052"

    # Email
    EMAIL_PROVIDER: str = "console"  # console | smtp | resend
    EMAIL_FROM: str = "GameForge <noreply@gamedev.ai>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    RESEND_API_KEY: str = ""

    # Deployment
    DEPLOYMENT_MODE: str = "saas"  # saas | onprem
    DISABLE_BILLING: bool = False
    FORCE_PLAN: str = ""  # free|indie|studio|enterprise when onprem
    LICENSE_KEY: str = ""
    STUDIO_SEATS: int = 5

    # Storage (S3 / MinIO)
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "gamedev-assets"
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: str = "http://localhost:9000/gamedev-assets"

    # Billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_INDIE: str = ""
    STRIPE_PRICE_STUDIO: str = ""
    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""
    BILLING_PROVIDER: str = "stripe"  # stripe | yukassa

    # Plans
    FREE_GENERATIONS: int = 5
    INDIE_GENERATIONS: int = 100
    STUDIO_GENERATIONS: int = 1000
    INDIE_PRICE_CENTS: int = 1900
    STUDIO_PRICE_CENTS: int = 9900

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Frontend URL (password reset links)
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_onprem(self) -> bool:
        return self.DEPLOYMENT_MODE.lower() == "onprem"

    @property
    def billing_disabled(self) -> bool:
        return self.DISABLE_BILLING or self.is_onprem


@lru_cache
def get_settings() -> Settings:
    return Settings()
