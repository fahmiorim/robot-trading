"""
Risk manager — tracks balance, drawdown, daily loss, position limits.
Extracted from the TradingBot class for single responsibility.
"""
import time
from datetime import datetime, date
from typing import Any, Dict, Optional

from src.risk.protection import ProtectionContext, ProtectionManager
from src.models.trade import TradeManager
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RiskManager:
    """Centralised risk management — balance tracking, drawdown, position limits."""

    def __init__(self, config):
        self.config = config
        self.protection_mgr = ProtectionManager(config)
        self.protection_ctx = ProtectionContext()

        # Risk state
        self.initial_balance: float = config.get("trading", "paper_initial_balance")
        self.peak_balance: float = self.initial_balance
        self.daily_start_balance: float = self.initial_balance
        self.current_balance: float = self.initial_balance
        self.daily_loss_pct: float = 0.0
        self.consecutive_errors: int = 0
        self._max_drawdown_pct_ever: float = 0.0
        self._last_trade_time: float = 0
        self._last_date = date.today()

        # Load state from DB if available
        self._load_state()

    def _load_state(self):
        """Load persistent risk state from database."""
        try:
            from src.persistence.database import get_db
            db = get_db()
            state = db.load_risk_state()
            if state:
                if state.get("initial_balance"):
                    self.initial_balance = state["initial_balance"]
                if state.get("peak_balance"):
                    self.peak_balance = state["peak_balance"]
                if state.get("daily_start_balance"):
                    self.daily_start_balance = state["daily_start_balance"]

                # Check when the state was last updated to ensure correct day comparison
                last_updated = state.get("last_updated")
                if isinstance(last_updated, datetime):
                    self._last_date = last_updated.date()

                logger.info(f"Persistent risk state loaded: peak={self.peak_balance:.2f}")
        except Exception as e:
            logger.warning(f"Failed to load persistent risk state: {e}")

    def _save_state(self):
        """Save persistent risk state to database."""
        try:
            from src.persistence.database import get_db
            db = get_db()
            db.save_risk_state(
                symbol=self.config.get("general", "symbol"),
                initial_balance=self.initial_balance,
                peak_balance=self.peak_balance,
                daily_start_balance=self.daily_start_balance
            )
        except Exception as e:
            logger.warning(f"Failed to save persistent risk state: {e}")

    def update_balance(self, balance: float) -> None:
        """Update balance tracking and recalculate risk metrics."""
        self.current_balance = balance
        changed = False

        if balance > self.peak_balance:
            self.peak_balance = balance
            changed = True

        # Daily start balance reset at midnight
        if self._is_new_day():
            self.daily_start_balance = balance
            self.daily_loss_pct = 0.0
            changed = True

        # Daily loss % since start of day
        if self.daily_start_balance > 0:
            self.daily_loss_pct = max(
                0, (self.daily_start_balance - balance) / self.daily_start_balance * 100
            )

        # Update protection context
        drawdown = self.get_drawdown_pct()
        self.protection_ctx.current_drawdown_pct = drawdown
        self.protection_ctx.max_drawdown_pct = max(
            self.protection_ctx.max_drawdown_pct, drawdown
        )

        if changed:
            self._save_state()

    def get_drawdown_pct(self) -> float:
        """Return current drawdown as percentage from peak."""
        if self.peak_balance <= 0:
            return 0.0
        return max(0, (self.peak_balance - self.current_balance) / self.peak_balance * 100)

    def get_max_drawdown_pct(self) -> float:
        """Return maximum drawdown seen so far."""
        return max(self._max_drawdown_pct_ever, self.get_drawdown_pct())

    def can_open_new_position(self, trade_manager: TradeManager) -> bool:
        """Check if we can open a new position based on risk rules."""
        max_positions = self.config.get("risk_management", "max_open_positions")
        if trade_manager.open_position_count() >= max_positions:
            logger.warning(f"Max positions ({max_positions}) reached")
            return False

        max_dd = self.config.get("risk_management", "max_drawdown_pct")
        if self.get_drawdown_pct() >= max_dd:
            logger.warning(f"Max drawdown ({max_dd:.0f}%) reached")
            return False

        max_daily_loss = self.config.get("risk_management", "max_daily_loss_pct")
        if self.daily_loss_pct >= max_daily_loss:
            logger.warning(f"Max daily loss ({max_daily_loss:.0f}%) reached")
            return False

        # Check protection rules
        blocked, reasons = self.protection_mgr.check_all(self.protection_ctx)
        if blocked:
            for r in reasons:
                logger.warning(f"Protection blocked: {r}")
            return False

        return True

    def record_trade(self, profit: float) -> None:
        """Update risk state after a trade is closed."""
        self._last_trade_time = time.time()
        self.protection_ctx.last_trade_time = self._last_trade_time
        self.protection_ctx.last_trade_profit = profit

        if profit < 0:
            self.protection_ctx.consecutive_losses += 1
            self.protection_ctx.stoploss_hits += 1
            if self.protection_ctx.stoploss_window_start == 0:
                self.protection_ctx.stoploss_window_start = self._last_trade_time
        else:
            self.protection_ctx.consecutive_losses = 0

    def get_state(self) -> Dict[str, Any]:
        """Return current risk state as a dict for status/display."""
        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "peak_balance": self.peak_balance,
            "drawdown_pct": round(self.get_drawdown_pct(), 2),
            "max_drawdown_pct": round(self.get_max_drawdown_pct(), 2),
            "daily_loss_pct": round(self.daily_loss_pct, 2),
            "open_positions": self.protection_ctx.open_positions,
            "consecutive_errors": self.consecutive_errors,
            "consecutive_losses": self.protection_ctx.consecutive_losses,
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """Comprehensive risk summary for dashboard display.

        Returns all keys from get_state() plus:
          can_trade, can_trade_reason, circuit_breaker_active,
          circuit_breaker_reason, daily_trades, window_loss_pct.
        """
        state = self.get_state()

        # Check protection rules
        blocked, reasons = self.protection_mgr.check_all(self.protection_ctx)

        # Determine can_trade from risk limits
        can_trade = True
        reasons_list: list[str] = []

        max_positions = self.config.get("risk_management", "max_open_positions")
        if self.protection_ctx.open_positions >= max_positions:
            reasons_list.append(f"Max positions ({max_positions}) reached")
            can_trade = False

        max_dd = self.config.get("risk_management", "max_drawdown_pct")
        if state.get("drawdown_pct", 0) >= max_dd:
            reasons_list.append(f"Max drawdown ({max_dd:.0f}%)")
            can_trade = False

        max_daily = self.config.get("risk_management", "max_daily_loss_pct")
        if state.get("daily_loss_pct", 0) >= max_daily:
            reasons_list.append(f"Max daily loss ({max_daily:.0f}%)")
            can_trade = False

        if blocked:
            can_trade = False
            reasons_list.extend(reasons)

        result = dict(state)
        result.update({
            "can_trade": can_trade,
            "can_trade_reason": " | ".join(reasons_list),
            "circuit_breaker_active": blocked,
            "circuit_breaker_reason": "; ".join(reasons) if blocked else "",
            "daily_trades": self.protection_ctx.daily_trades,
            "window_loss_pct": round(
                max(0, self.daily_loss_pct) if self._last_trade_time > 0 else 0, 2
            ),
        })
        return result

    def _is_new_day(self) -> bool:
        """Check if a new calendar day has started."""
        today = date.today()
        if not hasattr(self, "_last_date"):
            self._last_date = today
            return False
        if today != self._last_date:
            self._last_date = today
            return True
        return False
