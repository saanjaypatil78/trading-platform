"""Workspace role-matrix and persisted-membership authorization tests."""
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from shared.database import Base
from services.collaboration.authorization import (
    WorkspacePermission,
    WorkspaceRole,
    has_permission,
    require_workspace_permission,
)
from services.collaboration.models import Workspace, WorkspaceMember


ROLE_MATRIX = {
    WorkspaceRole.OWNER: set(WorkspacePermission),
    WorkspaceRole.ADMIN: {
        WorkspacePermission.READ,
        WorkspacePermission.EDIT,
        WorkspacePermission.EXECUTE,
        WorkspacePermission.APPROVE,
        WorkspacePermission.MANAGE_MEMBERS,
    },
    WorkspaceRole.COACH: {
        WorkspacePermission.READ,
        WorkspacePermission.EDIT,
        WorkspacePermission.EXECUTE,
        WorkspacePermission.APPROVE,
    },
    WorkspaceRole.EDITOR: {
        WorkspacePermission.READ,
        WorkspacePermission.EDIT,
        WorkspacePermission.EXECUTE,
    },
    WorkspaceRole.VIEWER: {WorkspacePermission.READ},
}


@pytest.mark.parametrize("role", list(WorkspaceRole))
@pytest.mark.parametrize("permission", list(WorkspacePermission))
def test_role_permission_matrix_is_explicit(role, permission):
    assert has_permission(role, permission) is (permission in ROLE_MATRIX[role])


@pytest.mark.parametrize("role", ["ROOT", "owner", "", None])
def test_unknown_or_malformed_role_fails_closed(role):
    assert has_permission(role, WorkspacePermission.READ) is False


@pytest.mark.parametrize("permission", ["DELETE_ALL", "", None])
def test_unknown_permission_fails_closed(permission):
    assert has_permission(WorkspaceRole.OWNER, permission) is False


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Workspace.__table__.create(engine)
    WorkspaceMember.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def create_membership(db_session, role="EDITOR", revoked_at=None):
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    workspace = Workspace(id=workspace_id, name="authorization-test", created_by=user_id)
    membership = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
        membership_version=1,
        revoked_at=revoked_at,
    )
    db_session.add_all([workspace, membership])
    db_session.commit()
    return workspace_id, user_id, membership


def test_active_member_is_authorized_from_database_role(db_session):
    workspace_id, user_id, membership = create_membership(db_session, "EDITOR")
    result = require_workspace_permission(
        db_session, workspace_id, user_id, WorkspacePermission.EDIT
    )
    assert result.id == membership.id
    assert result.role == "EDITOR"


def test_missing_membership_is_denied(db_session):
    with pytest.raises(HTTPException) as exc:
        require_workspace_permission(
            db_session, uuid.uuid4(), uuid.uuid4(), WorkspacePermission.READ
        )
    assert exc.value.status_code == 403


def test_cross_workspace_membership_is_denied(db_session):
    _, user_id, _ = create_membership(db_session, "OWNER")
    with pytest.raises(HTTPException) as exc:
        require_workspace_permission(
            db_session, uuid.uuid4(), user_id, WorkspacePermission.READ
        )
    assert exc.value.status_code == 403


def test_other_user_membership_is_denied(db_session):
    workspace_id, _, _ = create_membership(db_session, "OWNER")
    with pytest.raises(HTTPException) as exc:
        require_workspace_permission(
            db_session, workspace_id, uuid.uuid4(), WorkspacePermission.READ
        )
    assert exc.value.status_code == 403


def test_revoked_membership_is_denied(db_session):
    workspace_id, user_id, _ = create_membership(
        db_session, "OWNER", revoked_at=datetime.now(timezone.utc)
    )
    with pytest.raises(HTTPException) as exc:
        require_workspace_permission(
            db_session, workspace_id, user_id, WorkspacePermission.READ
        )
    assert exc.value.status_code == 403


def test_role_without_permission_is_denied(db_session):
    workspace_id, user_id, _ = create_membership(db_session, "VIEWER")
    with pytest.raises(HTTPException) as exc:
        require_workspace_permission(
            db_session, workspace_id, user_id, WorkspacePermission.EDIT
        )
    assert exc.value.status_code == 403


def test_authorization_database_failure_fails_closed():
    class BrokenQuery:
        def filter(self, *_conditions):
            return self

        def first(self):
            raise OperationalError("SELECT workspace_members", {}, RuntimeError("db down"))

    class BrokenSession:
        def query(self, _model):
            return BrokenQuery()

    with pytest.raises(HTTPException) as exc:
        require_workspace_permission(
            BrokenSession(), uuid.uuid4(), uuid.uuid4(), WorkspacePermission.READ
        )
    assert exc.value.status_code == 503
