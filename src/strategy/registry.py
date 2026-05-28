"""
Strategy registry and resolver.

Uses the auto-discovery pattern from IStrategy (__init_subclass__)
as the single source of truth for available strategies.
"""
from typing import Dict, Optional, Type

from src.utils.logging import get_logger
from src.strategy.interface import IStrategy

logger = get_logger(__name__)


class StrategyResolver:
    """Resolves strategy classes by name from the auto-discovered registry."""

    @staticmethod
    def get_strategy_class(name: str) -> Optional[Type[IStrategy]]:
        """Resolve a strategy class by its strategy_id."""
        registry = IStrategy.get_registry()
        cls = registry.get(name)
        if cls is None:
            logger.warning(f"Strategy '{name}' not found in registry")
        return cls

    @staticmethod
    def get_all_strategies() -> Dict[str, Type[IStrategy]]:
        """Return all registered strategy classes."""
        return IStrategy.get_registry()

    @staticmethod
    def create_strategy(name: str, params: Optional[dict] = None) -> Optional[IStrategy]:
        """Instantiate a strategy by name with optional parameters."""
        cls = StrategyResolver.get_strategy_class(name)
        if cls is None:
            return None
        try:
            return cls(**(params or {}))
        except Exception as e:
            logger.error(f"Failed to create strategy '{name}': {e}")
            return None


# ── Backward compatibility alias ──────────────────────────────
StrategyRegistry = StrategyResolver
