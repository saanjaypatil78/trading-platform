"""
Vectorized Backtesting Engine using vectorbt
Optimized for speed - can test thousands of parameter combinations rapidly
"""
import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from decimal import Decimal

try:
    import vectorbt as vbt
except ImportError:
    vbt = None
    logging.warning("vectorbt not installed. Install with: pip install vectorbt")

from .models import BacktestResult, PerformanceMetrics, Trade
from .validators import DataValidator

logger = logging.getLogger(__name__)


class VectorbtEngine:
    """Fast vectorized backtesting engine"""
    
    def __init__(self):
        if vbt is None:
            raise ImportError("vectorbt is required. Install with: pip install vectorbt")
    
    async def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_config: dict,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.0005
    ) -> Dict:
        """
        Execute vectorized backtest
        
        Args:
            data: OHLCV data with datetime index
            strategy_config: Strategy parameters
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
        
        Returns:
            Dictionary with performance metrics and trades
        """
        # Validate data first
        is_valid, errors = DataValidator.validate_ohlcv(
            data, 
            strategy_config.get('symbol', 'UNKNOWN')
        )
        
        if not is_valid:
            raise ValueError(f"Data validation failed: {errors}")
        
        logger.info(f"Running vectorbt backtest on {len(data)} bars")
        
        # Calculate indicators (vectorized)
        indicators = self._calculate_indicators(data, strategy_config['indicators'])
        
        # Generate signals (vectorized)
        entries, exits = self._generate_signals(
            data, 
            indicators, 
            strategy_config['entry_rules'],
            strategy_config['exit_rules']
        )
        
        # Run portfolio simulation
        portfolio = vbt.Portfolio.from_signals(
            close=data['close'],
            entries=entries,
            exits=exits,
            init_cash=initial_capital,
            fees=commission,
            slippage=slippage,
            freq='1D'  # Daily frequency
        )
        
        # Extract performance metrics
        metrics = self._extract_metrics(portfolio, initial_capital)
        
        # Extract trades
        trades = self._extract_trades(portfolio)
        
        # Generate equity curve
        equity_curve = self._generate_equity_curve(portfolio)
        
        return {
            'performance': metrics,
            'trades': trades,
            'equity_curve': equity_curve,
            'total_bars': len(data),
            'engine': 'vectorbt'
        }
    
    def _calculate_indicators(
        self, 
        data: pd.DataFrame, 
        indicator_config: Dict
    ) -> Dict[str, pd.Series]:
        """Calculate technical indicators using vectorbt"""
        indicators = {}
        
        for name, params in indicator_config.items():
            if name.upper() == 'RSI':
                period = params.get('period', 14)
                indicators['RSI'] = vbt.RSI.run(data['close'], window=period).rsi
            
            elif name.upper() == 'SMA':
                period = params.get('period', 20)
                indicators[f'SMA_{period}'] = vbt.MA.run(
                    data['close'], 
                    window=period
                ).ma
            
            elif name.upper() == 'EMA':
                period = params.get('period', 20)
                indicators[f'EMA_{period}'] = vbt.MA.run(
                    data['close'], 
                    window=period, 
                    ewm=True
                ).ma
            
            elif name.upper() == 'BBANDS':
                period = params.get('period', 20)
                std_dev = params.get('std_dev', 2)
                bbands = vbt.BBANDS.run(data['close'], window=period, alpha=std_dev)
                indicators['BB_UPPER'] = bbands.upper
                indicators['BB_MIDDLE'] = bbands.middle
                indicators['BB_LOWER'] = bbands.lower
            
            elif name.upper() == 'MACD':
                fast = params.get('fast', 12)
                slow = params.get('slow', 26)
                signal = params.get('signal', 9)
                macd = vbt.MACD.run(data['close'], fast_window=fast, slow_window=slow, signal_window=signal)
                indicators['MACD'] = macd.macd
                indicators['MACD_SIGNAL'] = macd.signal
                indicators['MACD_HIST'] = macd.hist
        
        return indicators
    
    def _generate_signals(
        self,
        data: pd.DataFrame,
        indicators: Dict[str, pd.Series],
        entry_rules: str,
        exit_rules: str
    ) -> tuple[pd.Series, pd.Series]:
        """
        Generate entry and exit signals from rules
        Simplified implementation - in production, use full DSL parser
        """
        # Example: RSI < 30 and price > SMA(20)
        # This is simplified; use the scanner's criteria engine for full support
        
        # For MVP, hardcode common patterns
        if 'RSI' in indicators:
            rsi_oversold = indicators['RSI'] < 30
            rsi_overbought = indicators['RSI'] > 70
        else:
            rsi_oversold = pd.Series([False] * len(data), index=data.index)
            rsi_overbought = pd.Series([False] * len(data), index=data.index)
        
        # Simple entry/exit logic
        entries = rsi_oversold
        exits = rsi_overbought
        
        return entries, exits
    
    def _extract_metrics(self, portfolio, initial_capital: float) -> Dict:
        """Extract performance metrics from portfolio"""
        stats = portfolio.stats()
        
        return {
            'total_return': float(stats.get('Total Return [%]', 0)),
            'sharpe_ratio': float(stats.get('Sharpe Ratio', 0)),
            'max_drawdown': float(stats.get('Max Drawdown [%]', 0)),
            'win_rate': float(stats.get('Win Rate [%]', 0)),
            'total_trades': int(stats.get('Total Trades', 0)),
            'profit_factor': float(stats.get('Profit Factor', 0))
        }
    
    def _extract_trades(self, portfolio) -> List[Dict]:
        """Extract individual trades"""
        trades_df = portfolio.trades.records_readable
        
        trades = []
        for _, row in trades_df.iterrows():
            trades.append({
                'entry_date': row['Entry Timestamp'],
                'exit_date': row['Exit Timestamp'],
                'entry_price': float(row['Entry Price']),
                'exit_price': float(row['Exit Price']),
                'pnl': float(row['PnL']),
                'pnl_percent': float(row['Return [%]']),
                'status': 'closed'
            })
        
        return trades
    
    def _generate_equity_curve(self, portfolio) -> List[Dict]:
        """Generate equity curve data points"""
        equity = portfolio.value()
        
        return [
            {'date': str(date), 'equity': float(value)}
            for date, value in equity.items()
        ]
