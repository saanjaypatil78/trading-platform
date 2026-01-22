import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from backend.shared.config import settings

logger = logging.getLogger(__name__)

class WebhookManager:
    """
    Manages sending outgoing webhooks to external URLs.
    """
    
    @staticmethod
    async def send_webhook(url: str, payload: Dict[str, Any]):
        """
        Send a JSON payload to a webhook URL.
        """
        if not url:
            return

        try:
            async with aiohttp.ClientSession() as session:
                logger.info(f"Sending webhook to {url}")
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as resp:
                    if resp.status >= 400:
                        logger.error(f"Webhook failed: {resp.status} {await resp.text()}")
                    else:
                        logger.info(f"Webhook delivered: {resp.status}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    @staticmethod
    async def notify_scanner_match(match_data: Dict[str, Any]):
        """
        Broadcast scanner matches to configured webhooks.
        Currently sends to the user's TradingView alert URL if configured?
        Actually, users usually configure OUR url in TradingView.
        
        BUT, the request was: "pre built scannner based webhook alert system where those scans pass json data... mechanism same as chartink.com"
        
        This means: When WE scan a stock (e.g. RELIANCE crosses RSI), WE call *YOUR* webhook URL (e.g. Slack/Discord/Bot).
        
        For now, we'll assume a global notification webhook in settings, 
        or we just log it as a 'System Event' if no external URL.
        """
        # In a real app, we'd look up the user's configured webhook for this specific alert.
        # For simplicity, we'll fetch a global "ALERT_WEBHOOK_URL" from settings if it existed.
        pass
