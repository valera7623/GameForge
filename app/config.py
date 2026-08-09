"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = frozenset(
    {
        "change-me-in-production-use-openssl-rand-hex-32",
        "change-me-use-openssl-rand-hex-32",
        "secret",
        "changeme",
        "",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "AI Game Dev Toolkit"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"
    ALLOW_MOCK_BILLING: bool = True  # forced False in production gate
    # Temporary escape hatch until SMTP/Resend keys are configured
    ALLOW_INSECURE_EMAIL: bool = False

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
    # ProxyAPI / OpenAI image models (dall-e-3 is retired; use gpt-image-*)
    OPENAI_IMAGE_MODEL: str = "gpt-image-1-mini"
    OPENAI_TIMEOUT_SEC: float = 180.0
    # Character / image gen: auto (openai→stability) | openai | stability
    IMAGE_PROVIDER: str = "auto"
    # Cloud Stability AI (https://platform.stability.ai) — no self-hosted SD needed
    STABILITY_API_KEY: str = ""
    # core | ultra | sd3 | sd3.5-large | sd3.5-large-turbo | sd3.5-medium | sd3.5-flash
    STABILITY_IMAGE_MODEL: str = "core"
    # Sound Designer: stable-audio-2.5 (default) | stable-audio-2 | stable-audio-3
    STABILITY_AUDIO_MODEL: str = "stable-audio-2.5"
    STABILITY_AUDIO_FORMAT: str = "mp3"
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
    # Browser-facing endpoint for presigned URLs (e.g. https://gameforge.website/s3)
    S3_PUBLIC_ENDPOINT: str = ""
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
    # Russia-first: YuKassa + RUB (price_* are kopecks / minor units)
    BILLING_PROVIDER: str = "yukassa"
    BILLING_CURRENCY: str = "RUB"
    # 54-FZ receipt for YuKassa (1 = без НДС). Set 0 to omit receipt payload.
    YUKASSA_VAT_CODE: int = 1

    # Plans — RUB prices in kopecks (1990.00 ₽ → 199000)
    FREE_GENERATIONS: int = 5
    INDIE_GENERATIONS: int = 100
    STUDIO_GENERATIONS: int = 1000
    INDIE_PRICE_CENTS: int = 199_000
    STUDIO_PRICE_CENTS: int = 999_000

    # LocForge word packs (one-time credits, RUB kopecks)
    LOC_STARTER_PRICE_CENTS: int = 499_000
    LOC_INDIE_PRICE_CENTS: int = 1_499_000
    LOC_STUDIO_PRICE_CENTS: int = 3_999_000
    LOC_STARTER_WORDS: int = 5000
    LOC_INDIE_WORDS: int = 25000
    LOC_STUDIO_WORDS: int = 100000

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


def _is_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
    except Exception:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_settings(settings: Settings) -> None:
    """Fail closed in production."""
    if not settings.is_production:
        return
    errors: list[str] = []
    if settings.SECRET_KEY in _INSECURE_SECRETS or len(settings.SECRET_KEY) < 32:
        errors.append("SECRET_KEY must be a strong value (≥32 chars) in production")
    if settings.DEBUG:
        errors.append("DEBUG must be false in production")
    if "*" in settings.CORS_ORIGINS:
        errors.append("CORS_ORIGINS must not contain * in production")
    if not settings.cors_origins_list:
        errors.append("CORS_ORIGINS must list explicit origins in production")
    for origin in settings.cors_origins_list:
        if not _is_https_url(origin):
            errors.append(f"CORS_ORIGINS must use HTTPS in production (got {origin!r})")
    if not _is_https_url(settings.FRONTEND_URL):
        errors.append("FRONTEND_URL must be HTTPS in production")
    if settings.ALLOW_MOCK_BILLING:
        errors.append("ALLOW_MOCK_BILLING must be false in production")
    # USE_MOCK_AI=true is allowed in production to avoid paid provider spend
    if not settings.USE_MOCK_AI and not settings.OPENAI_API_KEY.strip():
        errors.append("OPENAI_API_KEY is required when USE_MOCK_AI=false")

    provider = settings.EMAIL_PROVIDER.lower().strip()
    if provider == "console":
        if not settings.ALLOW_INSECURE_EMAIL:
            errors.append(
                "EMAIL_PROVIDER must be smtp or resend in production "
                "(set ALLOW_INSECURE_EMAIL=true only as a temporary escape hatch)"
            )
    elif provider == "smtp":
        if not settings.ALLOW_INSECURE_EMAIL and not settings.SMTP_HOST.strip():
            errors.append("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
    elif provider == "resend":
        if not settings.ALLOW_INSECURE_EMAIL and not settings.RESEND_API_KEY.strip():
            errors.append("RESEND_API_KEY is required when EMAIL_PROVIDER=resend")
    else:
        errors.append("EMAIL_PROVIDER must be smtp or resend in production")

    if not settings.billing_disabled:
        provider = settings.BILLING_PROVIDER.lower().strip()
        has_stripe = bool(settings.STRIPE_SECRET_KEY.strip() and settings.STRIPE_WEBHOOK_SECRET.strip())
        has_yukassa = bool(settings.YUKASSA_SHOP_ID.strip() and settings.YUKASSA_SECRET_KEY.strip())
        if provider == "yukassa":
            if not has_yukassa:
                errors.append(
                    "BILLING_PROVIDER=yukassa but YUKASSA_SHOP_ID / YUKASSA_SECRET_KEY are missing — "
                    "set DISABLE_BILLING=true or configure YuKassa"
                )
        elif provider == "stripe":
            if not has_stripe:
                errors.append(
                    "BILLING_PROVIDER=stripe but Stripe keys are missing — "
                    "set DISABLE_BILLING=true or configure Stripe"
                )
        elif not has_stripe and not has_yukassa:
            errors.append(
                "Billing is enabled but Stripe/YuKassa keys are missing — "
                "set DISABLE_BILLING=true or configure a payment provider"
            )

    if errors:
        raise RuntimeError("Production settings invalid:\n- " + "\n- ".join(errors))


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    validate_settings(s)
    return s
