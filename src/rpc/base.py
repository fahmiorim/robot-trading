"""
RPC (Remote Procedure Call) interface — abstract notification/communication layer.

Inspired by Freqtrade's RPC module. Supports Telegram and WebSocket backends,
with a common interface so the bot can send alerts, performance reports, and
status updates without caring about the transport.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable


class IRPC(ABC):
    """Abstract interface for all RPC/notification backends."""

    @abstractmethod
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class RPCManager:
    """Manages multiple RPC backends and broadcasts to all of them.

    Also acts as a command dispatch hub — interactive backends (Telegram)
    can call ``handle_command()`` which routes to the bot's methods.
    """

    def __init__(self):
        self._backends: List[IRPC] = []
        self.bot: Any = None  # Set by TradingBot after __init__

    def set_bot(self, bot: Any) -> None:
        self.bot = bot

    def register(self, backend: IRPC) -> None:
        self._backends.append(backend)

    def broadcast(self, message: str, parse_mode: str = "HTML") -> bool:
        all_ok = True
        for b in self._backends:
            if not b.send_message(message, parse_mode):
                all_ok = False
        return all_ok

    # ── Command Dispatch ──────────────────────────────────────

    def handle_command(self, cmd: str, args: Optional[str] = None) -> str:
        """Route a text command (e.g. /status, /start) to the bot.

        Returns a response string that the caller can echo back to the user.
        """
        if self.bot is None:
            return "❌ Bot not initialised"

        cmd = cmd.lower().strip("/").strip()

        # ── Basic commands ────────────────────────────────────
        if cmd == "start":
            return self._cmd_start()
        elif cmd == "stop":
            return self._cmd_stop()
        elif cmd == "stopbuy":
            return self._cmd_stopbuy()
        elif cmd == "status":
            return self._cmd_status()
        elif cmd == "balance":
            return self._cmd_balance()
        elif cmd == "profit":
            return self._cmd_profit()
        elif cmd == "daily":
            return self._cmd_daily()
        elif cmd == "trades":
            return self._cmd_trades()
        elif cmd in ("open", "positions", "pos"):
            return self._cmd_open_positions()
        elif cmd in ("buy", "forcebuy"):
            return self._cmd_forcebuy(args)
        elif cmd in ("sell", "forcesell"):
            return self._cmd_forcesell(args)
        elif cmd == "version":
            return "🤖 AI Trading Robot v2.0"
        elif cmd in ("help", "?"):
            return self._cmd_help()
        elif cmd == "delete":
            return self._cmd_delete(args)
        elif cmd == "reload":
            return self._cmd_reload()
        elif cmd == "show_config":
            return self._cmd_show_config()
        else:
            return f"❌ Unknown command: /{cmd}\nUse /help to see available commands."

    # ── Command Implementations ──────────────────────────────

    def _cmd_start(self) -> str:
        if getattr(self.bot, "auto_trading", False):
            return "⚠️ Bot is already running."
        self.bot.auto_trading = True
        setattr(self.bot, "_last_cycle_time", __import__("time").time())
        from src.rpc.websocket import set_shared
        set_shared("auto_trading", True)
        return "✅ Bot started — trading cycle active."

    def _cmd_stop(self) -> str:
        if not getattr(self.bot, "auto_trading", False):
            return "⚠️ Bot is already stopped."
        self.bot.auto_trading = False
        from src.rpc.websocket import set_shared
        set_shared("auto_trading", False)
        return "⏹ Bot stopped — no new trades."

    def _cmd_stopbuy(self) -> str:
        self.bot._stop_buy = True
        return "🛑 Stop-buy activated — will not open new long positions."

    def _cmd_status(self) -> str:
        s = self.bot.status()
        lines = [
            "🤖 <b>Bot Status</b>",
            f"Symbol: {s.get('symbol', 'N/A')} | Timeframe: {s.get('timeframe', 'N/A')}",
            f"Running: {'✅' if s.get('auto_trading', False) else '❌'}",
            f"Strategy: {s.get('best_strategy', 'N/A')}",
            f"Regime: {s.get('current_regime', 'N/A').upper()}",
            f"Cycle: #{s.get('cycle_count', 0)}",
            f"Open Positions: {s.get('risk', {}).get('open_positions', 0)}",
            f"Drawdown: {s.get('risk', {}).get('drawdown_pct', 0):.1f}%",
            f"Daily Loss: {s.get('risk', {}).get('daily_loss_pct', 0):.1f}%",
            f"Errors: {s.get('consecutive_errors', 0)}",
        ]
        return "\n".join(lines)

    def _cmd_balance(self) -> str:
        try:
            bal = self.bot.exchange.get_balance()
            return (
                "💰 <b>Balance</b>\n"
                f"Balance: ${bal.get('balance', 0):.2f}\n"
                f"Equity: ${bal.get('equity', 0):.2f}\n"
                f"Free Margin: ${bal.get('free_margin', 0):.2f}\n"
                f"Margin Level: {bal.get('margin_level', 0):.1f}%"
            )
        except Exception as e:
            return f"❌ Balance error: {e}"

    def _cmd_profit(self) -> str:
        s = self.bot.status()
        r = s.get("risk", {})
        daily_pnl = 0
        total_pnl = 0
        try:
            trades = self.bot.trade_manager.closed_trades
            total_pnl = sum(t.profit for t in trades if t.profit)
            today = __import__("datetime").date.today()
            daily_trades = [t for t in trades if t.exit_time and t.exit_time.date() == today]
            daily_pnl = sum(t.profit for t in daily_trades if t.profit)
        except Exception:
            pass
        return (
            "📈 <b>Profit Summary</b>\n"
            f"Total Profit: ${total_pnl:.2f}\n"
            f"Daily P&L: ${daily_pnl:.2f}\n"
            f"Drawdown: {r.get('drawdown_pct', 0):.1f}%\n"
            f"Win trades: ?  Lose trades: ?"
        )

    def _cmd_daily(self) -> str:
        try:
            from src.repositories.trade_repo import TradeRepository
            db = __import__("src.persistence.database", fromlist=["get_db"]).get_db()
            repo = TradeRepository(db)
            summary = repo.summary(days=1)
        except Exception:
            summary = {}
        return (
            "📊 <b>Daily Stats</b>\n"
            f"Trades: {summary.get('total_trades', 0)}\n"
            f"Wins: {summary.get('wins', 0)}\n"
            f"Losses: {summary.get('losses', 0)}\n"
            f"Win Rate: {summary.get('win_rate', 0):.1f}%\n"
            f"Profit: ${summary.get('total_profit', 0):.2f}"
        )

    def _cmd_trades(self) -> str:
        try:
            trades = self.bot.trade_manager.all_trades[-10:]  # last 10
        except Exception:
            trades = []
        if not trades:
            return "📭 No trades yet."
        lines = ["📜 <b>Recent Trades</b>"]
        for t in reversed(trades[-5:]):
            side = "🟢 BUY" if str(t.side).upper() == "BUY" else "🔴 SELL"
            pnl = f"P&L: ${t.profit:.2f}" if t.profit else "Open"
            lines.append(f"{side} {t.symbol} vol={t.volume} @ {t.entry_price:.2f} | {pnl}")
        return "\n".join(lines)

    def _cmd_open_positions(self) -> str:
        try:
            positions = self.bot.exchange.get_open_positions(self.bot.symbol)
        except Exception as e:
            return f"❌ Positions error: {e}"
        if not positions:
            return "📭 No open positions."
        lines = ["📋 <b>Open Positions</b>"]
        for p in positions:
            side = p.get("side", p.get("type", "?"))
            vol = p.get("volume", 0)
            entry = p.get("entry_price", p.get("open_price", 0))
            current = p.get("current_price", 0)
            pnl = p.get("pnl", p.get("profit", 0))
            lines.append(f"{'🟢' if side == 'BUY' else '🔴'} {side} {vol} @ {entry:.2f} → {current:.2f} | P&L: ${pnl:.2f}")
        return "\n".join(lines)

    def _cmd_forcebuy(self, args: Optional[str] = None) -> str:
        if not args:
            return "❌ Usage: /buy <pair> [volume]"
        parts = args.strip().split()
        pair = parts[0].upper()
        vol = float(parts[1]) if len(parts) > 1 else None
        result = self.bot.execute_trade(1, volume=vol)
        if result.get("success"):
            return f"✅ Buy order placed for {pair}: {result}"
        return f"❌ Buy failed: {result.get('error', 'Unknown')}"

    def _cmd_forcesell(self, args: Optional[str] = None) -> str:
        if not args:
            # Close all positions
            results = []
            try:
                positions = self.bot.exchange.get_open_positions(self.bot.symbol)
                for p in positions:
                    ticket = p.get("ticket") or p.get("id")
                    if ticket:
                        r = self.bot.close_position(ticket)
                        results.append(str(r))
            except Exception as e:
                return f"❌ Sell error: {e}"
            return "✅ Closed positions:\n" + "\n".join(results)
        try:
            ticket = int(args.strip())
            result = self.bot.close_position(ticket)
            if result.get("success"):
                return f"✅ Position {ticket} closed."
            return f"❌ Close failed: {result.get('error', 'Unknown')}"
        except ValueError:
            return f"❌ Invalid ticket: {args}"

    def _cmd_delete(self, args: Optional[str] = None) -> str:
        """Delete a specific trade from the database — use with caution."""
        return "❌ Command not available. Use forcesell to close positions."

    def _cmd_reload(self) -> str:
        try:
            self.bot.strategies = __import__("src.strategy.interface",
                                              fromlist=["create_strategies_from_config"]
                                              ).create_strategies_from_config(self.bot.config)
            return "✅ Strategies reloaded."
        except Exception as e:
            return f"❌ Reload error: {e}"

    def _cmd_show_config(self) -> str:
        cfg = self.bot.config.to_dict()
        lines = ["⚙️ <b>Config</b>"]
        for section, keys in cfg.items():
            if isinstance(keys, dict):
                for k, v in keys.items():
                    if isinstance(v, (str, int, float, bool)):
                        lines.append(f"• {section}.{k} = {v}")
        return "\n".join(lines[-50:])  # limit output

    def _cmd_help(self) -> str:
        return (
            "🤖 <b>Available Commands</b>\n"
            "/start — Start auto trading\n"
            "/stop — Stop auto trading\n"
            "/status — Bot status\n"
            "/balance — Account balance\n"
            "/profit — Profit summary\n"
            "/daily — Daily stats\n"
            "/trades — Recent trades\n"
            "/positions — Open positions\n"
            "/buy <pair> [vol] — Force buy\n"
            "/sell [ticket] — Force sell (all or by ticket)\n"
            "/show_config — Show current config\n"
            "/reload — Reload strategies\n"
            "/help — This message"
        )

    # ── Legacy helper methods ─────────────────────────────────

    def send_trade_alert(self, symbol: str, action: str, price: float,
                          strategy: str, regime: str) -> None:
        msg = (
            f"🤖 <b>Trade Alert</b>\n"
            f"📊 {symbol}\n"
            f"⚡ {action}\n"
            f"💰 {price:.2f}\n"
            f"🧠 {strategy}\n"
            f"📈 {regime}"
        )
        self.broadcast(msg)

    def send_daily_report(self, summary: Dict[str, Any]) -> None:
        msg = (
            f"📈 <b>Daily Report</b>\n"
            f"Trades: {summary.get('daily_trades', 0)}\n"
            f"Return: {summary.get('total_profit', 0):.2f}\n"
            f"Win Rate: {summary.get('win_rate', 0):.1f}%\n"
            f"Drawdown: {summary.get('max_drawdown', 0):.1f}%\n"
            f"Balance: ${summary.get('current_balance', 0):.2f}"
        )
        self.broadcast(msg)

    def send_status(self, status: Dict[str, Any]) -> None:
        lines = [f"🤖 <b>Bot Status</b>"]
        for k, v in status.items():
            if isinstance(v, float):
                lines.append(f"• {k}: {v:.2f}")
            else:
                lines.append(f"• {k}: {v}")
        self.broadcast("\n".join(lines))
