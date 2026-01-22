"""
Technical Indicators Module
Provides calculation functions for common technical indicators.
"""
from typing import List, Optional
import math

def sma(prices: List[float], period: int) -> Optional[float]:
    """Simple Moving Average"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def ema(prices: List[float], period: int) -> Optional[float]:
    """Exponential Moving Average"""
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema_value = sum(prices[:period]) / period  # Start with SMA
    
    for price in prices[period:]:
        ema_value = (price - ema_value) * multiplier + ema_value
    
    return ema_value

def rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow:
        return {"macd": None, "signal": None, "histogram": None}
    
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    
    if fast_ema is None or slow_ema is None:
        return {"macd": None, "signal": None, "histogram": None}
    
    macd_line = fast_ema - slow_ema
    
    # For signal line, we need MACD history
    macd_history = []
    for i in range(slow, len(prices) + 1):
        f = ema(prices[:i], fast)
        s = ema(prices[:i], slow)
        if f and s:
            macd_history.append(f - s)
    
    signal_line = ema(macd_history, signal) if len(macd_history) >= signal else None
    histogram = macd_line - signal_line if signal_line else None
    
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> dict:
    """Bollinger Bands"""
    if len(prices) < period:
        return {"upper": None, "middle": None, "lower": None}
    
    middle = sma(prices, period)
    if middle is None:
        return {"upper": None, "middle": None, "lower": None}
    
    # Calculate standard deviation
    squared_diff = [(p - middle) ** 2 for p in prices[-period:]]
    std = math.sqrt(sum(squared_diff) / period)
    
    return {
        "upper": middle + (std_dev * std),
        "middle": middle,
        "lower": middle - (std_dev * std)
    }

def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """Average True Range"""
    if len(highs) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)
    
    return sum(true_ranges[-period:]) / period

def vwap(prices: List[float], volumes: List[float]) -> Optional[float]:
    """Volume Weighted Average Price"""
    if not prices or not volumes or len(prices) != len(volumes):
        return None
    
    total_volume = sum(volumes)
    if total_volume == 0:
        return None
    
    return sum(p * v for p, v in zip(prices, volumes)) / total_volume

def volume_sma(volumes: List[float], period: int = 20) -> Optional[float]:
    """Volume SMA"""
    return sma(volumes, period)

# Indicator registry for dynamic access
INDICATORS = {
    "sma": sma,
    "ema": ema,
    "rsi": rsi,
    "macd": macd,
    "bollinger": bollinger_bands,
    "atr": atr,
    "vwap": vwap,
    "volume_sma": volume_sma
}
