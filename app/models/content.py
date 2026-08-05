"""CMS content items — pages, blog posts, FAQ."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentKind(str, enum.Enum):
    PAGE = "page"
    BLOG = "blog"
    FAQ = "faq"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (UniqueConstraint("kind", "slug", "locale", name="uq_content_kind_slug_locale"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ContentStatus.DRAFT.value)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
