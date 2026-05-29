"""Risk domain models — pure data classes for risk management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RiskState:
    """Current risk state of the trading bot."""
    symbol: str = ""
    initial_balance: Optional[float] = None
    current_balance: Optional[float] = None
    peak_balance: Optional[float] = None
    daily_start_balance: Optional[float] = None
    open_positions: int = 0
    drawdown_pct: float = 0.0
    daily_loss_pct: float = 0.0
    consecutive_errors: int = 0
    last_updated: Optional[datetime] = None

    @property
    def can_trade(self) -> bool:
        return self.consecutive_errors < 3


@dataclass
class DrawdownInfo:
    """Drawdown calculation result."""
    current_drawdown_pct: float = 0.0
    peak_balance: float = 0.0
    max_drawdown_pct: float = 0.0
    drawdown_start: Optional[datetime] = None
    is_in_drawdown: bool = False


@dataclass 
class ProtectionRule:
    """A single protection rule configuration."""
    name: str
    enabled: bool = True
    stop_duration_minutes: int = 60
    max_drawdown_pct: float = 5.0
    max_daily_loss_pct: float = 3.0
    cooldown_minutes: int = 120


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker trigger event."""
    reason: str
    drawdown_pct: Optional[float] = None
    balance_before: Optional[float] = None
    balance_after: Optional[float] = None
    triggered_at: datetime = None
    status: str = "active"

    def __post_init__(self):
        if self.triggered_at is None:
            self.triggered_at = datetime.now()
