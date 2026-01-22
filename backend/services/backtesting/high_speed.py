"""
High-Speed Backtesting Engine (Numba Accelerated)
Vectorized and JIT-compiled for HFT-grade performance.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
import time

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(func): return func # Dummy decorator to prevent NameError

@njit
def execute_crossover_strategy(close: np.ndarray, fast_sma: np.ndarray, slow_sma: np.ndarray) -> np.ndarray:
    """
    JIT-compiled strategy loop. Faster than vanilla NumPy for complex logic.
    """
    n = len(close)
    signals = np.zeros(n, dtype=np.int32)
    for i in range(1, n):
        if fast_sma[i] > slow_sma[i] and fast_sma[i-1] <= slow_sma[i-1]:
            signals[i] = 1 # Buy
        elif fast_sma[i] < slow_sma[i] and fast_sma[i-1] >= slow_sma[i-1]:
            signals[i] = -1 # Sell/Close
        else:
            signals[i] = signals[i-1] # Carry position
    return signals

class HighSpeedBacktest:
    """
    Accelerated backtester using Numba JIT and NumPy.
    """
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.close = data['close'].values.astype(np.float64)
        
    def run_sma_crossover(self, fast_window: int, slow_window: int) -> Dict[str, Any]:
        start_time = time.time()
        
        # Calculate SMAs (Rolling mean is efficient in Pandas/NumPy)
        fast_sma = self.data['close'].rolling(window=fast_window).mean().values
        slow_sma = self.data['close'].rolling(window=slow_window).mean().values
        
        # Strategy Execution
        if HAS_NUMBA:
            signals = execute_crossover_strategy(self.close, fast_sma, slow_sma)
        else:
            # Fallback to NumPy vectorization for simple crossover
            signals = np.where(fast_sma > slow_sma, 1, 0)
        
        # Calculate Returns
        returns = np.diff(self.close) / self.close[:-1]
        strategy_returns = signals[:-1] * returns
        
        # Metrics
        cum_returns = np.cumprod(1 + strategy_returns) - 1
        total_return = cum_returns[-1] if len(cum_returns) > 0 else 0
        
        # Risk Metrics
        vol = np.std(strategy_returns) * np.sqrt(252)
        sharpe = (np.mean(strategy_returns) / vol * np.sqrt(252)) if vol > 0 else 0
        
        return {
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "execution_time_ms": round((time.time() - start_time) * 1000, 4),
            "engine": "Numba" if HAS_NUMBA else "NumPy"
        }

    def optimize_params(self, fast_range: range, slow_range: range) -> List[Dict[str, Any]]:
        results = []
        for f in fast_range:
            for s in slow_range:
                if f >= s: continue
                res = self.run_sma_crossover(f, s)
                res["fast"] = f
                res["slow"] = s
                results.append(res)
        return sorted(results, key=lambda x: x["total_return_pct"], reverse=True)

if __name__ == "__main__":
    # Benchmark on load
    print(f"Engine Acceleration: {'ENABLED (Numba)' if HAS_NUMBA else 'DISABLED (NumPy Only)'}")
    dates = pd.date_range('2023-01-01', periods=5000)
    prices = 100 + np.cumsum(np.random.normal(0.01, 1, 5000))
    df = pd.DataFrame({'close': prices}, index=dates)
    
    engine = HighSpeedBacktest(df)
    res = engine.run_sma_crossover(50, 200)
    print(f"Test Result: {res}")
