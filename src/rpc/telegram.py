"""
Telegram RPC backend — sends trade alerts and performance reports via Telegram bot.

Ported from the old ``src/notifications.py``. Extended with interactive
command polling (Freqtrade-style) so you can manage the bot via Telegram.

Commands:
    /start — Start auto trading
    /stop — Stop auto trading
    /status — Bot status
    /balance — Account balance
    /profit — Profit summary
    /daily — Daily stats
    /trades — Recent trades
    /positions — Open positions
    /buy <pair> [vol] — Force buy
    /sell [ticket] — Force sell (all or by ticket)
    /show_config — Show current config
    /reload — Reload strategies
    /help — This message
"""
import threading
import time
from typing import Any, Dict, List, Optional

import requests

from src.rpc.base import IRPC, RPCManager
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramRPC(IRPC):
    """Send messages and poll commands via Telegram Bot API."""

    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"
    GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"

    def __init__(self, bot_token: str, chat_id: str,
                 rpc_manager: Optional[RPCManager] = None,
                 allowed_chat_ids: Optional[List[str]] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._send_url = self.BASE_URL.format(token=bot_token)
        self._get_url = self.GET_UPDATES_URL.format(token=bot_token)
        self._rpc = rpc_manager
        self._allowed_chat_ids = allowed_chat_ids or [chat_id]
        self._last_update_id: int = 0
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None

    def name(self) -> str:
        return "Telegram"

    def set_rpc_manager(self, rpc: RPCManager) -> None:
        self._rpc = rpc

    # ── Send ──────────────────────────────────────────────────

    def send_message(self, message: str, parse_mode: str) -> bool:
        if not self.bot_token or not self.chat_id:
            return False
        try:
            resp = requests.post(self._send_url, data={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    # ── Command Polling ──────────────────────────────────────

    def start_polling(self, interval: float = 2.0) -> None:
        """Start polling for Telegram commands in a background thread."""
        if self._polling:
            return
        self._polling = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, args=(interval,),
            daemon=True, name="tg-poll",
        )
        self._poll_thread.start()
        logger.info("Telegram command polling started")

    def stop_polling(self) -> None:
        self._polling = False
        logger.info("Telegram command polling stopped")

    def _poll_loop(self, interval: float) -> None:
        while self._polling:
            try:
                updates = self._fetch_updates()
                for update in updates:
                    self._process_update(update)
                    self._last_update_id = update.get("update_id", 0)
            except Exception as e:
                logger.warning(f"Telegram poll error: {e}")
            time.sleep(interval)

    def _fetch_updates(self) -> List[Dict[str, Any]]:
        """Fetch new updates from Telegram since last seen update_id."""
        try:
            resp = requests.get(self._get_url, params={
                "offset": self._last_update_id + 1,
                "timeout": 5,
            }, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("result", [])
        except Exception as e:
            logger.debug(f"Telegram getUpdates error: {e}")
            return []

    def _process_update(self, update: Dict[str, Any]) -> None:
        """Process a single Telegram update — extract and handle command."""
        msg = update.get("message", {})
        chat = msg.get("chat", {})
        chat_id = str(chat.get("id", ""))
        text = (msg.get("text") or "").strip()

        # ── Authorisation ──────────────────────────────────────
        if self._allowed_chat_ids and str(chat_id) not in [str(x) for x in self._allowed_chat_ids]:
            logger.warning(f"Ignored unauthorised Telegram command from {chat_id}: {text[:50]}")
            return

        if not text:
            return

        # ── Parse command ──────────────────────────────────────
        if not text.startswith("/"):
            return  # Not a command

        parts = text.split(maxsplit=1)
        cmd = parts[0].lstrip("/")
        args = parts[1] if len(parts) > 1 else None

        logger.info(f"Telegram cmd: /{cmd} from {chat_id}")

        if self._rpc is None:
            self._send_to_chat(chat_id, "❌ Bot RPC not connected. Restart bot.")
            return

        # Handle /buy and /sell with pair prefix (e.g. /buy BTC/USDT 0.01)
        response = self._rpc.handle_command(cmd, args)
        self._send_to_chat(chat_id, response)

    def _send_to_chat(self, chat_id: str, message: str) -> None:
        """Send a message to a specific chat ID (for multi-chat support)."""
        try:
            url = self.BASE_URL.format(token=self.bot_token)
            requests.post(url, data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
            }, timeout=10)
        except Exception as e:
            logger.error(f"Telegram send to {chat_id} failed: {e}")

    # ── Factory ──────────────────────────────────────────────

    @classmethod
    def from_config(cls, config) -> Optional["TelegramRPC"]:
        """Create from config manager if telegram is enabled."""
        enabled = config.get("notifications", "telegram_enabled")
        if not enabled:
            return None
        token = config.get("notifications", "telegram_bot_token")
        chat_id = config.get("notifications", "telegram_chat_id")
        if not token or not chat_id:
            logger.warning("Telegram enabled but token/chat_id missing")
            return None
        return cls(token, chat_id)
