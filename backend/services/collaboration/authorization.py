"""Server-side workspace authorization for Markdown collaboration.

Callers supply only a verified identity UUID. Role and membership state are
always loaded from the database; browser-supplied role claims are ignored.
"""
from enum import Enum
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.collaboration.models import WorkspaceMember


class WorkspaceRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    COACH = "COACH"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class WorkspacePermission(str, Enum):
    READ = "READ"
    EDIT = "EDIT"
    EXECUTE = "EXECUTE"
    APPROVE = "APPROVE"
    MANAGE_MEMBERS = "MANAGE_MEMBERS"
    TRANSFER_OWNER = "TRANSFER_OWNER"


_ROLE_PERMISSIONS = {
    WorkspaceRole.OWNER: frozenset(WorkspacePermission),
    WorkspaceRole.ADMIN: frozenset({
        WorkspacePermission.READ,
        WorkspacePermission.EDIT,
        WorkspacePermission.EXECUTE,
        WorkspacePermission.APPROVE,
        WorkspacePermission.MANAGE_MEMBERS,
    }),
    WorkspaceRole.COACH: frozenset({
        WorkspacePermission.READ,
        WorkspacePermission.EDIT,
        WorkspacePermission.EXECUTE,
        WorkspacePermission.APPROVE,
    }),
    WorkspaceRole.EDITOR: frozenset({
        WorkspacePermission.READ,
        WorkspacePermission.EDIT,
        WorkspacePermission.EXECUTE,
    }),
    WorkspaceRole.VIEWER: frozenset({WorkspacePermission.READ}),
}


def has_permission(role: WorkspaceRole | str, permission: WorkspacePermission | str) -> bool:
    """Return the fixed role-matrix result; unknown values always deny."""
    try:
        normalized_role = WorkspaceRole(role)
        normalized_permission = WorkspacePermission(permission)
    except (TypeError, ValueError):
        return False
    return normalized_permission in _ROLE_PERMISSIONS[normalized_role]


def require_workspace_permission(
    db: Session,
    workspace_id: UUID,
    user_id: UUID,
    permission: WorkspacePermission,
) -> WorkspaceMember:
    """Return active membership or fail closed with 403/503.

    user_id must come from the verified authentication dependency. The
    workspace role is fetched from persistence on every authorization call.
    """
    try:
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workspace authorization is temporarily unavailable",
        ) from exc

    if membership is None or membership.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active workspace membership is required",
        )

    if not has_permission(membership.role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace role does not permit this action",
        )

    return membership
