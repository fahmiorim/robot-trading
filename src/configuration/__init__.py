"""
Configuration management package.

All defaults come from the database ``settings`` table.
No hardcoded fallback values — everything is seeded by ``SETTINGS_SEED``.
"""
from src.configuration.manager import ConfigManager, TIMEFRAME_MAP

__all__ = ["ConfigManager", "TIMEFRAME_MAP"]
