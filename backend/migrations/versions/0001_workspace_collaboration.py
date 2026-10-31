"""Create the workspace and shared Markdown collaboration schema.

Revision ID: 0001_workspace_collaboration
Revises:
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_workspace_collaboration"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_workspace_name_nonempty"),
    )

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("membership_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_workspace_member_workspace"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member_user"),
        sa.CheckConstraint(
            "role IN ('OWNER', 'ADMIN', 'COACH', 'EDITOR', 'VIEWER')",
            name="ck_workspace_member_role",
        ),
        sa.CheckConstraint("membership_version > 0", name="ck_workspace_member_version"),
    )
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"], unique=False)
    op.create_index(
        "uq_workspace_active_owner",
        "workspace_members",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("role = 'OWNER' AND revoked_at IS NULL"),
    )

    op.create_table(
        "markdown_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("content_revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_markdown_document_workspace"),
        sa.UniqueConstraint("id", "workspace_id", name="uq_markdown_document_id_workspace"),
        sa.CheckConstraint(
            "document_type IN ('lesson', 'research', 'task', 'decision', 'runbook', 'trade_execution')",
            name="ck_markdown_document_type",
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_markdown_document_title_nonempty"),
        sa.CheckConstraint("schema_version > 0", name="ck_markdown_document_schema_version"),
        sa.CheckConstraint("content_revision >= 0", name="ck_markdown_document_revision"),
    )
    op.create_index("ix_markdown_documents_workspace_id", "markdown_documents", ["workspace_id"], unique=False)
    op.create_index("ix_markdown_documents_type", "markdown_documents", ["document_type"], unique=False)

    op.create_table(
        "document_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("content_revision", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_version", sa.String(length=64), nullable=False),
        sa.Column("snapshot_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["markdown_documents.id"], ondelete="RESTRICT", name="fk_document_snapshot_document"),
        sa.UniqueConstraint("document_id", "content_revision", name="uq_document_snapshot_revision"),
        sa.CheckConstraint("content_revision >= 0", name="ck_document_snapshot_revision"),
    )
    op.create_index("ix_document_snapshots_document_id", "document_snapshots", ["document_id"], unique=False)

    op.create_table(
        "document_updates",
        sa.Column("update_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("content_revision", sa.Integer(), nullable=False),
        sa.Column("payload_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("server_received_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["markdown_documents.id"], ondelete="RESTRICT", name="fk_document_update_document"),
        sa.CheckConstraint("content_revision >= 0", name="ck_document_update_revision"),
    )
    op.create_index(
        "ix_document_updates_document_received",
        "document_updates",
        ["document_id", "server_received_at"],
        unique=False,
    )

    op.create_table(
        "collaboration_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("membership_version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id", "workspace_id"],
            ["markdown_documents.id", "markdown_documents.workspace_id"],
            ondelete="CASCADE",
            name="fk_collaboration_session_document_workspace",
        ),
        sa.UniqueConstraint("token_hash", name="uq_collaboration_session_token_hash"),
        sa.CheckConstraint("membership_version > 0", name="ck_collaboration_session_version"),
        sa.CheckConstraint("length(token_hash) = 64", name="ck_collaboration_session_token_hash"),
        sa.CheckConstraint("expires_at > created_at", name="ck_collaboration_session_expiry"),
    )
    op.create_index(
        "ix_collaboration_sessions_workspace_document",
        "collaboration_sessions",
        ["workspace_id", "document_id"],
        unique=False,
    )
    op.create_index("ix_collaboration_sessions_expiry", "collaboration_sessions", ["expires_at"], unique=False)

    op.create_table(
        "collaboration_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("server_timestamp", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_collaboration_audit_workspace"),
        sa.ForeignKeyConstraint(["document_id"], ["markdown_documents.id"], ondelete="SET NULL", name="fk_collaboration_audit_document"),
        sa.UniqueConstraint("idempotency_key", name="uq_collaboration_audit_idempotency_key"),
        sa.CheckConstraint("length(trim(event_type)) > 0", name="ck_collaboration_audit_event_type"),
        sa.CheckConstraint("revision IS NULL OR revision >= 0", name="ck_collaboration_audit_revision"),
    )
    op.create_index(
        "ix_collaboration_audit_workspace_time",
        "collaboration_audit_events",
        ["workspace_id", "server_timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_collaboration_audit_document_time",
        "collaboration_audit_events",
        ["document_id", "server_timestamp"],
        unique=False,
    )

    # A workspace must commit with exactly one active OWNER. A partial unique
    # index above enforces at-most-one; this deferred trigger enforces at-least-one.
    op.execute(
        """
        CREATE FUNCTION enforce_workspace_exactly_one_active_owner()
        RETURNS trigger AS $$
        DECLARE
            affected_workspaces uuid[];
            target_workspace_id uuid;
            active_owner_count integer;
        BEGIN
            IF TG_TABLE_NAME = 'workspaces' THEN
                affected_workspaces := ARRAY[NEW.id];
            ELSIF TG_OP = 'DELETE' THEN
                affected_workspaces := ARRAY[OLD.workspace_id];
            ELSIF TG_OP = 'UPDATE' AND NEW.workspace_id IS DISTINCT FROM OLD.workspace_id THEN
                affected_workspaces := ARRAY[OLD.workspace_id, NEW.workspace_id];
            ELSE
                affected_workspaces := ARRAY[NEW.workspace_id];
            END IF;

            FOREACH target_workspace_id IN ARRAY affected_workspaces LOOP
                IF EXISTS (SELECT 1 FROM workspaces WHERE id = target_workspace_id) THEN
                    SELECT count(*) INTO active_owner_count
                    FROM workspace_members
                    WHERE workspace_id = target_workspace_id
                      AND role = 'OWNER'
                      AND revoked_at IS NULL;

                    IF active_owner_count <> 1 THEN
                        RAISE EXCEPTION
                            'workspace % must have exactly one active OWNER; found %',
                            target_workspace_id, active_owner_count
                            USING ERRCODE = '23514';
                    END IF;
                END IF;
            END LOOP;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_workspace_owner_invariant_after_create
        AFTER INSERT ON workspaces
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION enforce_workspace_exactly_one_active_owner();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_workspace_owner_invariant_after_membership_change
        AFTER INSERT OR UPDATE OR DELETE ON workspace_members
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION enforce_workspace_exactly_one_active_owner();
        """
    )

    # CRDT updates, snapshots, and audit events are append-only records.
    op.execute(
        """
        CREATE FUNCTION reject_append_only_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME
                USING ERRCODE = '55000';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table_name in ("document_updates", "document_snapshots", "collaboration_audit_events"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_append_only
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();
            """
        )


def downgrade() -> None:
    for table_name in ("document_updates", "document_snapshots", "collaboration_audit_events"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_append_only ON {table_name}")

    op.execute("DROP TRIGGER IF EXISTS trg_workspace_owner_invariant_after_membership_change ON workspace_members")
    op.execute("DROP TRIGGER IF EXISTS trg_workspace_owner_invariant_after_create ON workspaces")
    op.execute("DROP FUNCTION IF EXISTS reject_append_only_mutation()")
    op.execute("DROP FUNCTION IF EXISTS enforce_workspace_exactly_one_active_owner()")

    op.drop_index("ix_collaboration_audit_document_time", table_name="collaboration_audit_events")
    op.drop_index("ix_collaboration_audit_workspace_time", table_name="collaboration_audit_events")
    op.drop_table("collaboration_audit_events")

    op.drop_index("ix_collaboration_sessions_expiry", table_name="collaboration_sessions")
    op.drop_index("ix_collaboration_sessions_workspace_document", table_name="collaboration_sessions")
    op.drop_table("collaboration_sessions")

    op.drop_index("ix_document_updates_document_received", table_name="document_updates")
    op.drop_table("document_updates")

    op.drop_index("ix_document_snapshots_document_id", table_name="document_snapshots")
    op.drop_table("document_snapshots")

    op.drop_index("ix_markdown_documents_type", table_name="markdown_documents")
    op.drop_index("ix_markdown_documents_workspace_id", table_name="markdown_documents")
    op.drop_table("markdown_documents")

    op.drop_index("uq_workspace_active_owner", table_name="workspace_members")
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_table("workspace_members")

    op.drop_table("workspaces")
