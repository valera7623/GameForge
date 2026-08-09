"""User product feedback / support messages."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class FeedbackCategory(str, enum.Enum):
    BUG = "bug"
    IDEA = "idea"
    BILLING = "billing"
    OTHER = "other"


class FeedbackStatus(str, enum.Enum):
    NEW = "new"
    READ = "read"
    CLOSED = "closed"


class FeedbackMessage(Base):
    __tablename__ = "feedback_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[FeedbackCategory] = mapped_column(
        Enum(FeedbackCategory, name="FeedbackCategory", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=FeedbackCategory.OTHER,
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus, name="FeedbackStatus", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=FeedbackStatus.NEW,
        index=True,
    )
    page_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], lazy="selectin")
