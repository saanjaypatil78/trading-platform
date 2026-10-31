"""SQLAlchemy persistence models for the shared Markdown workspace."""
import uuid

from sqlalchemy import (
    CHAR, JSON, CheckConstraint, Column, DateTime, ForeignKeyConstraint,
    Index, Integer, LargeBinary, String, Text, UniqueConstraint, Uuid,
    func, text,
)
from shared.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_workspace_name_nonempty"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    created_by = Column(Uuid(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member_user"),
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_workspace_member_workspace",
        ),
        CheckConstraint(
            "role IN ('OWNER', 'ADMIN', 'COACH', 'EDITOR', 'VIEWER')",
            name="ck_workspace_member_role",
        ),
        CheckConstraint("membership_version > 0", name="ck_workspace_member_version"),
        Index("ix_workspace_members_user_id", "user_id"),
        Index(
            "uq_workspace_active_owner", "workspace_id", unique=True,
            postgresql_where=text("role = 'OWNER' AND revoked_at IS NULL"),
            sqlite_where=text("role = 'OWNER' AND revoked_at IS NULL"),
        ),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(Uuid(as_uuid=True), nullable=False)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    role = Column(String(16), nullable=False)
    membership_version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class MarkdownDocument(Base):
    __tablename__ = "markdown_documents"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_markdown_document_id_workspace"),
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_markdown_document_workspace",
        ),
        CheckConstraint(
            "document_type IN ('lesson', 'research', 'task', 'decision', 'runbook', 'trade_execution')",
            name="ck_markdown_document_type",
        ),
        CheckConstraint("length(trim(title)) > 0", name="ck_markdown_document_title_nonempty"),
        CheckConstraint("schema_version > 0", name="ck_markdown_document_schema_version"),
        CheckConstraint("content_revision >= 0", name="ck_markdown_document_revision"),
        Index("ix_markdown_documents_workspace_id", "workspace_id"),
        Index("ix_markdown_documents_type", "document_type"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(Uuid(as_uuid=True), nullable=False)
    document_type = Column(String(32), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False, default="", server_default="")
    schema_version = Column(Integer, nullable=False, default=1, server_default="1")
    content_revision = Column(Integer, nullable=False, default=0, server_default="0")
    created_by = Column(Uuid(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)


class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id"], ["markdown_documents.id"], ondelete="RESTRICT",
            name="fk_document_snapshot_document",
        ),
        UniqueConstraint("document_id", "content_revision", name="uq_document_snapshot_revision"),
        CheckConstraint("content_revision >= 0", name="ck_document_snapshot_revision"),
        Index("ix_document_snapshots_document_id", "document_id"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(Uuid(as_uuid=True), nullable=False)
    content_revision = Column(Integer, nullable=False)
    provider = Column(String(64), nullable=False)
    provider_version = Column(String(64), nullable=False)
    snapshot_bytes = Column(LargeBinary, nullable=False)
    created_by = Column(Uuid(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DocumentUpdate(Base):
    __tablename__ = "document_updates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id"], ["markdown_documents.id"], ondelete="RESTRICT",
            name="fk_document_update_document",
        ),
        CheckConstraint("content_revision >= 0", name="ck_document_update_revision"),
        Index("ix_document_updates_document_received", "document_id", "server_received_at"),
    )

    update_id = Column(Uuid(as_uuid=True), primary_key=True)
    document_id = Column(Uuid(as_uuid=True), nullable=False)
    actor_id = Column(Uuid(as_uuid=True), nullable=False)
    content_revision = Column(Integer, nullable=False)
    payload_bytes = Column(LargeBinary, nullable=False)
    server_received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CollaborationSession(Base):
    __tablename__ = "collaboration_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "workspace_id"],
            ["markdown_documents.id", "markdown_documents.workspace_id"],
            ondelete="CASCADE",
            name="fk_collaboration_session_document_workspace",
        ),
        UniqueConstraint("token_hash", name="uq_collaboration_session_token_hash"),
        CheckConstraint("membership_version > 0", name="ck_collaboration_session_version"),
        CheckConstraint("length(token_hash) = 64", name="ck_collaboration_session_token_hash"),
        CheckConstraint("expires_at > created_at", name="ck_collaboration_session_expiry"),
        Index("ix_collaboration_sessions_workspace_document", "workspace_id", "document_id"),
        Index("ix_collaboration_sessions_expiry", "expires_at"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(CHAR(64), nullable=False)
    workspace_id = Column(Uuid(as_uuid=True), nullable=False)
    document_id = Column(Uuid(as_uuid=True), nullable=False)
    user_id = Column(Uuid(as_uuid=True), nullable=False)
    membership_version = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CollaborationAuditEvent(Base):
    __tablename__ = "collaboration_audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_collaboration_audit_workspace",
        ),
        ForeignKeyConstraint(
            ["document_id"], ["markdown_documents.id"], ondelete="SET NULL",
            name="fk_collaboration_audit_document",
        ),
        UniqueConstraint("idempotency_key", name="uq_collaboration_audit_idempotency_key"),
        CheckConstraint("length(trim(event_type)) > 0", name="ck_collaboration_audit_event_type"),
        CheckConstraint("revision IS NULL OR revision >= 0", name="ck_collaboration_audit_revision"),
        Index("ix_collaboration_audit_workspace_time", "workspace_id", "server_timestamp"),
        Index("ix_collaboration_audit_document_time", "document_id", "server_timestamp"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(Uuid(as_uuid=True), nullable=False)
    document_id = Column(Uuid(as_uuid=True), nullable=True)
    actor_id = Column(Uuid(as_uuid=True), nullable=False)
    event_type = Column(String(64), nullable=False)
    revision = Column(Integer, nullable=True)
    idempotency_key = Column(Uuid(as_uuid=True), nullable=True)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict, server_default=text("'{}'"))
    server_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
