"""Settings repository — wraps SettingsMixin for config persistence."""

from typing import Any, Dict, List, Optional

from src.models.config import BotConfig, GeneralConfig, ExchangeConfig, RiskConfig, TradingConfig, MLConfig, BacktestConfig
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SettingsRepository:
    """Repository for bot settings/configuration persistence.

    Usage:
        repo = SettingsRepository(db)
        all_settings = repo.find_all()
        repo.set("risk_management", "position_size_pct", 2.0)
    """

    def __init__(self, db):
        self._db = db

    # ── Read ──

    def seed(self) -> bool:
        """Insert default settings if table is empty."""
        return self._db.seed_settings()

    def find_all(self, symbol: Optional[str] = None,
                 timeframe: Optional[str] = None) -> BotConfig:
        """Get all settings as a BotConfig domain model, optionally resolved for context.

        If symbol/timeframe are provided, context-specific overrides take priority.
        """
        raw = self._db.get_all_settings(symbol=symbol, timeframe=timeframe)
        return self._raw_to_config(raw)

    def find_all_flat(self) -> List[Dict[str, Any]]:
        """Get ALL settings rows including context info (flat list).

        Used by ConfigManager for context-aware in-memory caching.
        """
        return self._db.get_all_settings_flat()

    @staticmethod
    def _section_to_subconfig(section: str, values: Dict[str, Any]):
        """Map a DB settings section to a typed config sub-model."""
        mapping = {
            "general": GeneralConfig,
            "exchange": ExchangeConfig,
            "risk_management": RiskConfig,
            "trading": TradingConfig,
            "ml": MLConfig,
            "backtest": BacktestConfig,
        }
        cls = mapping.get(section)
        if cls is None:
            return None  # unmapped section, stored in raw
        # Filter to only valid kwargs for the sub-model
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in values.items() if k in valid_keys}
        return cls(**filtered)

    @staticmethod
    def _raw_to_config(raw: Dict[str, Dict[str, Any]]) -> BotConfig:
        """Convert raw nested settings dict to a BotConfig domain model."""
        config_kwargs = {"raw": dict(raw)}
        for section, values in raw.items():
            sub = SettingsRepository._section_to_subconfig(section, values)
            if sub is not None:
                # Map DB section names to BotConfig field names
                field_map = {
                    "risk_management": "risk",
                }
                field_name = field_map.get(section, section)
                config_kwargs[field_name] = sub
        return BotConfig(**config_kwargs)

    def find(self, section: str, key_name: str,
              symbol: Optional[str] = None,
              timeframe: Optional[str] = None) -> Optional[Dict]:
        """Get a single setting by section + key + optional context."""
        return self._db.get_setting(section, key_name, symbol=symbol, timeframe=timeframe)

    # ── Write ──

    def set(self, section: str, key_name: str, value: Any,
            symbol: Optional[str] = None,
            timeframe: Optional[str] = None) -> bool:
        """Update or insert a setting with optional symbol/timeframe context."""
        return self._db.set_setting(section, key_name, value, symbol=symbol, timeframe=timeframe)

    def set_many(self, settings: Dict[str, Dict[str, Any]],
                  symbol: Optional[str] = None,
                  timeframe: Optional[str] = None) -> bool:
        """Bulk update settings from a nested dict: {section: {key: value}}.

        If symbol/timeframe are provided, all settings are saved with that context.
        """
        try:
            for section, keys in settings.items():
                if isinstance(keys, dict):
                    for key_name, value in keys.items():
                        self._db.set_setting(section, key_name, value,
                                             symbol=symbol, timeframe=timeframe)
            return True
        except Exception as e:
            logger.error(f"Bulk settings save failed: {e}")
            return False

    def delete_all_context_overrides(self) -> bool:
        """Delete all context-specific settings (non-global) from DB.

        Only keeps rows where symbol='' AND timeframe='' (global defaults).
        """
        return self._db.delete_all_context_overrides()

    def delete_timeframe_overrides(self, timeframe: str) -> bool:
        """Delete all overrides for a specific timeframe.

        Removes both timeframe-only overrides (symbol='') and
        symbol-specific overrides for that timeframe.
        """
        return self._db.delete_timeframe_overrides(timeframe)

    def delete_global_defaults(self) -> bool:
        """Delete all global default settings from DB.

        Removes only rows where symbol='' AND timeframe='' (global defaults).
        Context-specific overrides are preserved.
        """
        return self._db.delete_global_defaults()
