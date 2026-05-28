"""Notification service — broadcasts messages to all RPC backends."""

from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Manages notification broadcasting to all RPC backends (Telegram, WebSocket, REST).

    Usage:
        service = NotificationService(rpc_manager)
        service.broadcast("Bot started!")
        service.send_trade_alert(symbol, action, price, strategy, regime)
    """

    def __init__(self, rpc_manager):
        self.rpc = rpc_manager

    def broadcast(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to all registered backends."""
        return self.rpc.broadcast(message, parse_mode)

    def send_trade_alert(self, symbol: str, action: str, price: float,
                         strategy: str, regime: str) -> None:
        """Send a trade alert notification."""
        self.rpc.send_trade_alert(symbol, action, price, strategy, regime)

    def send_daily_report(self, summary: Dict[str, Any]) -> None:
        """Send a daily performance report."""
        self.rpc.send_daily_report(summary)

    def send_status(self, status: Dict[str, Any]) -> None:
        """Send a status update."""
        self.rpc.send_status(status)

    def handle_command(self, cmd: str, args: Optional[str] = None) -> str:
        """Route a text command to the bot controller."""
        return self.rpc.handle_command(cmd, args)
