"""Risk state database operations from MySQL."""

from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RiskStateMixin:
    """Mixin providing risk state operations for DatabaseManager."""

    def save_risk_state(self, symbol: str, initial_balance: Optional[float],
                        peak_balance: Optional[float],
                        daily_start_balance: Optional[float]) -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO risk_state (id, symbol, initial_balance, peak_balance, daily_start_balance)
                VALUES (1, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    symbol=VALUES(symbol),
                    initial_balance=VALUES(initial_balance),
                    peak_balance=VALUES(peak_balance),
                    daily_start_balance=VALUES(daily_start_balance)
            """, (symbol, initial_balance, peak_balance, daily_start_balance))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Save risk state failed: {e}")
            return False

    def load_risk_state(self) -> Optional[Dict[str, Any]]:
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM risk_state WHERE id=1")
            row = cursor.fetchone()
            cursor.close()
            if row:
                for k in ('initial_balance', 'peak_balance', 'daily_start_balance'):
                    if row.get(k) is not None:
                        row[k] = float(row[k])
            return row
        except Exception as e:
            logger.error(f"Load risk state failed: {e}")
            return None
