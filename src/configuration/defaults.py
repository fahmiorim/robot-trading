"""
Default configuration values for the trading bot.

⚠️  ALL defaults have moved to ``src/persistence/database.py``
    (the ``SETTINGS_SEED`` dict) so they are stored in the
    database ``settings`` table on first run.

No hardcoded fallback values — everything comes from the DB.
"""
DEFAULT_CONFIG: dict = {}
