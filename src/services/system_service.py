"""System service — tracks bot health, cycle metrics, and execution state."""

import time
from typing import Dict

class SystemService:
    """Manages bot execution state and health metrics."""

    def __init__(self):
        self.cycle_count: int = 0
        self.consecutive_errors: int = 0
        self.last_cycle_time: float = time.time()
        self.auto_trading: bool = False
        self.stop_buy: bool = False

    def mark_cycle_start(self):
        self.cycle_count += 1
        self.last_cycle_time = time.time()

    def mark_success(self):
        self.consecutive_errors = 0

    def mark_error(self):
        self.consecutive_errors += 1

    def get_health_status(self) -> Dict:
        return {
            "cycle_count": self.cycle_count,
            "consecutive_errors": self.consecutive_errors,
            "last_cycle_time": self.last_cycle_time,
            "auto_trading": self.auto_trading,
            "up_time_seconds": time.time() - self.last_cycle_time # Approximated
        }
