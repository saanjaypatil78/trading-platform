"""
FACTRADE-inspired Algorithmic Trading Patterns
Ported from https://github.com/saanjaypatil78/FACTRADE-solana

This module provides:
- Tokenomics configuration and tax calculations
- Referral reward distribution (5-tier)
- Staking APY calculations (dynamic based on TVL)
- Auto-compound logic
"""

from .tokenomics import (
    TOKENOMICS_CONFIG,
    calculate_tax_amount,
    calculate_tax_distribution,
    calculate_referral_rewards,
    TransactionType,
)

from .staking import (
    STAKING_CONFIG,
    calculate_dynamic_apy,
    calculate_stake_rewards,
    calculate_compound_value,
    LockPeriod,
)

__all__ = [
    # Tokenomics
    "TOKENOMICS_CONFIG",
    "calculate_tax_amount",
    "calculate_tax_distribution",
    "calculate_referral_rewards",
    "TransactionType",
    # Staking
    "STAKING_CONFIG",
    "calculate_dynamic_apy",
    "calculate_stake_rewards",
    "calculate_compound_value",
    "LockPeriod",
]
