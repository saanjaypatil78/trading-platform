"""
State Store - Redis-style fast state management.
Handles LTP, Order Books, and Service state.
"""
from typing import Dict, Any, Optional, List
import time
import json

class StateStore:
    """
    Fast state store for real-time trading data.
    Designed to be a drop-in replacement for Redis.
    """
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        """Set value with optional expiry in seconds."""
        self._data[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        elif key in self._expiry:
            del self._expiry[key]

    def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)

    def hset(self, name: str, key: str, value: Any):
        """Hash set: name -> {key: value}"""
        if name not in self._data:
            self._data[name] = {}
        if not isinstance(self._data[name], dict):
            self._data[name] = {}
        self._data[name][key] = value

    def hget(self, name: str, key: str) -> Optional[Any]:
        """Hash get."""
        return self._data.get(name, {}).get(key)

    def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all hash values."""
        return self._data.get(name, {})

    def lpush(self, name: str, value: Any):
        """List push (left)."""
        if name not in self._data:
            self._data[name] = []
        if not isinstance(self._data[name], list):
            self._data[name] = []
        self._data[name].insert(0, value)
        # Cap list at 1000
        if len(self._data[name]) > 1000:
            self._data[name].pop()

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """List range."""
        lst = self._data.get(name, [])
        if not isinstance(lst, list): return []
        if end == -1: return lst[start:]
        return lst[start:end+1]

# Global Shared State
state = StateStore()

# Standard keys
class StateKeys:
    LTP = "market:ltp"              # Hash: symbol -> price
    ORDERBOOK = "market:orderbook"  # Hash: symbol -> {bids, asks}
    POSITIONS = "trading:positions" # Hash: symbol -> qty
    SIGNALS = "strategy:signals"    # List of recent signals
    SCANNER_RESULTS = "scanner:matches" # Hash: template -> list of symbols
