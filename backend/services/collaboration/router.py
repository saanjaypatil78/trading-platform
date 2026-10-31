"""Authenticated workspace and Markdown document HTTP API.

Document body updates are intentionally not exposed here. Concurrent editing
must be implemented through the approved CRDT transport, not last-write-wins
HTTP replacement.
"""
import uuid
from enum import Enum
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.services.auth.identity import AuthenticatedUser, get_current_user
from services.collaboration.authorization import (
    WorkspacePermission,
    require_workspace_permission,
)
from services.collaboration.models import (
    CollaborationAuditEvent,
    MarkdownDocument,
    Workspace,
    WorkspaceMember,
)
from shared.database import get_db


router = APIRouter(prefix="/api/v1/collaboration", tags=["Markdown Collaboration"])


class DocumentType(str, Enum):
    LESSON = "lesson"
    RESEARCH = "research"
    TASK = "task"
    DECISION = "decision"
    RUNBOOK = "runbook"
    TRADE_EXECUTION = "trade_execution"


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Workspace name cannot be blank")
        return normalized


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_type: DocumentType
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=250_000)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Document title cannot be blank")
        return normalized


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    role: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    document_type: str
    title: str
    body: str
    schema_version: int
    content_revision: int


def _verified_user_id(user: AuthenticatedUser) -> UUID:
    # The identity dependency already validates this as a UUID. Re-parse at the
    # boundary so malformed internal values cannot reach a database query.
    try:
        return UUID(user.user_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Verified user identity is invalid",
        ) from exc


def _database_unavailable(exc: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Workspace storage is temporarily unavailable",
    )


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a workspace and its OWNER membership in one transaction."""
    user_id = _verified_user_id(user)
    workspace = Workspace(
        id=uuid.uuid4(),
        name=payload.name,
        created_by=user_id,
    )
    owner = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user_id,
        role="OWNER",
        membership_version=1,
    )
    audit = CollaborationAuditEvent(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        document_id=None,
        actor_id=user_id,
        event_type="WORKSPACE_CREATED",
        event_metadata={"workspace_name": payload.name},
    )

    try:
        db.add(workspace)
        db.add(owner)
        db.add(audit)
        db.commit()
        db.refresh(workspace)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workspace could not be created due to a data constraint",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_unavailable(exc) from exc

    return WorkspaceResponse(id=workspace.id, name=workspace.name, role="OWNER")


@router.get("/workspaces", response_model=List[WorkspaceResponse])
def list_workspaces(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List only workspaces where the verified user has active membership."""
    user_id = _verified_user_id(user)
    try:
        rows = (
            db.query(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .filter(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.revoked_at.is_(None),
                Workspace.archived_at.is_(None),
            )
            .order_by(Workspace.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        raise _database_unavailable(exc) from exc

    return [
        WorkspaceResponse(id=workspace.id, name=workspace.name, role=role)
        for workspace, role in rows
    ]


@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    workspace_id: UUID,
    payload: DocumentCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a document only for a member with EDIT permission."""
    user_id = _verified_user_id(user)
    require_workspace_permission(db, workspace_id, user_id, WorkspacePermission.EDIT)

    document = MarkdownDocument(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        document_type=payload.document_type.value,
        title=payload.title,
        body=payload.body,
        schema_version=1,
        content_revision=0,
        created_by=user_id,
    )
    audit = CollaborationAuditEvent(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        document_id=document.id,
        actor_id=user_id,
        event_type="DOCUMENT_CREATED",
        revision=0,
        event_metadata={"document_type": payload.document_type.value},
    )

    try:
        db.add(document)
        db.add(audit)
        db.commit()
        db.refresh(document)
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_unavailable(exc) from exc

    return document


@router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=List[DocumentResponse],
)
def list_documents(
    workspace_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents only after resolving active READ permission."""
    user_id = _verified_user_id(user)
    require_workspace_permission(db, workspace_id, user_id, WorkspacePermission.READ)
    try:
        return (
            db.query(MarkdownDocument)
            .filter(
                MarkdownDocument.workspace_id == workspace_id,
                MarkdownDocument.archived_at.is_(None),
            )
            .order_by(MarkdownDocument.created_at.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        raise _database_unavailable(exc) from exc


@router.get(
    "/workspaces/{workspace_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    workspace_id: UUID,
    document_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read a document only within the authorized workspace boundary."""
    user_id = _verified_user_id(user)
    require_workspace_permission(db, workspace_id, user_id, WorkspacePermission.READ)
    try:
        document = (
            db.query(MarkdownDocument)
            .filter(
                MarkdownDocument.id == document_id,
                MarkdownDocument.workspace_id == workspace_id,
                MarkdownDocument.archived_at.is_(None),
            )
            .first()
        )
    except SQLAlchemyError as exc:
        raise _database_unavailable(exc) from exc

    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
