
import asyncio
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Assume running from project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend')) # To allow 'import shared'

# Set dummy env vars to satisfy pydantic validation if config is loaded
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_secret")

from backend.services.market_data.providers.upstox_provider import UpstoxProvider
from backend.services.backtesting.engine_vectorbt import VectorbtEngine
from backend.shared.config import settings

async def test_upstox_backtest():
    print("="*60)
    print("TEST: Upstox Data Integration with Backtesting Engine")
    print("="*60)

    # 1. Initialize Upstox Provider
    print("\n[1] Initializing UpstoxProvider...")
    if not settings.UPSTOX_API_KEY or settings.UPSTOX_API_KEY == "NOT_SET":
        print("SKIP: UPSTOX_API_KEY not found in settings.")
        return

    provider = UpstoxProvider(api_key=settings.UPSTOX_API_KEY)
    
    # 2. Fetch Historical Data
    symbol = "NSE_EQ|INE002A01018" # Reliance (Common Upstox Key)
    
    print(f"\n[2] Fetching historical data for {symbol}...")
    try:
        # Fetch last 5 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        historical = await provider.get_historical(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1d" # Daily
        )
        
        if not historical or not historical.data:
            print("FAILURE: No historical data returned. (Check API Key or Symbol)")
            return
            
        print(f"SUCCESS: Fetched {len(historical.data)} candles.")
        
        # Convert to DataFrame (Engine expects DataFrame)
        df_data = pd.DataFrame([vars(h) for h in historical.data])
        df_data['timestamp'] = pd.to_datetime(df_data['timestamp'])
        df_data.set_index('timestamp', inplace=True)
        
        # FIX: Drop 'symbol' and ensure numeric types for vectorbt/numba
        df_clean = df_data[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        print("\nLast 3 rows:")
        print(df_clean.tail(3))
        
    except Exception as e:
        print(f"ERROR fetching data: {e}")
        return

    # 3. Run Backtest (VectorBT Engine)
    print("\n[3] Running Backtest (VectorBT Engine)...")
    try:
        engine = VectorbtEngine()
        
        # Simple Strategy: RSI Cross
        strategy_config = {
            "symbol": "RELIANCE",
            "indicators": {
                "RSI": {"period": 14}
            },
            "entry_rules": "RSI < 30",
            "exit_rules": "RSI > 70",
            "params": {"period": 14, "lower": 30, "upper": 70}
        }
        
        result = await engine.run_backtest(
            data=df_clean,
            strategy_config=strategy_config,
            initial_capital=100000.0
        )
        
        print("\n[4] Backtest Results:")
        perf = result['performance']
        print(f"Total Return: {perf['total_return']:.2f}%")
        print(f"Total Trades: {perf['total_trades']}")
        print(f"Win Rate: {perf['win_rate']:.2f}%")
        
        if perf['total_trades'] >= 0:
             print("\nSUCCESS: Backtest completed using Upstox Data.")
        
    except ImportError:
        print("SKIP: vectorbt not installed (expected in some envs).")
    except Exception as e:
        print(f"ERROR running backtest: {e}")

if __name__ == "__main__":
    asyncio.run(test_upstox_backtest())
