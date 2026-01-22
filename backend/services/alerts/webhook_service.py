"""
Webhook Alerting Service
Handles incoming webhooks (TradingView, Upstox) and outgoing alerts (Gmail, Telegram).
Optimized for Free-Tier usage.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
import httpx
import os

from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.credentials import Credentials

logger = logging.getLogger(__name__)

app = FastAPI(title="Webhook Alert Service")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

class AlertManager:
    """Manages outgoing notifications via free channels."""
    
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.gmail_user = os.getenv("GMAIL_USER")
        self.gmail_pass = os.getenv("GMAIL_APP_PASSWORD")

    async def send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured")
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": self.telegram_chat_id, "text": message})

    def send_gmail(self, subject: str, body: str):
        if not self.gmail_user or not self.gmail_pass:
            logger.warning("Gmail not configured")
            return
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.gmail_user
        msg['To'] = self.gmail_user # Send to self
        
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.gmail_user, self.gmail_pass)
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Gmail failed: {e}")

@app.post("/api/v1/webhooks/tradingview")
async def tradingview_webhook(payload: Dict[str, Any]):
    """Ingest signals from TradingView."""
    logger.info(f"Received TradingView signal: {payload}")
    
    # Map TV signal to internal Event
    event = Event.create(
        event_type=EventTypes.STRATEGY_SIGNAL,
        payload={
            "symbol": payload.get("ticker"),
            "action": payload.get("action", "BUY").upper(),
            "price": payload.get("price"),
            "source": "tradingview_webhook"
        },
        source="webhook_service"
    )
    await bus.publish(event)
    
    # Also trigger urgent notification
    alert = AlertManager()
    await alert.send_telegram(f"🚨 Strategy Signal: {payload.get('ticker')} {payload.get('action')}")
    
    return {"status": "accepted"}

@app.on_event("startup")
async def startup_event():
    # Subscribe to critical system events to send alerts
    await bus.subscribe(EventTypes.SCAN_MATCH, handle_scan_match)

async def handle_scan_match(event: Event):
    payload = event.payload
    alert = AlertManager()
    # Only alert on high-confidence scanner matches to avoid spam
    if payload.get("indicator_values", {}).get("rsi", 50) < 30:
        await alert.send_telegram(f"🎯 Scanner Match: {payload['symbol']} (RSI: {payload['indicator_values']['rsi']})")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)
