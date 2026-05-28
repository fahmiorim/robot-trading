"""
System diagnostics — platform info, dependency checks.
"""
import platform
import sys
from datetime import datetime
from typing import Dict


def get_system_info() -> Dict[str, str]:
    """Collect system information for diagnostics."""
    return {
        "platform": platform.platform(),
        "python": sys.version,
        "hostname": platform.node(),
        "timestamp": datetime.now().isoformat(),
    }


def is_mt5_available() -> bool:
    """Check if MetaTrader5 package can be imported."""
    try:
        import MetaTrader5  # noqa: F401
        return True
    except ImportError:
        return False
