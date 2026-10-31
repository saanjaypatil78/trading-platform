"""PostgreSQL integration tests for one-time collaboration credentials."""
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from services.collaboration.models import (
    CollaborationSession,
    MarkdownDocument,
    Workspace,
    WorkspaceMember,
)
from services.collaboration.sessions import (
    consume_document_credential,
    hash_credential,
    issue_document_credential,
)


@pytest.fixture(scope="module")
def postgres_factory():
    database_url = os.environ["DATABASE_URL"]
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        pytest.skip("Credential lifecycle tests require PostgreSQL row-lock semantics")

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        command.downgrade(config, "base")
        engine.dispose()


def create_document(factory, role="EDITOR"):
    owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    with factory() as db:
        db.add_all([
            Workspace(id=workspace_id, name="credential-test", created_by=owner_id),
            WorkspaceMember(
                id=uuid.uuid4(), workspace_id=workspace_id, user_id=owner_id,
                role="OWNER", membership_version=1,
            ),
            WorkspaceMember(
                id=uuid.uuid4(), workspace_id=workspace_id, user_id=user_id,
                role=role, membership_version=1,
            ),
        ])
        db.flush()
        db.add(
            MarkdownDocument(
                id=document_id,
                workspace_id=workspace_id,
                document_type="research",
                title="Credential test document",
                body="",
                schema_version=1,
                content_revision=0,
                created_by=owner_id,
            )
        )
        db.commit()

    return workspace_id, document_id, user_id


def issue(factory, workspace_id, document_id, user_id):
    with factory() as db:
        return issue_document_credential(db, workspace_id, document_id, user_id)


def test_database_persists_only_hash_and_credential_is_scoped(postgres_factory):
    workspace_id, document_id, user_id = create_document(postgres_factory)
    issued = issue(postgres_factory, workspace_id, document_id, user_id)

    with postgres_factory() as db:
        row = db.query(CollaborationSession).filter_by(id=issued.session_id).one()
        assert row.token_hash == hash_credential(issued.credential)
        assert row.token_hash != issued.credential
        assert len(row.token_hash) == 64
        assert row.consumed_at is None
        assert row.revoked_at is None

    with postgres_factory() as db:
        wrong_document = consume_document_credential(
            db, uuid.uuid4(), issued.credential
        )
    assert wrong_document is None

    with postgres_factory() as db:
        consumed = consume_document_credential(db, document_id, issued.credential)
    assert consumed is not None
    assert consumed.workspace_id == workspace_id
    assert consumed.document_id == document_id
    assert consumed.user_id == user_id
    assert consumed.membership_version == 1
    assert consumed.role == "EDITOR"

    with postgres_factory() as db:
        replay = consume_document_credential(db, document_id, issued.credential)
    assert replay is None


def test_expired_credential_is_rejected_without_consumption(postgres_factory):
    workspace_id, document_id, user_id = create_document(postgres_factory)
    issued = issue(postgres_factory, workspace_id, document_id, user_id)

    # Simulate a clock after the persisted expiry. Do not mutate expires_at:
    # the database correctly enforces expires_at > created_at.
    simulated_now = issued.expires_at + timedelta(seconds=1)
    with postgres_factory() as db:
        consumed = consume_document_credential(
            db, document_id, issued.credential, now=simulated_now
        )
    assert consumed is None

    with postgres_factory() as db:
        row = db.query(CollaborationSession).filter_by(id=issued.session_id).one()
        assert row.consumed_at is None


def test_membership_version_change_burns_credential(postgres_factory):
    workspace_id, document_id, user_id = create_document(postgres_factory)
    issued = issue(postgres_factory, workspace_id, document_id, user_id)

    with postgres_factory() as db:
        member = db.query(WorkspaceMember).filter_by(
            workspace_id=workspace_id, user_id=user_id
        ).one()
        member.membership_version += 1
        db.commit()

    with postgres_factory() as db:
        consumed = consume_document_credential(db, document_id, issued.credential)
    assert consumed is None

    with postgres_factory() as db:
        row = db.query(CollaborationSession).filter_by(id=issued.session_id).one()
        assert row.consumed_at is not None
        assert row.revoked_at is not None


def test_credential_can_be_consumed_by_only_one_concurrent_request(postgres_factory):
    workspace_id, document_id, user_id = create_document(postgres_factory)
    issued = issue(postgres_factory, workspace_id, document_id, user_id)

    def consume_once():
        with postgres_factory() as db:
            return consume_document_credential(db, document_id, issued.credential)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: consume_once(), range(2)))

    assert sum(result is not None for result in results) == 1


def test_malformed_credential_is_rejected(postgres_factory):
    _, document_id, _ = create_document(postgres_factory)
    with postgres_factory() as db:
        assert consume_document_credential(db, document_id, "") is None
        assert consume_document_credential(db, document_id, "x" * 129) is None
