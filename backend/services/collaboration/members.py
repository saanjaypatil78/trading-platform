"""Workspace membership revocation with active session invalidation."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.collaboration.authorization import WorkspacePermission, has_permission
from services.collaboration.models import (
    CollaborationAuditEvent,
    CollaborationSession,
    WorkspaceMember,
)


@dataclass(frozen=True)
class MemberRevocationResult:
    workspace_id: UUID
    member_user_id: UUID
    membership_version: int
    revoked_at: datetime


def revoke_workspace_member(
    db: Session,
    workspace_id: UUID,
    actor_user_id: UUID,
    target_user_id: UUID,
) -> MemberRevocationResult:
    """Revoke one non-owner member and all its collaboration sessions atomically."""
    ordered_ids = sorted({actor_user_id, target_user_id}, key=str)
    now = datetime.now(timezone.utc)
    try:
        # Lock actor and target in deterministic order to prevent reciprocal
        # admin-removal deadlocks. Session consumers lock this member before
        # taking the corresponding collaboration-session lock.
        locked = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id.in_(ordered_ids),
            )
            .order_by(WorkspaceMember.user_id)
            .with_for_update()
            .all()
        )
        by_user = {member.user_id: member for member in locked}
        actor = by_user.get(actor_user_id)
        target = by_user.get(target_user_id)

        if actor is None or actor.revoked_at is not None or not has_permission(
            actor.role, WorkspacePermission.MANAGE_MEMBERS
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active MANAGE_MEMBERS permission is required",
            )
        if target is None or target.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active workspace member not found",
            )
        if target.role == "OWNER":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace OWNER cannot be removed; use audited owner transfer",
            )

        target.revoked_at = now
        target.membership_version += 1
        target.updated_at = now

        db.query(CollaborationSession).filter(
            CollaborationSession.workspace_id == workspace_id,
            CollaborationSession.user_id == target_user_id,
            CollaborationSession.revoked_at.is_(None),
        ).update(
            {CollaborationSession.revoked_at: now},
            synchronize_session=False,
        )

        db.add(
            CollaborationAuditEvent(
                id=uuid4(),
                workspace_id=workspace_id,
                document_id=None,
                actor_id=actor_user_id,
                event_type="WORKSPACE_MEMBER_REVOKED",
                event_metadata={
                    "target_user_id": str(target_user_id),
                    "membership_version": target.membership_version,
                },
            )
        )
        db.commit()
        return MemberRevocationResult(
            workspace_id=workspace_id,
            member_user_id=target_user_id,
            membership_version=target.membership_version,
            revoked_at=now,
        )
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workspace membership service is temporarily unavailable",
        ) from exc
