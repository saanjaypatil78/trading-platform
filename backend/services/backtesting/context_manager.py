import pandas as pd
import numpy as np
from typing import Dict, List
import logging
import hashlib
import json
from datetime import datetime
from decimal import Decimal

from .models import BacktestContext
from shared.cache import cache

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages persistent context for long-running backtests
    Enables resumability and state recovery
    """
    
    CHECKPOINT_INTERVAL = 1000  # Checkpoint every 1000 bars
    
    @staticmethod
    def create_context(backtest_id: str, config: dict, total_bars: int) -> BacktestContext:
        """Create new backtest context"""
        return BacktestContext(
            backtest_id=backtest_id,
            current_date=datetime.now(),
            processed_bars=0,
            total_bars=total_bars,
            portfolio_value=Decimal(str(config['initial_capital'])),
            cash=Decimal(str(config['initial_capital'])),
            positions={},
            state="pending",
            intermediate_results={}
        )
    
    @staticmethod
    async def save_checkpoint(context: BacktestContext) -> None:
        """
        Save context checkpoint to Redis
        Enables recovery from failures
        """
        # Calculate checksum for data integrity
        context_dict = context.dict()
        context_dict['checksum'] = ContextManager._calculate_checksum(context_dict)
        
        # Save to cache with 24-hour TTL
        cache_key = f"backtest:{context.backtest_id}:context"
        await cache.set(
            cache_key,
            json.dumps(context_dict, default=str),
            ttl=86400
        )
        
        logger.info(
            f"Checkpoint saved for backtest {context.backtest_id} "
            f"at bar {context.processed_bars}/{context.total_bars}"
        )
    
    @staticmethod
    async def load_checkpoint(backtest_id: str) -> BacktestContext | None:
        """
        Load context from checkpoint
        Returns None if no checkpoint exists
        """
        cache_key = f"backtest:{backtest_id}:context"
        data = await cache.get(cache_key)
        
        if not data:
            return None
        
        context_dict = json.loads(data)
        
        # Verify checksum
        stored_checksum = context_dict.pop('checksum', None)
        calculated_checksum = ContextManager._calculate_checksum(context_dict)
        
        if stored_checksum != calculated_checksum:
            logger.error(
                f"Checksum mismatch for backtest {backtest_id}. "
                f"Data may be corrupted."
            )
            return None
        
        logger.info(f"Loaded checkpoint for backtest {backtest_id}")
        return BacktestContext(**context_dict)
    
    @staticmethod
    async def delete_checkpoint(backtest_id: str) -> None:
        """Delete checkpoint after successful completion"""
        cache_key = f"backtest:{backtest_id}:context"
        await cache.delete(cache_key)
    
    @staticmethod
    def should_checkpoint(processed_bars: int) -> bool:
        """Determine if checkpoint should be saved"""
        return processed_bars % ContextManager.CHECKPOINT_INTERVAL == 0
    
    @staticmethod
    def _calculate_checksum(data: dict) -> str:
        """Calculate SHA256 checksum of context data"""
        # Remove checksum field if present
        data_copy = {k: v for k, v in data.items() if k != 'checksum'}
        data_str = json.dumps(data_copy, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()


class EventStore:
    """
    Store all backtest events for audit trail
    Implements event sourcing pattern
    """
    
    @staticmethod
    async def record_event(
        backtest_id: str,
        event_type: str,
        data: dict
    ) -> None:
        """Record an event to the immutable log"""
        event = {
            'backtest_id': backtest_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data,
            'checksum': hashlib.sha256(
                json.dumps(data, default=str).encode()
            ).hexdigest()
        }
        
        # Append to event log in cache (list)
        cache_key = f"backtest:{backtest_id}:events"
        events = await cache.get(cache_key)
        
        if events:
            events = json.loads(events)
        else:
            events = []
        
        events.append(event)
        
        # Store with 7-day TTL
        await cache.set(
            cache_key,
            json.dumps(events, default=str),
            ttl= 604800  # 7 days
        )
    
    @staticmethod
    async def get_events(backtest_id: str) -> List[dict]:
        """Retrieve all events for a backtest"""
        cache_key = f"backtest:{backtest_id}:events"
        data = await cache.get(cache_key)
        
        if not data:
            return []
        
        return json.loads(data)
    
    @staticmethod
    async def reconstruct_state(backtest_id: str) -> dict:
        """
        Reconstruct backtest state from event log
        Enables time-travel debugging
        """
        events = await EventStore.get_events(backtest_id)
        
        state = {
            'positions': {},
            'cash': 0,
            'trades': []
        }
        
        for event in events:
            event_type = event['event_type']
            data = event['data']
            
            if event_type == 'backtest.started':
                state['cash'] = data['initial_capital']
            
            elif event_type == 'trade.opened':
                symbol = data['symbol']
                state['positions'][symbol] = data
                state['cash'] -= data['cost']
            
            elif event_type == 'trade.closed':
                symbol = data['symbol']
                if symbol in state['positions']:
                    del state['positions'][symbol]
                state['cash'] += data['proceeds']
                state['trades'].append(data)
        
        return state
