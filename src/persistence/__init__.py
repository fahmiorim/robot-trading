"""Data persistence layer — database connection and domain-specific DB classes.

Usage:
    from src.persistence import get_db
    db = get_db()
    db.trading.log_trade({...})       # explicit domain access
    db.log_trade({...})               # legacy backward-compat (auto-delegated)
"""

from src.persistence.database import DatabaseManager, get_db

# Domain-specific DB classes
from src.persistence.trading_db import TradingDB
from src.persistence.analytics_db import AnalyticsDB
from src.persistence.settings_db import SettingsDB
from src.persistence.market_data_db import MarketDataDB
from src.persistence.risk_db import RiskDB

__all__ = [
    "DatabaseManager", "get_db",
    "TradingDB", "AnalyticsDB", "SettingsDB",
    "MarketDataDB", "RiskDB",
]
