
import pytest
import httpx
import respx
from httpx import Response
import pandas as pd
from datetime import datetime
import asyncio
import json
from decimal import Decimal
import sys
import os

# 1. SETUP PATHS
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
backend_dir = os.path.join(project_root, 'backend')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 2. MOCK EXTERNAL DEPENDENCIES
from unittest.mock import MagicMock, AsyncMock
if 'vectorbt' not in sys.modules: sys.modules['vectorbt'] = MagicMock()
if 'backtrader' not in sys.modules: sys.modules['backtrader'] = MagicMock()
if 'redis' not in sys.modules: sys.modules['redis'] = MagicMock()

# 3. MOCK SHARED MODULES
mock_shared = MagicMock()
mock_shared.__path__ = []
sys.modules['shared'] = mock_shared
sys.modules['shared.config'] = MagicMock()
sys.modules['shared.config'].settings.API_PORT = 8000
sys.modules['shared.models'] = MagicMock()
sys.modules['shared.database'] = MagicMock()
sys.modules['shared.cache'] = MagicMock()

# 4. MOCK INTERNAL DEPENDENCIES
sys.modules['backend.services.backtesting.context_manager'] = MagicMock()
sys.modules['backend.services.backtesting.context_manager'].ContextManager.create_context.return_value = MagicMock()
sys.modules['backend.services.backtesting.timeframe_validator'] = MagicMock()
sys.modules['backend.services.backtesting.timeframe_validator'].TimeframeValidator.validate_timeframe.return_value = (True, None)

# Mock Pydantic
mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MagicMock
sys.modules['pydantic'] = mock_pydantic
mock_pydantic_settings = MagicMock()
mock_pydantic_settings.BaseSettings = MagicMock
sys.modules['pydantic_settings'] = mock_pydantic_settings

# 5. STUB MODELS
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

sys.modules['backend.services.backtesting.models'] = MagicMock()
sys.modules['backend.services.backtesting.models'].BacktestConfig = StubConfig
sys.modules['backend.services.backtesting.models'].BacktestResult = StubResult
sys.modules['backend.services.backtesting.models'].Trade = StubTrade
sys.modules['backend.services.backtesting.models'].PerformanceMetrics = StubMetrics

# 6. IMPORT SERVICE UNDER TEST
from backend.services.backtesting.backtest_service import BacktestService

# CONFIG
USE_MOCK_SERVICES = True
MARKET_DATA_URL = "http://market-data-service:8000"

@pytest.fixture
def backtest_config():
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

@pytest.mark.asyncio
async def test_backtest_service_integration_flow(backtest_config):
    """
    Integration Test: BacktestService -> MarketDataService
    """
    # Setup Service
    service = BacktestService()
    
    # Mock Data Response
    mock_ohlcv = []
    base_price = 100.0
    for i in range(100):
        # We need to construct the datetime properly
        dt = datetime(2023, 1, 1)
        # Manually add days (simple approach to avoid timedelta import issues if any)
        # actually imports are fine
        from datetime import timedelta
        dt = dt + timedelta(days=i)
            
        mock_ohlcv.append({
            'timestamp': dt.isoformat(),
            'o': base_price,
            'h': base_price + 5,
            'l': base_price - 5,
            'c': base_price + 1,
            'v': 1000
        })
    
    # Use respx to mock HTTP calls
    with respx.mock(assert_all_called=False) as respx_mock:
        if USE_MOCK_SERVICES:
            # Setup Route Mock
            dataset_route = respx_mock.get(
                url__regex=r"http://market-data-service:8000/api/v1/historical/RELIANCE.*"
            ).mock(return_value=Response(200, json=mock_ohlcv))
            
            # Setup Engine Mock
            service.vectorbt_engine.run_backtest = AsyncMock(return_value={
                'performance': {
                    'total_return': 10.0,
                    'sharpe_ratio': 1.0, 
                    'max_drawdown': 5.0, 
                    'win_rate': 60.0, 
                    'total_trades': 10, 
                    'profit_factor': 1.5
                },
                'trades': [],
                'equity_curve': [],
                'engine': 'vectorbt'
            })
            
        else:
            respx_mock.route(url__regex=r".*").pass_through()

        # EXECUTE
        print(f"\n[Integration] Executing backtest with Mock Services = {USE_MOCK_SERVICES}")
        try:
            result = await service.execute_backtest(backtest_config)
            
            # VERIFY
            print("[Integration] Backtest completed successfully")
            assert result is not None
            assert result.performance.total_return is not None
            
            if USE_MOCK_SERVICES:
                assert dataset_route.called
                print("[Integration] Verified Market Data API was called correctly")
                
        except Exception as e:
            if not USE_MOCK_SERVICES:
                pytest.fail(f"Integration test failed against real services: {e}")
            else:
                raise e

if __name__ == "__main__":
    asyncio.run(test_backtest_service_integration_flow(
        StubConfig(
            symbols=["RELIANCE"],
            strategy=MagicMock(),
            start_date=datetime(2023,1,1),
            end_date=datetime(2023,1,5),
            initial_capital=100000,
            interval="1d",
            engine="vectorbt",
            commission=0.001,
            slippage=0.0005
        )
    ))
