"""
Test for AlpacaAdapter
Verifies the integration with the alpaca-py SDK using mocks.
"""
import unittest
from unittest.mock import MagicMock, patch
from backend.services.broker.alpaca_adapter import AlpacaAdapter
from backend.services.broker.adapter import OrderSide, OrderType, OrderStatus

class TestAlpacaAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = AlpacaAdapter()
        self.creds = {"key_id": "test_key", "secret_key": "test_secret", "paper": True}

    @patch("backend.services.broker.alpaca_adapter.TradingClient")
    def test_connect(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        success = self.adapter.connect(self.creds)
        
        self.assertTrue(success)
        mock_client_class.assert_called_once_with(api_key="test_key", secret_key="test_secret", paper=True)
        mock_client.get_account.assert_called_once()

    @patch("backend.services.broker.alpaca_adapter.TradingClient")
    def test_place_order(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        self.adapter.connect(self.creds)
        
        from datetime import datetime
        now = datetime.now()
        
        # Mock alpaca order response
        mock_alp_order = MagicMock()
        mock_alp_order.id = "order-123"
        mock_alp_order.symbol = "AAPL"
        mock_alp_order.side = "buy"
        mock_alp_order.status = "new"
        mock_alp_order.qty = 10
        mock_alp_order.limit_price = 150.0
        mock_alp_order.filled_qty = 0
        mock_alp_order.filled_avg_price = None
        mock_alp_order.created_at = now
        mock_alp_order.updated_at = now
        
        mock_client.submit_order.return_value = mock_alp_order
        
        order = self.adapter.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=150.0
        )
        
        self.assertEqual(order.order_id, "order-123")
        self.assertEqual(order.symbol, "AAPL")
        self.assertEqual(order.status, OrderStatus.OPEN)
        mock_client.submit_order.assert_called_once()

if __name__ == "__main__":
    unittest.main()
