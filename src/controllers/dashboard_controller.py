"""Dashboard controller — provides a clean API for the Streamlit dashboard.

The dashboard controller decouples the UI from the trading bot internals.
Dashboard pages call this controller instead of importing TradingBot or DB directly.

Implements ``IDashboardController`` interface so pages can depend on the
abstract contract rather than the concrete class.

Usage:
    ctrl = DashboardController()
    status = ctrl.get_status()
    trades = ctrl.get_trade_history()
"""

from typing import Any, Dict, List, Optional

from src.configuration.manager import ConfigManager
from src.models.backtest import HyperoptResult
from src.models.config import BotConfig
from src.controllers.dashboard_interface import IDashboardController
from src.repositories.analytics_repo import AnalyticsRepository
from src.repositories.trade_repo import TradeRepository
from src.repositories.settings_repo import SettingsRepository
from src.persistence.database import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DashboardController(IDashboardController):
    """Clean API for Streamlit dashboard — no direct bot or DB imports in pages.

    Implements :class:`IDashboardController` interface.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager(db=get_db())
        self._db = get_db()
        self.analytics_repo = AnalyticsRepository(self._db)
        self.trade_repo = TradeRepository(self._db)
        self.settings_repo = SettingsRepository(self._db)

    # ── Bot Status ──

    def get_status(self, bot=None) -> Dict:
        """Get combined status from bot and config."""
        status = {}
        if bot:
            try:
                status.update(bot.status())
            except Exception as e:
                logger.warning(f"Bot status failed: {e}")
        status.update({
            "symbol": self.config.get("general", "symbol"),
            "timeframe": self.config.get("general", "timeframe"),
            "trading_mode": self.config.get("trading", "mode"),
            "paper_trading": self.config.get("trading", "mode") in ("paper", "dry-run"),
        })
        return status

    # ── Trade History ──

    def get_trade_history(self, limit: int = 500) -> List[Dict]:
        trades = self.trade_repo.find_all(limit=limit)
        return [t.to_dict() for t in trades]

    def get_open_trades(self) -> List[Dict]:
        trades = self.trade_repo.find_open()
        return [t.to_dict() for t in trades]

    def get_trade_summary(self, days: int = 7) -> Dict:
        return self.trade_repo.summary(days=days)

    # ── Equity & Performance ──

    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        return self.analytics_repo.get_equity_curve(days=days)

    def get_best_hyperopt_params(self, strategy_name: str) -> Optional[HyperoptResult]:
        return self.analytics_repo.find_best_hyperopt_params(strategy_name)

    def get_all_hyperopt_results(self) -> List[HyperoptResult]:
        return self.analytics_repo.find_all_hyperopt_results()

    def get_ml_training_log(self, limit: int = 20) -> List[Dict]:
        """Get recent ML training runs from ml_training_log table."""
        return self.analytics_repo.get_ml_training_log(limit=limit)

    def check_concept_drift(self, threshold_pct: float = 5.0) -> Dict:
        """Check if latest training accuracy dropped >threshold_pct vs avg of previous 3 runs."""
        return self.analytics_repo.check_concept_drift(threshold_pct=threshold_pct)

    # ── Settings ──

    def get_all_settings(self) -> BotConfig:
        return self.settings_repo.find_all()

    def set_setting(self, section: str, key: str, value: Any) -> bool:
        return self.settings_repo.set(section, key, value)
