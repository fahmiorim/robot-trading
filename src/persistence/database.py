"""
MySQL Database Manager — slim connector with domain mixins.

Manages connection pooling, type casting, and table migration.
Domain logic (settings, trades, analytics, market data, risk state)
is delegated to mixins in sibling modules.

Uses singleton pattern (via ``get_db()``) so all callers share the same connection pool.
Connections auto-reconnect with exponential backoff.

Connection settings come from ``.env`` file (see ``.env.example``).
"""

import json
import os
import time
import random
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import MySQLConnection

from src.utils.logging import get_logger
from src.utils.env import load_env

# ── Load .env file ──────────────────────────────────────────
load_env()

# ── Domain mixins ───────────────────────────────────────────
from src.persistence.settings_db import SettingsMixin
from src.persistence.trading_db import TradingMixin
from src.persistence.analytics_db import AnalyticsMixin
from src.persistence.market_data_db import MarketDataMixin
from src.persistence.risk_db import RiskStateMixin

logger = get_logger(__name__)


# ── Singleton ─────────────────────────────────────────────────
_db_instance: Optional["DatabaseManager"] = None


def get_db() -> "DatabaseManager":
    """Get or create the singleton DatabaseManager."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


# ── DB Connection Config (from .env) ─────────────────────────

def _load_db_config() -> Dict[str, Any]:
    """Build DB connection dict from environment variables."""
    return {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "charset": "utf8mb4",
        "use_pure": True,
        "ssl_disabled": True,
    }


class DatabaseManager(
    SettingsMixin,
    TradingMixin,
    AnalyticsMixin,
    MarketDataMixin,
    RiskStateMixin,
):
    """Manages all MySQL operations. Singleton (use ``get_db()``).

    Inherits domain CRUD from:
        - SettingsMixin    (settings CRUD)
        - TradingMixin     (trade history, signal log)
        - AnalyticsMixin   (performance, equity, circuit breaker, hyperopt)
        - MarketDataMixin  (OHLCV cache)
        - RiskStateMixin   (risk state persistence)
    """

    _schema_lock = threading.Lock()
    _tables_ensured = False

    def __init__(self):
        self._local = threading.local()

        self._reconnect_delay: float = 1.0
        self._max_reconnect_delay: float = 30.0

    @property
    def _connection(self) -> Optional[MySQLConnection]:
        if not hasattr(self, '_local'):
            self._local = threading.local()
        return getattr(self._local, 'connection', None)

    @_connection.setter
    def _connection(self, value: Optional[MySQLConnection]):
        if not hasattr(self, '_local'):
            self._local = threading.local()
        self._local.connection = value

    # ── Connection ───────────────────────────────────────────

    def connect(self) -> MySQLConnection:
        """Get or create a connection with auto-reconnect and backoff.

        If the target database does not exist, it will be created automatically.
        After connecting, required tables and default settings are seeded.
        """
        if self._connection is not None:
            try:
                self._connection.ping(reconnect=True, attempts=1)
                self._reconnect_delay = 1.0
                self._ensure_required_tables()
                return self._connection
            except (mysql.connector.Error, AttributeError):
                logger.info("MySQL connection lost, reconnecting...")
                self._connection = None

        last_error = None
        for attempt in range(3):
            try:
                self._connection = mysql.connector.connect(**_load_db_config())
                self._connection.autocommit = False
                logger.info("MySQL connection established")
                self._reconnect_delay = 1.0
                self._ensure_required_tables()
                return self._connection
            except mysql.connector.Error as e:
                # Auto-create database if it does not exist (errno 1049)
                if e.errno == 1049:
                    logger.info(f"Database does not exist, creating it...")
                    self._create_database()
                    # Retry immediately after creation
                    continue
                last_error = e
                if attempt < 2:
                    delay = self._reconnect_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(f"MySQL connect attempt {attempt+1}: {e}. "
                                   f"Retry in {delay:.1f}s")
                    time.sleep(delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2,
                                                self._max_reconnect_delay)
        raise last_error  # type: ignore[misc]

    def _create_database(self):
        """Create the target database if it does not exist."""
        cfg = _load_db_config()
        db_name = cfg.pop("database")
        try:
            conn = mysql.connector.connect(**cfg)
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                           f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.close()
            conn.close()
            logger.info(f"Database `{db_name}` created successfully")
        except mysql.connector.Error as e2:
            logger.error(f"Failed to create database `{db_name}`: {e2}")
            raise

    _SCHEMA_TABLES: Dict[str, str] = {
        "risk_state": """
            CREATE TABLE IF NOT EXISTS risk_state (
                id INT PRIMARY KEY DEFAULT 1,
                symbol VARCHAR(20) NOT NULL,
                initial_balance DECIMAL(15,2),
                peak_balance DECIMAL(15,2),
                daily_start_balance DECIMAL(15,2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CHECK (id = 1)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "trade_history": """
            CREATE TABLE IF NOT EXISTS trade_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket BIGINT,
                symbol VARCHAR(20) NOT NULL,
                action VARCHAR(10) NOT NULL,
                volume DECIMAL(10,2) NOT NULL,
                price DECIMAL(15,5) NOT NULL,
                sl DECIMAL(15,5),
                tp DECIMAL(15,5),
                profit DECIMAL(15,5),
                retcode INT,
                comment VARCHAR(255),
                strategy VARCHAR(50),
                signal_val INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'open',
                entry_time DATETIME NOT NULL,
                exit_time DATETIME,
                exit_price DECIMAL(15,5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_entry_time (entry_time),
                INDEX idx_symbol (symbol),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "signal_log": """
            CREATE TABLE IF NOT EXISTS signal_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                timestamp DATETIME NOT NULL,
                source VARCHAR(30) NOT NULL,
                signal_val INT NOT NULL,
                regime VARCHAR(20),
                price DECIMAL(15,5),
                details JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp),
                INDEX idx_source (source)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "performance_log": """
            CREATE TABLE IF NOT EXISTS performance_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE NOT NULL,
                strategy_name VARCHAR(50) NOT NULL,
                regime VARCHAR(20),
                trades_count INT DEFAULT 0,
                total_return DECIMAL(10,2),
                win_rate DECIMAL(5,2),
                max_drawdown DECIMAL(5,2),
                sharpe_ratio DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_strat_date (strategy_name, date),
                INDEX idx_date (date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "equity_snapshots": """
            CREATE TABLE IF NOT EXISTS equity_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                balance DECIMAL(15,2) NOT NULL,
                equity DECIMAL(15,2),
                drawdown_pct DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "config_snapshots": """
            CREATE TABLE IF NOT EXISTS config_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                config_json JSON NOT NULL,
                notes VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "circuit_breaker_log": """
            CREATE TABLE IF NOT EXISTS circuit_breaker_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                triggered_at DATETIME NOT NULL,
                reason VARCHAR(255) NOT NULL,
                drawdown_pct DECIMAL(5,2),
                balance_before DECIMAL(15,2),
                balance_after DECIMAL(15,2),
                auto_reset_at DATETIME,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_triggered_at (triggered_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "health_check_log": """
            CREATE TABLE IF NOT EXISTS health_check_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                checked_at DATETIME NOT NULL,
                status VARCHAR(20) NOT NULL,
                mt5_connected TINYINT(1),
                last_cycle_seconds_ago INT,
                consecutive_errors INT DEFAULT 0,
                error_message VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_checked_at (checked_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "market_data": """
            CREATE TABLE IF NOT EXISTS market_data (
                symbol VARCHAR(20) NOT NULL,
                timeframe VARCHAR(30) NOT NULL,
                time DATETIME NOT NULL,
                open DECIMAL(15,5) NOT NULL,
                high DECIMAL(15,5) NOT NULL,
                low DECIMAL(15,5) NOT NULL,
                close DECIMAL(15,5) NOT NULL,
                tick_volume BIGINT DEFAULT 0,
                spread INT DEFAULT 0,
                real_volume BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timeframe, time),
                INDEX idx_symbol_tf (symbol, timeframe, time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "hyperopt_results": """
            CREATE TABLE IF NOT EXISTS hyperopt_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                strategy_name VARCHAR(50) NOT NULL,
                best_params JSON NOT NULL,
                best_score DECIMAL(10,4) NOT NULL,
                metrics JSON,
                n_trials INT DEFAULT 0,
                elapsed_seconds DECIMAL(10,2) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_strategy (strategy_name),
                INDEX idx_score (best_score DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "ml_training_log": """
            CREATE TABLE IF NOT EXISTS ml_training_log (
                id                  INT AUTO_INCREMENT PRIMARY KEY,
                trained_at          DATETIME NOT NULL,
                model_type          VARCHAR(30) NOT NULL,
                accuracy            DECIMAL(6,4),
                params_used         JSON,
                class_distribution  JSON,
                feature_importance  JSON,
                n_samples           INT,
                data_range_start    DATETIME,
                data_range_end      DATETIME,
                atr_multiplier      DECIMAL(5,2),
                threshold           DECIMAL(6,4),
                data_source         VARCHAR(30) DEFAULT 'mt5',
                symbol              VARCHAR(20),
                timeframe           VARCHAR(20),
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_trained_at (trained_at),
                INDEX idx_model_type (model_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "settings": """
            CREATE TABLE IF NOT EXISTS settings (
                section     VARCHAR(50) NOT NULL,
                key_name    VARCHAR(50) NOT NULL,
                value       TEXT,
                value_type  VARCHAR(20) NOT NULL DEFAULT 'string',
                description VARCHAR(255) DEFAULT '',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (section, key_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    }

    def _ensure_required_tables(self):
        """Create missing tables / columns (idempotent).

        Each operation is wrapped in its own try/except so one
        failure does not cascade and block other table creation.
        """
        if DatabaseManager._tables_ensured:
            return

        with DatabaseManager._schema_lock:
            if DatabaseManager._tables_ensured:
                return

            cursor = self._connection.cursor()
            db_name = self._connection.database

            # 1. CREATE ALL CORE TABLES (each in its own try/except — settings table
            #    must exist before seed_settings() is called later in _load_from_db())
            for table_name, ddl in self._SCHEMA_TABLES.items():
                try:
                    cursor.execute(ddl)
                    logger.debug(f"Table '{table_name}' ensured")
                except Exception as e:
                    logger.error(f"Could not create table '{table_name}': {e} — data for this table will not be saved!")

            # 2. ALTER operations (column additions, indexes)
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = 'trade_history'
                      AND COLUMN_NAME = 'paper_trade'
                """, (db_name,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("ALTER TABLE trade_history ADD COLUMN paper_trade TINYINT(1) DEFAULT 0")
                    cursor.execute("CREATE INDEX idx_paper_trade ON trade_history (paper_trade)")
            except Exception as e:
                logger.warning(f"Could not add paper_trade column: {e}")

            cursor.close()
            DatabaseManager._tables_ensured = True

    def disconnect(self):
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None

    def close(self):
        self.disconnect()

    # ── Type Casting (used by mixins) ─────────────────────────

    @staticmethod
    def _cast_value(value: Optional[str], value_type: str) -> Any:
        if value is None:
            return None
        try:
            if value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'bool':
                return value.lower() in ('true', '1', 'yes')
            elif value_type == 'json':
                return json.loads(value)
            return value
        except (ValueError, json.JSONDecodeError):
            return value

    @staticmethod
    def _infer_type(value: Any) -> str:
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        return 'string'

    @staticmethod
    def _stringify(value: Any, value_type: str) -> str:
        if value_type == 'bool':
            return 'true' if value else 'false'
        elif value_type == 'json':
            return json.dumps(value)
        elif value is None:
            return ''
        return str(value)

    def _rows_to_dicts(self, rows: List[Dict]) -> List[Dict]:
        """Convert Decimal values to float in result rows."""
        for row in rows:
            for k, v in row.items():
                if hasattr(v, 'scale'):  # Decimal type
                    row[k] = float(v)
        return rows
