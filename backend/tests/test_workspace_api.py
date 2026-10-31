"""HTTP acceptance tests for workspace and document authorization."""
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend.services.auth.identity import AuthenticatedUser, get_current_user
from services.collaboration.router import router
from services.collaboration.models import Workspace, WorkspaceMember, MarkdownDocument
from shared.database import Base, get_db


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    test_user_id = uuid.uuid4()

    def override_user():
        return AuthenticatedUser(user_id=str(test_user_id), email="owner@example.test")

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as client:
        yield client, factory, test_user_id

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_workspace_creation_atomically_creates_owner_and_audit(api_client):
    client, factory, user_id = api_client

    response = client.post("/api/v1/collaboration/workspaces", json={"name": "  My Workspace  "})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Workspace"
    assert data["role"] == "OWNER"

    with factory() as session:
        memberships = session.query(WorkspaceMember).filter_by(workspace_id=data["id"]).all()
        assert len(memberships) == 1
        assert memberships[0].user_id == user_id
        assert memberships[0].role == "OWNER"
        assert session.query(Workspace).count() == 1


def test_workspace_creation_rejects_client_supplied_role(api_client):
    client, _, _ = api_client
    response = client.post(
        "/api/v1/collaboration/workspaces",
        json={"name": "No role injection", "role": "OWNER"},
    )
    assert response.status_code == 422


def test_document_create_requires_edit_and_read_requires_membership(api_client):
    client, factory, user_id = api_client
    workspace_response = client.post(
        "/api/v1/collaboration/workspaces", json={"name": "Docs"}
    )
    workspace_id = workspace_response.json()["id"]

    create_response = client.post(
        f"/api/v1/collaboration/workspaces/{workspace_id}/documents",
        json={"document_type": "research", "title": "Market structure", "body": "# Notes"},
    )
    assert create_response.status_code == 201
    document = create_response.json()
    assert document["body"] == "# Notes"
    assert document["content_revision"] == 0

    list_response = client.get(
        f"/api/v1/collaboration/workspaces/{workspace_id}/documents"
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [document["id"]]

    detail_response = client.get(
        f"/api/v1/collaboration/workspaces/{workspace_id}/documents/{document['id']}"
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == document["id"]


def test_viewer_cannot_create_document_but_can_read(api_client):
    client, factory, owner_id = api_client
    workspace_response = client.post(
        "/api/v1/collaboration/workspaces", json={"name": "Viewer access"}
    )
    workspace_id = uuid.UUID(workspace_response.json()["id"])
    viewer_id = uuid.uuid4()

    with factory() as session:
        session.add(
            WorkspaceMember(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                user_id=viewer_id,
                role="VIEWER",
                membership_version=1,
            )
        )
        session.commit()

    # Rebind the identity dependency to the viewer; role remains DB-owned.
    from backend.services.auth.identity import get_current_user
    from services.collaboration.router import router as collaboration_router
    from backend.services.auth.identity import AuthenticatedUser

    app = FastAPI()
    app.include_router(collaboration_router)
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id=str(viewer_id))
    app.dependency_overrides[get_db] = lambda: next(_session_generator(factory))
    with TestClient(app) as viewer_client:
        forbidden = viewer_client.post(
            f"/api/v1/collaboration/workspaces/{workspace_id}/documents",
            json={"document_type": "lesson", "title": "Should fail"},
        )
        assert forbidden.status_code == 403


def _session_generator(factory):
    session = factory()
    try:
        yield session
    finally:
        session.close()


def test_user_outside_workspace_cannot_read_documents(api_client):
    client, _, _ = api_client
    workspace_response = client.post(
        "/api/v1/collaboration/workspaces", json={"name": "Private"}
    )
    workspace_id = workspace_response.json()["id"]

    app = FastAPI()
    app.include_router(router)
    outsider_id = uuid.uuid4()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id=str(outsider_id))

    client_dependency = api_client[1]
    def override_db():
        session = client_dependency()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as outsider_client:
        response = outsider_client.get(
            f"/api/v1/collaboration/workspaces/{workspace_id}/documents"
        )
        assert response.status_code == 403
