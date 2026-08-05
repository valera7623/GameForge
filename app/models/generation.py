"""Generation history model."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ToolType(str, enum.Enum):
    LEVEL_DESIGNER = "level_designer"
    QUEST_GENERATOR = "quest_generator"
    TEXTURE_UPSCALER = "texture_upscaler"
    CHARACTER_CREATOR = "character_creator"
    SOUND_DESIGNER = "sound_designer"
    PLAYTESTER = "playtester"
    LOCALIZATION = "localization"
    GAME_BALANCER = "game_balancer"
    LEVEL_ANALYZER = "level_analyzer"
    STORE_DESCRIPTION = "store_description"
    PLAYTEST_ANALYZER = "playtest_analyzer"


class GenerationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (Index("ix_generations_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    tool: Mapped[ToolType] = mapped_column(Enum(ToolType, name="ToolType", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus, name="GenerationStatus", values_callable=lambda x: [e.value for e in x]), default=GenerationStatus.PENDING, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    asset_urls: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    client_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="generations")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="generations")
