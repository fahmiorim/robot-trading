"""Data access repositories — wrap persistence mixins, return domain models.

Usage:
    from src.repositories.trade_repo import TradeRepository
    from src.repositories.settings_repo import SettingsRepository
    from src.repositories.analytics_repo import AnalyticsRepository
    from src.repositories.market_data_repo import MarketDataRepository
    from src.repositories.risk_repo import RiskRepository
"""

from src.repositories.trade_repo import TradeRepository
from src.repositories.settings_repo import SettingsRepository
from src.repositories.analytics_repo import AnalyticsRepository
from src.repositories.market_data_repo import MarketDataRepository
from src.repositories.risk_repo import RiskRepository

__all__ = [
    "TradeRepository", "SettingsRepository", "AnalyticsRepository",
    "MarketDataRepository", "RiskRepository",
]
