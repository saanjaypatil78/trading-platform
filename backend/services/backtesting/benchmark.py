"""
HFT Performance Benchmark: NumPy vs Numba
Tests execution speed for a rolling SMA crossover strategy.
"""
import numpy as np
import time
import pandas as pd

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

# 1. Standard NumPy (Vectorized)
def numpy_sma_crossover(close, fast_period, slow_period):
    # Rolling mean using stride_tricks for max numpy speed
    def rolling_mean(a, n):
        ret = np.cumsum(a, dtype=float)
        ret[n:] = ret[n:] - ret[:-n]
        return ret[n - 1:] / n

    fast_sma = rolling_mean(close, fast_period)
    slow_sma = rolling_mean(close, slow_period)
    
    # Align lengths
    offset = slow_period - 1
    fast_sma_aligned = fast_sma[slow_period - fast_period:]
    
    signals = np.where(fast_sma_aligned > slow_sma, 1, 0)
    return signals

# 2. Numba Accelerated (JIT)
if HAS_NUMBA:
    @njit
    def numba_sma_crossover(close, fast_period, slow_period):
        n = len(close)
        signals = np.zeros(n - slow_period + 1, dtype=np.int32)
        
        # Pre-calculate first windows
        fast_sum = 0.0
        for i in range(fast_period):
            fast_sum += close[i]
            
        slow_sum = 0.0
        for i in range(slow_period):
            slow_sum += close[i]
            
        # Initial signal
        if (fast_sum/fast_period) > (slow_sum/slow_period):
            signals[0] = 1
            
        # Sliding window
        for i in range(1, n - slow_period + 1):
            # Update slow window
            slow_sum = slow_sum - close[i-1] + close[i + slow_period - 1]
            # Update fast window
            # Fast index is relative to i + slow_period - 1
            fast_sum = fast_sum - close[i + slow_period - fast_period - 1] + close[i + slow_period - 1]
            
            if (fast_sum/fast_period) > (slow_sum/slow_period):
                signals[i] = 1
        
        return signals

def run_benchmark():
    # 1 Million data points
    N = 1_000_000
    close = np.random.random(N).astype(np.float64) * 100
    fast, slow = 50, 200

    print(f"Benchmarking on {N:,} data points...")

    # Warmup
    _ = numpy_sma_crossover(close, fast, slow)
    if HAS_NUMBA:
        _ = numba_sma_crossover(close, fast, slow)

    # NumPy Test
    start = time.time()
    for _ in range(10):
        res_np = numpy_sma_crossover(close, fast, slow)
    np_time = (time.time() - start) / 10
    print(f"NumPy Avg: {np_time*1000:.2f}ms")

    # Numba Test
    if HAS_NUMBA:
        start = time.time()
        for _ in range(10):
            res_nb = numba_sma_crossover(close, fast, slow)
        nb_time = (time.time() - start) / 10
        print(f"Numba Avg: {nb_time*1000:.2f}ms")
        print(f"Speedup: {np_time/nb_time:.1f}x")
    else:
        print("Numba not installed. Skipping.")

if __name__ == "__main__":
    run_benchmark()
