"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET = "change-me-in-production-use-openssl-rand-hex-32"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "AI Game Dev Toolkit"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = _INSECURE_SECRET
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"
    ALLOW_MOCK_BILLING: bool = True  # forced False in production gate

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://gamedev:gamedev@postgres:5432/gamedev"
    DATABASE_URL_SYNC: str = "postgresql://gamedev:gamedev@postgres:5432/gamedev"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # JWT / cookies
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    ACCESS_COOKIE: str = "gf_access"
    REFRESH_COOKIE: str = "gf_refresh"

    # AI providers
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.proxyapi.ru/openai/v1"
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_TIMEOUT_SEC: float = 90.0
    STABILITY_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    USE_MOCK_AI: bool = True

    REALESRGAN_URL: str = ""
    REPLICATE_API_TOKEN: str = ""
    MUSICGEN_MODEL: str = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837932052"

    # Email
    EMAIL_PROVIDER: str = "console"
    EMAIL_FROM: str = "GameForge <noreply@gamedev.ai>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    RESEND_API_KEY: str = ""

    # Deployment
    DEPLOYMENT_MODE: str = "saas"
    DISABLE_BILLING: bool = False
    FORCE_PLAN: str = ""
    LICENSE_KEY: str = ""
    STUDIO_SEATS: int = 5

    # Storage
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "gamedev-assets"
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: str = "http://localhost:9000/gamedev-assets"
    S3_USE_SIGNED_URLS: bool = True
    S3_SIGNED_URL_EXPIRE_SEC: int = 3600
    S3_PUBLIC_READ: bool = False  # anonymous bucket access

    # Billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_INDIE: str = ""
    STRIPE_PRICE_STUDIO: str = ""
    STRIPE_PORTAL_RETURN_URL: str = ""
    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""
    BILLING_PROVIDER: str = "stripe"

    # Plans
    FREE_GENERATIONS: int = 5
    INDIE_GENERATIONS: int = 100
    STUDIO_GENERATIONS: int = 1000
    INDIE_PRICE_CENTS: int = 1900
    STUDIO_PRICE_CENTS: int = 9900

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20

    # Observability
    SENTRY_DSN: str = ""
    LOG_JSON: bool = False

    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_onprem(self) -> bool:
        return self.DEPLOYMENT_MODE.lower() == "onprem"

    @property
    def billing_disabled(self) -> bool:
        return self.DISABLE_BILLING or self.is_onprem

    @property
    def mock_billing_allowed(self) -> bool:
        if self.is_production:
            return False
        return self.ALLOW_MOCK_BILLING and self.APP_ENV.lower() in ("development", "test", "dev")


def validate_settings(settings: Settings) -> None:
    """Fail closed in production."""
    if not settings.is_production:
        return
    errors: list[str] = []
    if settings.SECRET_KEY in (_INSECURE_SECRET, "", "secret", "changeme"):
        errors.append("SECRET_KEY must be set to a strong value in production")
    if settings.DEBUG:
        errors.append("DEBUG must be false in production")
    if "*" in settings.CORS_ORIGINS:
        errors.append("CORS_ORIGINS must not contain * in production")
    if not settings.cors_origins_list:
        errors.append("CORS_ORIGINS must list explicit origins in production")
    if settings.ALLOW_MOCK_BILLING:
        errors.append("ALLOW_MOCK_BILLING must be false in production")
    if errors:
        raise RuntimeError("Production settings invalid:\n- " + "\n- ".join(errors))


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    validate_settings(s)
    return s
