"""RPC setup service — initialises RPC backends (Telegram, WebSocket, REST API).

Extracted from TradingController._init_rpc() + _init_rest_api() to keep
controllers thin and focused on orchestration.

Usage:
    rpc = RPCManager()
    service = RPCSetupService(config, rpc)
    service.setup_all(bot_controller)
"""

from typing import Any, Optional

from src.configuration.manager import ConfigManager
from src.rpc.base import RPCManager
from src.rpc.telegram import TelegramRPC
from src.rpc.websocket import WebSocketRPC, start_data_pusher
from src.rpc.rest_api import RestAPI
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RPCSetupService:
    """Initialises all RPC/notification backends from config.

    Responsibilities:
      - Create and register Telegram bot (with optional command polling)
      - Create and start WebSocket server for real-time dashboard data
      - Start data pusher (periodic exchange data → WebSocket broadcast)
      - Optionally start REST API server
    """

    def __init__(self, config: ConfigManager, rpc_manager: RPCManager):
        self.config = config
        self.rpc = rpc_manager
        self.ws: Optional[WebSocketRPC] = None
        self.rest_api: Optional[RestAPI] = None

    def setup_all(self, bot: Any) -> None:
        """Set up all RPC backends and register them with the manager.

        Args:
            bot: The bot/controller instance to attach to the RPC manager.
        """
        self.rpc.set_bot(bot)

        # ── Telegram ──
        self._setup_telegram(bot)

        # ── WebSocket ──
        self._setup_websocket(bot)

        # ── REST API ──
        self._setup_rest_api(bot)

    def _setup_telegram(self, bot: Any) -> None:
        """Initialise Telegram RPC backend (optional)."""
        telegram = TelegramRPC.from_config(self.config)
        if not telegram:
            logger.info("Telegram RPC not configured, skipping")
            return

        telegram.set_rpc_manager(self.rpc)
        self.rpc.register(telegram)

        # Optional command polling
        cmd_cfg = self.config.get("telegram_cmd")
        if isinstance(cmd_cfg, dict) and cmd_cfg.get("enabled", False):
            allowed = cmd_cfg.get("allowed_chat_ids", [])
            if allowed:
                telegram._allowed_chat_ids = allowed
            telegram.start_polling()
            logger.info("Telegram command polling enabled")

    def _setup_websocket(self, bot: Any) -> None:
        """Initialise WebSocket RPC backend and data pusher."""
        self.ws = WebSocketRPC()
        start_data_pusher(self.ws, bot, self.config)
        self.ws.start()
        self.rpc.register(self.ws)
        logger.info("WebSocket RPC started on ws://localhost:8765")

    def _setup_rest_api(self, bot: Any) -> None:
        """Initialise REST API server (optional)."""
        api_cfg = self.config.get("rest_api")
        if not isinstance(api_cfg, dict) or not api_cfg.get("enabled", False):
            return

        self.rest_api = RestAPI(
            bot=bot,
            host=str(api_cfg.get("host", "0.0.0.0")),
            port=int(api_cfg.get("port", 8080)),
            api_key=str(api_cfg.get("api_key", "")),
        )
        self.rest_api.start()
        logger.info(
            f"REST API enabled on {api_cfg.get('host', '0.0.0.0')}:"
            f"{api_cfg.get('port', 8080)}"
        )

    def stop_all(self) -> None:
        """Gracefully stop all RPC backends."""
        if self.rest_api:
            try:
                self.rest_api.stop()
            except Exception:
                pass
        if self.ws:
            try:
                self.ws.stop()
            except Exception:
                pass
