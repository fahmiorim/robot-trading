"""Trading database operations — trade history, signal log from MySQL."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradingDB:
    """Trade history and signal log persistence.

    Standalone class (not a mixin). Takes a DatabaseManager instance
    for connection management.

    Usage:
        db = get_db()
        trading = TradingDB(db)
        trading.log_trade({...})
    """

    def __init__(self, db):
        self._db = db

    def get_trade_by_ticket(self, ticket: int) -> Optional[Dict]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM trade_history WHERE ticket=%s", (ticket,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {k: float(v) if hasattr(v, 'scale') else v for k, v in row.items()}
            return None
        except Exception as e:
            logger.error(f"Get trade by ticket failed: {e}")
            return None

    # ── Trade History ────────────────────────────────────────

    def log_trade(self, trade: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trade_history
                    (ticket, symbol, action, volume, price, sl, tp, profit,
                     retcode, comment, strategy, signal_val, status, entry_time, paper_trade)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trade.get('ticket'), trade['symbol'],
                trade['action'], trade['volume'],
                trade['price'], trade.get('sl'), trade.get('tp'),
                trade.get('profit'), trade.get('retcode'), trade['comment'],
                trade.get('strategy'), trade['signal_val'],
                trade['status'], trade['entry_time'],
                trade['paper_trade'],
            ))
            conn.commit()
            trade_id = cursor.lastrowid
            cursor.close()
            return trade_id
        except Exception as e:
            logger.error(f"Log trade failed: {e}")
            return None

    def update_trade_exit(self, ticket: int, exit_price: float,
                          profit: float, exit_time: Optional[datetime] = None) -> bool:
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trade_history SET status='closed', exit_price=%s,
                    profit=%s, exit_time=%s
                WHERE ticket=%s AND status='open'
            """, (exit_price, profit, exit_time or datetime.now(), ticket))
            conn.commit()
            ok = cursor.rowcount > 0
            cursor.close()
            return ok
        except Exception as e:
            logger.error(f"Update trade exit failed: {e}")
            return False

    def get_trade_history(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM trade_history ORDER BY entry_time DESC LIMIT %s OFFSET %s
            """, (limit, offset))
            rows = self._db._rows_to_dicts(cursor.fetchall())
            cursor.close()
            return rows
        except Exception as e:
            logger.error(f"Get trade history failed: {e}")
            return []

    def get_open_trades(self) -> List[Dict]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM trade_history WHERE status='open' ORDER BY entry_time DESC
            """)
            rows = self._db._rows_to_dicts(cursor.fetchall())
            cursor.close()
            return rows
        except Exception as e:
            logger.error(f"Get open trades failed: {e}")
            return []

    # ── Trade Summary ────────────────────────────────────────

    def get_trade_summary(self, days: int = 30) -> Dict[str, Any]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_trades,
                    SUM(CASE WHEN status='closed' AND profit>0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status='closed' AND profit<0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(profit), 0) as total_profit,
                    COALESCE(AVG(CASE WHEN status='closed' THEN profit END), 0) as avg_profit
                FROM trade_history WHERE entry_time >= NOW() - INTERVAL %s DAY
            """, (days,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                row = {k: float(v) if hasattr(v, 'scale') else v for k, v in row.items()}
                closed = (row.get('wins', 0) or 0) + (row.get('losses', 0) or 0)
                row['win_rate'] = (row['wins'] / closed * 100) if closed > 0 else 0
            return row or {}
        except Exception as e:
            logger.error(f"Trade summary failed: {e}")
            return {}

    # ── Signal Log ───────────────────────────────────────────

    def log_signal(self, signal_data: Dict[str, Any]) -> Optional[int]:
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO signal_log (symbol, timestamp, source, signal_val, regime, price, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                signal_data['symbol'],
                signal_data['timestamp'],
                signal_data['source'],
                signal_data['signal_val'],
                signal_data.get('regime'),
                signal_data.get('price'),
                json.dumps(signal_data.get('details')),
            ))
            conn.commit()
            sig_id = cursor.lastrowid
            cursor.close()
            return sig_id
        except Exception as e:
            logger.error(f"Log signal failed: {e}")
            return None
