"""
Configuration manager.

All configuration values are stored in the database's ``settings`` table.
The seeder (``seed_settings()``) inserts all defaults on first run.
**No hardcoded fallback values — everything comes from the DB.**

ConfigManager auto-connects to MySQL via ``get_db()`` and **fails fast**
if the database is unavailable. No config.json fallback.

If you need to migrate from config.json, run::

    python migrate_config_to_db.py

Usage::
    config = ConfigManager()
    val = config.get("risk_management", "position_size_pct")
    config.set("risk_management", "position_size_pct", 5.0)
    config.save()
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional

from src.constants.timeframes import TIMEFRAME_MAP  # noqa: F401
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Re-export for convenience
TIMEFRAME_MAP = TIMEFRAME_MAP


class ConfigManager:
    """Centralised configuration manager — **DB only**, no file fallback.

    All defaults come from the database seed (``SETTINGS_SEED``).
    Fails immediately if the database is not available.
    """

    def __init__(self, db: Optional[Any] = None):
        self.config: Dict[str, Any] = {}
        if db is None:
            from src.persistence.database import get_db
            db = get_db()
        from src.repositories.settings_repo import SettingsRepository
        self.repository = SettingsRepository(db)
        self.load()

    # ── Load ──────────────────────────────────────────────────

    def load(self) -> Dict[str, Any]:
        """Load config from MySQL settings table. Fails fast on DB error."""
        return self._load_from_db()

    def _load_from_db(self) -> Dict[str, Any]:
        """Load config from MySQL settings table. Seeds defaults first."""
        self.repository.seed()
        bot_config = self.repository.find_all()
        db_settings = bot_config.raw
        if db_settings:
            self.config = deepcopy(db_settings)
            n_keys = sum(len(v) for v in db_settings.values())
            logger.info(f"Config loaded from DB ({n_keys} keys)")
        else:
            logger.warning("No settings found in DB — config is empty")
        return self.config

    # ── Save ──────────────────────────────────────────────────

    def save(self) -> bool:
        """Persist current config back to the database."""
        try:
            success = self.repository.set_many(self.config)
            if success:
                logger.info("Config saved to DB")
            return success
        except Exception as e:
            logger.error(f"Failed to save config to DB: {e}")
            return False

    # ── Get / Set / Update ────────────────────────────────────

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value by key path.

        All values come from the DB seed — no hardcoded defaults.

        Example::
            config.get("risk_management", "position_size_pct")
        """
        if keys and not isinstance(keys[-1], str):
            *keys, default = keys
        val: Any = self.config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return default
            else:
                return default
        return val

    def set(self, *args: Any) -> bool:
        """Set nested config value. Last arg = value, prior args = keys.

        Example::
            config.set("risk_management", "position_size_pct", 5.0)
        """
        if len(args) < 2:
            return False
        *keys, value = args
        section = self.config
        for k in keys[:-1]:
            if k not in section or not isinstance(section[k], dict):
                section[k] = {}
            section = section[k]
        section[keys[-1]] = value
        return True

    def update(self, updates: Dict[str, Any]) -> bool:
        """Apply a nested dict of updates."""
        self._deep_merge(self.config, updates)
        return True

    def reset_to_defaults(self) -> None:
        """Reset all values to factory defaults by re-seeding from DB."""
        self._db.seed_settings()
        db_settings = self._db.get_all_settings()
        if db_settings:
            self.config = deepcopy(db_settings)
            logger.info("Config reset to DB defaults")
        else:
            self.config = {}

    def to_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the entire config dict."""
        return deepcopy(self.config)

    # ── Convenience ───────────────────────────────────────────

    def get_timeframe_mt5(self) -> int:
        tf = self.get("general", "timeframe")
        return TIMEFRAME_MAP.get(tf, 15)

    def get_strategy_params(self, name: str) -> Dict[str, Any]:
        return self.get("strategies", name) or {}

    def is_strategy_enabled(self, name: str) -> bool:
        return bool(self.get("strategies", name, "enabled"))

    # ── Merge ─────────────────────────────────────────────────

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)

    # ── Validation ────────────────────────────────────────────

    def validate(self) -> List[str]:
        """Validate config values. Returns list of error/warning messages."""
        errors: List[str] = []

        symbol = self.get("general", "symbol")
        if not symbol or not isinstance(symbol, str):
            errors.append("general.symbol: must be a non-empty string")

        tf = self.get("general", "timeframe")
        if tf and tf not in TIMEFRAME_MAP:
            errors.append(f"general.timeframe: '{tf}' invalid")

        pos_size = self.get("risk_management", "position_size_pct")
        if pos_size is not None and not (0.01 <= pos_size <= 100):
            errors.append(f"risk_management.position_size_pct: {pos_size} out of range")

        max_dd = self.get("risk_management", "max_drawdown_pct")
        if max_dd is not None and not (0.1 <= max_dd <= 100):
            errors.append(f"risk_management.max_drawdown_pct: {max_dd} out of range")

        max_loss = self.get("risk_management", "max_daily_loss_pct")
        if max_loss is not None and not (0.1 <= max_loss <= 100):
            errors.append(f"risk_management.max_daily_loss_pct: {max_loss} out of range")

        sl = self.get("risk_management", "stop_loss_pct")
        if sl is not None and not (0.01 <= sl <= 50):
            errors.append(f"risk_management.stop_loss_pct: {sl} out of range")

        tp = self.get("risk_management", "take_profit_pct")
        if tp is not None and not (0.01 <= tp <= 100):
            errors.append(f"risk_management.take_profit_pct: {tp} out of range")

        max_pos = self.get("risk_management", "max_open_positions")
        if max_pos is not None and not (1 <= max_pos <= 100):
            errors.append(f"risk_management.max_open_positions: {max_pos} out of range")

        model = self.get("ml", "model_type")
        valid = {"random_forest", "gradient_boosting", "lstm"}
        if model and model not in valid:
            errors.append(f"ml.model_type: '{model}' not in {valid}")

        bt_bal = self.get("backtest", "initial_balance")
        if bt_bal is not None and bt_bal <= 0:
            errors.append("backtest.initial_balance: must be positive")

        tg_enabled = self.get("notifications", "telegram_enabled")
        if tg_enabled:
            if not self.get("notifications", "telegram_bot_token"):
                errors.append("telegram_bot_token required when telegram_enabled=True")
            if not self.get("notifications", "telegram_chat_id"):
                errors.append("telegram_chat_id required when telegram_enabled=True")

        if errors:
            for e in errors:
                logger.warning(f"Config validation: {e}")
        else:
            logger.info("Config validation passed")
        return errors

    def validate_and_fix(self) -> List[str]:
        """Validate and auto-fix safe values."""
        errors = self.validate()
        fixes = []

        sl = self.get("risk_management", "stop_loss_pct")
        if sl is None or sl <= 0:
            self.set("risk_management", "stop_loss_pct", 1.0)
            fixes.append("Auto-fix: stop_loss_pct → 1.0")
        tp = self.get("risk_management", "take_profit_pct")
        if tp is None or tp <= 0:
            self.set("risk_management", "take_profit_pct", 2.0)
            fixes.append("Auto-fix: take_profit_pct → 2.0")
        ps = self.get("risk_management", "position_size_pct")
        if ps is None or ps <= 0:
            self.set("risk_management", "position_size_pct", 1.0)
            fixes.append("Auto-fix: position_size_pct → 1.0")

        if fixes:
            logger.info(f"Config auto-fixes: {fixes}")
            self.save()
        return errors + fixes
