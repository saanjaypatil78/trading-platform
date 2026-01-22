"""
Main Backtesting Service Coordinator
Orchestrates vectorbt and backtrader engines with validation
"""
import pandas as pd
from typing import Dict, Optional
import uuid
import logging
from datetime import datetime
import httpx

from .models import BacktestConfig, BacktestResult, PerformanceMetrics, Trade
from .engine_vectorbt import VectorbtEngine
from .engine_backtrader import BacktraderEngine
from .validators import DataValidator
from .timeframe_validator import TimeframeValidator, RiskAcknowledgment
from .context_manager import ContextManager, EventStore
from shared.config import settings

logger = logging.getLogger(__name__)


class BacktestService:
    """
    Main backtesting service with hybrid engine approach
    Uses vectorbt for speed, backtrader for validation
    """
    
    def __init__(self):
        self.vectorbt_engine = VectorbtEngine()
        self.backtrader_engine = BacktraderEngine()
        self.market_data_url = f"http://market-data-service:{settings.API_PORT}"
    
    async def execute_backtest(
        self,
        config: BacktestConfig,
        resume: bool = False,
        user_id: str = "anonymous",
        risk_acknowledged: bool = False
    ) -> BacktestResult:
        """
        Execute backtest with specified configuration
        
        Args:
            config: Backtest configuration
            resume: If True, attempt to resume from checkpoint
            user_id: User identifier for risk tracking
            risk_acknowledged: Whether user acknowledged risks for risky timeframes
        
        Returns:
            BacktestResult with performance metrics and trades
        
        Raises:
            ValueError: If timeframe validation fails or risks not acknowledged
        """
        backtest_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # 🚨 VALIDATE TIMEFRAME AND ISSUE WARNINGS
        is_valid, warning = TimeframeValidator.validate_timeframe(config.interval)
        
        if not is_valid and warning:
            # Check if user already acknowledged
            if not risk_acknowledged:
                # Return warning for user acknowledgment
                raise ValueError({
                    "type": "timeframe_warning",
                    "warning": warning,
                    "message": "User must acknowledge risks before proceeding",
                    "requires_action": True
                })
            else:
                # Record acknowledgment
                await RiskAcknowledgment.record_acknowledgment(
                    user_id,
                    config.interval,
                    True
                )
                logger.warning(
                    f"Proceeding with risky timeframe {config.interval} "
                    f"after user acknowledgment"
                )
        
        # Log recommended timeframes for reference
        if config.is_scalping or config.is_high_frequency:
            logger.info(
                "Consider using recommended timeframes: "
                + str(TimeframeValidator.get_recommended_timeframes())
            )
        
        # Record start event
        await EventStore.record_event(
            backtest_id,
            'backtest.started',
            config.dict()
        )
        
        try:
            # Fetch historical data
            data = await self._fetch_historical_data(
                config.symbols[0],  # Single symbol for now
                config.start_date,
                config.end_date
            )
            
            # Validate data
            is_valid, errors = DataValidator.validate_ohlcv(data, config.symbols[0])
            if not is_valid:
                raise ValueError(f"Data validation failed: {errors}")
            
            # Create or resume context
            if resume:
                context = await ContextManager.load_checkpoint(backtest_id)
                if context:
                    logger.info(f"Resuming backtest from bar {context.processed_bars}")
                else:
                    context = ContextManager.create_context(
                        backtest_id,
                        config.dict(),
                        len(data)
                    )
            else:
                context = ContextManager.create_context(
                    backtest_id,
                    config.dict(),
                    len(data)
                )
            
            # Execute based on engine choice
            if config.engine == "vectorbt":
                result = await self._run_vectorbt(data, config)
                validation_status = "not_validated"
            
            elif config.engine == "backtrader":
                result = await self._run_backtrader(data, config)
                validation_status = "not_validated"
            
            elif config.engine == "both":
                # Run both engines and cross-validate
                vbt_result = await self._run_vectorbt(data, config)
                bt_result = await self._run_backtrader(data, config)
                
                # Cross-validate results
                validation_status, validation_notes = self._cross_validate_results(
                    vbt_result,
                    bt_result
                )
                
                # Use vectorbt results (faster and more detailed)
                result = vbt_result
                result['validation_status'] = validation_status
                result['validation_notes'] = validation_notes
            
            # Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Create result object
            backtest_result = BacktestResult(
                backtest_id=backtest_id,
                config=config,
                performance=PerformanceMetrics(**result['performance']),
                trades=[Trade(**t) for t in result.get('trades', [])],
                equity_curve=result.get('equity_curve', []),
                executed_at=datetime.now(),
                execution_time_ms=execution_time_ms,
                engine_used=result.get('engine', config.engine),
                validation_status=result.get('validation_status'),
                validation_notes=result.get('validation_notes')
            )
            
            # Record completion event
            await EventStore.record_event(
                backtest_id,
                'backtest.completed',
                {
                    'total_return': float(backtest_result.performance.total_return),
                    'total_trades': backtest_result.performance.total_trades,
                    'execution_time_ms': execution_time_ms
                }
            )
            
            # Clean up checkpoint
            await ContextManager.delete_checkpoint(backtest_id)
            
            return backtest_result
        
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            await EventStore.record_event(
                backtest_id,
                'backtest.failed',
                {'error': str(e)}
            )
            raise
    
    async def _fetch_historical_data(
        self,
        symbol: str,
        start_date,
        end_date,
        interval: str = "1h"
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data from market data service"""
        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for large datasets
            response = await client.get(
                f"{self.market_data_url}/api/v1/historical/{symbol}",
                params={
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'interval': interval
                }
            )
            
            if response.status_code != 200:
                raise ValueError(
                    f"Failed to fetch historical data: {response.text}"
                )
            
            data_list = response.json()
            
            # Convert to DataFrame
            df = pd.DataFrame(data_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Rename columns to match expected format
            df.rename(columns={
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume'
            }, inplace=True)
            
            return df
    
    async def _run_vectorbt(
        self,
        data: pd.DataFrame,
        config: BacktestConfig
    ) -> Dict:
        """Run vectorbt engine"""
        return await self.vectorbt_engine.run_backtest(
            data,
            config.strategy.dict(),
            float(config.initial_capital),
            float(config.commission),
            float(config.slippage)
        )
    
    async def _run_backtrader(
        self,
        data: pd.DataFrame,
        config: BacktestConfig
    ) -> Dict:
        """Run backtrader engine"""
        return await self.backtrader_engine.run_backtest(
            data,
            config.strategy.dict(),
            float(config.initial_capital),
            float(config.commission),
            float(config.slippage)
        )
    
    def _cross_validate_results(
        self,
        vbt_result: Dict,
        bt_result: Dict,
        tolerance: float = 0.10  # 10% tolerance
    ) -> tuple[str, str]:
        """
        Cross-validate results from both engines
        Returns (status, notes)
        """
        vbt_perf = vbt_result['performance']
        bt_perf = bt_result['performance']
        
        discrepancies = []
        
        # Compare total return
        return_diff = abs(
            vbt_perf['total_return'] - bt_perf['total_return']
        ) / abs(bt_perf['total_return']) if bt_perf['total_return'] != 0 else 0
        
        if return_diff > tolerance:
            discrepancies.append(
                f"Total return mismatch: vectorbt={vbt_perf['total_return']:.2f}%, "
                f"backtrader={bt_perf['total_return']:.2f}% "
                f"(diff={return_diff*100:.1f}%)"
            )
        
        # Compare total trades
        trade_diff = abs(vbt_perf['total_trades'] - bt_perf['total_trades'])
        if trade_diff > 5:  # Allow 5 trade difference
            discrepancies.append(
                f"Trade count mismatch: vectorbt={vbt_perf['total_trades']}, "
                f"backtrader={bt_perf['total_trades']}"
            )
        
        if discrepancies:
            status = "failed"
            notes = "Cross-validation failed: " + "; ".join(discrepancies)
            logger.warning(notes)
        else:
            status = "passed"
            notes = "Both engines produced consistent results"
            logger.info(notes)
        
        return status, notes
