"""
Orderflow MCP Server

Exposes orderflow analysis tools via Model Context Protocol for AI agents.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
import sys

logger = logging.getLogger(__name__)


class OrderflowMCPServer:
    """
    MCP Server exposing orderflow analysis capabilities to AI agents.
    
    Tools:
    - connect_l2_stream: Connect to L2 data provider
    - get_orderbook_state: Get current orderbook snapshot
    - analyze_footprint: Run footprint detection algorithms
    - validate_signal: Validate signal through confirmation mesh
    - estimate_slippage: Estimate execution slippage
    """
    
    def __init__(self):
        from .orderbook_manager import orderbook_manager
        from .footprint_engine import footprint_engine
        from .confirmation_mesh import confirmation_mesh
        from .l2_provider import AlpacaL2Provider, PolygonL2Provider
        
        self.orderbook_manager = orderbook_manager
        self.footprint_engine = footprint_engine
        self.confirmation_mesh = confirmation_mesh
        
        self._providers = {}
        self._connected = False
    
    def get_tools(self) -> list:
        """Return list of available MCP tools"""
        return [
            {
                "name": "connect_l2_stream",
                "description": "Connect to L2 data provider for orderbook streaming",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["alpaca", "polygon"],
                            "description": "L2 data provider to connect to"
                        },
                        "api_key": {
                            "type": "string",
                            "description": "API key for the provider"
                        }
                    },
                    "required": ["provider", "api_key"]
                }
            },
            {
                "name": "subscribe_symbol",
                "description": "Subscribe to L2 updates for a trading symbol",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading symbol (e.g., AAPL, RELIANCE)"
                        },
                        "provider": {
                            "type": "string",
                            "default": "alpaca"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_orderbook_state",
                "description": "Get current orderbook snapshot with bid/ask levels",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading symbol"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "analyze_footprint",
                "description": "Run footprint detection algorithms to find institutional patterns",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Trading symbol"
                        },
                        "window_seconds": {
                            "type": "integer",
                            "default": 60,
                            "description": "Analysis window in seconds"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "validate_signal",
                "description": "Validate trading signal through confirmation mesh before execution",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "side": {"type": "string", "enum": ["buy", "sell"]},
                        "quantity": {"type": "number"},
                        "signal_type": {
                            "type": "string",
                            "enum": ["absorption", "exhaustion", "imbalance", "sweep"]
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "default": "medium"
                        },
                        "max_slippage_pct": {
                            "type": "number",
                            "default": 0.5
                        }
                    },
                    "required": ["symbol", "side", "quantity", "signal_type"]
                }
            },
            {
                "name": "estimate_slippage",
                "description": "Estimate execution slippage based on current orderbook",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "side": {"type": "string", "enum": ["buy", "sell"]},
                        "quantity": {"type": "number"}
                    },
                    "required": ["symbol", "side", "quantity"]
                }
            },
            {
                "name": "get_confirmation_metrics",
                "description": "Get metrics from confirmation mesh (approvals, rejections, reasons)",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "trip_circuit_breaker",
                "description": "Trip circuit breaker for a symbol to halt trading",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "reason": {"type": "string", "default": "Manual trip"}
                    },
                    "required": ["symbol"]
                }
            }
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Execute an MCP tool call"""
        try:
            if tool_name == "connect_l2_stream":
                return await self._connect_l2(arguments)
            elif tool_name == "subscribe_symbol":
                return await self._subscribe(arguments)
            elif tool_name == "get_orderbook_state":
                return self._get_orderbook(arguments)
            elif tool_name == "analyze_footprint":
                return await self._analyze(arguments)
            elif tool_name == "validate_signal":
                return await self._validate(arguments)
            elif tool_name == "estimate_slippage":
                return self._estimate_slippage(arguments)
            elif tool_name == "get_confirmation_metrics":
                return self.confirmation_mesh.get_metrics()
            elif tool_name == "trip_circuit_breaker":
                return self._trip_breaker(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool error: {e}")
            return {"error": str(e)}
    
    async def _connect_l2(self, args: Dict) -> Dict:
        """Connect to L2 provider"""
        from .l2_provider import AlpacaL2Provider, PolygonL2Provider
        import os
        
        provider_name = args["provider"]
        api_key = args.get("api_key", os.getenv(f"{provider_name.upper()}_API_KEY"))
        
        if provider_name == "alpaca":
            provider = AlpacaL2Provider(
                api_key=api_key,
                api_secret=os.getenv("ALPACA_API_SECRET", "")
            )
        elif provider_name == "polygon":
            provider = PolygonL2Provider(api_key=api_key)
        else:
            return {"error": f"Unknown provider: {provider_name}"}
        
        connected = await provider.connect()
        if connected:
            self._providers[provider_name] = provider
            provider.on_orderbook(self.orderbook_manager.update_snapshot)
            provider.on_trade(self.footprint_engine.process_trade)
            return {"status": "connected", "provider": provider_name}
        return {"status": "failed", "provider": provider_name}
    
    async def _subscribe(self, args: Dict) -> Dict:
        """Subscribe to symbol"""
        symbol = args["symbol"]
        provider_name = args.get("provider", "alpaca")
        
        provider = self._providers.get(provider_name)
        if not provider:
            return {"error": f"Provider {provider_name} not connected"}
        
        success = await provider.subscribe(symbol)
        return {"subscribed": success, "symbol": symbol}
    
    def _get_orderbook(self, args: Dict) -> Dict:
        """Get orderbook state"""
        symbol = args["symbol"]
        book = self.orderbook_manager.get_orderbook(symbol)
        
        if not book:
            return {"error": f"No orderbook for {symbol}"}
        
        return {
            "symbol": symbol,
            "best_bid": book.best_bid,
            "best_ask": book.best_ask,
            "spread": book.spread,
            "bid_depth": book.total_bid_size(5),
            "ask_depth": book.total_ask_size(5),
            "imbalance_ratio": book.imbalance_ratio(5)
        }
    
    async def _analyze(self, args: Dict) -> Dict:
        """Analyze footprint"""
        symbol = args["symbol"]
        cluster = await self.footprint_engine.flush_buffer(symbol)
        
        if not cluster:
            return {"symbol": symbol, "signals": [], "message": "No data"}
        
        return {
            "symbol": symbol,
            "total_delta": cluster.total_delta,
            "buy_volume": cluster.total_buy_volume,
            "sell_volume": cluster.total_sell_volume,
            "poc": cluster.poc,
            "imbalance_count": len(cluster.imbalances())
        }
    
    async def _validate(self, args: Dict) -> Dict:
        """Validate through confirmation mesh"""
        from .l2_models import FootprintSignal, ConfirmationRequest, Side, SignalType, SignalConfidence
        
        signal = FootprintSignal(
            symbol=args["symbol"],
            signal_type=SignalType(args["signal_type"]),
            direction=Side(args["side"]),
            confidence=SignalConfidence(args.get("confidence", "medium")),
            price_level=0,
            delta=0,
            price_movement=0
        )
        
        request = ConfirmationRequest(
            signal=signal,
            symbol=args["symbol"],
            side=Side(args["side"]),
            quantity=args["quantity"],
            max_slippage_pct=args.get("max_slippage_pct", 0.5)
        )
        
        result = await self.confirmation_mesh.validate(request)
        return {
            "approved": result.approved,
            "rejection_reason": result.rejection_reason,
            "liquidity_check": result.liquidity_check,
            "footprint_confirmed": result.footprint_confirmed,
            "risk_check": result.risk_check
        }
    
    def _estimate_slippage(self, args: Dict) -> Dict:
        """Estimate slippage"""
        from .l2_models import Side
        
        result = self.orderbook_manager.estimate_slippage(
            args["symbol"],
            Side(args["side"]),
            args["quantity"]
        )
        
        if result is None:
            return {"error": "Insufficient liquidity data"}
        
        return {
            "avg_price": result[0],
            "slippage_pct": result[1]
        }
    
    def _trip_breaker(self, args: Dict) -> Dict:
        """Trip circuit breaker"""
        self.confirmation_mesh.trip_circuit_breaker(
            args["symbol"],
            args.get("reason", "Manual trip")
        )
        return {"tripped": True, "symbol": args["symbol"]}


def main():
    """Run MCP server in stdio mode"""
    import asyncio
    
    server = OrderflowMCPServer()
    
    # Simple stdio MCP protocol handler
    async def handle_stdio():
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            line = await reader.readline()
            if not line:
                break
            
            try:
                request = json.loads(line.decode())
                
                if request.get("method") == "tools/list":
                    response = {"tools": server.get_tools()}
                elif request.get("method") == "tools/call":
                    params = request.get("params", {})
                    result = await server.call_tool(
                        params.get("name"),
                        params.get("arguments", {})
                    )
                    response = {"content": [{"type": "text", "text": json.dumps(result)}]}
                else:
                    response = {"error": "Unknown method"}
                
                print(json.dumps(response), flush=True)
            except Exception as e:
                print(json.dumps({"error": str(e)}), flush=True)
    
    asyncio.run(handle_stdio())


if __name__ == "__main__":
    main()
