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
from typing import Any, Dict, List, Optional, Tuple

from src.constants.timeframes import TIMEFRAME_MAP  # noqa: F401
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Re-export for convenience
TIMEFRAME_MAP = TIMEFRAME_MAP

# Context key for (symbol, timeframe) tuple
_ContextKey = Tuple[Optional[str], Optional[str]]


class ConfigManager:
    """Centralised configuration manager — **DB only**, no file fallback.

    Supports per-symbol/per-timeframe settings via context.
    When ``set_context(symbol, timeframe)`` is called, all ``get()`` calls
    will prefer context-specific overrides over global defaults.

    Usage::
        config = ConfigManager()
        config.set_context("XAUUSD", "TIMEFRAME_M15")
        val = config.get("risk_management", "stop_loss_pct")  # context-aware
        config.set("risk_management", "stop_loss_pct", 0.8)  # saved with context
    """

    def __init__(self, db: Optional[Any] = None):
        self.config: Dict[str, Any] = {}
        self._raw_settings: Dict[str, Dict[str, Dict[_ContextKey, Any]]] = {}
        self._context_symbol: Optional[str] = None
        self._context_timeframe: Optional[str] = None
        self._dirty_keys: set[Tuple[str, str]] = set()

        if db is None:
            from src.persistence.database import get_db
            db = get_db()
        from src.repositories.settings_repo import SettingsRepository
        self.repository = SettingsRepository(db)
        self.load()

    # ── Context ───────────────────────────────────────────────

    @property
    def context_symbol(self) -> Optional[str]:
        """Current symbol context (None = global)."""
        return self._context_symbol

    @property
    def context_timeframe(self) -> Optional[str]:
        """Current timeframe context (None = global)."""
        return self._context_timeframe

    def set_context(self, symbol: Optional[str], timeframe: Optional[str]) -> None:
        """Set the active symbol/timeframe context.

        After calling this, ``get()`` will prefer values saved for this
        specific context over global defaults.

        Three levels of resolution:
        1. Exact (symbol, timeframe) — highest priority
        2. Timeframe-only (None, timeframe) — applies to all symbols in this timeframe
        3. Global (None, None) — fallback default
        """
        changed = (self._context_symbol != symbol or
                    self._context_timeframe != timeframe)
        self._context_symbol = symbol
        self._context_timeframe = timeframe
        if changed:
            self._resolve_context()
            label = f"{symbol or 'GLOBAL'}/{timeframe or 'GLOBAL'}"
            logger.info(f"Config context set to: {label}")

    def set_timeframe_context(self, timeframe: Optional[str]) -> None:
        """Set context to timeframe-only mode.

        After calling this, ``get()`` will prefer values saved for this
        timeframe across ALL symbols, then fall back to global defaults.

        Useful for settings that depend on candle speed/frequency
        (e.g. cycle_interval, cooldown, data_count) but are the same
        regardless of which symbol is being traded.
        """
        changed = self._context_timeframe != timeframe
        self._context_symbol = None  # timeframe-only: no symbol binding
        self._context_timeframe = timeframe
        if changed:
            self._resolve_context()
            logger.info(f"Config context set to timeframe-only: {timeframe or 'GLOBAL'}")

    def clear_context(self) -> None:
        """Clear context — all get() calls return global defaults."""
        self.set_context(None, None)

    def _resolve_context(self) -> None:
        """Re-resolve all settings for the current context into self.config.

        Priority (highest to lowest):
        1. Exact match (symbol, timeframe)
        2. Timeframe-only (None, timeframe) — applies to all symbols in this TF
        3. Symbol-only (symbol, None) — applies to all TFs for this symbol
        4. Global default (None, None)
        """
        resolved: Dict[str, Dict[str, Any]] = {}
        ctx_key = (self._context_symbol, self._context_timeframe)
        tf_only_key = (None, self._context_timeframe)
        sym_only_key = (self._context_symbol, None)
        global_key = (None, None)

        for section, keys in self._raw_settings.items():
            for key_name, contexts in keys.items():
                # Priority: exact > timeframe-only > symbol-only > global
                if ctx_key in contexts:
                    value = contexts[ctx_key]
                elif ctx_key != tf_only_key and tf_only_key in contexts:
                    # Timeframe-only override (e.g. M15 SL applies to all symbols)
                    value = contexts[tf_only_key]
                elif ctx_key != sym_only_key and sym_only_key in contexts:
                    # Symbol-only override (e.g. EURUSD magic_number applies to all TFs)
                    value = contexts[sym_only_key]
                elif global_key in contexts:
                    value = contexts[global_key]
                else:
                    value = list(contexts.values())[0] if contexts else None
                resolved.setdefault(section, {})[key_name] = value

        self.config = resolved

    # ── Load ──────────────────────────────────────────────────

    def load(self) -> Dict[str, Any]:
        """Load config from MySQL settings table. Fails fast on DB error."""
        return self._load_from_db()

    def _load_from_db(self) -> Dict[str, Any]:
        """Load config from MySQL settings table. Seeds defaults first."""
        self.repository.seed()

        # Load all settings flat (including context info)
        flat_rows = self.repository.find_all_flat()
        raw: Dict[str, Dict[str, Dict[_ContextKey, Any]]] = {}
        for row in flat_rows:
            section = row['section']
            key_name = row['key_name']
            ctx = (row.get('symbol'), row.get('timeframe'))
            value = row['value']
            raw.setdefault(section, {}).setdefault(key_name, {})[ctx] = value
        self._raw_settings = raw

        # Resolve for current context
        self._resolve_context()

        n_keys = sum(
            len(keys) for section_keys in raw.values()
            for keys in section_keys.values()
        )
        logger.info(f"Config loaded from DB ({n_keys} total settings, "
                    f"{sum(len(v) for v in self.config.values())} resolved "
                    f"for {self._context_symbol or 'GLOBAL'}/"
                    f"{self._context_timeframe or 'GLOBAL'})")
        return self.config

    # ── Save ──────────────────────────────────────────────────

    def save(self) -> bool:
        """Persist changed settings back to the database.

        - If context is set (symbol+timeframe or timeframe-only), only saves
          settings that were explicitly changed (via ``set()``) for that context.
        - If context is global (None/None), saves all resolved settings.
        """
        try:
            if self._context_symbol is not None or self._context_timeframe is not None:
                # Context-specific save: only persist dirty (explicitly set) keys
                for section, key_name in self._dirty_keys:
                    ctx_key = (self._context_symbol, self._context_timeframe)
                    value = self._raw_settings.get(
                        section, {}
                    ).get(key_name, {}).get(ctx_key)
                    if value is not None:
                        self.repository.set(
                            section, key_name, value,
                            symbol=self._context_symbol,
                            timeframe=self._context_timeframe,
                        )
            else:
                # Global save: persist all resolved settings
                success = self.repository.set_many(
                    self.config,
                    symbol=None,
                    timeframe=None,
                )
                if not success:
                    return False

            n_saved = len(self._dirty_keys)
            self._dirty_keys.clear()
            ctx_label = f"{self._context_symbol or 'GLOBAL'}/{self._context_timeframe or 'GLOBAL'}"
            logger.info(f"Config saved to DB (context: {ctx_label}, "
                        f"{n_saved} keys saved)")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to DB: {e}")
            return False

    # ── Get / Set / Update ────────────────────────────────────

    def get(self, *keys: str, **kwargs) -> Any:
        """Get nested config value by key path.

        Returns the value resolved for the current context
        (set via ``set_context()``). Falls back to global default
        if no context-specific override exists.

        All values come from the database only. Raises ``KeyError``
        if the key does not exist — unless ``default`` is provided.

        Example::
            config.get("risk_management", "position_size_pct")
            config.get("websocket", default={})  # safe fallback
        """
        default = kwargs.pop("default", None)
        val: Any = self.config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                if default is not None:
                    return default
                raise KeyError(
                    f"Config key \"{' > '.join(keys)}\" not found in database. "
                    f"Ensure the settings table is seeded."
                )
        return val

    def set(self, *args: Any) -> bool:
        """Set nested config value. Last arg = value, prior args = keys.

        The value is saved to the current context (if set via ``set_context()``
        or ``set_timeframe_context()``) or to global defaults if context is
        not set.

        Tracks dirty keys so ``save()`` only persists what changed.

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

        # Update raw cache with context
        ctx_key = (self._context_symbol, self._context_timeframe)
        if len(keys) >= 1:
            section_name = keys[0]
            key_name = keys[-1]
            self._raw_settings.setdefault(
                section_name, {}
            ).setdefault(key_name, {})[ctx_key] = value
            self._dirty_keys.add((section_name, key_name))

        return True

    def set_global(self, *args: Any) -> bool:
        """Set a config value that is ALWAYS saved to global context,
        regardless of the current symbol/timeframe context.

        The value is persisted to DB immediately (bypasses dirty-key tracking)
        and written into the raw cache under the global (None, None) key.

        Use this for settings that should NOT be tied to any symbol/timeframe
        — they remain the same everywhere.

        Example::
            config.set_global("exchange", "type", "mt5")
            config.set_global("signals", "use_ml", True)
        """
        if len(args) < 2:
            return False
        *keys, value = args

        # Update in-memory config
        section = self.config
        for k in keys[:-1]:
            if k not in section or not isinstance(section[k], dict):
                section[k] = {}
            section = section[k]
        section[keys[-1]] = value

        # Update raw cache under global context (None, None)
        if len(keys) >= 1:
            section_name = keys[0]
            key_name = keys[-1]
            self._raw_settings.setdefault(
                section_name, {}
            ).setdefault(key_name, {})[(None, None)] = value

        # Persist immediately to DB as global
        try:
            self.repository.set(
                keys[0], keys[-1], value,
                symbol=None,
                timeframe=None,
            )
            logger.info(f"Global config saved immediately: {keys[0]}.{keys[-1]} = {value!r}")
            return True
        except Exception as e:
            logger.error(f"Failed to save global config {keys[0]}.{keys[-1]}: {e}")
            return False

    def update(self, updates: Dict[str, Any]) -> bool:
        """Apply a nested dict of updates."""
        self._deep_merge(self.config, updates)
        return True

    def reset_to_defaults(self) -> None:
        """Reset all values to factory defaults by re-seeding from DB.

        Deletes all context-specific overrides from DB and reloads only global defaults.
        """
        self.repository.delete_all_context_overrides()
        self.repository.seed()
        # Load only global defaults from DB
        global_rows = self._load_all_global_settings()
        self._raw_settings = global_rows
        self._dirty_keys.clear()
        self._resolve_context()
        logger.info("Config reset to DB defaults (context overrides deleted)")

    def _reload_settings_from_db(self) -> None:
        """Reload all settings from DB into in-memory cache."""
        flat_rows = self.repository.find_all_flat()
        raw: Dict[str, Dict[str, Dict[_ContextKey, Any]]] = {}
        for row in flat_rows:
            section = row['section']
            key_name = row['key_name']
            ctx = (row.get('symbol'), row.get('timeframe'))
            raw.setdefault(section, {}).setdefault(key_name, {})[ctx] = row['value']
        self._raw_settings = raw
        self._dirty_keys.clear()
        self._resolve_context()

    def reset_timeframe_overrides(self, timeframe: str) -> None:
        """Reset all overrides for a specific timeframe back to global defaults.

        Deletes all DB rows where timeframe=%s (both timeframe-only and
        symbol-specific overrides), re-seeds defaults, then reloads the
        in-memory cache so the UI reflects the reset state immediately.
        """
        self.repository.delete_timeframe_overrides(timeframe)
        self.repository.seed()
        self._reload_settings_from_db()
        logger.info(f"Config reset: all overrides for {timeframe} deleted (reverted to global defaults)")

    def reset_global_defaults(self) -> None:
        """Reset all global defaults back to factory values from schema.sql.

        Deletes all rows where symbol='' AND timeframe='' (global defaults),
        re-seeds fresh factory defaults, then reloads everything from DB.
        Context-specific overrides (TF/symbol) are NOT affected.
        """
        self.repository.delete_global_defaults()
        self.repository.seed()
        self._reload_settings_from_db()
        logger.info("Config reset: global defaults reverted to factory values (TF overrides preserved)")
        logger.info("Config reset: global defaults reverted to factory values (TF overrides preserved)")

    def _load_all_global_settings(self) -> Dict[str, Dict[str, Dict[_ContextKey, Any]]]:
        """Load only global (NULL context) settings from DB into raw structure."""
        flat_rows = self.repository.find_all_flat()
        raw: Dict[str, Dict[str, Dict[_ContextKey, Any]]] = {}
        for row in flat_rows:
            section = row['section']
            key_name = row['key_name']
            ctx = (row.get('symbol'), row.get('timeframe'))
            # Only keep global defaults
            if ctx == (None, None):
                raw.setdefault(section, {}).setdefault(key_name, {})[ctx] = row['value']
        return raw

    def to_dict(self) -> Dict[str, Any]:
        """Return a deep copy of the entire config dict."""
        return deepcopy(self.config)

    # ── Convenience ───────────────────────────────────────────

    def get_timeframe_mt5(self) -> int:
        tf = self.get("general", "timeframe")
        if tf not in TIMEFRAME_MAP:
            raise ValueError(f"Unknown timeframe '{tf}'; valid: {list(TIMEFRAME_MAP)}")
        return TIMEFRAME_MAP[tf]

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
        valid = {"random_forest", "gradient_boosting"}
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
        """Validate config — reports errors instead of auto-fixing missing/invalid values.

        All config values must come from the database seed — no silent fallbacks.
        """
        errors = self.validate()

        sl = self.get("risk_management", "stop_loss_pct")
        if sl is None or sl <= 0:
            errors.append(
                "risk_management.stop_loss_pct: missing or invalid — "
                "must be provided by DB seed data"
            )
        tp = self.get("risk_management", "take_profit_pct")
        if tp is None or tp <= 0:
            errors.append(
                "risk_management.take_profit_pct: missing or invalid — "
                "must be provided by DB seed data"
            )
        ps = self.get("risk_management", "position_size_pct")
        if ps is None or ps <= 0:
            errors.append(
                "risk_management.position_size_pct: missing or invalid — "
                "must be provided by DB seed data"
            )

        if errors:
            for e in errors:
                logger.warning(f"Config validation: {e}")
        else:
            logger.info("Config validation passed")
        return errors
