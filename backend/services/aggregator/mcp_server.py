"""
Signal Aggregator MCP Server

Exposes aggregation tools for AI agents via Model Context Protocol.
"""

import json
import asyncio
from typing import Any, Dict

from .main import SignalAggregator, SignalRequest, MultiSymbolRequest


class AggregatorMCPServer:
    """MCP Server for signal aggregation"""
    
    def __init__(self):
        self.aggregator = SignalAggregator()
        self.tools = {
            "get_unified_signal": self._get_unified_signal,
            "get_batch_signals": self._get_batch_signals,
            "execute_signal": self._execute_signal,
        }
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Handle incoming tool calls"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = await self.tools[tool_name](arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_unified_signal(self, args: Dict) -> Dict:
        """
        Get unified signal for a symbol.
        
        Args:
            symbol: Stock symbol
            include_orderflow: Include L2/footprint data (default: true)
            include_scanner: Include technical indicators (default: true)
            include_brain: Include AI analysis (default: true)
            account_size: Optional account size for position sizing
        """
        request = SignalRequest(
            symbol=args.get("symbol", "AAPL"),
            include_orderflow=args.get("include_orderflow", True),
            include_scanner=args.get("include_scanner", True),
            include_brain=args.get("include_brain", True),
            account_size=args.get("account_size")
        )
        
        signal = await self.aggregator.aggregate_signal(request)
        return signal.dict()
    
    async def _get_batch_signals(self, args: Dict) -> Dict:
        """
        Get signals for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            include_orderflow: Include L2 data (default: true)
            include_scanner: Include technicals (default: true)
        """
        request = MultiSymbolRequest(
            symbols=args.get("symbols", []),
            include_orderflow=args.get("include_orderflow", True),
            include_scanner=args.get("include_scanner", True)
        )
        
        tasks = [
            self.aggregator.aggregate_signal(SignalRequest(
                symbol=s,
                include_orderflow=request.include_orderflow,
                include_scanner=request.include_scanner
            ))
            for s in request.symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = []
        for symbol, result in zip(request.symbols, results):
            if hasattr(result, 'dict'):
                signals.append(result.dict())
            else:
                signals.append({"symbol": symbol, "error": str(result)})
        
        return {"signals": signals}
    
    async def _execute_signal(self, args: Dict) -> Dict:
        """
        Get signal and execute if strong.
        
        Args:
            symbol: Stock symbol
            account_size: Account size for position sizing
            force: Execute even if signal is moderate (default: false)
        """
        request = SignalRequest(
            symbol=args.get("symbol", "AAPL"),
            include_orderflow=True,
            include_scanner=True,
            include_brain=True,
            account_size=args.get("account_size")
        )
        
        signal = await self.aggregator.aggregate_signal(request)
        
        # Check if should execute
        if signal.strength.value == "weak" and not args.get("force", False):
            return {
                "executed": False,
                "reason": "Signal too weak",
                "signal": signal.dict()
            }
        
        # Would call broker here
        return {
            "executed": False,
            "reason": "Execution disabled in MCP server - use /execute endpoint",
            "signal": signal.dict()
        }
    
    def get_tool_definitions(self) -> list:
        """Return MCP tool definitions"""
        return [
            {
                "name": "get_unified_signal",
                "description": "Get aggregated trading signal from orderflow, scanner, and AI brain",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol (e.g., AAPL)"},
                        "include_orderflow": {"type": "boolean", "default": True},
                        "include_scanner": {"type": "boolean", "default": True},
                        "include_brain": {"type": "boolean", "default": True},
                        "account_size": {"type": "number", "description": "Account size for position sizing"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_batch_signals",
                "description": "Get signals for multiple symbols at once",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbols": {"type": "array", "items": {"type": "string"}},
                        "include_orderflow": {"type": "boolean", "default": True},
                        "include_scanner": {"type": "boolean", "default": True}
                    },
                    "required": ["symbols"]
                }
            },
            {
                "name": "execute_signal",
                "description": "Analyze signal and potentially execute trade",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "account_size": {"type": "number"},
                        "force": {"type": "boolean", "default": False}
                    },
                    "required": ["symbol"]
                }
            }
        ]


# MCP stdio server runner
async def run_mcp_server():
    """Run MCP server via stdio"""
    import sys
    
    server = AggregatorMCPServer()
    
    print(json.dumps({
        "protocolVersion": "1.0",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "trading-aggregator", "version": "1.0.0"}
    }), flush=True)
    
    for line in sys.stdin:
        try:
            message = json.loads(line.strip())
            
            if message.get("method") == "tools/list":
                response = {
                    "id": message.get("id"),
                    "result": {"tools": server.get_tool_definitions()}
                }
            elif message.get("method") == "tools/call":
                params = message.get("params", {})
                result = asyncio.run(server.handle_tool_call(
                    params.get("name"),
                    params.get("arguments", {})
                ))
                response = {"id": message.get("id"), "result": result}
            else:
                response = {"id": message.get("id"), "error": "Unknown method"}
            
            print(json.dumps(response), flush=True)
            
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    asyncio.run(run_mcp_server())
