"""
Tokenomics Module - Ported from FACTRADE-solana
Source: https://github.com/saanjaypatil78/FACTRADE-solana/blob/main/programs/factrade-token/

This module provides:
- Token configuration and distribution
- Tax calculation (buy/sell/transfer)
- Tax distribution breakdown
- Referral rewards calculation (5-tier)
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class TransactionType(Enum):
    """Transaction types for tax calculation"""
    BUY = "buy"
    SELL = "sell"
    TRANSFER = "transfer"


@dataclass
class TaxDistributionResult:
    """Result of tax distribution calculation"""
    marketing: float
    treasury: float
    burn: float
    holder_rewards: float
    total: float


@dataclass
class ReferralRewardsResult:
    """Result of referral rewards calculation"""
    level1: float
    level2: float
    level3: float
    level4: float
    level5: float
    total: float


# Tokenomics Configuration (from tokenomics.json)
TOKENOMICS_CONFIG = {
    "name": "FACTRADE Token",
    "symbol": "FACT",
    "decimals": 9,
    "total_supply": 1_000_000_000,
    "distribution": {
        "public_sale": {"percentage": 40, "amount": 400_000_000},
        "team": {"percentage": 20, "amount": 200_000_000, "vesting_months": 24, "cliff_months": 6},
        "liquidity": {"percentage": 15, "amount": 150_000_000},
        "ecosystem": {"percentage": 15, "amount": 150_000_000},
        "reserve": {"percentage": 10, "amount": 100_000_000},
    },
    "tax_system": {
        "enabled": True,
        "buy_tax_bps": 200,      # 2% in basis points
        "sell_tax_bps": 200,     # 2%
        "transfer_tax_bps": 100, # 1%
        "distribution": {
            "marketing": 25,     # 25% of tax
            "treasury": 25,
            "burn": 25,
            "holder_rewards": 25,
        },
    },
    "referral_rewards": {
        "enabled": True,
        "tax_allocation_percent": 25,  # 25% of total rewards go to referrals
        "levels": 5,
        "level_distribution": {
            1: 40,  # Level 1 gets 40% of referral pool
            2: 20,
            3: 15,
            4: 15,
            5: 10,
        },
    },
}


def calculate_tax_amount(
    amount: float,
    transaction_type: TransactionType,
    config: Optional[Dict] = None
) -> float:
    """
    Calculate tax amount for a transaction.
    
    Args:
        amount: Transaction amount
        transaction_type: Type of transaction (buy, sell, transfer)
        config: Optional custom config, defaults to TOKENOMICS_CONFIG
    
    Returns:
        Tax amount to be deducted
    
    Example:
        >>> calculate_tax_amount(1000, TransactionType.SELL)
        20.0  # 2% of 1000
    """
    cfg = config or TOKENOMICS_CONFIG
    tax_system = cfg.get("tax_system", {})
    
    if not tax_system.get("enabled", False):
        return 0.0
    
    tax_bps_map = {
        TransactionType.BUY: tax_system.get("buy_tax_bps", 0),
        TransactionType.SELL: tax_system.get("sell_tax_bps", 0),
        TransactionType.TRANSFER: tax_system.get("transfer_tax_bps", 0),
    }
    
    tax_bps = tax_bps_map.get(transaction_type, 0)
    
    # Basis points to percentage: 200 bps = 2% = 0.02
    return (amount * tax_bps) / 10000


def calculate_tax_distribution(
    tax_amount: float,
    config: Optional[Dict] = None
) -> Optional[TaxDistributionResult]:
    """
    Calculate how tax is distributed across categories.
    
    Args:
        tax_amount: Total tax collected
        config: Optional custom config
    
    Returns:
        TaxDistributionResult with breakdown, or None if tax disabled
    
    Example:
        >>> result = calculate_tax_distribution(100)
        >>> result.marketing
        25.0  # 25% of 100
    """
    cfg = config or TOKENOMICS_CONFIG
    tax_system = cfg.get("tax_system", {})
    
    if not tax_system.get("enabled", False):
        return None
    
    distribution = tax_system.get("distribution", {})
    
    marketing = (tax_amount * distribution.get("marketing", 0)) / 100
    treasury = (tax_amount * distribution.get("treasury", 0)) / 100
    burn = (tax_amount * distribution.get("burn", 0)) / 100
    holder_rewards = (tax_amount * distribution.get("holder_rewards", 0)) / 100
    
    return TaxDistributionResult(
        marketing=marketing,
        treasury=treasury,
        burn=burn,
        holder_rewards=holder_rewards,
        total=tax_amount,
    )


def calculate_referral_rewards(
    trading_volume: float,
    config: Optional[Dict] = None
) -> Optional[ReferralRewardsResult]:
    """
    Calculate referral rewards across 5 levels based on trading volume.
    
    Args:
        trading_volume: Total trading volume for reward calculation
        config: Optional custom config
    
    Returns:
        ReferralRewardsResult with per-level breakdown, or None if disabled
    
    Example:
        >>> result = calculate_referral_rewards(10000)
        >>> result.level1
        100.0  # 40% of (25% of 10000) = 40% of 2500 = 1000
    """
    cfg = config or TOKENOMICS_CONFIG
    referral_config = cfg.get("referral_rewards", {})
    
    if not referral_config.get("enabled", False):
        return None
    
    # Total reward pool is a percentage of trading volume
    tax_allocation = referral_config.get("tax_allocation_percent", 0)
    total_reward_pool = (trading_volume * tax_allocation) / 100
    
    level_dist = referral_config.get("level_distribution", {})
    
    level1 = (total_reward_pool * level_dist.get(1, 0)) / 100
    level2 = (total_reward_pool * level_dist.get(2, 0)) / 100
    level3 = (total_reward_pool * level_dist.get(3, 0)) / 100
    level4 = (total_reward_pool * level_dist.get(4, 0)) / 100
    level5 = (total_reward_pool * level_dist.get(5, 0)) / 100
    
    return ReferralRewardsResult(
        level1=level1,
        level2=level2,
        level3=level3,
        level4=level4,
        level5=level5,
        total=total_reward_pool,
    )

class FactradeToken:
    """
    Factrade Token (FACT) Utility Logic.
    Pegged value for platform fetch: 1 Credit = 1 USDT (approx).
    """
    
    # Cost Table (in Credits/Tokens)
    COSTS = {
        "HISTORICAL_DATA": 1.0,   # $1 per fetch/export
        "BACKTEST_RUN": 0.5,      # $0.50 per backtest
        "SCANNER_RUN": 0.1,       # $0.10 per scan
        "LIVE_TRADE": 0.05        # $0.05 per trade
    }

    @staticmethod
    def get_required_credits(action: str) -> float:
        return FactradeToken.COSTS.get(action, 0.0)

    @staticmethod
    def check_balance(current_balance: float, required: float) -> bool:
        return current_balance >= required

    @staticmethod
    def deduct_credits(current_balance: float, action: str) -> float:
        """
        Deduct credits for an action.
        Returns new balance. Raises ValueError if insufficient.
        """
        cost = FactradeToken.get_required_credits(action)
        if current_balance < cost:
            raise ValueError(f"Insufficient FACT tokens. Required: {cost}, Available: {current_balance}")
        return current_balance - cost
