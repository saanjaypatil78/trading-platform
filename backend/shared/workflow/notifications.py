"""
Telegram Bot Integration
Inspired by OpenAlgo's Telegram integration.
Provides real-time notifications and command execution.
"""
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel
from datetime import datetime
import asyncio
import httpx

class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str
    enabled: bool = True

class TelegramBot:
    """
    Telegram bot for trading notifications and commands.
    """
    
    def __init__(self, config: Optional[TelegramConfig] = None):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}" if config else ""
        self.command_handlers: Dict[str, Callable] = {}
        
        # Register default commands
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default command handlers."""
        self.command_handlers["/start"] = self._cmd_start
        self.command_handlers["/help"] = self._cmd_help
        self.command_handlers["/positions"] = self._cmd_positions
        self.command_handlers["/orders"] = self._cmd_orders
        self.command_handlers["/funds"] = self._cmd_funds
        self.command_handlers["/pnl"] = self._cmd_pnl
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat."""
        if not self.config or not self.config.enabled:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.config.chat_id,
                        "text": text,
                        "parse_mode": parse_mode
                    }
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False
    
    async def notify_order(self, order: Dict[str, Any]):
        """Send order notification."""
        side_emoji = "🟢" if order.get("side") == "BUY" else "🔴"
        status_emoji = "✅" if order.get("status") == "COMPLETE" else "⏳"
        
        message = f"""
{side_emoji} <b>Order {order.get('status', 'PLACED')}</b> {status_emoji}

<b>Symbol:</b> {order.get('symbol', 'N/A')}
<b>Side:</b> {order.get('side', 'N/A')}
<b>Qty:</b> {order.get('quantity', 0)}
<b>Price:</b> Rs.{order.get('average_price', 0):.2f}
<b>Type:</b> {order.get('order_type', 'MARKET')}
<b>Order ID:</b> <code>{order.get('order_id', 'N/A')}</code>

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}</i>
"""
        await self.send_message(message)
    
    async def notify_alert(self, alert: Dict[str, Any]):
        """Send strategy alert notification."""
        message = f"""
🔔 <b>Strategy Alert</b>

<b>Strategy:</b> {alert.get('strategy', 'N/A')}
<b>Symbol:</b> {alert.get('symbol', 'N/A')}
<b>Signal:</b> {alert.get('signal', 'N/A')}
<b>Price:</b> Rs.{alert.get('price', 0):.2f}

<i>{alert.get('message', '')}</i>

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}</i>
"""
        await self.send_message(message)
    
    async def notify_pnl(self, pnl_data: Dict[str, Any]):
        """Send P&L update."""
        total_pnl = pnl_data.get('total_pnl', 0)
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        
        message = f"""
{pnl_emoji} <b>P&L Update</b>

<b>Today's P&L:</b> Rs.{pnl_data.get('today_pnl', 0):+,.2f}
<b>Total P&L:</b> Rs.{total_pnl:+,.2f}
<b>Realized:</b> Rs.{pnl_data.get('realized_pnl', 0):+,.2f}
<b>Unrealized:</b> Rs.{pnl_data.get('unrealized_pnl', 0):+,.2f}

<b>Win Rate:</b> {pnl_data.get('win_rate', 0):.1f}%
<b>Total Trades:</b> {pnl_data.get('total_trades', 0)}
"""
        await self.send_message(message)
    
    def register_command(self, command: str, handler: Callable):
        """Register a custom command handler."""
        self.command_handlers[command] = handler
    
    async def handle_update(self, update: Dict[str, Any]) -> Optional[str]:
        """Handle incoming Telegram update."""
        message = update.get("message", {})
        text = message.get("text", "")
        
        if not text.startswith("/"):
            return None
        
        command = text.split()[0]
        args = text.split()[1:]
        
        if command in self.command_handlers:
            return await self.command_handlers[command](args)
        
        return "Unknown command. Use /help for available commands."
    
    # Default command handlers
    async def _cmd_start(self, args: List[str]) -> str:
        return """
🚀 <b>Trading Bot Active</b>

Welcome! I'll send you real-time updates on:
• Order executions
• Position changes
• Strategy alerts
• P&L updates

Use /help to see available commands.
"""
    
    async def _cmd_help(self, args: List[str]) -> str:
        return """
📚 <b>Available Commands</b>

/positions - View current positions
/orders - View today's orders
/funds - Check available funds
/pnl - View P&L summary
/help - Show this message
"""
    
    async def _cmd_positions(self, args: List[str]) -> str:
        # In production, fetch from broker
        return "📊 <b>Positions</b>\n\nNo open positions."
    
    async def _cmd_orders(self, args: List[str]) -> str:
        return "📋 <b>Orders</b>\n\nNo orders today."
    
    async def _cmd_funds(self, args: List[str]) -> str:
        return "💰 <b>Funds</b>\n\nAvailable: Rs.10,00,000"
    
    async def _cmd_pnl(self, args: List[str]) -> str:
        return "📈 <b>P&L Summary</b>\n\nToday: Rs.0\nTotal: Rs.0"


class NotificationService:
    """
    Unified notification service supporting multiple channels.
    """
    
    def __init__(self):
        self.telegram: Optional[TelegramBot] = None
        self.email_enabled: bool = False
        self.webhook_urls: List[str] = []
    
    def configure_telegram(self, bot_token: str, chat_id: str):
        """Configure Telegram notifications."""
        self.telegram = TelegramBot(TelegramConfig(
            bot_token=bot_token,
            chat_id=chat_id
        ))
    
    def add_webhook(self, url: str):
        """Add a webhook notification endpoint."""
        self.webhook_urls.append(url)
    
    async def notify(self, event_type: str, data: Dict[str, Any]):
        """Send notification to all configured channels."""
        tasks = []
        
        # Telegram
        if self.telegram:
            if event_type == "order":
                tasks.append(self.telegram.notify_order(data))
            elif event_type == "alert":
                tasks.append(self.telegram.notify_alert(data))
            elif event_type == "pnl":
                tasks.append(self.telegram.notify_pnl(data))
        
        # Webhooks
        for url in self.webhook_urls:
            tasks.append(self._send_webhook(url, event_type, data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_webhook(self, url: str, event_type: str, data: Dict[str, Any]):
        """Send webhook notification."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, json={
                    "event": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Webhook error: {e}")
