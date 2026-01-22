"""
Vectorized Scanner Conditions Module
Uses NumPy and Pandas for high-performance stock screening.
"""
import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from pydantic import BaseModel

class Operator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    CROSS_ABOVE = "crosses_above"
    CROSS_BELOW = "crosses_below"

class Condition(BaseModel):
    """A single scanner condition"""
    left: str
    operator: Operator
    right: str

class ScannerConditions(BaseModel):
    """Collection of conditions with AND/OR logic"""
    conditions: List[Condition]
    logic: str = "AND"

class VectorizedEvaluator:
    """
    Evaluates scanner conditions using vectorized operations.
    """
    
    def __init__(self):
        self.operators = {
            Operator.GT: np.greater,
            Operator.GTE: np.greater_equal,
            Operator.LT: np.less,
            Operator.LTE: np.less_equal,
            Operator.EQ: np.equal,
            Operator.NEQ: np.not_equal,
        }

    def evaluate_stock(self, conditions: ScannerConditions, df: pd.DataFrame) -> bool:
        """
        Evaluate conditions against a single stock's historical DataFrame.
        Returns True if the LATEST row matches.
        """
        if df.empty:
            return False
            
        final_mask = None
        
        for condition in conditions.conditions:
            left_series = self._resolve_expression(condition.left, df)
            right_series = self._resolve_expression(condition.right, df)
            
            if left_series is None or right_series is None:
                mask = np.zeros(len(df), dtype=bool)
            elif condition.operator == Operator.CROSS_ABOVE:
                mask = self._cross_above(left_series, right_series)
            elif condition.operator == Operator.CROSS_BELOW:
                mask = self._cross_below(left_series, right_series)
            else:
                op_func = self.operators.get(condition.operator)
                mask = op_func(left_series, right_series)
            
            if final_mask is None:
                final_mask = mask
            else:
                if conditions.logic == "AND":
                    final_mask &= mask
                else:
                    final_mask |= mask
        
        return bool(final_mask[-1]) if final_mask is not None else False

    def _resolve_expression(self, expr: str, df: pd.DataFrame) -> Optional[pd.Series]:
        """Resolves an expression (close, rsi(14), numbers) to a pandas Series."""
        expr = expr.strip()
        
        # 1. Numeric Constant
        try:
            val = float(expr)
            return pd.Series([val] * len(df), index=df.index)
        except ValueError:
            pass
            
        # 2. Direct Column
        if expr in df.columns:
            return df[expr]
            
        # 3. Technical Indicator: name(args)
        if "(" in expr and ")" in expr:
            name = expr[:expr.index("(")].strip().lower()
            args = expr[expr.index("(")+1:expr.rindex(")")].strip()
            
            if name == "rsi":
                period = int(args) if args else 14
                return ta.rsi(df['close'], length=period)
            elif name == "sma":
                period = int(args.split(",")[-1])
                return ta.sma(df['close'], length=period)
            elif name == "ema":
                period = int(args.split(",")[-1])
                return ta.ema(df['close'], length=period)
            elif name == "macd":
                macd_df = ta.macd(df['close'])
                return macd_df.iloc[:, 0] if macd_df is not None else None
            elif name == "macd_signal":
                macd_df = ta.macd(df['close'])
                return macd_df.iloc[:, 2] if macd_df is not None else None
            elif name == "bb_upper":
                bb = ta.bbands(df['close'])
                return bb.iloc[:, 2] if bb is not None else None
            elif name == "bb_lower":
                bb = ta.bbands(df['close'])
                return bb.iloc[:, 0] if bb is not None else None

        return None

    def _cross_above(self, series_a: pd.Series, series_b: pd.Series) -> np.ndarray:
        """Vectorized Cross Above logic."""
        return (series_a > series_b) & (series_a.shift(1) <= series_b.shift(1))

    def _cross_below(self, series_a: pd.Series, series_b: pd.Series) -> np.ndarray:
        """Vectorized Cross Below logic."""
        return (series_a < series_b) & (series_a.shift(1) >= series_b.shift(1))

# Updated Templates
SCANNER_TEMPLATES = {
    "rsi_overbought": ScannerConditions(
        conditions=[Condition(left="rsi(14)", operator=Operator.GT, right="70")],
        logic="AND"
    ),
    "rsi_oversold": ScannerConditions(
        conditions=[Condition(left="rsi(14)", operator=Operator.LT, right="30")],
        logic="AND"
    ),
    "golden_cross": ScannerConditions(
        conditions=[
            Condition(left="sma(close, 50)", operator=Operator.CROSS_ABOVE, right="sma(close, 200)")
        ],
        logic="AND"
    ),
    "death_cross": ScannerConditions(
        conditions=[
            Condition(left="sma(close, 50)", operator=Operator.CROSS_BELOW, right="sma(close, 200)")
        ],
        logic="AND"
    )
}
