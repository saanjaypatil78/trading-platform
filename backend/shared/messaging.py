"""
Message Bus - Event-Driven Architecture (EDA) Core
Provides asynchronous communication between microservices.
Pluggable backends: InMemory (Testing), Redis (Production), or Kafka (HFT).
"""
import json
import asyncio
from typing import Dict, List, Callable, Any, Optional, Awaitable
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

@dataclass
class Event:
    """Base class for all system events."""
    event_id: str
    event_type: str
    timestamp: str
    payload: Dict[str, Any]
    source: str

    @classmethod
    def create(cls, event_type: str, payload: Dict[str, Any], source: str):
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            payload=payload,
            source=source
        )

class MessageBus:
    """
    Message Bus for decoupled service communication.
    Implements Publish/Subscribe pattern.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self.history: List[Event] = []
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Register a handler for a specific event type."""
        async with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
            print(f"[Bus] Subscribed handler to {event_type}")

    async def publish(self, event: Event):
        """Publish an event to all interested subscribers."""
        async with self._lock:
            self.history.append(event)
            if len(self.history) > 1000:
                self.history.pop(0)

            handlers = self.subscribers.get(event_type := event.event_type, [])
            # Also support global subscribers via '*'
            handlers += self.subscribers.get('*', [])

            if not handlers:
                # print(f"[Bus] No subscribers for {event_type}")
                return

            # Execute handlers concurrently
            tasks = [handler(event) for handler in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get past events."""
        if event_type:
            return [asdict(e) for e in self.history if e.event_type == event_type]
        return [asdict(e) for e in self.history]

# Global Bus Instance
bus = MessageBus()

# Event Types Constants
class EventTypes:
    TICK_DATA = "market.tick"
    ORDER_PLACED = "order.placed"
    ORDER_EXECUTED = "order.executed"
    SCAN_MATCH = "scanner.match"
    STRATEGY_SIGNAL = "strategy.signal"
    SYSTEM_ALERT = "system.alert"
    MEMORY_LEARNED = "brain.memory_learned"
