"""Organization / team seats API."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.organization import Organization, OrgInvite, OrgMemberRole, OrgMembership
from app.models.subscription import PlanType
from app.models.user import User
from app.services.billing_service import get_or_create_subscription
from app.services.email_service import send_org_invite

router = APIRouter(prefix="/orgs", tags=["organizations"])
settings = get_settings()


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class OrgInviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class OrgMemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str]
    role: str


class OrgOut(BaseModel):
    id: UUID
    name: str
    seats_limit: int
    seats_used: int
    generations_this_month: int
    role: str


class InviteAccept(BaseModel):
    token: str


async def _require_studio_or_enterprise(user: User, db: AsyncSession) -> None:
    if settings.is_onprem:
        return
    sub = await get_or_create_subscription(db, user)
    if sub.plan not in (PlanType.STUDIO, PlanType.ENTERPRISE):
        raise HTTPException(status_code=402, detail="Team seats require Studio or Enterprise plan")


async def _membership(db: AsyncSession, user_id: UUID, org_id: UUID) -> Optional[OrgMembership]:
    result = await db.execute(
        select(OrgMembership).where(OrgMembership.user_id == user_id, OrgMembership.organization_id == org_id)
    )
    return result.scalar_one_or_none()


@router.post("", response_model=OrgOut, status_code=201)
async def create_org(
    body: OrgCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_studio_or_enterprise(user, db)

    existing = await db.execute(select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in an organization")

    org = Organization(
        name=body.name,
        owner_id=user.id,
        seats_limit=settings.STUDIO_SEATS if not settings.is_onprem else 50,
    )
    db.add(org)
    await db.flush()
    db.add(OrgMembership(organization_id=org.id, user_id=user.id, role=OrgMemberRole.OWNER))
    await db.flush()
    return OrgOut(
        id=org.id,
        name=org.name,
        seats_limit=org.seats_limit,
        seats_used=1,
        generations_this_month=org.generations_this_month,
        role=OrgMemberRole.OWNER.value,
    )


@router.get("/mine", response_model=Optional[OrgOut])
async def my_org(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OrgMembership)
        .options(selectinload(OrgMembership.organization))
        .where(OrgMembership.user_id == user.id)
        .limit(1)
    )
    mem = result.scalar_one_or_none()
    if not mem:
        return None
    org = mem.organization
    used = await db.scalar(
        select(func.count(OrgMembership.id)).where(OrgMembership.organization_id == org.id)
    )
    return OrgOut(
        id=org.id,
        name=org.name,
        seats_limit=org.seats_limit,
        seats_used=used or 0,
        generations_this_month=org.generations_this_month,
        role=mem.role.value,
    )


@router.get("/{org_id}/members", response_model=List[OrgMemberOut])
async def list_members(
    org_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await _membership(db, user.id, org_id):
        raise HTTPException(status_code=403, detail="Not a member")
    result = await db.execute(
        select(OrgMembership, User)
        .join(User, User.id == OrgMembership.user_id)
        .where(OrgMembership.organization_id == org_id)
    )
    return [
        OrgMemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role.value)
        for m, u in result.all()
    ]


@router.delete("/{org_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    org_id: UUID,
    member_user_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    actor = await _membership(db, user.id, org_id)
    if not actor or actor.role not in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owners/admins can remove members")

    if member_user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself — leave the team instead")

    target = await _membership(db, member_user_id, org_id)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    if target.role == OrgMemberRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot remove the organization owner")

    # Admins may only remove members, not other admins.
    if actor.role == OrgMemberRole.ADMIN and target.role != OrgMemberRole.MEMBER:
        raise HTTPException(status_code=403, detail="Admins can only remove members")

    target_user = await db.get(User, member_user_id)
    await db.delete(target)

    # Drop leftover pending invite for the same email so seats/invite UX stay clean.
    if target_user and target_user.email:
        pending = await db.scalar(
            select(OrgInvite).where(
                OrgInvite.organization_id == org_id,
                OrgInvite.email == target_user.email.lower(),
                OrgInvite.accepted_at.is_(None),
            )
        )
        if pending:
            await db.delete(pending)

    await db.flush()


@router.post("/{org_id}/invites", status_code=201)
async def invite_member(
    org_id: UUID,
    body: OrgInviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import secrets

    mem = await _membership(db, user.id, org_id)
    if not mem or mem.role not in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only owners/admins can invite")

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    email = body.email.lower().strip()
    role = OrgMemberRole.ADMIN if body.role == "admin" else OrgMemberRole.MEMBER

    # Already a member?
    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user:
        already = await db.scalar(
            select(OrgMembership.id).where(
                OrgMembership.organization_id == org_id,
                OrgMembership.user_id == existing_user.id,
            )
        )
        if already:
            raise HTTPException(status_code=400, detail="User is already a team member")

    existing_invite = await db.scalar(
        select(OrgInvite).where(
            OrgInvite.organization_id == org_id,
            OrgInvite.email == email,
        )
    )
    if existing_invite and existing_invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite was already accepted")

    if existing_invite:
        # Re-send: refresh token/role instead of inserting a duplicate (uq_org_invite_email).
        existing_invite.role = role
        existing_invite.token = secrets.token_urlsafe(24)
        existing_invite.invited_by = user.id
        existing_invite.accepted_at = None
        await db.flush()
        await send_org_invite(email, org.name, existing_invite.token, user.full_name or user.email)
        return {
            "id": existing_invite.id,
            "email": existing_invite.email,
            "resent": True,
            "token": existing_invite.token if settings.DEBUG else None,
        }

    used = await db.scalar(
        select(func.count(OrgMembership.id)).where(OrgMembership.organization_id == org_id)
    )
    pending = await db.scalar(
        select(func.count(OrgInvite.id)).where(
            OrgInvite.organization_id == org_id, OrgInvite.accepted_at.is_(None)
        )
    )
    if (used or 0) + (pending or 0) >= org.seats_limit:
        raise HTTPException(status_code=400, detail=f"Seat limit reached ({org.seats_limit})")

    invite = OrgInvite(
        organization_id=org_id,
        email=email,
        role=role,
        invited_by=user.id,
    )
    db.add(invite)
    await db.flush()
    await send_org_invite(email, org.name, invite.token, user.full_name or user.email)
    return {"id": invite.id, "email": invite.email, "token": invite.token if settings.DEBUG else None}


@router.post("/invites/accept")
async def accept_invite(
    body: InviteAccept,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OrgInvite).where(OrgInvite.token == body.token))
    invite = result.scalar_one_or_none()
    if not invite or invite.accepted_at:
        raise HTTPException(status_code=400, detail="Invalid or used invite")
    if invite.email.lower() != user.email.lower():
        raise HTTPException(status_code=403, detail="Invite email does not match your account")

    existing = await db.execute(select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in an organization")

    used = await db.scalar(
        select(func.count(OrgMembership.id)).where(OrgMembership.organization_id == invite.organization_id)
    )
    org = await db.get(Organization, invite.organization_id)
    if not org or (used or 0) >= org.seats_limit:
        raise HTTPException(status_code=400, detail="No seats available")

    db.add(
        OrgMembership(
            organization_id=invite.organization_id,
            user_id=user.id,
            role=invite.role,
        )
    )
    invite.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "Joined organization", "organization_id": invite.organization_id}
