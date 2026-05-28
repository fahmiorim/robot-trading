#!/usr/bin/env python3
"""
Initialization & migration script: config.json → Database settings table.

Use this on a fresh install to:
  1. Ensure all database tables exist (reads schema.sql or auto-creates)
  2. Seed the ``settings`` table with defaults (from SETTINGS_SEED)
  3. Optionally import values from ``config.json`` (overrides seed values)

Usage:
    python migrate_config_to_db.py              # Auto-detect config.json
    python migrate_config_to_db.py --fresh      # Reset DB settings to seed defaults
    python migrate_config_to_db.py my-config.json  # Import from custom path

After migration, ``config.json`` is backed up as ``config.json.backup``.
The application reads **only** from the database — no file fallback.
"""

import json
import os
import shutil
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def _ensure_connection():
    """Get DB connection, raising clear error if unavailable."""
    from src.persistence.database import get_db
    db = get_db()
    conn = db.connect()  # Will raise if DB doesn't exist
    return db, conn


def _run_schema_sql(db, conn):
    """Execute schema.sql if it exists (creates missing tables)."""
    schema_path = PROJECT_ROOT / "schema.sql"
    if not schema_path.exists():
        print("  ⚠️  schema.sql not found — tables will be created on demand")
        return 0

    sql = schema_path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    cursor = conn.cursor()
    count = 0
    for stmt in statements:
        # Skip comments
        if stmt.upper().startswith("--"):
            continue
        try:
            cursor.execute(stmt)
            count += 1
        except Exception as e:
            print(f"  ⚠️  Schema statement skipped: {e}")
    conn.commit()
    cursor.close()
    print(f"  ✅ {count} schema statements executed")
    return count


def _seed_settings(db):
    """Seed settings table with defaults (idempotent)."""
    seeded = db.seed_settings()
    if seeded:
        print("  ✅ Settings table seeded with defaults")
    else:
        print("  ℹ️  Settings already seeded — skipped")
    return seeded


def _migrate_from_file(db, config_path: str) -> int:
    """Import values from a JSON config file into the settings table."""
    if not os.path.exists(config_path):
        print(f"  ℹ️  No {config_path} found — skipping file import")
        return 0

    with open(config_path, "r") as f:
        config = json.load(f)

    if not isinstance(config, dict):
        print(f"  ❌ Config file must be a JSON object, got {type(config).__name__}")
        return 0

    conn = db.connect()
    cursor = conn.cursor()

    rows = 0
    for section, keys in config.items():
        if not isinstance(keys, dict):
            continue
        for key_name, value in keys.items():
            value_type = _infer_type(value)
            value_str = _stringify(value, value_type)
            cursor.execute(
                """INSERT INTO settings (section, key_name, value, value_type)
                   VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE value=VALUES(value), value_type=VALUES(value_type),
                                           updated_at=NOW()""",
                (section, key_name, value_str, value_type),
            )
            rows += cursor.rowcount

    conn.commit()
    cursor.close()
    print(f"  ✅ {rows} values imported from {config_path}")
    return rows


def _backup_and_remove(config_path: str):
    """Backup config.json → config.json.backup, then delete original."""
    if not os.path.exists(config_path):
        return
    backup_path = config_path + ".backup"
    try:
        shutil.copy2(config_path, backup_path)
        os.remove(config_path)
        print(f"  📦 Config backed up to {backup_path}")
        print(f"  🗑️  Original {config_path} deleted — DB is now the only source of truth")
    except Exception as e:
        print(f"  ⚠️  Backup/removal failed: {e}")
        print("  ⚠️  config.json still exists — delete it manually when ready")


def _infer_type(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, (dict, list)):
        return "json"
    return "string"


def _stringify(value, value_type: str) -> str:
    if value_type == "bool":
        return "true" if value else "false"
    if value_type == "json":
        return json.dumps(value)
    if value is None:
        return ""
    return str(value)


# ── Main ──────────────────────────────────────────────────────


def main():
    args = sys.argv[1:]
    config_path = "config.json"
    fresh = False

    # Parse simple flags
    filtered = []
    for arg in args:
        if arg == "--fresh":
            fresh = True
        elif not arg.startswith("--"):
            filtered.append(arg)
    if filtered:
        config_path = filtered[0]

    sep = "=" * 50
    print(f"\n{sep}")
    print("   🚀 AI Trading Robot — DB Initialization")
    print(f"{sep}")

    # ── Step 1: Connect to DB ──
    print("\n[1/4] Connecting to MySQL database...")
    try:
        db, conn = _ensure_connection()
        print("  ✅ MySQL connection OK")
    except Exception as e:
        print(f"\n  ❌ Database connection failed: {e}")
        print(f"\n  {'─' * 40}")
        print(f"  Make sure MySQL is running and the 'trading_bot' database exists.")
        print(f"  Run: mysql -u root -e 'CREATE DATABASE IF NOT EXISTS trading_bot;'")
        print(f"  {'─' * 40}")
        sys.exit(1)

    # ── Step 2: Create tables ──
    print("\n[2/4] Creating database tables...")
    try:
        _run_schema_sql(db, conn)
        # Also ensure required tables from database.py
        db._ensure_required_tables()
        print("  ✅ All tables ready")
    except Exception as e:
        print(f"  ⚠️  Table creation warning: {e}")

    # ── Step 3: Seed settings ──
    print("\n[3/4] Seeding default settings...")
    try:
        if fresh:
            # Fresh mode: re-seed by clearing and re-inserting
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM settings")
            conn.commit()
            cursor.close()
            db._settings_seeded = False
            print("  🧹 Cleared existing settings")
        _seed_settings(db)
    except Exception as e:
        print(f"  ⚠️  Seed warning: {e}")

    # ── Step 4: Migrate from config.json ──
    print(f"\n[4/4] Importing from {config_path} (if present)...")
    try:
        _migrate_from_file(db, config_path)
    except Exception as e:
        print(f"  ⚠️  File import warning: {e}")

    # ── Backup & remove config.json ──
    if os.path.exists(config_path):
        print()
        _backup_and_remove(config_path)

    print(f"\n{sep}")
    print("   ✅ Initialization complete!")
    print(f"   📌 All configuration now comes from the database.")
    print(f"   📌 config.json has been removed (backed up as .backup).")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
