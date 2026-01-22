
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import asyncio

# Assume running from project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.services.broker.adapter import OrderRequest
# Import UpstoxAdapter inside test to avoid early import errors if deps missing
# from backend.services.broker.upstox_adapter import UpstoxAdapter 

class TestUpstoxOrders(unittest.TestCase):

    def setUp(self):
        # Patch configuration settings if needed
        pass

    @patch('backend.services.broker.upstox_adapter.OrderApi')
    @patch('backend.services.broker.upstox_adapter.ApiClient')
    @patch('backend.services.broker.upstox_adapter.Configuration')
    @patch('backend.services.broker.upstox_adapter.UserApi') # For connect
    def test_place_order_mis_mapping(self, mock_user_api, mock_config, mock_client, mock_order_api):
        from backend.services.broker.upstox_adapter import UpstoxAdapter
        
        # Setup Mocks
        adapter = UpstoxAdapter("key", "secret", "uri", "token")
        adapter.connected = True # Force connected state
        
        # Mock PlaceOrder return
        mock_response = MagicMock()
        mock_response.data.order_id = "12345"
        adapter.order_api.place_order.return_value = mock_response

        # Test Case 1: MIS -> I
        req = OrderRequest(
            symbol="RELIANCE",
            quantity=10,
            side="BUY",
            order_type="MARKET",
            product="MIS"
        )
        
        response = asyncio.run(adapter.place_order(req))
        
        # Verify
        self.assertEqual(response.status, "SUBMITTED")
        self.assertEqual(response.order_id, "12345")
        
        # Check arguments passed to upstox sdk
        # args[0] is the PlaceOrderRequest object
        call_args = adapter.order_api.place_order.call_args
        sent_request = call_args[0][0] 
        
        self.assertEqual(sent_request.product, "I") # MIS should be I
        print("SUCCESS: MIS mapped to I")

    @patch('backend.services.broker.upstox_adapter.OrderApi')
    @patch('backend.services.broker.upstox_adapter.ApiClient')
    @patch('backend.services.broker.upstox_adapter.Configuration')
    def test_place_order_cnc_mapping(self, mock_config, mock_client, mock_order_api):
        from backend.services.broker.upstox_adapter import UpstoxAdapter
        
        adapter = UpstoxAdapter("key", "secret", "uri", "token")
        adapter.connected = True
        
        mock_response = MagicMock()
        mock_response.data.order_id = "67890"
        adapter.order_api.place_order.return_value = mock_response

        # Test Case 2: CNC -> D
        req = OrderRequest(
            symbol="TCS",
            quantity=5,
            side="SELL",
            product="CNC"
        )
        asyncio.run(adapter.place_order(req))
        
        call_args = adapter.order_api.place_order.call_args
        sent_request = call_args[0][0] 
        self.assertEqual(sent_request.product, "D") # CNC should be D
        print("SUCCESS: CNC mapped to D")

if __name__ == '__main__':
    unittest.main()
