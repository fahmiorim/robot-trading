"""WebSocket data pusher — background thread that polls exchange and broadcasts to clients.

Extracted from websocket.py for modularity.
"""

import threading
import time
from typing import Any, Dict

from src.configuration.manager import ConfigManager
from src.rpc.websocket import WebSocketRPC, set_shared, get_shared
from src.utils.logging import get_logger

logger = get_logger(__name__)


def start_data_pusher(ws: WebSocketRPC, bot: Any,
                      config: ConfigManager) -> None:
    """Start background thread that polls the exchange and broadcasts."""

    def _push():
        err_count = 0

        # ── Establish DB connection once for this thread ────────
        try:
            from src.persistence.database import get_db
            get_db().connect()
        except Exception:
            pass

        # Wait for the WebSocket server to start running
        for _ in range(50):
            if ws._running:
                break
            time.sleep(0.1)

        while ws._running:
            try:
                symbol = config.get("general", "symbol")
                exchange = getattr(bot, "exchange", None)
                if not exchange:
                    time.sleep(1.5)
                    continue

                # Use bot.paper_positions if paper_trading is enabled, else exchange positions
                paper_trading = getattr(bot, "paper_trading", True)
                if paper_trading:
                    try:
                        bot.update_paper_positions()
                    except Exception:
                        pass
                    positions = getattr(bot, "paper_positions", [])
                    # Account metrics for paper trading
                    account_balance = getattr(bot, "paper_balance", 0.0)
                    total_pnl = sum(p.get("profit", 0) for p in positions) if positions else 0.0
                    account_equity = account_balance + total_pnl
                    free_margin = account_equity
                    margin_level = 100.0
                    mt5_connected = exchange.is_connected()
                    ticker = {}
                    try:
                        ticker = exchange.fetch_ticker(symbol) or {}
                    except Exception:
                        pass
                else:
                    ticker = exchange.fetch_ticker(symbol) or {}
                    balance = exchange.get_balance() or {}
                    positions = exchange.get_open_positions(symbol) or []
                    account_balance = balance.get("balance", 0.0)
                    account_equity = balance.get("equity", 0.0)
                    free_margin = balance.get("free_margin", 0.0)
                    margin_level = balance.get("margin_level", 0.0)
                    mt5_connected = exchange.is_connected()

                # Update risk manager's balance so drawdown is calculated correctly
                try:
                    bot.risk.update_balance(account_balance)
                    bot.risk.protection_ctx.open_positions = len(positions) if positions else 0
                except Exception:
                    pass

                regime = get_shared("regime", "unknown")
                auto = get_shared("auto_trading", False)
                strategy = get_shared("best_strategy", "N/A")
                cycles = getattr(bot, "cycle_count", 0)

                # Fetch candles to compute signals
                candles = None
                try:
                    candles = bot.fetch_data(count=100)
                except Exception:
                    pass

                sig_strat = 0
                sig_ml = 0
                sig_agent = 0
                sig_swarm = 0
                if candles is not None and not candles.empty:
                    try:
                        raw = bot.get_individual_signals(candles)
                        sig_strat = raw.get("strategy", 0)
                        sig_ml = raw.get("ml", 0)
                        sig_agent = raw.get("agent", 0)
                        sig_swarm = raw.get("swarm", 0)
                    except Exception:
                        pass

                # Risk summary
                risk_summary = {}
                try:
                    risk_summary = bot.risk.get_status_summary()
                except Exception:
                    pass

                # Format positions for JS ease-of-use
                formatted_positions = []
                for p in positions:
                    formatted_positions.append({
                        "ticket": p.get("ticket"),
                        "symbol": p.get("symbol"),
                        "type": p.get("type", p.get("action", "")),
                        "volume": p.get("volume"),
                        "price": p.get("price") or p.get("open_price"),
                        "current_price": p.get("current_price"),
                        "sl": p.get("sl"),
                        "tp": p.get("tp"),
                        "profit": p.get("profit", 0)
                    })

                # Real-time ML training event (push from set_shared, clear after read)
                ml_event = get_shared("ml_training_event", None)
                ml_training_data = None
                if ml_event is not None:
                    if time.time() - ml_event.get("timestamp", 0) < 3:
                        ml_training_data = ml_event
                    set_shared("ml_training_event", None)

                data = {
                    "type": "market_data",
                    "timestamp": time.time(),
                    "price": {
                        "symbol": symbol,
                        "bid": ticker.get("bid"),
                        "ask": ticker.get("ask"),
                        "spread": round(ticker.get("ask", 0) - ticker.get("bid", 0), 2)
                        if ticker.get("ask") and ticker.get("bid") else None,
                        "time": ticker.get("time"),
                    },
                    "account": {
                        "balance": account_balance,
                        "equity": account_equity,
                        "free_margin": free_margin,
                        "margin_level": margin_level,
                    },
                    "positions": {
                        "count": len(positions),
                        "list": formatted_positions
                    },
                    "status": {
                        "auto_trading": auto,
                        "regime": regime.upper(),
                        "best_strategy": strategy,
                        "mt5_connected": mt5_connected,
                        "cycles": cycles,
                        "timeframe": config.get("general", "timeframe"),
                        "paper_trading": paper_trading,
                        "last_cycle_time": getattr(getattr(bot, "system_service", None), "last_cycle_time", 0.0)
                    },
                    "signals": {
                        "strategy": sig_strat,
                        "ml": sig_ml,
                        "agent": sig_agent,
                        "swarm": sig_swarm
                    },
                    "risk": risk_summary,
                    "ml_training": ml_training_data,
                }
                ws.broadcast(data)
                err_count = 0
            except Exception as e:
                err_count += 1
                logger.error(f"WS pusher error: {e}")
                if err_count > 10:
                    for _ in range(10):
                        if not ws._running:
                            return
                        time.sleep(1)
            # Poll ws._running to stop promptly on shutdown
            for _ in range(3):
                if not ws._running:
                    return
                time.sleep(0.5)

    t = threading.Thread(target=_push, daemon=True, name="ws-pusher")
    t.start()
    logger.info("WS pusher started (every 1.5s)")
