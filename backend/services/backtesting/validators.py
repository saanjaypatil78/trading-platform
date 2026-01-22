import pandas as pd
import numpy as np
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Multi-layer validation for market data
    Prevents hallucination by catching data anomalies
    """
    
    @staticmethod
    def validate_ohlcv(data: pd.DataFrame, symbol: str) -> tuple[bool, List[str]]:
        """
        Validate OHLCV data integrity
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
            return False, errors
        
        # Price sanity checks
        if not (data['high'] >= data['low']).all():
            errors.append("High price less than low price detected")
        
        if not (data['high'] >= data['open']).all():
            bad_rows = data[data['high'] < data['open']].index.tolist()
            errors.append(f"High price less than open price in rows: {bad_rows[:5]}")
        
        if not (data['high'] >= data['close']).all():
            bad_rows = data[data['high'] < data['close']].index.tolist()
            errors.append(f"High price less than close price in rows: {bad_rows[:5]}")
        
        if not (data['low'] <= data['open']).all():
            bad_rows = data[data['low'] > data['open']].index.tolist()
            errors.append(f"Low price greater than open price in rows: {bad_rows[:5]}")
        
        if not (data['low'] <= data['close']).all():
            bad_rows = data[data['low'] > data['close']].index.tolist()
            errors.append(f"Low price greater than close price in rows: {bad_rows[:5]}")
        
        # No zero or negative values
        if (data[required_cols] <= 0).any().any():
            errors.append("Zero or negative values detected in OHLCV data")
        
        # Reasonable price changes (< 50% single candle circuit limit)
        price_ratio = data['high'] / data['low']
        extreme_moves = price_ratio[price_ratio > 1.5]
        if not extreme_moves.empty:
            errors.append(
                f"Extreme price moves detected (>50% single bar): "
                f"{len(extreme_moves)} occurrences"
            )
        
        # No missing values
        if data[required_cols].isnull().any().any():
            null_counts = data[required_cols].isnull().sum()
            errors.append(f"Null values detected: {null_counts[null_counts > 0].to_dict()}")
        
        # Timestamps are monotonically increasing
        if not data.index.is_monotonic_increasing:
            errors.append("Timestamps are not monotonically increasing")
        
        # Check for duplicate timestamps
        if data.index.duplicated().any():
            dup_count = data.index.duplicated().sum()
            errors.append(f"Duplicate timestamps detected: {dup_count} duplicates")
        
        # Volume sanity check (should be positive)
        if (data['volume'] < 0).any():
            errors.append("Negative volume detected")
        
        # Check for data gaps (missing trading days)
        if len(data) > 1:
            time_diff = data.index.to_series().diff()
            # Expect max 3 days gap (weekend + holiday)
            large_gaps = time_diff[time_diff > pd.Timedelta(days=4)]
            if not large_gaps.empty:
                logger.warning(
                    f"{symbol}: {len(large_gaps)} large time gaps detected "
                    f"(>4 days). This may indicate missing data."
                )
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.error(f"Data validation failed for {symbol}: {errors}")
        
        return is_valid, errors
    
    @staticmethod
    def cross_validate_data(
        data1: pd.DataFrame, 
        data2: pd.DataFrame, 
        tolerance: float = 0.02
    ) -> bool:
        """
        Cross-validate data from two providers
        Returns True if data matches within tolerance (2%)
        """
        if len(data1) != len(data2):
            logger.warning("Data length mismatch between providers")
            return False
        
        # Align data by index
        common_index = data1.index.intersection(data2.index)
        d1 = data1.loc[common_index]
        d2 = data2.loc[common_index]
        
        # Compare prices within tolerance
        for col in ['close', 'high', 'low']:
            if col in d1.columns and col in d2.columns:
                diff_percent = abs((d1[col] - d2[col]) / d1[col])
                mismatches = diff_percent > tolerance
                
                if mismatches.any():
                    mismatch_pct = (mismatches.sum() / len(d1)) * 100
                    logger.warning(
                        f"{col} price mismatch: {mismatch_pct:.1f}% of data points "
                        f"exceed {tolerance*100}% tolerance"
                    )
                    if mismatch_pct > 10:  # More than 10% mismatches
                        return False
        
        return True


class CalculationVerifier:
    """
    Verify indicator calculations against ground truth
    Prevents calculation hallucination
    """
    
    @staticmethod
    def verify_sma(data: pd.Series, period: int, expected: pd.Series) -> bool:
        """Verify Simple Moving Average calculation"""
        calculated = data.rolling(window=period).mean()
        return np.allclose(
            calculated.dropna(), 
            expected.dropna(), 
            rtol=1e-5,
            equal_nan=True
        )
    
    @staticmethod
    def verify_ema(data: pd.Series, period: int, expected: pd.Series) -> bool:
        """Verify Exponential Moving Average calculation"""
        calculated = data.ewm(span=period, adjust=False).mean()
        return np.allclose(
            calculated.dropna(), 
            expected.dropna(), 
            rtol=1e-5,
            equal_nan=True
        )
    
    @staticmethod
    def generate_test_cases() -> List[Dict]:
        """
        Generate test cases with known inputs and expected outputs
        Used for continuous validation
        """
        # Simple test case: constant price should give constant SMA
        test1 = {
            'name': 'constant_price',
            'data': pd.Series([100.0] * 20),
            'sma_10': pd.Series([100.0] * 20),
            'rsi_14': pd.Series([50.0] * 20)  # Neutral RSI
        }
        
        # Linear uptrend
        test2 = {
            'name': 'linear_uptrend',
            'data': pd.Series(range(100, 120)),
            'expected_trend': 'up'
        }
        
        return [test1, test2]
