"""Email delivery — SMTP or Resend, with console fallback for local/dev."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def email_configured() -> bool:
    if settings.EMAIL_PROVIDER == "resend":
        return bool(settings.RESEND_API_KEY)
    if settings.EMAIL_PROVIDER == "smtp":
        return bool(settings.SMTP_HOST and settings.EMAIL_FROM)
    return False


async def send_email(to: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    """Send email. Returns True if accepted by provider or logged in console mode."""
    text = text or _strip_tags(html)
    provider = settings.EMAIL_PROVIDER.lower()

    if provider == "resend" and settings.RESEND_API_KEY:
        return await _send_resend(to, subject, html, text)
    if provider == "smtp" and settings.SMTP_HOST:
        return await _send_smtp(to, subject, html, text)

    # Console / log fallback — never fail auth flows in dev
    logger.info("EMAIL[%s] to=%s subject=%s\n%s", provider or "console", to, subject, text)
    print(f"\n=== EMAIL ({provider or 'console'}) → {to} ===\nSubject: {subject}\n{text}\n=== END EMAIL ===\n")
    return True


async def send_password_reset(to: str, token: str) -> bool:
    link = f"{settings.FRONTEND_URL.rstrip('/')}/src/pages/reset-password.html?token={token}"
    subject = f"Reset your {settings.APP_NAME} password"
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>{settings.APP_NAME}</h2>
      <p>We received a request to reset your password.</p>
      <p><a href="{link}" style="display:inline-block;padding:12px 18px;background:#0d9f90;color:#fff;text-decoration:none;border-radius:8px">
        Reset password
      </a></p>
      <p style="color:#666;font-size:13px">Or open this link:<br/>{link}</p>
      <p style="color:#666;font-size:13px">If you did not request this, ignore this email.</p>
    </div>
    """
    return await send_email(to, subject, html, f"Reset your password: {link}")


async def send_welcome(to: str, name: Optional[str] = None) -> bool:
    greet = name or "developer"
    base = settings.FRONTEND_URL.rstrip("/")
    subject = f"Welcome to {settings.APP_NAME}"
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>Welcome, {greet}!</h2>
      <p>Your GameForge account is ready. Start forging levels, quests, characters, and more.</p>
      <p><a href="{base}/dashboard">Open dashboard</a></p>
    </div>
    """
    return await send_email(to, subject, html)


async def send_locforge_welcome(to: str, name: Optional[str] = None, pack: Optional[str] = None) -> bool:
    """Welcome email for users who signed up from LocForge."""
    greet = name or "developer"
    base = settings.FRONTEND_URL.rstrip("/")
    pack_note = ""
    if pack:
        pack_note = f"<p>You selected the <strong>{pack}</strong> word pack — you can buy it after your first translate.</p>"
    subject = "LocForge — localize your first CSV"
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>Welcome to LocForge, {greet}!</h2>
      <p>CSV in → glossary + length QA → Unity / Godot export. Start with a free translate slot or a word pack.</p>
      {pack_note}
      <p><a href="{base}/localization" style="display:inline-block;padding:12px 18px;background:#b7d43a;color:#132008;text-decoration:none;border-radius:8px;font-weight:600">
        Open Localization
      </a></p>
      <p style="color:#666;font-size:13px">Tip: load the Ashen Hollow sample CSV on the tool page to try the full pipeline in one click.</p>
      <p style="color:#666;font-size:13px">LocForge is powered by <a href="{base}/">{settings.APP_NAME}</a> — 14 AI tools for game dev.</p>
    </div>
    """
    return await send_email(to, subject, html)


async def send_post_localize_upsell(to: str, name: Optional[str] = None) -> bool:
    """One-shot email after first successful localization."""
    greet = name or "developer"
    base = settings.FRONTEND_URL.rstrip("/")
    subject = "Next: word pack or explore GameForge tools"
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>Nice work, {greet}!</h2>
      <p>Your first LocForge translate is done. Two good next steps:</p>
      <ol>
        <li><a href="{base}/localization">Buy a word pack</a> (Starter from 4&nbsp;990&nbsp;₽) so larger CSVs do not burn generation slots.</li>
        <li>Try other GameForge tools — Character Creator, Level Designer, Store Description, and 11 more.</li>
      </ol>
      <p><a href="{base}/dashboard" style="display:inline-block;padding:12px 18px;background:#0d9f90;color:#fff;text-decoration:none;border-radius:8px">
        Open GameForge dashboard
      </a></p>
    </div>
    """
    return await send_email(to, subject, html)


async def send_org_invite(to: str, org_name: str, invite_token: str, inviter: str) -> bool:
    link = f"{settings.FRONTEND_URL.rstrip('/')}/accept-invite?token={invite_token}"
    subject = f"You're invited to {org_name} on {settings.APP_NAME}"
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <h2>Team invite</h2>
      <p><strong>{inviter}</strong> invited you to join <strong>{org_name}</strong>.</p>
      <p>Use this email address (<strong>{to}</strong>) when you register or sign in.</p>
      <p><a href="{link}" style="display:inline-block;padding:12px 18px;background:#0d9f90;color:#fff;text-decoration:none;border-radius:8px">
        Accept invite
      </a></p>
      <p style="color:#666;font-size:13px">{link}</p>
    </div>
    """
    return await send_email(to, subject, html, f"Accept invite: {link}")


async def _send_resend(to: str, subject: str, html: str, text: str) -> bool:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": settings.EMAIL_FROM or "GameForge <onboarding@resend.dev>",
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            },
        )
        if resp.status_code >= 400:
            logger.error("Resend error %s: %s", resp.status_code, resp.text)
            return False
        return True


async def _send_smtp(to: str, subject: str, html: str, text: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    def _send() -> None:
        if settings.SMTP_USE_TLS:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                server.starttls()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())

    try:
        import asyncio

        await asyncio.to_thread(_send)
        return True
    except Exception:
        logger.exception("SMTP send failed")
        return False


def _strip_tags(html: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", html)
