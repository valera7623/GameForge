"""Staff RBAC for the admin panel."""

from __future__ import annotations

from typing import Callable, FrozenSet

from fastapi import Depends, HTTPException, status

from app.deps import get_current_user
from app.models.user import User, UserRole

STAFF_ROLES: FrozenSet[UserRole] = frozenset(
    {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.SUPPORT,
    }
)

# permission -> roles that may perform it
PERMISSIONS: dict[str, FrozenSet[UserRole]] = {
    "dashboard:read": STAFF_ROLES,
    "users:read": STAFF_ROLES,
    "users:write": frozenset({UserRole.SUPER_ADMIN, UserRole.ADMIN}),
    "users:role": frozenset({UserRole.SUPER_ADMIN, UserRole.ADMIN}),
    "generations:read": STAFF_ROLES,
    "tools:write": frozenset({UserRole.SUPER_ADMIN, UserRole.ADMIN}),
    "subscriptions:write": frozenset({UserRole.SUPER_ADMIN, UserRole.ADMIN}),
    "settings:read": STAFF_ROLES,
    "settings:write": frozenset({UserRole.SUPER_ADMIN}),
}


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def has_permission(user: User, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission)
    if not allowed:
        return False
    return user.role in allowed


def can_assign_role(actor: User, target_role: UserRole) -> bool:
    """Admin cannot assign or touch super_admin; only super_admin can."""
    if target_role == UserRole.SUPER_ADMIN:
        return actor.role == UserRole.SUPER_ADMIN
    if not has_permission(actor, "users:role"):
        return False
    return True


async def require_staff(user: User = Depends(get_current_user)) -> User:
    if not is_staff(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff only")
    return user


def require_permission(permission: str) -> Callable:
    async def _dep(user: User = Depends(require_staff)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return _dep
