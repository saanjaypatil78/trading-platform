"""PostgreSQL integration checks for the first workspace migration."""
import os
import sys
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")


def test_workspace_migration_constraints_and_downgrade():
    database_url = os.environ["DATABASE_URL"]
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        pytest.skip("Workspace migration integration test requires PostgreSQL")

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    engine = create_engine(database_url, pool_pre_ping=True)

    command.upgrade(config, "head")
    try:
        expected_tables = {
            "workspaces",
            "workspace_members",
            "markdown_documents",
            "document_snapshots",
            "document_updates",
            "collaboration_sessions",
            "collaboration_audit_events",
        }
        assert expected_tables <= set(inspect(engine).get_table_names())

        # The deferred constraint must reject a workspace without an active owner.
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, :name, :creator)"),
                    {"id": uuid.uuid4(), "name": "ownerless", "creator": uuid.uuid4()},
                )

        workspace_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        document_id = uuid.uuid4()
        update_id = uuid.uuid4()
        audit_id = uuid.uuid4()

        # Workspace and its OWNER are created atomically in one transaction.
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, :name, :creator)"),
                {"id": workspace_id, "name": "integration-test", "creator": owner_id},
            )
            connection.execute(
                text(
                    "INSERT INTO workspace_members "
                    "(id, workspace_id, user_id, role) "
                    "VALUES (:id, :workspace_id, :user_id, 'OWNER')"
                ),
                {
                    "id": uuid.uuid4(),
                    "workspace_id": workspace_id,
                    "user_id": owner_id,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO markdown_documents "
                    "(id, workspace_id, document_type, title, body, created_by) "
                    "VALUES (:id, :workspace_id, 'task', 'migration-test', '', :creator)"
                ),
                {
                    "id": document_id,
                    "workspace_id": workspace_id,
                    "creator": owner_id,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO document_updates "
                    "(update_id, document_id, actor_id, content_revision, payload_bytes) "
                    "VALUES (:update_id, :document_id, :actor_id, 1, :payload)"
                ),
                {
                    "update_id": update_id,
                    "document_id": document_id,
                    "actor_id": owner_id,
                    "payload": b"crdt-update",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO collaboration_audit_events "
                    "(id, workspace_id, document_id, actor_id, event_type, revision) "
                    "VALUES (:id, :workspace_id, :document_id, :actor_id, 'DOCUMENT_UPDATE', 1)"
                ),
                {
                    "id": audit_id,
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "actor_id": owner_id,
                },
            )

        # Revoking/demoting the last active owner must fail at transaction commit.
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE workspace_members SET revoked_at = CURRENT_TIMESTAMP "
                        "WHERE workspace_id = :workspace_id AND role = 'OWNER'"
                    ),
                    {"workspace_id": workspace_id},
                )

        # Append-only records reject mutation at the database boundary.
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE document_updates SET payload_bytes = :payload WHERE update_id = :id"),
                    {"payload": b"tampered", "id": update_id},
                )

        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM collaboration_audit_events WHERE id = :id"),
                    {"id": audit_id},
                )
    finally:
        command.downgrade(config, "base")
        engine.dispose()
