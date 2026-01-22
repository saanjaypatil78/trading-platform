
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from datetime import datetime

# 1. Mock External Deps
sys.modules['redis'] = MagicMock()
sys.modules['redis.asyncio'] = MagicMock()
sys.modules['vectorbt'] = MagicMock()
sys.modules['backtrader'] = MagicMock()
sys.modules['backtrader.feeds'] = MagicMock()
sys.modules['backtrader.indicators'] = MagicMock()
sys.modules['backtrader.analyzers'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['pydantic'] = MagicMock()
sys.modules['pydantic_settings'] = MagicMock()

# 2. Mock Internal Shared Deps (absolute paths)
sys.modules['shared'] = MagicMock()
sys.modules['shared.config'] = MagicMock()
sys.modules['shared.config'].settings.API_PORT = 8000
sys.modules['shared.models'] = MagicMock()
sys.modules['shared.database'] = MagicMock()
sys.modules['shared.cache'] = MagicMock()

# 3. Mock Sibling Modules (relative imports will resolve to these if mapped correctly)
# We need to ensure that when backtest_service does "from .models import ...", 
# it finds these mocks.
# Since we are importing BacktestService from "backend.services.backtesting.backtest_service",
# relative imports look for "backend.services.backtesting.models".

# Mock Models
mock_models = MagicMock()
# Define simple stub classes for Models to hold data
class StubConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def dict(self): return self.__dict__
    @property
    def is_scalping(self): return False
    @property
    def is_high_frequency(self): return False

class StubResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class StubTrade:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class StubMetrics:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if 'total_return' not in kwargs: self.total_return = 0.0
        if 'total_trades' not in kwargs: self.total_trades = 0

mock_models.BacktestConfig = StubConfig
mock_models.BacktestResult = StubResult
mock_models.Trade = StubTrade
mock_models.PerformanceMetrics = StubMetrics
# Also need to mock BacktestStrategy if it's imported? No, it's inside Config usually.
# But checking backtest_service.py, it imports BacktestConfig, BacktestResult, PerformanceMetrics, Trade
sys.modules['backend.services.backtesting.models'] = mock_models

# Mock Validators
mock_validators = MagicMock()
mock_validators.DataValidator.validate_ohlcv.return_value = (True, [])
sys.modules['backend.services.backtesting.validators'] = mock_validators

# Mock TimeframeValidator
mock_tf_validator = MagicMock()
mock_tf_validator.TimeframeValidator.validate_timeframe.return_value = (True, None)
mock_tf_validator.RiskAcknowledgment.record_acknowledgment = AsyncMock()
sys.modules['backend.services.backtesting.timeframe_validator'] = mock_tf_validator

# Mock ContextManager
mock_ctx = MagicMock()
mock_ctx.ContextManager.create_context.return_value = MagicMock()
mock_ctx.ContextManager.load_checkpoint = AsyncMock(return_value=None)
mock_ctx.ContextManager.delete_checkpoint = AsyncMock()
mock_ctx.EventStore.record_event = AsyncMock()
sys.modules['backend.services.backtesting.context_manager'] = mock_ctx

# Mock Engines (to avoid importing them and their deps)
# But backtest_service imports classes VectorbtEngine, BacktraderEngine
mock_vbt_engine_mod = MagicMock()
mock_vbt_engine_mod.VectorbtEngine = MagicMock
sys.modules['backend.services.backtesting.engine_vectorbt'] = mock_vbt_engine_mod

mock_bt_engine_mod = MagicMock()
mock_bt_engine_mod.BacktraderEngine = MagicMock
sys.modules['backend.services.backtesting.engine_backtrader'] = mock_bt_engine_mod

# Adjust path to find backend package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
sys.path.insert(0, project_root)

# Now import the service under test
from backend.services.backtesting.backtest_service import BacktestService

import pytest

# Fixtures
@pytest.fixture
def mock_config():
    # Create config using the Stub class
    return StubConfig(
        symbols=["RELIANCE"],
        strategy=MagicMock(),
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 4, 1),
        initial_capital=100000.0,
        interval="1d",
        engine="vectorbt",
        commission=0.001,
        slippage=0.0005
    )

@pytest.fixture
def backtest_service():
    service = BacktestService()
    # Instantiate mock engines
    service.vectorbt_engine = AsyncMock()
    service.backtrader_engine = AsyncMock()
    return service

# Tests
@pytest.mark.asyncio
async def test_execute_backtest_vectorbt_flow(backtest_service, mock_config):
    # Mock _fetch_historical_data
    mock_data = pd.DataFrame({'close': [100, 101, 102]})
    
    with patch.object(backtest_service, '_fetch_historical_data', return_value=mock_data) as mock_fetch:
        # Mock engine result
        mock_result = {
            'performance': {
                'total_return': 10.5,
                'sharpe_ratio': 1.2,
                'max_drawdown': 5.0,
                'win_rate': 60.0,
                'total_trades': 10,
                'profit_factor': 1.5
            },
            'trades': [],
            'equity_curve': [],
            'engine': 'vectorbt',
            'validation_status': 'not_validated'
        }
        backtest_service.vectorbt_engine.run_backtest.return_value = mock_result
        
        # Execute
        result = await backtest_service.execute_backtest(mock_config)
        
        # Verify
        assert result.performance.total_return == 10.5
        mock_fetch.assert_called_once()
        backtest_service.vectorbt_engine.run_backtest.assert_called_once()

@pytest.mark.asyncio
async def test_execute_backtest_validation_failure(backtest_service, mock_config):
    mock_data = pd.DataFrame() # empty
    with patch.object(backtest_service, '_fetch_historical_data', return_value=mock_data):
        # Mock validator failure
        mock_validators.DataValidator.validate_ohlcv.return_value = (False, "Bad data")
        
        with pytest.raises(ValueError) as excinfo:
            await backtest_service.execute_backtest(mock_config)
        
        assert "Data validation failed" in str(excinfo.value)
        # Reset mock for other tests
        mock_validators.DataValidator.validate_ohlcv.return_value = (True, [])

