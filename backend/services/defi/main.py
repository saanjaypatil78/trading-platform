"""
FACTRADE - DeFi Service
Ported from FACTRADE-solana for integrated passive income.
Manages staking, rewards, and tokenomics simulation.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import time
import uuid
import asyncio
from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.state import state, StateKeys

app = FastAPI(title="FACTRADE DeFi Service")

# Models
class StakeRequest(BaseModel):
    user_id: str
    amount: float
    lock_period: int # Days: 7, 14, 30

class ClaimRequest(BaseModel):
    user_id: str

# In-memory database (StateStore used for persistence/sync)
# Mock data for demonstration
STAKE_PERIODS = {
    7: {"apr": 5.0, "multiplier": 1.0},
    14: {"apr": 10.0, "multiplier": 1.5},
    30: {"apr": 20.0, "multiplier": 2.0}
}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "defi"}

@app.post("/api/v1/defi/stake")
async def stake(req: StakeRequest):
    """Stake FACT tokens."""
    if req.lock_period not in STAKE_PERIODS:
        raise HTTPException(status_code=400, detail="Invalid lock period")
    
    stake_id = str(uuid.uuid4())
    stake_info = {
        "id": stake_id,
        "user_id": req.user_id,
        "amount": req.amount,
        "lock_period": req.lock_period,
        "apr": STAKE_PERIODS[req.lock_period]["apr"],
        "timestamp": time.time(),
        "status": "ACTIVE"
    }
    
    # Store in StateStore
    user_stakes = state.hget("defi:stakes", req.user_id) or []
    user_stakes.append(stake_info)
    state.hset("defi:stakes", req.user_id, user_stakes)
    
    # Update TVL
    current_tvl = state.get("defi:tvl") or 0.0
    state.set("defi:tvl", current_tvl + req.amount)
    
    # Publish Event
    await bus.publish(Event.create(
        event_type="defi.stake",
        payload=stake_info,
        source="defi_service"
    ))
    
    return stake_info

@app.get("/api/v1/defi/rewards/{user_id}")
async def get_rewards(user_id: str):
    """Calculate pending rewards based on stakes."""
    stakes = state.hget("defi:stakes", user_id) or []
    total_pending = 0.0
    
    now = time.time()
    for s in stakes:
        # Simple daily interest calculation
        days_elapsed = (now - s["timestamp"]) / (24 * 3600)
        daily_rate = (s["apr"] / 100) / 365
        pending = s["amount"] * daily_rate * days_elapsed
        total_pending += pending
        
    return {
        "user_id": user_id,
        "pending_rewards": round(total_pending, 4),
        "total_active_stakes": len(stakes)
    }

@app.post("/api/v1/defi/claim")
async def claim(req: ClaimRequest):
    """Claim pending rewards."""
    rewards = await get_rewards(req.user_id)
    if rewards["pending_rewards"] <= 0:
        raise HTTPException(status_code=400, detail="No rewards to claim")
    
    # Update lifetime claimed in state
    total_claimed = state.hget("defi:claimed", req.user_id) or 0.0
    state.hset("defi:claimed", req.user_id, total_claimed + rewards["pending_rewards"])
    
    # Reset stake timestamps (simplified claim logic)
    stakes = state.hget("defi:stakes", req.user_id) or []
    for s in stakes:
        s["timestamp"] = time.time()
    state.hset("defi:stakes", req.user_id, stakes)
    
    return {
        "status": "SUCCESS",
        "amount_claimed": rewards["pending_rewards"]
    }

@app.get("/api/v1/defi/stats")
async def get_stats():
    """Get global DeFi stats."""
    tvl = state.get("defi:tvl") or 456700000.0 # Default mock
    return {
        "total_value_locked": tvl,
        "active_stakers": 12485,
        "base_apr": 12.0,
        "max_apr": 25.0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
