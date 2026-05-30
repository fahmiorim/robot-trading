"""
MySQL Database Manager — slim connector with domain-specific sub-modules.

Manages connection pooling, type casting, and table migration.
Domain logic (settings, trades, analytics, market data, risk state)
is delegated to standalone domain classes (``SettingsDB``, ``TradingDB``,
``AnalyticsDB``, ``MarketDataDB``, ``RiskDB``) exposed as properties.

Uses singleton pattern (via ``get_db()``) so all callers share the same connection pool.
Connections auto-reconnect with exponential backoff.

Connection settings come from ``.env`` file (see ``.env.example``).

For backward compatibility, unknown attribute access is automatically
delegated to domain instances (e.g. ``db.log_trade(...)`` → ``db.trading.log_trade(...)``).

DDL definitions are in the sibling ``schema.py`` module.
"""

import json
import os
import time
import random
import threading
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import MySQLConnection

from src.utils.logging import get_logger
from src.utils.env import load_env
from src.persistence.schema import SCHEMA_TABLES

# ── Load .env file ──────────────────────────────────────────
load_env()

# ── Domain DB classes (composition, not mixins) ─────────────
from src.persistence.settings_db import SettingsDB
from src.persistence.trading_db import TradingDB
from src.persistence.analytics_db import AnalyticsDB
from src.persistence.market_data_db import MarketDataDB
from src.persistence.risk_db import RiskDB

logger = get_logger(__name__)


# ── Singleton ─────────────────────────────────────────────────
_db_instance: Optional["DatabaseManager"] = None


class DatabaseManager:
    """Manages all MySQL operations. Singleton (use ``get_db()``).

    Domain CRUD is delegated to standalone sub-modules:
        - ``self.settings``      → :class:`SettingsDB`    (settings CRUD)
        - ``self.trading``       → :class:`TradingDB`     (trade history, signal log)
        - ``self.analytics``     → :class:`AnalyticsDB`   (performance, equity, hyperopt)
        - ``self.market_data``   → :class:`MarketDataDB`  (OHLCV cache)
        - ``self.risk``          → :class:`RiskDB`        (risk state persistence)

    For full backward compatibility, any method not found on ``DatabaseManager``
    is automatically delegated to the domain instances (e.g. ``db.log_trade(...)``
    resolves to ``db.trading.log_trade(...)``).
    """

    _schema_lock = threading.Lock()
    _tables_ensured = False

    def __init__(self):
        self._local = threading.local()

        self._reconnect_delay: float = 1.0
        self._max_reconnect_delay: float = 30.0

        # Domain-specific DB instances (composition over inheritance)
        self.settings = SettingsDB(self)
        self.trading = TradingDB(self)
        self.analytics = AnalyticsDB(self)
        self.market_data = MarketDataDB(self)
        self.risk = RiskDB(self)

    def __getattr__(self, name: str) -> Any:
        """Auto-delegate unknown attribute access to domain instances.

        This provides full backward compatibility: existing callers
        using ``db.log_trade(...)`` continue to work without changes —
        the call is forwarded to ``self.trading.log_trade(...)``.

        Domain instances are checked in order: trading, analytics,
        settings, market_data, risk.
        """
        for domain in (self.trading, self.analytics, self.settings,
                       self.market_data, self.risk):
            if hasattr(domain, name):
                return getattr(domain, name)
        msg = f"'{type(self).__name__}' object has no attribute '{name}'"
        raise AttributeError(msg)

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
                logger.debug("MySQL connection established")
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

            # 1. CREATE ALL CORE TABLES
            for table_name, ddl in SCHEMA_TABLES.items():
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

            # 3. Migrate settings table: symbol/timeframe columns + PK
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = 'settings'
                      AND COLUMN_NAME = 'symbol'
                """, (db_name,))
                has_symbol_col = cursor.fetchone()[0] > 0

                if not has_symbol_col:
                    logger.info("Migrating settings table: adding symbol & timeframe columns...")
                    cursor.execute("""
                        ALTER TABLE settings
                        ADD COLUMN symbol VARCHAR(20) NOT NULL DEFAULT ''
                            COMMENT ''' = global default' AFTER key_name,
                        ADD COLUMN timeframe VARCHAR(30) NOT NULL DEFAULT ''
                            COMMENT ''' = global default' AFTER symbol
                    """)
                    cursor.execute("ALTER TABLE settings DROP PRIMARY KEY")
                    cursor.execute("""
                        ALTER TABLE settings ADD PRIMARY KEY (section, key_name, symbol, timeframe)
                    """)
                    logger.info("Settings table migration complete")
                else:
                    cursor.execute("""
                        SELECT IS_NULLABLE, COLUMN_DEFAULT FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s
                          AND TABLE_NAME = 'settings'
                          AND COLUMN_NAME = 'symbol'
                    """, (db_name,))
                    row = cursor.fetchone()
                    is_still_nullable = (row and row[0] == 'YES')

                    if is_still_nullable:
                        logger.info("Migrating settings table: NULL -> NOT NULL DEFAULT ''...")
                        cursor.execute("""
                            DELETE t1 FROM settings t1
                            INNER JOIN settings t2
                            WHERE t1.section = t2.section
                              AND t1.key_name = t2.key_name
                              AND t1.symbol IS NULL
                              AND t2.symbol IS NULL
                              AND t1.timeframe IS NULL
                              AND t2.timeframe IS NULL
                              AND t1.created_at < t2.created_at
                        """)
                        deleted = cursor.rowcount
                        if deleted > 0:
                            logger.info(f"  Removed {deleted} duplicate rows")
                        cursor.execute("""
                            UPDATE settings SET symbol = '' WHERE symbol IS NULL
                        """)
                        cursor.execute("""
                            UPDATE settings SET timeframe = '' WHERE timeframe IS NULL
                        """)
                        cursor.execute("""
                            ALTER TABLE settings
                            MODIFY symbol VARCHAR(20) NOT NULL DEFAULT ''
                                COMMENT ''' = global default',
                            MODIFY timeframe VARCHAR(30) NOT NULL DEFAULT ''
                                COMMENT ''' = global default'
                        """)
                        try:
                            cursor.execute("ALTER TABLE settings DROP PRIMARY KEY")
                        except Exception:
                            logger.info("  (no existing PK to drop)")
                        try:
                            cursor.execute("""
                                ALTER TABLE settings ADD PRIMARY KEY (section, key_name, symbol, timeframe)
                            """)
                            logger.info("  PRIMARY KEY added")
                        except Exception as pk_err:
                            logger.warning(f"  Could not add PK: {pk_err}")
                        logger.info("Settings table migration complete")
            except Exception as e:
                logger.warning(f"Settings table migration failed: {e}")

            cursor.close()
            DatabaseManager._tables_ensured = True

    def disconnect(self):
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None

    def close(self):
        self.disconnect()

    # ── Type Casting ─────────────────────────────────────────

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


def get_db() -> DatabaseManager:
    """Return singleton DatabaseManager instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


def _load_db_config() -> Dict:
    """Load MySQL connection config from environment variables."""
    return {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "database": os.environ.get("MYSQL_DATABASE", "robot_trading"),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
    }
