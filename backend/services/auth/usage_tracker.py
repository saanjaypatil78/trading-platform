"""
Usage Tracker Service
Tracks trade usage and enforces trial limits (Monetization Gate).
Uses Redis for persistence.
"""
import logging
from typing import Optional
from backend.shared.state import state  # Redis wrapper
from datetime import datetime

logger = logging.getLogger(__name__)

from backend.shared.algorithms.tokenomics import FactradeToken

class UsageTracker:
    """
    Tracks usage and enforces Factrade Token limits.
    """
    
    KEY_PREFIX = "wallet:fact_balance:"
    
    @classmethod
    def get_balance(cls, user_id: str = "default_user") -> float:
        """Get current FACT token balance."""
        key = f"{cls.KEY_PREFIX}{user_id}"
        try:
            val = state.hget("user_wallets", key)
            # Default to 10.0 credits (Trial Gift) if not set
            if val is None:
                initial_gift = 10.0
                state.hset("user_wallets", key, initial_gift)
                return initial_gift
            return float(val)
        except:
            return 0.0

    @classmethod
    def debit_user(cls, user_id: str, action: str) -> bool:
        """
        Attempt to debit user for an action.
        Returns True if successful, False if insufficient funds.
        """
        try:
            balance = cls.get_balance(user_id)
            new_balance = FactradeToken.deduct_credits(balance, action)
            
            # Persist new balance
            key = f"{cls.KEY_PREFIX}{user_id}"
            state.hset("user_wallets", key, new_balance)
            
            logger.info(f"User {user_id} debited for {action}. New Balance: {new_balance} FACT")
            return True
        except ValueError as e:
            logger.warning(f"Debit failed for {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"System error during debit: {e}")
            return False

    @staticmethod
    def get_monetization_message() -> str:
        return "Insufficient FACT Tokens. Please purchase more to continue."
