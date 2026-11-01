from fastapi import APIRouter, Depends

from backend.services.auth.identity import AuthenticatedUser, get_current_user
from backend.services.auth.usage_tracker import UsageTracker

router = APIRouter(tags=["Auth & Credits"])


@router.get("/credits/balance")
async def get_balance(user: AuthenticatedUser = Depends(get_current_user)):
    """Return the authenticated user's Factrade Token balance."""
    balance = UsageTracker.get_balance(user.user_id)
    return {"balance": balance, "currency": "FACT"}
