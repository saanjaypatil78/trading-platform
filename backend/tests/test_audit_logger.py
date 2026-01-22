
import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Assume running from project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Set dummy env vars to satisfy pydantic
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_secret")

from backend.services.reporting.audit_logger import AuditLogger

class TestAuditLogger(unittest.TestCase):
    
    def test_log_event(self):
        """Verify log event structure and execution"""
        
        # We need to run async method in sync test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        with patch('backend.services.reporting.audit_logger.logger') as mock_logger:
            loop.run_until_complete(
                AuditLogger.log_event(
                    AuditLogger.ACTION_BACKTEST,
                    user_id="test_user",
                    details={"strategy": "RSI"},
                    resource_id="bt_123"
                )
            )
            
            # Verify logger.info was called with correct JSON structure
            self.assertTrue(mock_logger.info.called)
            args, _ = mock_logger.info.call_args
            log_message = args[0]
            
            self.assertIn("AUDIT_EVENT", log_message)
            self.assertIn("BACKTEST_RUN", log_message)
            self.assertIn("test_user", log_message)
            print(f"SUCCESS: Audit Logged: {log_message}")

    def test_log_trade_helper(self):
        """Verify specific helper method"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        with patch('backend.services.reporting.audit_logger.logger') as mock_logger:
            loop.run_until_complete( AuditLogger.log_trade("ord_1", "AAPL", "BUY", 10, 150.0) )
            self.assertTrue(mock_logger.info.called)

if __name__ == '__main__':
    unittest.main()
