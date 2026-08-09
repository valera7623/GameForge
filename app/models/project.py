"""Project model — a game the user is building."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.generation import Generation
    from app.models.user import User


class GameEngine(str, enum.Enum):
    UNITY = "unity"
    UNREAL = "unreal"
    GODOT = "godot"
    CUSTOM = "custom"
    OTHER = "other"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    engine: Mapped[GameEngine] = mapped_column(Enum(GameEngine, name="GameEngine", values_callable=lambda x: [e.value for e in x]), default=GameEngine.UNITY)
    cover_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    localization_glossary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    generations: Mapped[List["Generation"]] = relationship(
        "Generation", back_populates="project", cascade="all, delete-orphan"
    )
