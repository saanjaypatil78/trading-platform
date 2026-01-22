"""
Action Center - Order Approval Workflow
Inspired by OpenAlgo's Action Center feature.
Supports Auto and Semi-Auto execution modes.
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import uuid

class ExecutionMode(str, Enum):
    AUTO = "auto"           # Immediate execution
    SEMI_AUTO = "semi-auto" # Manual approval required

class PendingAction(BaseModel):
    action_id: str
    timestamp: datetime
    action_type: str  # "place_order", "modify_order", "cancel_order"
    payload: Dict[str, Any]
    source: str  # "scanner", "webhook", "strategy", "manual"
    status: str = "pending"  # pending, approved, rejected, executed, expired
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

class ActionCenter:
    """
    Manages order execution workflow.
    - Auto Mode: Orders execute immediately
    - Semi-Auto Mode: Orders queue for manual approval
    """
    
    def __init__(self, mode: ExecutionMode = ExecutionMode.AUTO):
        self.mode = mode
        self.pending_actions: Dict[str, PendingAction] = {}
        self.action_history: List[PendingAction] = []
        self.max_pending = 100
        self.auto_expire_minutes = 30
    
    def submit_action(
        self, 
        action_type: str, 
        payload: Dict[str, Any],
        source: str = "manual"
    ) -> Dict[str, Any]:
        """
        Submit an action for execution or approval.
        Returns immediately if AUTO mode, creates pending action if SEMI_AUTO.
        """
        action_id = str(uuid.uuid4())[:8].upper()
        now = datetime.now()
        
        action = PendingAction(
            action_id=action_id,
            timestamp=now,
            action_type=action_type,
            payload=payload,
            source=source,
            status="pending"
        )
        
        if self.mode == ExecutionMode.AUTO:
            # Execute immediately
            result = self._execute_action(action)
            action.status = "executed"
            action.executed_at = datetime.now()
            action.result = result
            self.action_history.append(action)
            return {
                "mode": "auto",
                "action_id": action_id,
                "status": "executed",
                "result": result
            }
        else:
            # Queue for approval
            self.pending_actions[action_id] = action
            return {
                "mode": "semi-auto",
                "action_id": action_id,
                "status": "pending_approval",
                "message": "Action queued for manual approval"
            }
    
    def approve_action(self, action_id: str) -> Dict[str, Any]:
        """Approve and execute a pending action."""
        if action_id not in self.pending_actions:
            return {"error": "Action not found", "action_id": action_id}
        
        action = self.pending_actions[action_id]
        
        if action.status != "pending":
            return {"error": f"Action already {action.status}", "action_id": action_id}
        
        # Execute the action
        result = self._execute_action(action)
        
        action.status = "executed"
        action.approved_at = datetime.now()
        action.executed_at = datetime.now()
        action.result = result
        
        # Move to history
        del self.pending_actions[action_id]
        self.action_history.append(action)
        
        return {
            "action_id": action_id,
            "status": "approved_and_executed",
            "result": result
        }
    
    def reject_action(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a pending action."""
        if action_id not in self.pending_actions:
            return {"error": "Action not found"}
        
        action = self.pending_actions[action_id]
        action.status = "rejected"
        action.result = {"reason": reason}
        
        del self.pending_actions[action_id]
        self.action_history.append(action)
        
        return {"action_id": action_id, "status": "rejected"}
    
    def approve_all(self) -> Dict[str, Any]:
        """Approve all pending actions."""
        results = []
        for action_id in list(self.pending_actions.keys()):
            result = self.approve_action(action_id)
            results.append(result)
        return {"approved_count": len(results), "results": results}
    
    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending actions."""
        return [a.dict() for a in self.pending_actions.values()]
    
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get action history."""
        return [a.dict() for a in self.action_history[-limit:]]
    
    def set_mode(self, mode: ExecutionMode):
        """Switch execution mode."""
        self.mode = mode
    
    def _execute_action(self, action: PendingAction) -> Dict[str, Any]:
        """
        Execute an action. Override this in subclass to connect to broker.
        """
        # Mock execution - in production, this calls the broker
        return {
            "executed": True,
            "action_type": action.action_type,
            "payload": action.payload,
            "execution_time": datetime.now().isoformat()
        }


class SmartRouter:
    """
    Smart Order Routing with connection pooling and latency optimization.
    Routes orders to the best execution path.
    """
    
    def __init__(self):
        self.brokers: Dict[str, Any] = {}
        self.latency_stats: Dict[str, List[float]] = {}
        self.connection_pool: Dict[str, Any] = {}
    
    def register_broker(self, name: str, adapter: Any, priority: int = 1):
        """Register a broker adapter."""
        self.brokers[name] = {
            "adapter": adapter,
            "priority": priority,
            "active": True,
            "avg_latency": 0
        }
        self.latency_stats[name] = []
    
    def route_order(self, order: Dict[str, Any], preferred_broker: Optional[str] = None) -> Dict[str, Any]:
        """
        Route order to the best available broker.
        Uses latency-based routing if no preference specified.
        """
        if preferred_broker and preferred_broker in self.brokers:
            return self._execute_via(preferred_broker, order)
        
        # Find best broker by latency
        best_broker = self._get_best_broker()
        if not best_broker:
            return {"error": "No active brokers available"}
        
        return self._execute_via(best_broker, order)
    
    def _get_best_broker(self) -> Optional[str]:
        """Get broker with lowest average latency."""
        active_brokers = [(name, info) for name, info in self.brokers.items() if info["active"]]
        if not active_brokers:
            return None
        
        # Sort by latency (lower is better)
        active_brokers.sort(key=lambda x: x[1]["avg_latency"])
        return active_brokers[0][0]
    
    def _execute_via(self, broker_name: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order via specific broker and track latency."""
        import time
        start = time.time()
        
        broker = self.brokers[broker_name]
        # Mock execution
        result = {
            "broker": broker_name,
            "order": order,
            "status": "executed"
        }
        
        # Track latency
        latency = (time.time() - start) * 1000  # ms
        self.latency_stats[broker_name].append(latency)
        
        # Update running average
        recent = self.latency_stats[broker_name][-100:]
        broker["avg_latency"] = sum(recent) / len(recent) if recent else 0
        
        result["latency_ms"] = latency
        return result
    
    def get_broker_stats(self) -> Dict[str, Any]:
        """Get statistics for all brokers."""
        return {
            name: {
                "active": info["active"],
                "priority": info["priority"],
                "avg_latency_ms": info["avg_latency"],
                "order_count": len(self.latency_stats.get(name, []))
            }
            for name, info in self.brokers.items()
        }
