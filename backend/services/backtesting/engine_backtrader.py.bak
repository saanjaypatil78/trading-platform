"""
Event-driven Backtesting Engine using backtrader  
Provides realistic trade simulation closer to live trading
"""
import pandas as pd
from typing import Dict, List
import logging
from decimal import Decimal
from datetime import datetime

try:
    import backtrader as bt
except ImportError:
    bt = None
    logging.warning("backtrader not installed. Install with: pip install backtrader")

from .validators import DataValidator

logger = logging.getLogger(__name__)



if bt is not None:
    class BacktraderStrategy(bt.Strategy):
        """Base strategy class for backtrader"""
        
        params = (
            ('rsi_period', 14),
            ('rsi_lower', 30),
            ('rsi_upper', 70),
            ('sma_period', 20),
        )
        
        def __init__(self):
            # Indicators
            self.rsi = bt.indicators.RSI(
                self.data.close,
                period=self.params.rsi_period
            )
            self.sma = bt.indicators.SMA(
                self.data.close,
                period=self.params.sma_period
            )
            
            # Track trades
            self.trade_list = []
        
        def next(self):
            """Called for each bar"""
            # Simple RSI strategy
            if not self.position:
                # Entry: RSI oversold and price above SMA
                if self.rsi < self.params.rsi_lower and self.data.close > self.sma:
                    size = int(self.broker.get_cash() * 0.95 / self.data.close)
                    self.buy(size=size)
            else:
                # Exit: RSI overbought or price below SMA
                if self.rsi > self.params.rsi_upper or self.data.close < self.sma:
                    self.close()
        
        def notify_order(self, order):
            """Track order execution"""
            if order.status in [order.Completed]:
                if order.isbuy():
                    self.log(
                        f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}'
                    )
                else:
                    self.log(
                        f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, '
                        f'Comm: {order.executed.comm:.2f}'
                    )
        
        def notify_trade(self, trade):
            """Track trade closure"""
            if trade.isclosed:
                self.trade_list.append({
                    'entry_date': bt.num2date(trade.dtopen),
                    'exit_date': bt.num2date(trade.dtclose),
                    'entry_price': trade.price,
                    'exit_price': trade.price + trade.pnl / trade.size,
                    'pnl': trade.pnl,
                    'pnl_percent': (trade.pnl / (trade.price * trade.size)) * 100,
                    'commission': trade.commission,
                    'status': 'closed'
                })
        
        def log(self, txt):
            """Logging function"""
            date = self.datas[0].datetime.date(0)
            logger.debug(f'{date.isoformat()} - {txt}')
else:
    class BacktraderStrategy:
        pass



class BacktraderEngine:
    """Event-driven backtesting engine using backtrader"""
    
    def __init__(self):
        if bt is None:
            raise ImportError("backtrader is required. Install with: pip install backtrader")
    
    async def run_backtest(
        self,
        data: pd.DataFrame,
        strategy_config: dict,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.0005
    ) -> Dict:
        """
        Execute event-driven backtest
        
        Args:
            data: OHLCV data with datetime index
            strategy_config: Strategy parameters
            initial_capital: Starting capital
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
        
        Returns:
            Dictionary with performance metrics and trades
        """
        # Validate data
        is_valid, errors = DataValidator.validate_ohlcv(
            data,
            strategy_config.get('symbol', 'UNKNOWN')
        )
        
        if not is_valid:
            raise ValueError(f"Data validation failed: {errors}")
        
        logger.info(f"Running backtrader backtest on {len(data)} bars")
        
        # Create cerebro engine
        cerebro = bt.Cerebro()
        
        # Add strategy
        cerebro.addstrategy(BacktraderStrategy)
        
        # Convert pandas DataFrame to backtrader data feed
        bt_data = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Use index
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        
        cerebro.adddata(bt_data)
        
        # Set initial capital
        cerebro.broker.setcash(initial_capital)
        
        # Set commission
        cerebro.broker.setcommission(commission=commission)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # Run backtest
        start_value = cerebro.broker.getvalue()
        results = cerebro.run()
        end_value = cerebro.broker.getvalue()
        
        # Extract results
        strategy = results[0]
        
        # Extract metrics
        metrics = self._extract_metrics(
            strategy,
            start_value,
            end_value
        )
        
        # Extract trades
        trades = strategy.trade_list
        
        # Generate equity curve (simplified - backtrader doesn't provide this directly)
        equity_curve = self._generate_equity_curve(start_value, end_value, len(data))
        
        return {
            'performance': metrics,
            'trades': trades,
            'equity_curve': equity_curve,
            'total_bars': len(data),
            'engine': 'backtrader'
        }
    
    def _extract_metrics(
        self,
        strategy,
        start_value: float,
        end_value: float
    ) -> Dict:
        """Extract performance metrics from strategy analyzers"""
        # Sharpe Ratio
        sharpe = strategy.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe.get('sharperatio', 0) if sharpe else 0
        
        # Drawdown
        drawdown = strategy.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown.get('max', {}).get('drawdown', 0)
        
        # Trade Analysis
        trade_analysis = strategy.analyzers.trades.get_analysis()
        total_trades = trade_analysis.get('total', {}).get('total', 0)
        won_trades = trade_analysis.get('won', {}).get('total', 0)
        lost_trades = trade_analysis.get('lost', {}).get('total', 0)
        
        # Win rate
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Returns
        total_return = ((end_value - start_value) / start_value) * 100
        
        # Profit factor
        gross_profit = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)
        gross_loss = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio if sharpe_ratio else 0,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'winning_trades': won_trades,
            'losing_trades': lost_trades,
            'profit_factor': profit_factor
        }
    
    def _generate_equity_curve(
        self,
        start_value: float,
        end_value: float,
        num_points: int
    ) -> List[Dict]:
        """
        Generate simplified equity curve
        Note: backtrader doesn't provide easy access to equity curve
        In production, track this manually in strategy
        """
        # Simple linear interpolation for demonstration
        step = (end_value - start_value) / num_points
        
        return [
            {
                'date': f'day_{i}',
                'equity': start_value + (i * step)
            }
            for i in range(num_points + 1)
        ]
