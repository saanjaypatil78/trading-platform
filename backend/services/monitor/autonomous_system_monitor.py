"""
Autonomous System Monitor
Monitors system health, performance, and triggers self-healing via DebugAgent.
Integrated with the EDA MessageBus.
"""
import asyncio
import time
import json
from typing import Dict, List, Any
from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.state import state
from debug_agent import DebugAgent

class AutonomousMonitor:
    def __init__(self):
        self.services = {
            "brain": 8007,
            "scanner": 8008,
            "orders": 8009,
            "defi": 8010
        }
        self.debug_agent = DebugAgent(root_dir=".")
        self.is_running = False
        self.health_history = []

    async def start(self):
        self.is_running = True
        print("[Autonomous Monitor] Started")
        
        # Subscribe to error events
        await bus.subscribe("*.error", self.handle_error_event)
        
        # Monitor Loop
        while self.is_running:
            await self.check_system_health()
            await asyncio.sleep(10) # Check every 10 seconds

    async def check_system_health(self):
        """Perform a holistic system health check."""
        status_report = {
            "timestamp": time.time(),
            "services": {},
            "performance": {},
            "system_load": 0.0 # Placeholder for actual CPU/MEM
        }
        
        for name, port in self.services.items():
            is_up = await self._check_service(port)
            status_report["services"][name] = "UP" if is_up else "DOWN"
            
            if not is_up:
                print(f"[Autonomous Monitor] CRITICAL: Service {name} is DOWN!")
                await self.trigger_self_healing(name)
        
        # Log to StateStore
        state.set("monitor:last_report", status_report)
        
        # Publish generic heartbeat
        await bus.publish(Event.create(
            event_type="monitor.heartbeat",
            payload=status_report,
            source="autonomous_monitor"
        ))

    async def _check_service(self, port: int) -> bool:
        """Simple TCP/HTTP health check."""
        import htautolib # Not needed, use standard lib
        import http.client
        try:
            conn = http.client.HTTPConnection("localhost", port, timeout=2)
            conn.request("GET", "/health")
            res = conn.getresponse()
            return res.status == 200
        except:
            return False

    async def handle_error_event(self, event: Event):
        """React to error events published by other services."""
        print(f"[Autonomous Monitor] Detected Remote Error: {event.payload}")
        await self.trigger_self_healing(event.source)

    async def trigger_self_healing(self, service_name: str):
        """Invoke DebugAgent to fix common code issues."""
        print(f"[Autonomous Monitor] Triggering self-healing for {service_name}...")
        
        # Run DebugAgent scan
        report = self.debug_agent.scan_all()
        
        if report["auto_fixable"] > 0:
            print(f"[Autonomous Monitor] Found {report['auto_fixable']} auto-fixable issues. Fixing...")
            fixed_count = self.debug_agent.auto_fix()
            
            await bus.publish(Event.create(
                event_type="monitor.fix_applied",
                payload={"service": service_name, "fixed_count": fixed_count},
                source="autonomous_monitor"
            ))
        else:
            print("[Autonomous Monitor] No auto-fixes available. Alerting Admin.")
            await bus.publish(Event.create(
                event_type="monitor.alert",
                payload={"service": service_name, "message": "Service down, no auto-fix found"},
                source="autonomous_monitor"
            ))

if __name__ == "__main__":
    monitor = AutonomousMonitor()
    asyncio.run(monitor.start())
