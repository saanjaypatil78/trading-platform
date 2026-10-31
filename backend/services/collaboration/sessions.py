"""One-time document-scoped collaboration credential lifecycle."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.collaboration.authorization import (
    WorkspacePermission,
    has_permission,
    require_workspace_permission,
)
from services.collaboration.models import (
    CollaborationAuditEvent,
    CollaborationSession,
    MarkdownDocument,
    WorkspaceMember,
)

CREDENTIAL_TTL_SECONDS = 60
MAX_CREDENTIAL_LENGTH = 128


@dataclass(frozen=True)
class IssuedCredential:
    session_id: UUID
    credential: str
    expires_at: datetime
    expires_in_seconds: int = CREDENTIAL_TTL_SECONDS


@dataclass(frozen=True)
class ConsumedCredential:
    session_id: UUID
    workspace_id: UUID
    document_id: UUID
    user_id: UUID
    membership_version: int
    role: str


def hash_credential(credential: str) -> str:
    """Return a SHA-256 digest; callers must never persist or log raw values."""
    if not isinstance(credential, str) or not credential or len(credential) > MAX_CREDENTIAL_LENGTH:
        raise ValueError("Invalid collaboration credential")
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()


def issue_document_credential(
    db: Session,
    workspace_id: UUID,
    document_id: UUID,
    user_id: UUID,
) -> IssuedCredential:
    """Issue a 60-second one-time credential after active READ authorization."""
    membership = require_workspace_permission(
        db, workspace_id, user_id, WorkspacePermission.READ
    )
    document = (
        db.query(MarkdownDocument)
        .filter(
            MarkdownDocument.id == document_id,
            MarkdownDocument.workspace_id == workspace_id,
            MarkdownDocument.archived_at.is_(None),
        )
        .first()
    )
    if document is None:
        raise ValueError("Document not found in the requested workspace")

    raw_credential = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=CREDENTIAL_TTL_SECONDS)
    session_id = uuid4()

    session_row = CollaborationSession(
        id=session_id,
        token_hash=hash_credential(raw_credential),
        workspace_id=workspace_id,
        document_id=document_id,
        user_id=user_id,
        membership_version=membership.membership_version,
        expires_at=expires_at,
    )
    audit_event = CollaborationAuditEvent(
        id=uuid4(),
        workspace_id=workspace_id,
        document_id=document_id,
        actor_id=user_id,
        event_type="COLLABORATION_CREDENTIAL_ISSUED",
        event_metadata={
            "expires_in_seconds": CREDENTIAL_TTL_SECONDS,
            "membership_version": membership.membership_version,
        },
    )

    try:
        db.add(session_row)
        db.add(audit_event)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return IssuedCredential(
        session_id=session_id,
        credential=raw_credential,
        expires_at=expires_at,
    )


def consume_document_credential(
    db: Session,
    document_id: UUID,
    raw_credential: str,
    *,
    now: datetime | None = None,
) -> ConsumedCredential | None:
    """Atomically consume a document credential once, validating current membership.

    Lock order is WorkspaceMember then CollaborationSession. Any revocation
    path must follow this same order. PostgreSQL SKIP LOCKED prevents concurrent
    handshakes from consuming the same credential.
    """
    try:
        token_hash = hash_credential(raw_credential)
    except ValueError:
        return None

    current_time = now or datetime.now(timezone.utc)

    try:
        candidate = (
            db.query(CollaborationSession)
            .filter(
                CollaborationSession.document_id == document_id,
                CollaborationSession.token_hash == token_hash,
            )
            .first()
        )
        if candidate is None:
            db.rollback()
            return None

        # Lock membership first. Revocation must use the same lock order.
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == candidate.workspace_id,
                WorkspaceMember.user_id == candidate.user_id,
            )
            .with_for_update()
            .first()
        )

        # Lock and conditionally re-read the credential after the membership
        # lock. This is the single-use gate on PostgreSQL.
        session_row = (
            db.query(CollaborationSession)
            .filter(
                CollaborationSession.id == candidate.id,
                CollaborationSession.document_id == document_id,
                CollaborationSession.token_hash == token_hash,
                CollaborationSession.consumed_at.is_(None),
                CollaborationSession.revoked_at.is_(None),
                CollaborationSession.expires_at > current_time,
            )
            .with_for_update(skip_locked=True)
            .first()
        )
        if session_row is None:
            db.rollback()
            return None

        document = (
            db.query(MarkdownDocument)
            .filter(
                MarkdownDocument.id == document_id,
                MarkdownDocument.workspace_id == session_row.workspace_id,
                MarkdownDocument.archived_at.is_(None),
            )
            .first()
        )

        valid_membership = (
            membership is not None
            and membership.revoked_at is None
            and membership.membership_version == session_row.membership_version
            and has_permission(membership.role, WorkspacePermission.READ)
        )

        session_row.consumed_at = current_time
        if not valid_membership or document is None:
            session_row.revoked_at = current_time
            db.commit()
            return None

        result = ConsumedCredential(
            session_id=session_row.id,
            workspace_id=session_row.workspace_id,
            document_id=session_row.document_id,
            user_id=session_row.user_id,
            membership_version=session_row.membership_version,
            role=membership.role,
        )
        db.commit()
        return result
    except SQLAlchemyError:
        db.rollback()
        raise
