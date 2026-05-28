"""
Pairlist manager — multi-symbol pair list with dynamic filtering.

Inspired by Freqtrade's pairlist manager. Filters symbols by
volume, price range, and blacklist. Refreshes periodically.
"""
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from src.configuration.manager import ConfigManager
from src.exchange.base import IExchange
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PairlistManager:
    """Manages multi-symbol pair list with dynamic filtering.

    Usage:
        pm = PairlistManager(config, exchange)
        pairs = pm.get_pairs()  # returns sorted list of symbols
    """

    def __init__(self, config: ConfigManager, exchange: "IExchange"):
        self.config = config
        self.exchange = exchange
        self._cache: List[str] = []
        self._last_refresh: float = 0

    def get_pairs(self, force_refresh: bool = False) -> List[str]:
        if not self._cache or force_refresh:
            self._refresh()
        return self._cache

    def get_pair_metrics(self, count: int = 200) -> pd.DataFrame:
        rows = []
        for pair in self.get_pairs():
            try:
                ticker = self.exchange.fetch_ticker(pair)
                info = self.exchange.get_symbol_info(pair)
                rows.append({
                    "symbol": pair,
                    "bid": ticker.get("bid", 0),
                    "ask": ticker.get("ask", 0),
                    "spread": round(ticker.get("ask", 0) - ticker.get("bid", 0), 2),
                    "volume_min": info.get("volume_min", 0.01),
                    "volume_max": info.get("volume_max", 100),
                    "digits": info.get("digits", 2),
                })
            except Exception:
                continue
        return pd.DataFrame(rows)

    def _refresh(self):
        try:
            symbols = self.exchange.get_symbols()
            cfg = self.config.get("pairlist")
            base_symbols = cfg.get("symbols", ["XAUUSD"]) if isinstance(cfg, dict) else ["XAUUSD"]
            blacklist = cfg.get("blacklist", []) if isinstance(cfg, dict) else []
            max_pairs = cfg.get("max_pairs", 10) if isinstance(cfg, dict) else 10
            filters_cfg = self.config.get("pairlist_filters")

            filtered = [
                s for s in symbols
                if s.upper() in [x.upper() for x in base_symbols]
                or any(keyword.upper() in s.upper() for keyword in base_symbols)
            ]
            filtered = [s for s in filtered if s not in blacklist]
            filt_desc = []

            # Volume filter
            if isinstance(filters_cfg, dict) and filters_cfg.get("volume_enabled", False):
                vol_min = float(filters_cfg.get("volume_min_avg", 10000.0))
                before = len(filtered)
                vol_filtered = []
                for s in filtered:
                    try:
                        ticker = self.exchange.fetch_ticker(s)
                        vol = float(ticker.get("quoteVolume", 0) or 0)
                        if vol >= vol_min:
                            vol_filtered.append(s)
                    except Exception:
                        vol_filtered.append(s)
                filtered = vol_filtered
                removed = before - len(filtered)
                if removed > 0:
                    filt_desc.append(f"volume({removed} removed)")

                if filters_cfg.get("volume_sort", True):
                    vol_map = {}
                    for s in filtered:
                        try:
                            ticker = self.exchange.fetch_ticker(s)
                            vol_map[s] = float(ticker.get("quoteVolume", 0) or 0)
                        except Exception:
                            vol_map[s] = 0
                    filtered.sort(key=lambda s: vol_map.get(s, 0), reverse=True)

            # Price filter
            if isinstance(filters_cfg, dict) and filters_cfg.get("price_enabled", False):
                p_min = float(filters_cfg.get("price_min", 0.001))
                p_max = float(filters_cfg.get("price_max", 100000.0))
                before = len(filtered)
                price_filtered = []
                for s in filtered:
                    try:
                        ticker = self.exchange.fetch_ticker(s)
                        last = float(ticker.get("last", 0) or 0)
                        if p_min <= last <= p_max:
                            price_filtered.append(s)
                    except Exception:
                        price_filtered.append(s)
                filtered = price_filtered
                removed = before - len(filtered)
                if removed > 0:
                    filt_desc.append(f"price({removed} removed)")

            # Spread filter
            if isinstance(filters_cfg, dict) and filters_cfg.get("spread_enabled", False):
                max_spread_pct = float(filters_cfg.get("spread_max_pct", 0.5))
                before = len(filtered)
                spread_filtered = []
                for s in filtered:
                    try:
                        ticker = self.exchange.fetch_ticker(s)
                        bid = float(ticker.get("bid", 0) or 0)
                        ask = float(ticker.get("ask", 0) or 0)
                        if bid > 0 and ask > 0:
                            spread_pct = ((ask - bid) / bid) * 100
                            if spread_pct <= max_spread_pct:
                                spread_filtered.append(s)
                        else:
                            spread_filtered.append(s)
                    except Exception:
                        spread_filtered.append(s)
                filtered = spread_filtered
                removed = before - len(filtered)
                if removed > 0:
                    filt_desc.append(f"spread({removed} removed)")

            # Age filter
            if isinstance(filters_cfg, dict) and filters_cfg.get("age_enabled", False):
                min_candles = int(filters_cfg.get("age_min_candles", 200))
                before = len(filtered)
                age_filtered = []
                for s in filtered:
                    try:
                        info = self.exchange.get_symbol_info(s)
                        candle_count = info.get("candle_count", min_candles)
                        if candle_count >= min_candles:
                            age_filtered.append(s)
                    except Exception:
                        age_filtered.append(s)
                filtered = age_filtered
                removed = before - len(filtered)
                if removed > 0:
                    filt_desc.append(f"age({removed} removed)")

            self._cache = filtered[:max_pairs]
            self._last_refresh = time.time()
            if filt_desc:
                logger.info(f"Pairlist filtered: {', '.join(filt_desc)} → {len(self._cache)} pairs")
            else:
                logger.info(f"Pairlist refreshed: {len(self._cache)} pairs")
        except Exception as e:
            logger.error(f"Pairlist refresh failed: {e}")


# ── Backward compatibility alias ────────────────────────────
PairListManager = PairlistManager
