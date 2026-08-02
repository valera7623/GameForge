"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=128)


class APIKeyCreate(BaseModel):
    name: str = "default"


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    key: Optional[str] = None  # only on create
    created_at: datetime

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str]
    role: str
    xp: int
    total_generations: int
    generations_this_month: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(UserResponse):
    plan: str = "free"
    generations_limit: int = 5
    achievements_count: int = 0


# ── Projects ──────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    engine: str = "unity"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    engine: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    engine: str
    cover_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    generations_count: int = 0

    model_config = {"from_attributes": True}


# ── Generations ───────────────────────────────────────────────────────


class GenerationResponse(BaseModel):
    id: UUID
    tool: str
    status: str
    title: Optional[str]
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]]
    asset_urls: Optional[List[Any]]
    error_message: Optional[str]
    xp_awarded: int
    project_id: Optional[UUID]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Tools ─────────────────────────────────────────────────────────────


class LevelDesignerRequest(BaseModel):
    project_id: Optional[UUID] = None
    description: str = Field(min_length=5, max_length=2000)
    width: int = Field(default=32, ge=8, le=128)
    height: int = Field(default=32, ge=8, le=128)
    style: str = "dungeon"


class QuestGeneratorRequest(BaseModel):
    project_id: Optional[UUID] = None
    setting: str = Field(min_length=3, max_length=500)
    quest_type: str = Field(default="side", pattern="^(main|side)$")
    length: str = Field(default="medium", pattern="^(short|medium|long)$")
    tone: str = "adventure"


class TextureUpscalerRequest(BaseModel):
    project_id: Optional[UUID] = None
    scale: int = Field(default=2, ge=2, le=4)
    enhance: bool = True


class CharacterCreatorRequest(BaseModel):
    project_id: Optional[UUID] = None
    description: str = Field(min_length=5, max_length=1000)
    style: str = "fantasy"
    view: str = "full_body"


class SoundDesignerRequest(BaseModel):
    project_id: Optional[UUID] = None
    description: str = Field(min_length=5, max_length=1000)
    kind: str = Field(default="sfx", pattern="^(sfx|music)$")
    mood: str = "dark"
    duration_sec: int = Field(default=5, ge=1, le=60)


class PlaytesterRequest(BaseModel):
    project_id: Optional[UUID] = None
    game_description: str = Field(min_length=10, max_length=5000)
    scenarios: List[str] = Field(default_factory=list)
    focus: str = "bugs"  # bugs | balance | ux | all


class LocalizationRequest(BaseModel):
    project_id: Optional[UUID] = None
    texts: dict[str, str]  # key -> source text
    source_lang: str = "en"
    target_langs: List[str] = Field(default_factory=lambda: ["ru", "es", "de", "fr", "ja"])
    export_format: str = Field(default="json", pattern="^(json|csv)$")


# ── Billing ───────────────────────────────────────────────────────────


class CheckoutRequest(BaseModel):
    plan: str = Field(pattern="^(indie|studio)$")
    provider: Optional[str] = None  # stripe | yukassa
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: Optional[str] = None


class PlanInfo(BaseModel):
    id: str
    name: str
    price_cents: int
    generations: int
    features: List[str]


# ── Dashboard / Gamification ──────────────────────────────────────────


class DashboardStats(BaseModel):
    total_generations: int
    generations_this_month: int
    generations_limit: int
    xp: int
    xp_this_month: int = 0
    plan: str
    projects_count: int
    recent_generations: List[GenerationResponse]
    achievements: List[dict[str, Any]]
    leaderboard_rank: Optional[int] = None


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    full_name: Optional[str]
    email_masked: str
    xp: int
    total_generations: int
