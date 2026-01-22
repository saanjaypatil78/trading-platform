from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime, date
from decimal import Decimal


class StrategyConfig(BaseModel):
    """Configuration for a trading strategy"""
    name: str
    description: Optional[str] = None
    indicators: Dict[str, dict]  # indicator_name: {params}
    entry_rules: str  # Expression DSL
    exit_rules: str
    position_sizing: Literal["fixed", "percent_equity", "kelly"] = "percent_equity"
    position_size_value: float = 0.1  # 10% of equity


class BacktestConfig(BaseModel):
    """Configuration for backtest execution"""
    strategy: StrategyConfig
    symbols: List[str]
    start_date: date
    end_date: date
    interval: Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"] = "1h"  # Default to 1-hour
    initial_capital: Decimal = Field(default=Decimal("100000"))
    commission: Decimal = Field(default=Decimal("0.001"))  # 0.1%
    slippage: Decimal = Field(default=Decimal("0.0005"))  # 0.05%
    engine: Literal["vectorbt", "backtrader", "both"] = "both"
    
    @property
    def is_high_frequency(self) -> bool:
        """Check if timeframe is below 5 minutes (potential HFT)"""
        hft_intervals = ["1m"]
        return self.interval in hft_intervals
    
    @property
    def is_scalping(self) -> bool:
        """Check if timeframe is scalping range (5min or less)"""
        scalping_intervals = ["1m", "5m"]
        return self.interval in scalping_intervals
    
    @property
    def max_data_points(self) -> int:
        """Calculate maximum data points for 5 years"""
        # 5 years worth of bars for each timeframe
        interval_bars = {
            "1m": 365 * 24 * 60 * 5,  # ~2.6M bars
            "5m": 365 * 24 * 12 * 5,  # ~525K bars
            "15m": 365 * 24 * 4 * 5,  # ~175K bars
            "30m": 365 * 24 * 2 * 5,  # ~87K bars
            "1h": 365 * 24 * 5,       # ~43K bars
            "2h": 365 * 12 * 5,       # ~21K bars
            "4h": 365 * 6 * 5,        # ~10K bars
            "1d": 365 * 5,            # ~1.8K bars
        }
        return interval_bars.get(self.interval, 10000)


class Trade(BaseModel):
    """Individual trade record"""
    entry_date: datetime
    exit_date: Optional[datetime] = None
    symbol: str
    direction: Literal["long", "short"]
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: int
    pnl: Optional[Decimal] = None
    pnl_percent: Optional[Decimal] = None
    commission_paid: Decimal
    status: Literal["open", "closed"]


class PerformanceMetrics(BaseModel):
    """Backtest performance metrics"""
    total_return: Decimal
    total_return_percent: Decimal
    cagr: Decimal
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown: Decimal
    max_drawdown_percent: Decimal
    win_rate: Decimal
    profit_factor: Optional[Decimal] = None
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    avg_trade_duration: Optional[float] = None  # in days


class BacktestResult(BaseModel):
    """Complete backtest result"""
    backtest_id: str
    config: BacktestConfig
    performance: PerformanceMetrics
    trades: List[Trade]
    equity_curve: List[Dict[str, float]]  # [{date, equity}]
    executed_at: datetime
    execution_time_ms: int
    engine_used: str
    validation_status: Optional[Literal["passed", "failed", "not_validated"]] = None
    validation_notes: Optional[str] = None


class BacktestContext(BaseModel):
    """Persistent context for resumable backtests"""
    backtest_id: str
    current_date: datetime
    processed_bars: int
    total_bars: int
    portfolio_value: Decimal
    cash: Decimal
    positions: Dict[str, dict]  # symbol: {quantity, avg_price}
    state: Literal["pending", "running", "paused", "completed", "failed"]
    intermediate_results: Dict
    checksum: Optional[str] = None
