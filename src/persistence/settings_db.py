"""Settings database operations — settings CRUD from MySQL."""

import json
from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


# ── Settings Seed ─────────────────────────────────────────────

SETTINGS_SEED = {
    "general": {
        "symbol": ("string", "XAUUSD", "Trading symbol"),
        "timeframe": ("string", "TIMEFRAME_M1", "Chart timeframe"),
        "auto_trade": ("bool", "false", "Enable auto trading"),
        "data_count": ("int", "2000", "Candles to fetch"),
        "magic_number": ("int", "2024", "MT5 magic number"),
        "cycle_interval_minutes": ("int", "1", "Minutes between auto cycles"),
    },
    "strategies": {
        "MA_Crossover": ("json", '{"enabled": true, "fast_period": 30, "slow_period": 54}', ""),
        "RSI": ("json", '{"enabled": true, "period": 9, "overbought": 85, "oversold": 15}', ""),
        "MACD": ("json", '{"enabled": true, "fast": 20, "slow": 38, "signal": 13}', ""),
        "Bollinger": ("json", '{"enabled": true, "period": 10, "std_dev": 1.74}', ""),
        "Breakout": ("json", '{"enabled": true, "lookback": 38}', ""),
    },
    "risk_management": {
        "position_size_pct": ("float", "5.0", ""),
        "max_daily_loss_pct": ("float", "5.0", ""),
        "max_drawdown_pct": ("float", "15.0", ""),
        "max_open_positions": ("int", "3", ""),
        "cooldown_minutes": ("int", "1", ""),
        "stop_loss_pct": ("float", "0.5", ""),
        "take_profit_pct": ("float", "1.0", ""),
        "use_trailing_stop": ("bool", "false", ""),
        "trailing_stop_activation_pct": ("float", "1.0", ""),
        "trailing_stop_distance_pct": ("float", "0.5", ""),
        "circuit_breaker_enabled": ("bool", "true", ""),
        "circuit_breaker_loss_pct": ("float", "10.0", ""),
        "circuit_breaker_window_minutes": ("int", "60", ""),
        "circuit_breaker_cooldown_minutes": ("int", "120", ""),
    },
    "backtest": {
        "initial_balance": ("int", "10000", ""),
        "commission_pct": ("float", "0.1", ""),
        "slippage_pct": ("float", "0.05", ""),
        "position_sizing": ("string", "fixed_pct", ""),
    },
    "signals": {
        "use_ml": ("bool", "false", ""),
        "use_agent": ("bool", "false", ""),
        "use_swarm": ("bool", "false", ""),
        "consensus_buy_threshold": ("float", "0.3", ""),
        "consensus_sell_threshold": ("float", "-0.3", ""),
    },
    "trading": {
        "mode": ("string", "live", "live, paper, or dry-run"),
        "paper_trading": ("bool", "false", ""),
        "paper_initial_balance": ("float", "10000.0", ""),
        "strategy_pre_validation": ("bool", "true", ""),
        "min_backtest_trades": ("int", "5", ""),
        "min_win_rate": ("float", "15.0", ""),
        "max_backtest_drawdown": ("float", "30.0", ""),
        "max_consecutive_losses": ("int", "5", ""),
    },
    "health_check": {
        "enabled": ("bool", "true", ""),
        "check_interval_seconds": ("int", "60", ""),
        "max_consecutive_errors": ("int", "10", ""),
        "max_idle_minutes": ("int", "30", ""),
        "auto_restart": ("bool", "true", ""),
    },
    "notifications": {
        "telegram_enabled": ("bool", "false", ""),
        "telegram_bot_token": ("string", "", ""),
        "telegram_chat_id": ("string", "", ""),
        "notify_on_trade": ("bool", "true", ""),
        "notify_daily_report": ("bool", "true", ""),
    },
    "strategy_weights": {
        "trending": ("json", '{"MA_Crossover": 1.0, "Breakout": 0.8, "RSI": 0.5, "MACD": 0.4, "Bollinger": 0.2}', ""),
        "ranging": ("json", '{"Bollinger": 1.0, "RSI": 1.0, "Breakout": 0.4, "MA_Crossover": 0.3, "MACD": 0.3}', ""),
        "choppy": ("json", '{"RSI": 1.0, "Bollinger": 0.9, "MACD": 0.5, "MA_Crossover": 0.3, "Breakout": 0.1}', ""),
    },
    "edge": {
        "enabled": ("bool", "false", "Kelly / position sizing"),
        "sizing_method": ("string", "kelly", "kelly or fixed_pct"),
        "kelly_fraction": ("float", "0.25", "Fractional Kelly (0.25 = 25%)"),
        "min_trades_for_stats": ("int", "10", ""),
        "kelly_win_loss_ratio": ("float", "2.0", ""),
        "kelly_win_rate": ("float", "55.0", ""),
        "max_position_size_pct": ("float", "10.0", ""),
    },
    "order_types": {
        "custom": ("bool", "false", "Enable custom order types"),
        "use_stop_loss_limit": ("bool", "false", ""),
        "use_oco": ("bool", "false", ""),
    },
    "roi": {
        "enabled": ("bool", "true", ""),
        "use_roi_table": ("bool", "true", ""),
        "table": ("json", '[{"minutes": 0, "roi_pct": 100}, {"minutes": 15, "roi_pct": 3.0}, {"minutes": 30, "roi_pct": 2.0}, {"minutes": 60, "roi_pct": 1.5}, {"minutes": 120, "roi_pct": 0.8}, {"minutes": 240, "roi_pct": 0.3}, {"minutes": 1440, "roi_pct": 0.1}]', ""),
    },
    "dca": {
        "enabled": ("bool", "false", ""),
        "max_dca_orders": ("int", "3", ""),
        "dca_increment_factor": ("float", "1.5", ""),
        "dca_trigger_pct": ("float", "-1.0", ""),
        "dca_cooldown_minutes": ("int", "5", ""),
        "dca_position_limit_pct": ("float", "20.0", ""),
        "dca_min_profit_pct": ("float", "0.5", ""),
    },
    "pairlist": {
        "symbols": ("json", '["XAUUSD"]', ""),
        "max_pairs": ("int", "10", ""),
        "min_price": ("float", "0.0", ""),
        "max_price": ("float", "100000.0", ""),
        "min_volume": ("int", "1000", ""),
        "sort_by": ("string", "volume", ""),
        "blacklist": ("json", '[]', ""),
        "refresh_interval_hours": ("int", "24", ""),
    },
    "pairlist_filters": {
        "volume_enabled": ("bool", "false", ""),
        "volume_min_avg": ("float", "10000.0", ""),
        "volume_sort": ("bool", "true", ""),
        "price_enabled": ("bool", "false", ""),
        "price_min": ("float", "0.001", ""),
        "price_max": ("float", "100000.0", ""),
        "spread_enabled": ("bool", "false", ""),
        "spread_max_pct": ("float", "0.5", ""),
        "age_enabled": ("bool", "false", ""),
        "age_min_candles": ("int", "200", ""),
    },
    "exchange": {
        "type": ("string", "mt5", "mt5 or bybit or ccxt"),
        "name": ("string", "binance", "Exchange name for CCXT"),
        "api_key": ("string", "", ""),
        "secret": ("string", "", ""),
        "password": ("string", "", ""),
        "sandbox": ("bool", "true", ""),
        "options": ("json", '{"defaultType": "swap"}', ""),
        "bybit": ("json", '{"category": "linear", "position_mode": "one-way", "default_leverage": 5}', ""),
    },
    "telegram_cmd": {
        "enabled": ("bool", "false", ""),
        "allowed_chat_ids": ("json", '[]', ""),
    },
    "rest_api": {
        "enabled": ("bool", "false", ""),
        "host": ("string", "0.0.0.0", ""),
        "port": ("int", "8080", ""),
        "api_key": ("string", "", ""),
    },
    "dashboard": {
        "port": ("int", "8501", ""),
        "theme": ("string", "dark", ""),
    },
    "ml": {
        "model_type": ("string", "random_forest", "ML model type"),
        "retrain_interval_hours": ("int", "24", ""),
        "sequence_length": ("int", "60", "LSTM sequence length"),
        "lstm_epochs": ("int", "50", ""),
        "test_size": ("float", "0.2", ""),
        "random_state": ("int", "42", ""),
    },
}


class SettingsMixin:
    """Mixin providing settings CRUD operations for DatabaseManager."""

    _settings_seeded: bool = False

    def seed_settings(self) -> bool:
        """Insert defaults if settings table is empty."""
        if self._settings_seeded:
            return False
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM settings")
            if cursor.fetchone()[0] > 0:
                cursor.close()
                self._settings_seeded = True
                return False

            rows = 0
            for section, keys in SETTINGS_SEED.items():
                for key_name, (value_type, value, description) in keys.items():
                    cursor.execute("""
                        INSERT INTO settings (section, key_name, value, value_type, description)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE value = VALUES(value)
                    """, (section, key_name, value, value_type, description))
                    rows += 1
            conn.commit()
            cursor.close()
            logger.info(f"Settings seeded: {rows} rows")
            self._settings_seeded = True
            return True
        except Exception as e:
            logger.error(f"Seed settings failed: {e}")
            return False

    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """Get all settings grouped by section, with proper type casting."""
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM settings ORDER BY section, key_name")
            rows = cursor.fetchall()
            cursor.close()

            result: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                section = row['section']
                key_name = row['key_name']
                value = self._cast_value(row['value'], row['value_type'])
                result.setdefault(section, {})[key_name] = value
            return result
        except Exception as e:
            logger.error(f"Get all settings failed: {e}")
            return {}

    def get_setting(self, section: str, key_name: str) -> Optional[Dict]:
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM settings WHERE section=%s AND key_name=%s",
                           (section, key_name))
            row = cursor.fetchone()
            cursor.close()
            return row
        except Exception as e:
            logger.error(f"Get setting {section}.{key_name} failed: {e}")
            return None

    def set_setting(self, section: str, key_name: str, value: Any) -> bool:
        try:
            value_type = self._infer_type(value)
            value_str = self._stringify(value, value_type)
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (section, key_name, value, value_type)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE value=VALUES(value), value_type=VALUES(value_type),
                                        updated_at=NOW()
            """, (section, key_name, value_str, value_type))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Set setting {section}.{key_name} failed: {e}")
            return False
