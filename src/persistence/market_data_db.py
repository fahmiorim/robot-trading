"""Market data database operations — caching OHLCV data from MySQL.

Standalone class (not a mixin). Takes a DatabaseManager instance
for connection management.

Usage:
    db = get_db()
    md = MarketDataDB(db)
    md.save_market_data(symbol, timeframe, df)
"""

from typing import Optional

import pandas as pd

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MarketDataDB:
    """Market data cache operations (OHLCV).

    Standalone class (not a mixin). Takes a DatabaseManager instance
    for connection management.
    """

    def __init__(self, db):
        self._db = db

    def save_market_data(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """Save OHLCV DataFrame to market_data table."""
        try:
            conn = self._db.connect()
            cursor = conn.cursor()
            rows_inserted = 0
            for idx, row in df.iterrows():
                time_val = idx.to_pydatetime() if isinstance(idx, pd.Timestamp) else idx
                cursor.execute("""
                    INSERT IGNORE INTO market_data
                        (symbol, timeframe, time, open, high, low, close,
                         tick_volume, spread, real_volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    symbol, timeframe, time_val,
                    float(row.get('open', 0)), float(row.get('high', 0)),
                    float(row.get('low', 0)), float(row.get('close', 0)),
                    int(row.get('tick_volume', row.get('volume', 0))),
                    int(row.get('spread', 0)),
                    int(row.get('real_volume', 0)),
                ))
                rows_inserted += cursor.rowcount
            conn.commit()
            cursor.close()
            return rows_inserted > 0
        except Exception as e:
            logger.error(f"Save market data failed: {e}")
            return False

    def load_market_data(self, symbol: str, timeframe: str,
                         limit: int = 2000) -> Optional[pd.DataFrame]:
        """Load OHLCV data from market_data table."""
        try:
            conn = self._db.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT time, open, high, low, close, tick_volume, spread, real_volume
                FROM market_data WHERE symbol=%s AND timeframe=%s
                ORDER BY time DESC LIMIT %s
            """, (symbol, timeframe, limit))
            rows = cursor.fetchall()
            cursor.close()
            if not rows:
                return None
            rows.reverse()
            df = pd.DataFrame(rows)
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time')
            if 'tick_volume' in df.columns:
                df = df.rename(columns={'tick_volume': 'volume'})
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            return df
        except Exception as e:
            logger.error(f"Load market data failed: {e}")
            return None
