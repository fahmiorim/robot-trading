"""Signal domain models — pure data classes for trading signals."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.constants.trading import SignalType, SIGNAL_LABELS


@dataclass
class SignalResult:
    """Result from a single signal source (strategy, ML, agent, swarm)."""

    source: str
    signal: SignalType        # BUY=1, SELL=-1, HOLD=0
    confidence: float = 0.0   # 0.0 – 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def label(self) -> str:
        return SIGNAL_LABELS.get(self.signal, "UNKNOWN")

    @property
    def is_bullish(self) -> bool:
        return self.signal == SignalType.BUY

    @property
    def is_bearish(self) -> bool:
        return self.signal == SignalType.SELL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "signal": self.signal,
            "label": self.label,
            "confidence": self.confidence,
            "metadata": self.metadata or {},
        }


@dataclass
class AggregatedSignal:
    """Final consensus signal after merging multiple sources."""

    signal: SignalType
    buy_votes: int = 0
    sell_votes: int = 0
    hold_votes: int = 0
    total_votes: int = 0
    buy_ratio: float = 0.0
    sell_ratio: float = 0.0
    details: List[SignalResult] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []

    @property
    def label(self) -> str:
        return SIGNAL_LABELS.get(self.signal, "UNKNOWN")


@dataclass
class SignalLogEntry:
    """A signal logged to the database."""
    symbol: str
    timestamp: datetime
    source: str
    signal_val: int
    regime: Optional[str] = None
    price: Optional[float] = None
    details: Optional[Dict] = None
