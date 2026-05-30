"""Trade domain models — pure data classes with no I/O dependencies."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from src.constants.trading import OrderSide, TradeStatus


@dataclass
class Trade:
    """Represents a single trade (opened or closed)."""

    ticket: int
    symbol: str
    side: OrderSide
    volume: float
    entry_price: float
    entry_time: datetime

    # Optional fields
    sl: Optional[float] = None
    tp: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    profit: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    strategy: Optional[str] = None
    signal_val: int = 0
    retcode: Optional[int] = None
    comment: str = ""
    paper_trade: bool = False
    magic: Optional[int] = None

    # ── Computed Properties ──

    @property
    def is_open(self) -> bool:
        return self.status == TradeStatus.OPEN

    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0 or self.volume == 0:
            return 0.0
        
        if self.exit_price is not None:
            if self.side == OrderSide.BUY:
                return (self.exit_price - self.entry_price) / self.entry_price * 100
            else:
                return (self.entry_price - self.exit_price) / self.entry_price * 100
        return 0.0

    @property
    def duration(self) -> float:
        start = self.entry_time
        now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
        end = self.exit_time or now
        return (end - start).total_seconds() / 3600

    # ── Serialisation ──

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticket': self.ticket,
            'symbol': self.symbol,
            'action': self.side.value,
            'volume': self.volume,
            'price': self.entry_price,
            'sl': self.sl,
            'tp': self.tp,
            'profit': self.profit,
            'exit_price': self.exit_price,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'status': self.status.value,
            'strategy': self.strategy,
            'signal_val': self.signal_val,
            'retcode': self.retcode,
            'comment': self.comment,
            'paper_trade': 1 if self.paper_trade else 0,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Trade":
        return cls(
            ticket=int(d.get('ticket', 0)),
            symbol=d.get('symbol', ''),
            side=OrderSide(d.get('action', 'BUY').upper()),
            volume=float(d.get('volume', 0)),
            entry_price=float(d.get('price', 0)),
            entry_time=d.get('entry_time', datetime.now()),
            sl=float(d['sl']) if d.get('sl') is not None else None,
            tp=float(d['tp']) if d.get('tp') is not None else None,
            exit_price=float(d['exit_price']) if d.get('exit_price') is not None else None,
            exit_time=d.get('exit_time'),
            profit=float(d.get('profit', 0)),
            status=TradeStatus(d.get('status', 'open')),
            strategy=d.get('strategy'),
            signal_val=int(d.get('signal_val', 0)),
            retcode=int(d['retcode']) if d.get('retcode') is not None else None,
            comment=d.get('comment', ''),
            paper_trade=bool(d.get('paper_trade', 0)),
        )


class TradeManager:
    """In-memory trade lifecycle manager. Persistence delegated to repository."""

    def __init__(self):
        self._trades: Dict[int, Trade] = {}
        self._open_trades: Dict[int, Trade] = {}

    @property
    def open_trades(self) -> List[Trade]:
        return list(self._open_trades.values())

    @property
    def closed_trades(self) -> List[Trade]:
        return [t for t in self._trades.values() if not t.is_open]

    @property
    def all_trades(self) -> List[Trade]:
        return list(self._trades.values())

    def add_trade(self, trade: Trade) -> None:
        self._trades[trade.ticket] = trade
        if trade.is_open:
            self._open_trades[trade.ticket] = trade

    def close_trade(self, ticket: int, exit_price: float, profit: float,
                    exit_time: Optional[datetime] = None) -> Optional[Trade]:
        trade = self._trades.get(ticket)
        if trade is None or not trade.is_open:
            return None
        trade.exit_price = exit_price
        trade.profit = profit
        trade.exit_time = exit_time or datetime.now()
        trade.status = TradeStatus.CLOSED
        self._open_trades.pop(ticket, None)
        return trade

    def get_trade(self, ticket: int) -> Optional[Trade]:
        return self._trades.get(ticket)

    def open_position_count(self) -> int:
        return len(self._open_trades)
