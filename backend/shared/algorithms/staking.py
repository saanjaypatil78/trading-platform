"""
Staking Module - Ported from FACTRADE-solana
Source: https://github.com/saanjaypatil78/FACTRADE-solana/blob/main/app/components/StakingInterface.tsx

This module provides:
- Staking lock periods with APR multipliers
- Dynamic APY calculation based on Total Value Locked (TVL)
- Stake rewards calculation
- Auto-compound logic for maximized returns
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
import math


class LockPeriod(Enum):
    """Pre-defined lock periods with their durations in days"""
    DAYS_7 = 7
    DAYS_14 = 14
    DAYS_30 = 30


@dataclass
class StakeRewardsResult:
    """Result of stake rewards calculation"""
    principal: float
    rewards: float
    total: float
    apy_used: float
    days_staked: int


# Staking Configuration (from StakingInterface.tsx)
STAKING_CONFIG = {
    "lock_periods": {
        LockPeriod.DAYS_7: {
            "days": 7,
            "apr": 8.0,           # 8% APR
            "multiplier": 1.0,
            "unbonding_days": 2,
        },
        LockPeriod.DAYS_14: {
            "days": 14,
            "apr": 15.0,          # 15% APR
            "multiplier": 1.5,
            "unbonding_days": 3,
        },
        LockPeriod.DAYS_30: {
            "days": 30,
            "apr": 20.0,          # 20% APR
            "multiplier": 2.0,
            "unbonding_days": 5,
        },
    },
    "dynamic_apy": {
        "enabled": True,
        "base_apy": 12.0,         # 12% minimum
        "max_apy": 25.0,          # 25% maximum
        "tvl_thresholds": [
            # (TVL in millions, APY adjustment factor)
            (0, 25.0),      # 0-10M TVL: 25% APY
            (10, 22.0),     # 10-50M: 22%
            (50, 18.0),     # 50-100M: 18%
            (100, 15.0),    # 100-500M: 15%
            (500, 12.0),    # 500M+: 12%
        ],
    },
    "auto_compound": {
        "enabled": True,
        "frequency_days": 1,      # Compound daily
        "min_amount": 1.0,        # Minimum amount to compound
    },
}


def calculate_dynamic_apy(
    tvl_millions: float,
    config: Optional[Dict] = None
) -> float:
    """
    Calculate dynamic APY based on Total Value Locked (TVL).
    Lower TVL = Higher APY to attract stakers.
    Higher TVL = Lower APY for sustainability.
    
    Args:
        tvl_millions: Total Value Locked in millions
        config: Optional custom config
    
    Returns:
        APY percentage
    
    Example:
        >>> calculate_dynamic_apy(25)  # 25M TVL
        22.0  # Falls in 10-50M range
    """
    cfg = config or STAKING_CONFIG
    dynamic_config = cfg.get("dynamic_apy", {})
    
    if not dynamic_config.get("enabled", False):
        return dynamic_config.get("base_apy", 12.0)
    
    thresholds = dynamic_config.get("tvl_thresholds", [])
    
    # Find applicable APY based on TVL
    applicable_apy = dynamic_config.get("base_apy", 12.0)
    
    for threshold_tvl, apy in sorted(thresholds, reverse=True):
        if tvl_millions >= threshold_tvl:
            applicable_apy = apy
            break
    
    return applicable_apy


def calculate_stake_rewards(
    principal: float,
    lock_period: LockPeriod,
    days_staked: Optional[int] = None,
    tvl_millions: Optional[float] = None,
    config: Optional[Dict] = None
) -> StakeRewardsResult:
    """
    Calculate staking rewards for a given principal and lock period.
    
    Args:
        principal: Amount staked
        lock_period: Lock period enum
        days_staked: Actual days staked (defaults to lock period)
        tvl_millions: TVL for dynamic APY (if None, uses base APR)
        config: Optional custom config
    
    Returns:
        StakeRewardsResult with principal, rewards, and total
    
    Example:
        >>> result = calculate_stake_rewards(1000, LockPeriod.DAYS_30)
        >>> result.rewards
        16.44  # ~20% APR for 30 days
    """
    cfg = config or STAKING_CONFIG
    periods = cfg.get("lock_periods", {})
    
    period_config = periods.get(lock_period, periods.get(LockPeriod.DAYS_7))
    base_apr = period_config.get("apr", 8.0)
    
    # Use dynamic APY if TVL is provided
    if tvl_millions is not None:
        apy = calculate_dynamic_apy(tvl_millions, cfg)
        # Apply lock period multiplier to dynamic APY
        apy = apy * period_config.get("multiplier", 1.0)
    else:
        apy = base_apr
    
    # Days staked defaults to lock period
    actual_days = days_staked if days_staked is not None else period_config.get("days", 7)
    
    # Calculate rewards: principal * (APY / 100) * (days / 365)
    rewards = principal * (apy / 100) * (actual_days / 365)
    
    return StakeRewardsResult(
        principal=principal,
        rewards=rewards,
        total=principal + rewards,
        apy_used=apy,
        days_staked=actual_days,
    )


def calculate_compound_value(
    principal: float,
    apy: float,
    days: int,
    compound_frequency: int = 1,
    config: Optional[Dict] = None
) -> float:
    """
    Calculate the final value with auto-compounding.
    
    Args:
        principal: Initial stake amount
        apy: Annual Percentage Yield
        days: Number of days to compound
        compound_frequency: How often to compound (1 = daily)
        config: Optional custom config
    
    Returns:
        Final compounded value
    
    Formula:
        A = P * (1 + r/n)^(n*t)
        Where:
        - P = principal
        - r = annual rate (APY / 100)
        - n = compounds per year (365 / compound_frequency)
        - t = time in years (days / 365)
    
    Example:
        >>> calculate_compound_value(1000, 20, 365)
        1221.39  # 20% APY compounded daily for 1 year
    """
    cfg = config or STAKING_CONFIG
    compound_config = cfg.get("auto_compound", {})
    
    if not compound_config.get("enabled", True):
        # Simple interest if compounding disabled
        return principal * (1 + (apy / 100) * (days / 365))
    
    freq = compound_frequency or compound_config.get("frequency_days", 1)
    
    # Rate per compound period
    r = apy / 100
    n = 365 / freq  # Compounds per year
    t = days / 365  # Time in years
    
    # Compound interest formula
    final_value = principal * math.pow(1 + r / n, n * t)
    
    return round(final_value, 2)


def get_lock_period_config(
    lock_period: LockPeriod,
    config: Optional[Dict] = None
) -> Dict:
    """
    Get configuration for a specific lock period.
    
    Args:
        lock_period: Lock period enum
        config: Optional custom config
    
    Returns:
        Dictionary with days, apr, multiplier, unbonding_days
    """
    cfg = config or STAKING_CONFIG
    periods = cfg.get("lock_periods", {})
    return periods.get(lock_period, {})
