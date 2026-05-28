"""Settings repository — wraps SettingsMixin for config persistence."""

from typing import Any, Dict, Optional

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

    def find_all(self) -> BotConfig:
        """Get all settings as a BotConfig domain model.

        Sections that don't map to a specific config sub-model are
        stored in ``BotConfig.raw``.
        """
        raw = self._db.get_all_settings()
        return self._raw_to_config(raw)

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

    def find(self, section: str, key_name: str) -> Optional[Dict]:
        """Get a single setting by section + key."""
        return self._db.get_setting(section, key_name)

    def find_value(self, section: str, key_name: str, default: Any = None) -> Any:
        """Get the value of a single setting, or default if not found."""
        setting = self.find(section, key_name)
        if setting:
            return setting.get("value", default)
        return default

    # ── Write ──

    def set(self, section: str, key_name: str, value: Any) -> bool:
        """Update or insert a setting."""
        return self._db.set_setting(section, key_name, value)

    def set_many(self, settings: Dict[str, Dict[str, Any]]) -> bool:
        """Bulk update settings from a nested dict: {section: {key: value}}."""
        try:
            for section, keys in settings.items():
                if isinstance(keys, dict):
                    for key_name, value in keys.items():
                        self._db.set_setting(section, key_name, value)
            return True
        except Exception as e:
            logger.error(f"Bulk settings save failed: {e}")
            return False
