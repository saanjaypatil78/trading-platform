"""Verified Supabase identity for FastAPI request handlers.

The access token is validated by Supabase Auth's /auth/v1/user endpoint.
Never trust a user ID supplied in request parameters or client metadata.
"""
from typing import Optional
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from backend.shared.config import settings

_bearer = HTTPBearer(auto_error=False)
_AUTH_TIMEOUT_SECONDS = 5.0
_MAX_BEARER_LENGTH = 8192


class AuthenticatedUser(BaseModel):
    """Minimal verified identity; workspace roles are resolved separately."""

    user_id: str
    email: Optional[str] = None


async def _fetch_supabase_user(access_token: str) -> Optional[dict]:
    """Ask Supabase Auth to validate the access token and return its user."""
    base_url = (settings.SUPABASE_URL or "").rstrip("/")
    api_key = settings.SUPABASE_ANON_KEY or ""
    if not base_url or not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=_AUTH_TIMEOUT_SECONDS) as client:
            response = await client.get(
                f"{base_url}/auth/v1/user",
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {access_token}",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is temporarily unavailable",
        ) from exc

    if response.status_code in (401, 403):
        return None
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider could not verify the session",
        )

    try:
        payload = response.json()
        user_id = UUID(str(payload.get("id", "")))
    except (ValueError, TypeError, AttributeError):
        return None

    return {"id": str(user_id), "email": payload.get("email")}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthenticatedUser:
    """FastAPI dependency that fails closed when identity cannot be verified."""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials
        or len(credentials.credentials) > _MAX_BEARER_LENGTH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await _fetch_supabase_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(user_id=user["id"], email=user.get("email"))
