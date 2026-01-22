from pydantic import BaseModel
from typing import Optional, Dict
from enum import Enum

class LockPeriodEnum(str, Enum):
    DAYS_7 = "DAYS_7"
    DAYS_14 = "DAYS_14"
    DAYS_30 = "DAYS_30"

class StakeRequest(BaseModel):
    principal: float
    lock_period: LockPeriodEnum
    tvl_millions: Optional[float] = None

class StakeResponse(BaseModel):
    principal: float
    rewards: float
    total: float
    apy_used: float
    days_staked: int

class ReferralRequest(BaseModel):
    trading_volume: float

class ReferralResponse(BaseModel):
    level1: float
    level2: float
    level3: float
    level4: float
    level5: float
    total: float

class TaxRequest(BaseModel):
    amount: float
    transaction_type: str  # buy, sell, transfer

class TaxResponse(BaseModel):
    tax_amount: float
    distribution: Optional[Dict[str, float]]
