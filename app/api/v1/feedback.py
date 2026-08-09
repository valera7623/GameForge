"""Public feedback / support form API."""

from __future__ import annotations

import html
import logging
import re
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limiter import rate_limit
from app.database import get_db
from app.deps import get_optional_user
from app.models.feedback import FeedbackCategory, FeedbackMessage, FeedbackStatus
from app.models.user import User
from app.services.email_service import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])
settings = get_settings()


class FeedbackCreateRequest(BaseModel):
    category: str = Field(pattern="^(bug|idea|billing|other)$")
    message: str = Field(min_length=10, max_length=5000)
    subject: str = Field(default="", max_length=200)
    email: Optional[EmailStr] = None
    page_url: Optional[str] = Field(default=None, max_length=512)
    # Privacy consent — required for GDPR-style forms
    consent: bool = False
    # Honeypot (bots fill this; humans leave empty)
    website: str = Field(default="", max_length=200)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 10:
            raise ValueError("Message is too short")
        return v

    @field_validator("subject")
    @classmethod
    def strip_subject(cls, v: str) -> str:
        return (v or "").strip()[:200]

    @field_validator("page_url")
    @classmethod
    def sanitize_page_url(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip()[:512]
        if v.startswith(("http://", "https://", "/")):
            return v
        return None


class FeedbackCreateResponse(BaseModel):
    id: str
    ok: bool = True
    message: str = "Thank you — we received your feedback."


@router.post("", response_model=FeedbackCreateResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: FeedbackCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    # Strict per-IP limit for public form
    await rate_limit(request, limit=5)

    if body.website and body.website.strip():
        # Silent success for bots
        return FeedbackCreateResponse(id=str(uuid4()), message="Thank you.")

    if not body.consent:
        raise HTTPException(status_code=400, detail="Consent is required to send feedback")

    email = str(body.email).strip() if body.email else None
    if user and user.email and not email:
        email = user.email
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Invalid email")

    client_ip = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()[:64]
    ua = (request.headers.get("user-agent") or "")[:512]

    row = FeedbackMessage(
        id=uuid4(),
        user_id=user.id if user else None,
        category=FeedbackCategory(body.category),
        subject=body.subject or "",
        message=body.message,
        email=email,
        status=FeedbackStatus.NEW,
        page_url=body.page_url,
        client_ip=client_ip,
        user_agent=ua or None,
    )
    db.add(row)
    await db.flush()

    try:
        await _notify_staff(row, user)
    except Exception:
        logger.exception("Feedback notify email failed id=%s", row.id)

    return FeedbackCreateResponse(id=str(row.id))


async def _notify_staff(row: FeedbackMessage, user: Optional[User]) -> None:
    to = (settings.FEEDBACK_NOTIFY_EMAIL or "").strip() or "valera7623@gmail.com"
    who = html.escape(user.email if user else (row.email or "guest"))
    subj_line = row.subject or "(no subject)"
    subject = f"[GameForge feedback] {row.category.value}: {subj_line[:80]}"
    admin_url = f"{settings.FRONTEND_URL.rstrip('/')}/admin/feedback"
    body_html = f"""
    <div style="font-family:sans-serif;max-width:560px;margin:0 auto">
      <h2>New feedback</h2>
      <p><strong>Category:</strong> {html.escape(row.category.value)}<br/>
         <strong>From:</strong> {who}<br/>
         <strong>Subject:</strong> {html.escape(subj_line)}</p>
      <pre style="white-space:pre-wrap;background:#f4f4f5;padding:12px;border-radius:8px">{html.escape(row.message)}</pre>
      <p><a href="{html.escape(admin_url)}">Open inbox</a></p>
    </div>
    """
    await send_email(to, subject, body_html)
