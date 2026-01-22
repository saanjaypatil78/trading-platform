
from fastapi import APIRouter
from backend.services.auth.usage_tracker import UsageTracker

router = APIRouter(tags=["Auth & Credits"])

@router.get("/credits/balance")
async def get_balance(user_id: str = "default_user"):
    """
    Get current Factrade Token balance for the user.
    """
    balance = UsageTracker.get_balance(user_id)
    return {"balance": balance, "currency": "FACT"}
