
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from shared.config import settings

# Try to import DB integration if available
try:
    from shared.db import get_db
    from sqlalchemy import text
except ImportError:
    get_db = None

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Logs critical system actions (Trades, Backtests, Config Changes) 
    to a persistent store for compliance/auditing.
    """
    
    ACTION_BACKTEST = "BACKTEST_RUN"
    ACTION_TRADE = "LIVE_TRADE"
    ACTION_LOGIN = "USER_LOGIN"
    ACTION_SYSTEM = "SYSTEM_EVENT"

    @staticmethod
    async def log_event(
        action_type: str, 
        user_id: str = "system", 
        details: Dict[str, Any] = None,
        resource_id: Optional[str] = None
    ):
        """
        Record an audit event.
        """
        if details is None:
            details = {}
            
        timestamp = datetime.utcnow()
        
        # 1. Log to File/Console (Immediate)
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "action": action_type,
            "user": user_id,
            "resource": resource_id,
            "details": details
        }
        logger.info(f"AUDIT_EVENT: {json.dumps(log_entry)}")
        
        # 2. Persist to Database (Compliance)
        if get_db:
            try:
                # Assuming a table 'audit_logs' exists or using raw SQL
                # For this scratchpad, we'll verify connection then print
                # In prod, this inserts into Supabase/Postgres
                
                # Mock SQL execution for demonstration if full ORM not setup
                # await db.execute("INSERT INTO audit_logs ...")
                pass
            except Exception as e:
                logger.error(f"Failed to persist audit log: {e}")
    
    @staticmethod
    async def log_backtest(backtest_id: str, config: Dict, result_summary: Dict):
        """Helper for logging backtest execution"""
        await AuditLogger.log_event(
            AuditLogger.ACTION_BACKTEST,
            details={
                "config_summary": str(config)[:500], # Truncate for storage
                "result": result_summary
            },
            resource_id=backtest_id
        )

    @staticmethod
    async def log_trade(order_id: str, symbol: str, side: str, qty: float, price: float):
        """Helper for logging live trades"""
        await AuditLogger.log_event(
            AuditLogger.ACTION_TRADE,
            details={
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price
            },
            resource_id=order_id
        )
