"""Trading engine — signal aggregation, order management, and bot orchestration."""

from src.services.trading.engine import TradingBot
from src.services.trading.order_manager import OrderManager
from src.services.trading.lock_manager import LockManager
from src.services.trading.signal_aggregator import SignalAggregator
from src.services.trading.dca_manager import DCAManager
from src.services.trading.roi_manager import ROIManager

__all__ = [
    "TradingBot", "OrderManager",
    "LockManager", "SignalAggregator", "DCAManager", "ROIManager",
]
