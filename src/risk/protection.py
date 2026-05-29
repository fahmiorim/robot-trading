"""
Protection rules — inspired by Freqtrade's protections module.
Each protection is a self-contained check that prevents trading
under adverse conditions.
"""
import time
from abc import ABC, abstractmethod
from typing import List, Tuple

from src.utils.logging import get_logger

logger = get_logger(__name__)


class IProtection(ABC):
    """Abstract interface for a protection rule."""

    @abstractmethod
    def check(self, context: "ProtectionContext") -> Tuple[bool, str]:
        """Return (is_blocked, reason). True = block trading."""
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class ProtectionContext:
    """Context object holding state for protection rules to evaluate."""

    def __init__(self):
        self.last_trade_time: float = 0
        self.stoploss_hits: int = 0
        self.stoploss_window_start: float = 0
        self.consecutive_losses: int = 0
        self.open_positions: int = 0
        self.max_drawdown_pct: float = 0
        self.current_drawdown_pct: float = 0
        self.daily_trades: int = 0
        self.daily_loss_pct: float = 0
        self.last_trade_profit: float = 0


class CooldownProtection(IProtection):
    """Prevents trading too soon after the last trade."""

    def __init__(self, minutes: int):
        self._minutes = minutes

    def name(self) -> str:
        return f"Cooldown ({self._minutes}min)"

    def check(self, ctx: ProtectionContext) -> Tuple[bool, str]:
        cd_sec = self._minutes * 60
        elapsed = time.time() - ctx.last_trade_time
        if elapsed < cd_sec:
            return True, f"Cooldown: {int(cd_sec - elapsed)}s remaining"
        return False, ""


class StoplossGuard(IProtection):
    """Limits stop-loss hits within a time window."""

    def __init__(self, max_stoploss: int, window_hours: int):
        self._max = max_stoploss
        self._window = window_hours * 3600

    def name(self) -> str:
        return f"StoplossGuard ({self._max}/{self._window // 3600}h)"

    def check(self, ctx: ProtectionContext) -> Tuple[bool, str]:
        if ctx.stoploss_hits == 0:
            return False, ""

        now = time.time()
        # If the window has expired, reset the hits and the window start
        if ctx.stoploss_window_start > 0 and (now - ctx.stoploss_window_start) > self._window:
            ctx.stoploss_hits = 0
            ctx.stoploss_window_start = 0
            return False, ""

        if ctx.stoploss_hits >= self._max:
            elapsed = now - ctx.stoploss_window_start if ctx.stoploss_window_start > 0 else 0
            return True, f"Stoploss hit {ctx.stoploss_hits}x in {elapsed / 3600:.1f}h"
        return False, ""


class MaxDrawdownProtection(IProtection):
    """Stops trading when drawdown exceeds the configured limit."""

    def __init__(self, max_drawdown_pct: float):
        self._max_dd = max_drawdown_pct

    def name(self) -> str:
        return f"MaxDrawdown ({self._max_dd:.0f}%)"

    def check(self, ctx: ProtectionContext) -> Tuple[bool, str]:
        if ctx.current_drawdown_pct >= self._max_dd:
            return True, f"Drawdown {ctx.current_drawdown_pct:.1f}% >= {self._max_dd:.0f}%"
        return False, ""


class ProtectionManager:
    """Manages all protection rules and evaluates them together."""

    def __init__(self, config):
        self._protections: List[IProtection] = [
            CooldownProtection(minutes=config.get("risk_management", "cooldown_minutes")),
            StoplossGuard(max_stoploss=config.get("protection", "max_stoploss"),
                          window_hours=config.get("protection", "stoploss_window_hours")),
            MaxDrawdownProtection(max_drawdown_pct=config.get("risk_management", "max_drawdown_pct")),
        ]

    def add(self, protection: IProtection) -> None:
        self._protections.append(protection)

    def check_all(self, ctx: ProtectionContext) -> Tuple[bool, List[str]]:
        blocked = False
        reasons: List[str] = []
        for p in self._protections:
            b, r = p.check(ctx)
            if b:
                blocked = True
                reasons.append(r)
                logger.warning(f"Protection '{p.name()}': {r}")
        return blocked, reasons
