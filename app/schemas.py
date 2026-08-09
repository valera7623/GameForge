"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

# ── Auth ──────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=128)


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
    style: str = Field(
        default="dungeon",
        pattern="^(dungeon|cave|temple|city|winter|sci_fi|desert)$",
    )
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")


class LevelDesignerSaveRequest(BaseModel):
    """Persist an edited tilemap back onto an existing generation (no quota)."""

    output_data: dict[str, Any]
    project_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, max_length=200)


class QuestGeneratorRequest(BaseModel):
    project_id: Optional[UUID] = None
    setting: str = Field(min_length=3, max_length=500)
    quest_type: str = Field(default="side", pattern="^(main|side|daily)$")
    length: str = Field(default="medium", pattern="^(short|medium|long)$")
    tone: str = Field(
        default="adventure",
        pattern="^(adventure|dark|heroic|mystery|humorous|tragic|horror|epic)$",
    )


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


class GameBalancerRequest(BaseModel):
    """JSON game parameters for balance analysis."""

    project_id: Optional[UUID] = None
    game_name: str = Field(default="Untitled Game", max_length=200)
    version: str = Field(default="1.0.0", max_length=64)
    lang: str = Field(default="en", pattern="^(en|ru)$")
    classes: List[dict] = Field(default_factory=list)
    enemies: List[dict] = Field(default_factory=list)
    weapons: List[dict] = Field(default_factory=list)
    abilities: List[dict] = Field(default_factory=list)
    economy: dict = Field(default_factory=dict)

    def to_game_data(self) -> dict:
        return {
            "game_name": self.game_name,
            "version": self.version,
            "lang": self.lang,
            "classes": self.classes,
            "enemies": self.enemies,
            "weapons": self.weapons,
            "abilities": self.abilities,
            "economy": self.economy,
        }

    @model_validator(mode="after")
    def _require_payload(self) -> "GameBalancerRequest":
        if not (self.classes or self.enemies or self.weapons or self.abilities or self.economy):
            raise ValueError("Provide at least one of: classes, enemies, weapons, abilities, economy")
        return self


class LevelAnalyzerRequest(BaseModel):
    """Level map JSON for playability / difficulty analysis."""

    project_id: Optional[UUID] = None
    level_name: str = Field(default="Untitled Level", max_length=200)
    width: Optional[int] = Field(default=None, ge=1, le=200)
    height: Optional[int] = Field(default=None, ge=1, le=200)
    tiles: List[List[Any]] = Field(default_factory=list)
    legend: dict = Field(default_factory=dict)
    entities: List[dict] = Field(default_factory=list)
    time_limit: Optional[int] = Field(default=None, ge=0, le=86400)
    lang: str = Field(default="en", pattern="^(en|ru)$")

    def to_level_data(self) -> dict:
        data = {
            "level_name": self.level_name,
            "tiles": self.tiles,
            "legend": self.legend,
            "entities": self.entities,
            "lang": self.lang,
        }
        if self.width is not None:
            data["width"] = self.width
        if self.height is not None:
            data["height"] = self.height
        if self.time_limit is not None:
            data["time_limit"] = self.time_limit
        return data

    @model_validator(mode="after")
    def _require_map(self) -> "LevelAnalyzerRequest":
        if not self.tiles and not self.entities:
            raise ValueError("Provide tiles and/or entities for level analysis")
        return self


class LevelAnalyzerCompareRequest(BaseModel):
    level_a: dict
    level_b: dict
    lang: str = Field(default="en", pattern="^(en|ru)$")


class StoreDescriptionRequest(BaseModel):
    """Game marketing brief for store listing copy."""

    project_id: Optional[UUID] = None
    game_name: str = Field(default="Untitled Game", max_length=200)
    genre: str = Field(default="Adventure", max_length=120)
    platform: str = Field(default="PC", max_length=64)
    target_audience: str = Field(default="casual", max_length=64)
    usp: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=4000)
    key_features: List[str] = Field(default_factory=list)
    target_platform: str = Field(default="steam", pattern="^(steam|appstore|googleplay|epic)$")
    language: str = Field(default="en", max_length=16)
    tone: str = Field(default="epic", pattern="^(epic|mysterious|fun|serious|retro)$")

    def to_game_data(self) -> dict:
        return {
            "game_name": self.game_name,
            "genre": self.genre,
            "platform": self.platform,
            "target_audience": self.target_audience,
            "usp": self.usp,
            "description": self.description,
            "key_features": self.key_features,
            "target_platform": self.target_platform,
            "language": self.language,
            "tone": self.tone,
        }

    @model_validator(mode="after")
    def _require_brief(self) -> "StoreDescriptionRequest":
        if not (self.game_name.strip() and (self.description.strip() or self.usp.strip() or self.key_features)):
            raise ValueError("Provide game_name and at least description, usp, or key_features")
        return self


class PlaytestAnalyzerRequest(BaseModel):
    """Playtest session dump for retention / difficulty / feedback analysis."""

    project_id: Optional[UUID] = None
    game_name: str = Field(default="Untitled Game", max_length=200)
    sessions: List[dict] = Field(default_factory=list)
    lang: str = Field(default="en", pattern="^(en|ru)$")

    def to_playtest_data(self) -> dict:
        return {
            "game_name": self.game_name,
            "sessions": self.sessions,
            "lang": self.lang,
        }

    @model_validator(mode="after")
    def _require_sessions(self) -> "PlaytestAnalyzerRequest":
        if not self.sessions:
            raise ValueError("Provide at least one playtest session")
        return self


class TrailerScriptRequest(BaseModel):
    """Game brief for trailer / promo video script generation."""

    project_id: Optional[UUID] = None
    game_name: str = Field(default="Untitled Game", max_length=200)
    genre: str = Field(default="Adventure", max_length=120)
    description: str = Field(default="", max_length=4000)
    trailer_type: str = Field(default="launch", pattern="^(launch|gameplay|story|teaser|feature)$")
    duration: int = Field(default=60, ge=15, le=180)
    tone: str = Field(default="epic", pattern="^(epic|mysterious|fun|dramatic|retro)$")
    key_features: List[str] = Field(default_factory=list)
    target_audience: str = Field(default="", max_length=120)
    platform: str = Field(default="PC", max_length=120)
    release_date: str = Field(default="", max_length=64)
    urls: dict = Field(default_factory=dict)
    lang: str = Field(default="en", pattern="^(en|ru)$")

    def to_game_data(self) -> dict:
        return {
            "game_name": self.game_name,
            "genre": self.genre,
            "description": self.description,
            "trailer_type": self.trailer_type,
            "duration": self.duration,
            "tone": self.tone,
            "key_features": self.key_features,
            "target_audience": self.target_audience,
            "platform": self.platform,
            "release_date": self.release_date,
            "urls": self.urls,
            "lang": self.lang,
        }

    @model_validator(mode="after")
    def _require_brief(self) -> "TrailerScriptRequest":
        if not (self.game_name.strip() and (self.description.strip() or self.key_features)):
            raise ValueError("Provide game_name and at least description or key_features")
        return self


class ReviewAnalyzerRequest(BaseModel):
    """Player reviews dump for sentiment / issue analysis."""

    project_id: Optional[UUID] = None
    game_name: str = Field(default="Untitled Game", max_length=200)
    source: str = Field(default="custom", pattern="^(steam|appstore|googleplay|custom)$")
    reviews: List[dict] = Field(default_factory=list)
    lang: str = Field(default="en", pattern="^(en|ru)$")

    def to_payload(self) -> dict:
        return {
            "game_name": self.game_name,
            "source": self.source,
            "reviews": self.reviews,
            "lang": self.lang,
        }

    @model_validator(mode="after")
    def _require_reviews(self) -> "ReviewAnalyzerRequest":
        if not self.reviews:
            raise ValueError("Provide at least one review")
        return self


class DiscordConfigureRequest(BaseModel):
    bot_name: str = Field(default="GameForge Bot", max_length=120)
    guild_id: str = Field(default="", max_length=64)
    channel_id: str = Field(default="", max_length=64)
    bot_token: Optional[str] = Field(default=None, max_length=300)
    prefix: str = Field(default="!", max_length=8)
    moderation_enabled: bool = True
    welcome_enabled: bool = True
    analytics_enabled: bool = True
    moderation: dict = Field(default_factory=dict)
    welcome: dict = Field(default_factory=dict)
    analytics: dict = Field(default_factory=dict)
    game_info: dict = Field(default_factory=dict)
    mark_connected: Optional[bool] = None
    lang: str = Field(default="en", pattern="^(en|ru)$")


class DiscordCommandCreate(BaseModel):
    command: str = Field(..., max_length=64)
    description: str = Field(default="", max_length=300)
    usage: str = Field(default="", max_length=120)
    response: str = Field(default="", max_length=4000)
    category: str = Field(default="custom", max_length=32)
    is_active: bool = True


class DiscordCommandUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=300)
    usage: Optional[str] = Field(default=None, max_length=120)
    response: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[str] = Field(default=None, max_length=32)
    is_active: Optional[bool] = None


class DiscordCommandOut(BaseModel):
    id: UUID
    command: str
    description: str
    usage: str
    response: str
    category: str
    is_active: bool

    model_config = {"from_attributes": True}


class DiscordStatusOut(BaseModel):
    id: Optional[UUID] = None
    bot_name: str
    guild_id: str
    channel_id: str
    prefix: str
    token_masked: Optional[str] = None
    has_token: bool = False
    moderation_enabled: bool = True
    welcome_enabled: bool = True
    analytics_enabled: bool = True
    moderation: dict = Field(default_factory=dict)
    welcome: dict = Field(default_factory=dict)
    analytics: dict = Field(default_factory=dict)
    game_info: dict = Field(default_factory=dict)
    is_connected: bool = False
    status: str = "offline"
    status_label: str = ""
    stats: dict = Field(default_factory=dict)
    commands: List[DiscordCommandOut] = Field(default_factory=list)
    updated_at: Optional[str] = None


class DiscordModerateRequest(BaseModel):
    content: str = Field(..., max_length=4000)
    user_id: Optional[str] = Field(default=None, max_length=64)
    lang: str = Field(default="en", pattern="^(en|ru)$")


class DiscordSimulateCommandRequest(BaseModel):
    command: str = Field(..., max_length=64)
    args: str = Field(default="", max_length=500)
    lang: str = Field(default="en", pattern="^(en|ru)$")


class DiscordAnalyzeRequest(BaseModel):
    project_id: Optional[UUID] = None
    bot_name: str = Field(default="Discord Bot", max_length=120)
    messages: List[Any] = Field(default_factory=list)
    moderation: dict = Field(default_factory=dict)
    lang: str = Field(default="en", pattern="^(en|ru)$")

    def to_payload(self) -> dict:
        return {
            "bot_name": self.bot_name,
            "messages": self.messages,
            "moderation": self.moderation,
            "lang": self.lang,
        }

    @model_validator(mode="after")
    def _require_messages(self) -> "DiscordAnalyzeRequest":
        if not self.messages:
            raise ValueError("Provide at least one community message sample")
        return self


class LocalizationRequest(BaseModel):
    project_id: Optional[UUID] = None
    texts: dict[str, str]  # key -> source text
    source_lang: str = "en"
    target_langs: List[str] = Field(default_factory=lambda: ["ru", "es", "de", "fr", "ja"])
    export_format: str = Field(
        default="json",
        pattern="^(json|csv|unity_csv|unity_json|godot_csv)$",
    )
    # term (source spelling) → { lang_code → required translation }
    glossary: Optional[dict[str, dict[str, str]]] = None
    include_qa: bool = True
    include_pseudo: bool = True

    @model_validator(mode="after")
    def _normalize_glossary(self) -> "LocalizationRequest":
        if not self.glossary:
            self.glossary = None
            return self
        cleaned: dict[str, dict[str, str]] = {}
        for term, langs in self.glossary.items():
            term_key = (term or "").strip()
            if not term_key or not isinstance(langs, dict):
                continue
            lang_map = {
                str(code).strip().lower(): str(val)
                for code, val in langs.items()
                if str(code).strip() and str(val).strip()
            }
            if lang_map:
                cleaned[term_key] = lang_map
        self.glossary = cleaned or None
        return self


class LocalizationCsvParseResponse(BaseModel):
    texts: dict[str, str]
    key_count: int
    warnings: List[str] = Field(default_factory=list)
    delimiter: str = ","


class ProjectGlossaryResponse(BaseModel):
    project_id: UUID
    glossary: dict[str, dict[str, str]] = Field(default_factory=dict)


class ProjectGlossaryUpdate(BaseModel):
    glossary: dict[str, dict[str, str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalize(self) -> "ProjectGlossaryUpdate":
        cleaned: dict[str, dict[str, str]] = {}
        for term, langs in (self.glossary or {}).items():
            term_key = (term or "").strip()
            if not term_key or not isinstance(langs, dict):
                continue
            lang_map = {
                str(code).strip().lower(): str(val)
                for code, val in langs.items()
                if str(code).strip() and str(val).strip()
            }
            if lang_map:
                cleaned[term_key] = lang_map
        self.glossary = cleaned
        return self


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
