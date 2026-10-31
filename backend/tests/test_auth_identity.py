"""Tests for verified Supabase request identity."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ.setdefault("SUPABASE_URL", "https://auth.example.test")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.services.auth import identity


@pytest.mark.asyncio
async def test_missing_bearer_token_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await identity.get_current_user(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_supabase_token_is_rejected(monkeypatch):
    async def invalid_token(_token):
        return None

    monkeypatch.setattr(identity, "_fetch_supabase_user", invalid_token)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="invalid-token"
    )

    with pytest.raises(HTTPException) as exc:
        await identity.get_current_user(credentials)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verified_user_identity_is_returned(monkeypatch):
    expected_id = "5c7b5f2e-4b0c-4d0f-8f4a-2f53e3c45a10"

    async def verified_user(token):
        assert token == "valid-access-token"
        return {"id": expected_id, "email": "trader@example.test"}

    monkeypatch.setattr(identity, "_fetch_supabase_user", verified_user)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="valid-access-token"
    )

    user = await identity.get_current_user(credentials)
    assert user.user_id == expected_id
    assert user.email == "trader@example.test"
    assert not hasattr(user, "role")


@pytest.mark.asyncio
async def test_missing_provider_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(identity.settings, "SUPABASE_URL", None)
    monkeypatch.setattr(identity.settings, "SUPABASE_ANON_KEY", None)

    with pytest.raises(HTTPException) as exc:
        await identity._fetch_supabase_user("some-token")
    assert exc.value.status_code == 503
