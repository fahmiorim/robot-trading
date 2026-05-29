"""Settings database operations — settings CRUD from MySQL."""

import json
import os
import re
from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "schema.sql")


class SettingsMixin:
    """Mixin providing settings CRUD operations for DatabaseManager."""

    def seed_settings(self) -> bool:
        """Seed missing settings from schema.sql using INSERT IGNORE.

        Reads the ``INSERT IGNORE INTO settings`` block from
        ``schema.sql`` and executes it.  Existing rows are preserved;
        only missing (section, key_name) rows are inserted.
        Safe to call on every startup — idempotent.
        """
        try:
            conn = self.connect()
            sql_path = _SCHEMA_PATH
            if not os.path.isfile(sql_path):
                logger.warning(f"schema.sql not found at {sql_path}")
                return False

            with open(sql_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract the INSERT IGNORE INTO settings block
            m = re.search(
                r"INSERT IGNORE INTO settings\s+.*?;",
                content,
                re.DOTALL,
            )
            if not m:
                logger.warning("No INSERT IGNORE INTO settings found in schema.sql")
                return False

            cursor = conn.cursor()
            insert_sql = m.group(0)
            cursor.execute(insert_sql)
            conn.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected > 0:
                logger.info(f"Settings seeded from schema.sql ({affected} rows added)")
            else:
                logger.debug("Settings already up to date — no rows added")
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
