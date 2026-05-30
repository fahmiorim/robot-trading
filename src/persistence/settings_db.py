"""Settings database operations — settings CRUD from MySQL.

Standalone class (not a mixin). Takes a DatabaseManager instance
for connection management.

Usage:
    db = get_db()
    settings = SettingsDB(db)
    settings.get_all_settings(...)
"""

import os
import re
from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "schema.sql")


class SettingsDB:
    """Settings CRUD operations.

    Standalone class (not a mixin). Takes a DatabaseManager instance
    for connection management.

    Usage:
        db = get_db()
        settings = SettingsDB(db)
        settings.get_all_settings(...)
    """

    def __init__(self, db):
        self._db = db

    def seed_settings(self) -> bool:
        """Seed missing settings from schema.sql using INSERT IGNORE.

        Reads the ``INSERT IGNORE INTO settings`` block from
        ``schema.sql`` and executes it.  Existing rows are preserved;
        only missing (section, key_name) rows are inserted.
        Safe to call on every startup — idempotent.
        """
        try:
            conn = self._db.connect()
            sql_path = _SCHEMA_PATH
            if not os.path.isfile(sql_path):
                logger.warning(f"schema.sql not found at {sql_path}")
                return False

            with open(sql_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract all INSERT IGNORE INTO settings blocks
            matches = list(re.finditer(
                r"INSERT IGNORE INTO settings\s+.*?;",
                content,
                re.DOTALL,
            ))
            if not matches:
                logger.warning("No INSERT IGNORE INTO settings found in schema.sql")
                return False

            cursor = conn.cursor()
            total_affected = 0
            for m in matches:
                insert_sql = m.group(0)
                cursor.execute(insert_sql)
                conn.commit()
                if cursor.rowcount > 0:
                    total_affected += cursor.rowcount
            cursor.close()
            if total_affected > 0:
                logger.info(f"Settings seeded from schema.sql ({total_affected} rows added)")
            else:
                logger.debug("Settings already up to date — no rows added")
            return True
        except Exception as e:
            logger.error(f"Seed settings failed: {e}")
            return False

    @staticmethod
    def _db_to_internal(symbol: str, timeframe: str) -> tuple:
        """Map DB empty string to None for internal Python API."""
        return (
            None if symbol == '' else symbol,
            None if timeframe == '' else timeframe,
        )

    @staticmethod
    def _internal_to_db(symbol: Optional[str], timeframe: Optional[str]) -> tuple:
        """Map None to empty string for DB storage."""
        return (
            '' if symbol is None else symbol,
            '' if timeframe is None else timeframe,
        )

    def get_all_settings(self, symbol: Optional[str] = None,
                          timeframe: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get settings grouped by section, resolved for a specific context.

        If symbol/timeframe are provided, context-specific overrides take priority
        over global defaults (symbol='', timeframe='').
        If neither is provided, returns only global defaults (backward compat).
        """
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            if symbol is not None and timeframe is not None:
                db_sym, db_tf = self._internal_to_db(symbol, timeframe)
                # Context-aware: load all, resolve key by key
                cursor.execute("""
                    SELECT * FROM settings
                    WHERE (symbol = '' AND timeframe = '')
                       OR (symbol = %s AND timeframe = %s)
                    ORDER BY section, key_name, symbol, timeframe
                """, (db_sym, db_tf))
            else:
                # Global only (backward compat)
                cursor.execute("""
                    SELECT * FROM settings
                    WHERE symbol = '' AND timeframe = ''
                    ORDER BY section, key_name
                """)
            rows = cursor.fetchall()
            cursor.close()

            result: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                section = row['section']
                key_name = row['key_name']
                value = self._db._cast_value(row['value'], row['value_type'])
                row_sym, row_tf = self._db_to_internal(
                    row['symbol'], row['timeframe']
                )
                if symbol is not None and timeframe is not None:
                    # Context-specific override wins over global
                    if row_sym is not None and row_tf is not None:
                        result.setdefault(section, {})[key_name] = value
                    elif key_name not in result.get(section, {}):
                        result.setdefault(section, {})[key_name] = value
                else:
                    result.setdefault(section, {})[key_name] = value
            return result
        except Exception as e:
            logger.error(f"Get all settings failed: {e}")
            return {}

    def get_all_settings_flat(self) -> List[Dict[str, Any]]:
        """Get ALL settings rows including symbol/timeframe context, flat list.

        Loads global defaults and all context-specific overrides.
        Used by ConfigManager to build context-aware in-memory cache.
        Returns '' mapped to None for global context.
        """
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT section, key_name, symbol, timeframe, value, value_type
                FROM settings ORDER BY section, key_name, symbol, timeframe
            """)
            rows = cursor.fetchall()
            cursor.close()
            for row in rows:
                row['value'] = self._db._cast_value(row['value'], row['value_type'])
                # Map '' -> None for Python API
                row['symbol'] = None if row['symbol'] == '' else row['symbol']
                row['timeframe'] = None if row['timeframe'] == '' else row['timeframe']
            return rows
        except Exception as e:
            logger.error(f"Get all settings flat failed: {e}")
            return []

    def get_setting(self, section: str, key_name: str,
                     symbol: Optional[str] = None,
                     timeframe: Optional[str] = None) -> Optional[Dict]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            if symbol is not None and timeframe is not None:
                db_sym, db_tf = self._internal_to_db(symbol, timeframe)
                # Try context-specific first, fall back to global
                cursor.execute("""
                    SELECT * FROM settings
                    WHERE section=%s AND key_name=%s
                      AND symbol = '' AND timeframe = ''
                """, (section, key_name))
                global_row = cursor.fetchone()
                cursor.execute("""
                    SELECT * FROM settings
                    WHERE section=%s AND key_name=%s
                      AND symbol=%s AND timeframe=%s
                """, (section, key_name, db_sym, db_tf))
                context_row = cursor.fetchone()
                cursor.close()
                return context_row or global_row
            else:
                cursor.execute("""
                    SELECT * FROM settings
                    WHERE section=%s AND key_name=%s
                      AND symbol = '' AND timeframe = ''
                """, (section, key_name))
                row = cursor.fetchone()
                cursor.close()
                return row
        except Exception as e:
            logger.error(f"Get setting {section}.{key_name} failed: {e}")
            return None

    def set_setting(self, section: str, key_name: str, value: Any,
                     symbol: Optional[str] = None,
                     timeframe: Optional[str] = None) -> bool:
        try:
            value_type = self._db._infer_type(value)
            value_str = self._db._stringify(value, value_type)
            db_sym, db_tf = self._internal_to_db(symbol, timeframe)
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings (section, key_name, symbol, timeframe, value, value_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE value=VALUES(value), value_type=VALUES(value_type),
                                        updated_at=NOW()
            """, (section, key_name, db_sym, db_tf, value_str, value_type))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Set setting {section}.{key_name} failed: {e}")
            return False

    def delete_all_context_overrides(self) -> bool:
        """Delete all context-specific settings (non-global) from DB.

        Only keeps rows where symbol='' AND timeframe='' (global defaults).
        """
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM settings
                WHERE symbol != '' OR timeframe != ''
            """)
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            if affected > 0:
                logger.info(f"Deleted {affected} context-specific override(s) from settings")
            return True
        except Exception as e:
            logger.error(f"Delete context overrides failed: {e}")
            return False

    def delete_timeframe_overrides(self, timeframe: str) -> bool:
        """Delete all overrides for a specific timeframe.

        Removes rows WHERE timeframe=%s — covers both timeframe-only overrides
        (symbol='') and symbol-specific overrides for that timeframe.
        Global defaults (symbol='', timeframe='') are preserved.
        """
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM settings WHERE timeframe = %s AND timeframe != ''",
                (timeframe,),
            )
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            if affected > 0:
                logger.info(f"Deleted {affected} override(s) for timeframe {timeframe}")
            return True
        except Exception as e:
            logger.error(f"Delete timeframe overrides for {timeframe} failed: {e}")
            return False

    def delete_global_defaults(self) -> bool:
        """Delete all global default settings from DB.

        Removes rows WHERE symbol='' AND timeframe='' (global defaults only).
        Context-specific overrides (TF/symbol) are preserved.
        Call seed_settings() afterward to re-insert factory defaults.
        """
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM settings WHERE symbol = '' AND timeframe = ''"
            )
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            if affected > 0:
                logger.info(f"Deleted {affected} global default(s) from settings")
            return True
        except Exception as e:
            logger.error(f"Delete global defaults failed: {e}")
            return False
