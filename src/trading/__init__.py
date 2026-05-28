"""Trading engine — signal aggregation, order management, and bot orchestration."""

from src.trading.pairlist import PairlistManager
from src.trading.engine import TradingBot
from src.trading.order_manager import OrderManager
from src.trading.lock_manager import LockManager
from src.trading.signal_aggregator import SignalAggregator
from src.trading.dca_manager import DCAManager
from src.trading.roi_manager import ROIManager

__all__ = [
    "TradingBot", "PairlistManager", "OrderManager",
    "LockManager", "SignalAggregator", "DCAManager", "ROIManager",
]
