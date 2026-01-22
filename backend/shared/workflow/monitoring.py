"""
Latency and Traffic Monitor
Inspired by OpenAlgo's monitoring tools.
Tracks API performance, error rates, and endpoint statistics.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from collections import defaultdict
import time

class RequestLog(BaseModel):
    timestamp: datetime
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    client_ip: str = ""
    user_agent: str = ""
    error_message: Optional[str] = None

class LatencyMonitor:
    """
    Tracks order execution latency and round-trip times.
    """
    
    def __init__(self):
        self.order_latencies: List[Dict[str, Any]] = []
        self.broker_latencies: Dict[str, List[float]] = defaultdict(list)
    
    def record_order_latency(
        self, 
        order_id: str, 
        broker: str, 
        action: str,
        latency_ms: float,
        success: bool = True
    ):
        """Record latency for an order operation."""
        record = {
            "timestamp": datetime.now(),
            "order_id": order_id,
            "broker": broker,
            "action": action,  # place, modify, cancel
            "latency_ms": latency_ms,
            "success": success
        }
        self.order_latencies.append(record)
        self.broker_latencies[broker].append(latency_ms)
        
        # Keep only last 1000 records
        if len(self.order_latencies) > 1000:
            self.order_latencies = self.order_latencies[-1000:]
    
    def get_stats(self, broker: Optional[str] = None) -> Dict[str, Any]:
        """Get latency statistics."""
        if broker:
            latencies = self.broker_latencies.get(broker, [])
        else:
            latencies = [r["latency_ms"] for r in self.order_latencies]
        
        if not latencies:
            return {"count": 0}
        
        sorted_latencies = sorted(latencies)
        
        return {
            "count": len(latencies),
            "avg_ms": sum(latencies) / len(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "p50_ms": sorted_latencies[len(sorted_latencies) // 2],
            "p95_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)],
            "p99_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)]
        }
    
    def get_broker_comparison(self) -> Dict[str, Dict[str, Any]]:
        """Compare latency across all brokers."""
        return {
            broker: self.get_stats(broker)
            for broker in self.broker_latencies.keys()
        }


class TrafficMonitor:
    """
    Tracks API usage, error rates, and endpoint statistics.
    """
    
    def __init__(self):
        self.requests: List[RequestLog] = []
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "errors": 0, "total_latency": 0}
        )
        self.hourly_stats: Dict[str, int] = defaultdict(int)
        self.error_log: List[Dict[str, Any]] = []
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        client_ip: str = "",
        user_agent: str = "",
        error_message: Optional[str] = None
    ):
        """Record an API request."""
        now = datetime.now()
        
        log = RequestLog(
            timestamp=now,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            error_message=error_message
        )
        
        self.requests.append(log)
        
        # Update endpoint stats
        key = f"{method} {endpoint}"
        self.endpoint_stats[key]["count"] += 1
        self.endpoint_stats[key]["total_latency"] += latency_ms
        
        if status_code >= 400:
            self.endpoint_stats[key]["errors"] += 1
            self.error_log.append({
                "timestamp": now.isoformat(),
                "endpoint": key,
                "status": status_code,
                "error": error_message
            })
        
        # Update hourly stats
        hour_key = now.strftime("%Y-%m-%d %H:00")
        self.hourly_stats[hour_key] += 1
        
        # Trim old data
        if len(self.requests) > 10000:
            self.requests = self.requests[-10000:]
        if len(self.error_log) > 500:
            self.error_log = self.error_log[-500:]
    
    def get_overview(self) -> Dict[str, Any]:
        """Get traffic overview."""
        now = datetime.now()
        
        # Last hour stats
        one_hour_ago = now - timedelta(hours=1)
        last_hour = [r for r in self.requests if r.timestamp > one_hour_ago]
        
        # Last 24 hours
        one_day_ago = now - timedelta(hours=24)
        last_day = [r for r in self.requests if r.timestamp > one_day_ago]
        
        return {
            "total_requests": len(self.requests),
            "last_hour": len(last_hour),
            "last_24h": len(last_day),
            "error_count": len(self.error_log),
            "endpoints": len(self.endpoint_stats),
            "avg_latency_ms": sum(r.latency_ms for r in self.requests) / len(self.requests) if self.requests else 0
        }
    
    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Get statistics per endpoint."""
        results = []
        for endpoint, stats in self.endpoint_stats.items():
            avg_latency = stats["total_latency"] / stats["count"] if stats["count"] else 0
            error_rate = (stats["errors"] / stats["count"] * 100) if stats["count"] else 0
            
            results.append({
                "endpoint": endpoint,
                "requests": stats["count"],
                "errors": stats["errors"],
                "error_rate": f"{error_rate:.1f}%",
                "avg_latency_ms": round(avg_latency, 2)
            })
        
        return sorted(results, key=lambda x: x["requests"], reverse=True)
    
    def get_hourly_traffic(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly traffic for the last N hours."""
        now = datetime.now()
        results = []
        
        for i in range(hours):
            hour = now - timedelta(hours=i)
            key = hour.strftime("%Y-%m-%d %H:00")
            results.append({
                "hour": key,
                "requests": self.hourly_stats.get(key, 0)
            })
        
        return list(reversed(results))
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent errors."""
        return self.error_log[-limit:]


class PnLTracker:
    """
    Real-time P&L tracking with historical data.
    """
    
    def __init__(self):
        self.realized_pnl: float = 0
        self.unrealized_pnl: float = 0
        self.trades: List[Dict[str, Any]] = []
        self.daily_pnl: Dict[str, float] = {}
    
    def record_trade(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        pnl: float
    ):
        """Record a completed trade."""
        now = datetime.now()
        
        trade = {
            "timestamp": now.isoformat(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl
        }
        self.trades.append(trade)
        self.realized_pnl += pnl
        
        # Update daily P&L
        day_key = now.strftime("%Y-%m-%d")
        self.daily_pnl[day_key] = self.daily_pnl.get(day_key, 0) + pnl
    
    def update_unrealized(self, positions: List[Dict[str, Any]]):
        """Update unrealized P&L from current positions."""
        self.unrealized_pnl = sum(p.get("pnl", 0) for p in positions)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get P&L summary."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        winning_trades = [t for t in self.trades if t["pnl"] > 0]
        losing_trades = [t for t in self.trades if t["pnl"] < 0]
        
        return {
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_pnl": self.realized_pnl + self.unrealized_pnl,
            "today_pnl": self.daily_pnl.get(today, 0),
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.trades) * 100 if self.trades else 0,
            "avg_win": sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            "avg_loss": sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        }
    
    def get_daily_pnl(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily P&L for charting."""
        return [
            {"date": date, "pnl": pnl}
            for date, pnl in sorted(self.daily_pnl.items())[-days:]
        ]
