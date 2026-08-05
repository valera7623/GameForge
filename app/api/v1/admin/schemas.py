"""Admin API schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AdminMeOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    permissions: list[str]


class DashboardOut(BaseModel):
    users_total: int
    generations_total: int
    revenue_usd_estimate: float
    activity_pct: float
    generations_last_7_days: list[dict[str, Any]]
    recent_users: list[dict[str, Any]]
    ai_spend_usd_7d: float = 0.0


class AdminUserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    plan: Optional[str] = None
    generations_this_month: int
    generations_limit: int
    total_generations: int
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_verified: Optional[bool] = None


class AdminRoleUpdate(BaseModel):
    role: str


class AdminGenerationOut(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    tool: str
    status: str
    title: Optional[str] = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    xp_awarded: int = 0
    project_id: Optional[UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    client_ip: Optional[str] = None
    duration_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    model_name: Optional[str] = None


class AdminGenerationListOut(BaseModel):
    items: list[AdminGenerationOut]
    total: int
    page: int
    page_size: int


class GenerationStatsOut(BaseModel):
    by_tool: list[dict[str, Any]]
    by_status: list[dict[str, Any]]
    last_7_days: list[dict[str, Any]]
    total: int


class AdminSubscriptionOut(BaseModel):
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    plan: str
    status: str
    generations_limit: int
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
    created_at: datetime


class AdminSubscriptionListOut(BaseModel):
    items: list[AdminSubscriptionOut]
    total: int
    page: int
    page_size: int


class AdminToolOut(BaseModel):
    name: str
    display_name: str
    enabled: bool


class AdminToolsOut(BaseModel):
    tools: list[AdminToolOut]


class AdminToolUpdate(BaseModel):
    display_name: Optional[str] = None
    enabled: Optional[bool] = None


class GeneralSettingsOut(BaseModel):
    app_name: str = "GameForge"
    domain: str = "gameforge.website"
    notes: str = ""


class GeneralSettingsUpdate(BaseModel):
    app_name: Optional[str] = None
    domain: Optional[str] = None
    notes: Optional[str] = None


class AiModelsOut(BaseModel):
    models: dict[str, Any]


class AiModelsUpdate(BaseModel):
    models: dict[str, Any]


class AiCostsOut(BaseModel):
    total_usd: float
    by_tool: list[dict[str, Any]]
    by_day: list[dict[str, Any]]
    by_model: list[dict[str, Any]]


class AuditLogOut(BaseModel):
    id: UUID
    actor_id: Optional[UUID] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    meta: dict[str, Any] = Field(default_factory=dict)
    ip: Optional[str] = None
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int


class ErrorLogOut(BaseModel):
    id: UUID
    source: str
    message: str
    status_code: Optional[int] = None
    path: Optional[str] = None
    user_id: Optional[UUID] = None
    generation_id: Optional[UUID] = None
    request_id: Optional[str] = None
    created_at: datetime


class ErrorLogListOut(BaseModel):
    items: list[ErrorLogOut]
    total: int
    page: int
    page_size: int


class ApiRequestLogOut(BaseModel):
    id: UUID
    method: str
    path: str
    status_code: int
    duration_ms: int
    user_id: Optional[UUID] = None
    ip: Optional[str] = None
    request_id: Optional[str] = None
    created_at: datetime


class ApiRequestLogListOut(BaseModel):
    items: list[ApiRequestLogOut]
    total: int
    page: int
    page_size: int


class PurgeLogsOut(BaseModel):
    deleted: dict[str, int]


class ContentItemOut(BaseModel):
    id: UUID
    kind: str
    slug: str
    locale: str
    title: str
    body_md: str
    body_html: str = ""
    excerpt: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: str
    sort_order: int = 0
    published_at: Optional[datetime] = None
    author_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ContentItemListOut(BaseModel):
    items: list[ContentItemOut]
    total: int
    page: int
    page_size: int


class ContentItemCreate(BaseModel):
    kind: str
    slug: str
    locale: str = "en"
    title: str
    body_md: str = ""
    excerpt: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    sort_order: int = 0


class ContentItemUpdate(BaseModel):
    slug: Optional[str] = None
    locale: Optional[str] = None
    title: Optional[str] = None
    body_md: Optional[str] = None
    excerpt: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    sort_order: Optional[int] = None


class SitemapUrlOut(BaseModel):
    loc: str
    lastmod: Optional[str] = None


class SitemapUrlsOut(BaseModel):
    urls: list[SitemapUrlOut]