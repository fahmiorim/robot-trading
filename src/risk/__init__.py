"""Risk management — protection rules and risk state manager."""

from src.risk.protection import (
    IProtection,
    ProtectionContext,
    ProtectionManager,
    CooldownProtection,
    StoplossGuard,
    MaxDrawdownProtection,
)

__all__ = [
    "IProtection", "ProtectionContext", "ProtectionManager",
    "CooldownProtection", "StoplossGuard", "MaxDrawdownProtection",
]
