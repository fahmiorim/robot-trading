"""
Bybit Exchange — exchange-specific connector extending CCXTExchange.

Adds Bybit-specific features that the generic CCXTExchange cannot support:

  - **Category:** linear (USDT perpetual), inverse (coin-margined), spot
  - **Position Mode:** One-way (positionIdx=0) vs Hedge (positionIdx=1 buy / 2 sell)
  - **Leverage Tiers & Risk Limits** — fetch and validate position sizes
  - **Trading Stop** — set TP/SL via Bybit's dedicated endpoint
  - **Conditional Orders** — stop-loss, take-profit, trailing stop
  - **Funding Rate** — enhanced fetch + history

Usage:
    exchange = BybitExchange(
        symbol="BTC/USDT",
        api_key="...",
        secret="...",
        sandbox=True,
        category="linear",      # "linear" | "inverse" | "spot"
        position_mode="one-way", # "one-way" | "hedge"
        default_leverage=5,
    )
    exchange.connect()
    exchange.set_leverage(10)
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import ccxt
import pandas as pd

from src.exchange.ccxt import CCXTExchange
from src.utils.logging import get_logger
from src.utils.exceptions import (
    ExchangeError, ConnectionError, OrderError,
    InvalidPriceError, InvalidVolumeError,
)

logger = get_logger(__name__)


class BybitExchange(CCXTExchange):
    """Bybit-specific exchange implementation.

    Extends CCXTExchange with Bybit's unique features: category
    (linear/inverse/spot), position mode (one-way/hedge), leverage
    tiers, trading-stop TP/SL, and conditional orders.

    Args:
        symbol: Trading pair (e.g. BTC/USDT).
        api_key: Bybit API key.
        secret: Bybit API secret.
        password: Bybit password (optional).
        sandbox: Use testnet (default True).
        category: "linear" (USDT perpetual), "inverse" (coin-margined),
                  or "spot".
        position_mode: "one-way" or "hedge".
        default_leverage: Default leverage for futures.
        options: Additional CCXT options.
    """

    def __init__(
        self,
        symbol: str,
        api_key: str,
        secret: str,
        password: str,
        sandbox: bool,
        category: str,
        position_mode: str,
        default_leverage: int,
        options: Optional[Dict] = None,
        **kwargs,
    ):
        # Force exchange_name to bybit
        super().__init__(
            exchange_name="bybit",
            symbol=symbol,
            api_key=api_key,
            secret=secret,
            password=password,
            sandbox=sandbox,
            options=options,
            **kwargs,
        )

        # Bybit-specific config
        self.category = category.lower()  # linear, inverse, spot
        self.position_mode = position_mode.lower()  # one-way, hedge
        self.default_leverage = default_leverage

        # Validate category
        valid_categories = {"linear", "inverse", "spot"}
        if self.category not in valid_categories:
            logger.warning(
                f"Unknown category '{category}', defaulting to 'linear'. "
                f"Valid: {valid_categories}"
            )
            self.category = "linear"

        # Override options for Bybit
        if self.category == "linear":
            self._options.setdefault("defaultType", "swap")
        elif self.category == "inverse":
            self._options.setdefault("defaultType", "inverse")
        else:
            self._options.setdefault("defaultType", "spot")

        logger.info(
            f"BybitExchange: {self.symbol}, category={self.category}, "
            f"position_mode={self.position_mode}, leverage={self.default_leverage}"
        )

    # ── Connection Lifecycle ─────────────────────────────────

    def connect(self) -> bool:
        """Connect to Bybit with category-specific defaults."""
        result = super().connect()
        if result and self._exchange:
            # Set default leverage if futures
            if self.category in ("linear", "inverse"):
                try:
                    self._set_leverage_internal(self.default_leverage, self.symbol)
                except Exception as e:
                    logger.warning(f"Could not set default leverage: {e}")

            # Set position mode
            try:
                self._set_position_mode_internal()
            except Exception as e:
                logger.warning(f"Could not set position mode: {e}")

            logger.info(
                f"Bybit connected: {len(self._exchange.markets)} markets, "
                f"leverage={self.default_leverage}x, mode={self.position_mode}"
            )
        return result

    # ── Leverage Management ───────────────────────────────────

    def set_leverage(
        self, leverage: int, symbol: Optional[str] = None
    ) -> bool:
        """Set leverage for a symbol.

        Bybit uses /v5/position/set-leverage with buyLeverage and
        sellLeverage (for hedge mode) or a single value (one-way).

        Args:
            leverage: Leverage value (1-100 depending on tier).
            symbol: Trading pair (defaults to self.symbol).

        Returns:
            True if successful.
        """
        return self._set_leverage_internal(
            leverage, symbol or self.symbol
        )

    def _set_leverage_internal(self, leverage: int, symbol: str) -> bool:
        """Internal method to set leverage via CCXT."""
        if not self._exchange or not self.is_connected():
            return False

        sym = self._normalise_symbol(symbol)
        try:
            if self._exchange.has.get("setLeverage"):
                if self.position_mode == "hedge":
                    # Hedge mode: set buy and sell leverage separately
                    self._exchange.set_leverage(
                        leverage, sym,
                        params={"buyLeverage": str(leverage),
                                "sellLeverage": str(leverage)},
                    )
                else:
                    self._exchange.set_leverage(leverage, sym)
                logger.info(f"Leverage set to {leverage}x for {sym}")
                return True
            else:
                logger.warning("setLeverage not supported by this CCXT version")
                return False
        except ccxt.BadRequest as e:
            logger.warning(f"Leverage error for {sym}: {e}")
            return False
        except Exception as e:
            logger.error(f"set_leverage error: {e}")
            return False

    def get_leverage(self, symbol: Optional[str] = None) -> Dict:
        """Get current leverage info for a symbol.

        Returns:
            Dict with 'leverage', 'max_leverage', 'leverage_tier'.
        """
        if not self._exchange or not self.is_connected():
            return {"leverage": self.default_leverage, "max_leverage": 100,
                    "leverage_tier": 1}

        sym = self._normalise_symbol(symbol or self.symbol)
        try:
            if self._exchange.has.get("fetchLeverage"):
                lev_info = self._exchange.fetch_leverage(sym)
                return {
                    "leverage": float(
                        lev_info.get("longLeverage", 0) or
                        lev_info.get("leverage", self.default_leverage)
                    ),
                    "max_leverage": float(lev_info.get("maxLeverage", 100)),
                    "leverage_tier": int(lev_info.get("leverageTier", 1)),
                }
        except Exception as e:
            logger.debug(f"get_leverage error: {e}")

        return {"leverage": self.default_leverage, "max_leverage": 100,
                "leverage_tier": 1}

    # ── Position Mode ─────────────────────────────────────────

    def set_position_mode(self, mode: str = "one-way") -> bool:
        """Switch between One-way and Hedge position mode.

        Bybit uses /v5/position/switch-mode with mode=0 (one-way)
        or mode=3 (hedge).

        Args:
            mode: "one-way" or "hedge".

        Returns:
            True if successful.
        """
        self.position_mode = mode.lower()
        return self._set_position_mode_internal()

    def _set_position_mode_internal(self) -> bool:
        """Internal method to set position mode via CCXT."""
        if not self._exchange or not self.is_connected():
            return False

        try:
            if self._exchange.has.get("setPositionMode"):
                hedge = self.position_mode == "hedge"
                self._exchange.set_position_mode(hedge)
                logger.info(f"Position mode set to '{self.position_mode}'")
                return True
            else:
                logger.debug("setPositionMode not available")
                return False
        except Exception as e:
            logger.warning(f"set_position_mode error: {e}")
            return False

    # ── Leverage Tiers & Risk Limits ──────────────────────────

    def get_leverage_tiers(
        self, symbols: Optional[List[str]] = None
    ) -> Dict[str, List[Dict]]:
        """Fetch leverage tiers for symbols.

        Bybit has tier-based leverage where max leverage decreases
        as position size increases.

        Args:
            symbols: List of symbols (defaults to [self.symbol]).

        Returns:
            Dict mapping symbol → list of tier dicts.
        """
        if not self._exchange or not self.is_connected():
            return {}

        syms = symbols or [self.symbol]
        syms = [self._normalise_symbol(s) for s in syms]

        try:
            if self._exchange.has.get("fetchLeverageTiers"):
                tiers = self._exchange.fetch_leverage_tiers(syms)
                result = {}
                for sym, tier_list in tiers.items():
                    parsed = []
                    for t in tier_list:
                        parsed.append({
                            "tier": int(t.get("tier", 0)),
                            "min_size": float(t.get("minNotional", 0)
                                              or t.get("minAmount", 0)),
                            "max_size": float(t.get("maxNotional", float("inf"))
                                              or t.get("maxAmount", float("inf"))),
                            "max_leverage": float(t.get("maxLeverage", 1)),
                            "maintenance_margin_rate": float(
                                t.get("maintenanceMarginRate", 0)
                            ),
                            "initial_margin_rate": float(
                                t.get("initialMarginRate", 0)
                            ),
                        })
                    result[sym] = parsed
                return result
        except Exception as e:
            logger.warning(f"fetch_leverage_tiers error: {e}")

        return {}

    def get_risk_limit(self, symbol: Optional[str] = None) -> Dict:
        """Get current risk limit for a symbol.

        Returns:
            Dict with 'risk_id', 'risk_limit_value', 'max_leverage'.
        """
        tiers = self.get_leverage_tiers(
            [symbol or self.symbol]
        )
        sym = self._normalise_symbol(symbol or self.symbol)
        symbol_tiers = tiers.get(sym, [])
        if symbol_tiers:
            # Find the tier matching current position size
            return {
                "tiers": symbol_tiers,
                "current_tier": symbol_tiers[0].get("tier", 1),
                "max_leverage": symbol_tiers[0].get("max_leverage", 100),
            }
        return {
            "tiers": [],
            "current_tier": 1,
            "max_leverage": 100,
        }

    def validate_position_size(
        self, volume: float, symbol: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Check if position size is within current leverage tier.

        Args:
            volume: Position size in base currency.
            symbol: Trading pair.

        Returns:
            (is_valid, reason) tuple.
        """
        tiers = self.get_leverage_tiers([symbol or self.symbol])
        sym = self._normalise_symbol(symbol or self.symbol)
        symbol_tiers = tiers.get(sym, [])
        if not symbol_tiers:
            return True, "No tier data available"

        for tier in symbol_tiers:
            if tier["min_size"] <= volume <= tier["max_size"]:
                return True, f"Tier {tier['tier']}: max leverage {tier['max_leverage']}x"

        return False, (
            f"Volume {volume} outside all leverage tiers for {sym}. "
            f"Range: {symbol_tiers[0]['min_size']}-"
            f"{symbol_tiers[-1]['max_size']}"
        )

    # ── Category Helper ───────────────────────────────────────

    def _category_params(self) -> Dict[str, str]:
        """Return CCXT params dict with category for Bybit API calls."""
        return {"category": self.category}

    def _position_idx(self, side: str) -> int:
        """Get positionIdx for hedge/one-way mode.

        Bybit requires positionIdx in order params:
        - One-way mode: 0
        - Hedge mode: 1 for buy, 2 for sell

        Args:
            side: "buy" or "sell".

        Returns:
            0 (one-way), 1 (buy-hedge), or 2 (sell-hedge).
        """
        if self.position_mode == "hedge":
            return 1 if side.lower() == "buy" else 2
        return 0

    # ── Order Override ────────────────────────────────────────

    def create_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        order_type: str = "market",
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Place an order on Bybit with category and positionIdx.

        Extends CCXTExchange.create_order with:
        - category param (linear/inverse/spot)
        - positionIdx for hedge/one-way mode
        - triggerPrice / triggerDirection for conditional orders
        - orderFilter for distinguishing regular vs stop orders
        - timeInForce options

        Args:
            symbol: Trading pair.
            side: "buy" or "sell".
            volume: Amount.
            order_type: "market", "limit", "stop", "stop_limit",
                       "take_profit", "take_profit_limit", "trailing_stop".
            price: Required for limit orders.
            sl: Stop-loss price.
            tp: Take-profit price.
            **kwargs: Additional params including:
                - reduce_only (bool)
                - trigger_price (float) — for stop/trigger orders
                - trailing_stop_pct (float) — trailing stop distance %
                - time_in_force (str): "GTC", "IOC", "FOK", "PostOnly"

        Returns:
            Dict with order result.
        """
        if not self.ensure_connection():
            raise ConnectionError("Exchange not connected")

        sym = self._normalise_symbol(symbol)
        side = side.lower()
        order_type = order_type.lower()

        # Validate
        if order_type in ("limit", "stop_limit", "take_profit_limit") and price is None:
            raise InvalidPriceError(f"'{order_type}' orders require a price")

        # --- Build order params ---
        order_params: Dict[str, Any] = {}

        # Always include category
        order_params["category"] = self.category

        # Position index (hedge/one-way)
        order_params["positionIdx"] = self._position_idx(side)

        # Reduce-only flag
        reduce_only = kwargs.pop("reduce_only", False)
        if reduce_only:
            order_params["reduceOnly"] = True
            # Bybit requires positionIdx for reduce-only orders
            if self.position_mode == "one-way":
                order_params["positionIdx"] = 0

        # Time in force
        tif = kwargs.pop("time_in_force", None) or kwargs.pop("timeInForce", None)
        if tif:
            order_params["timeInForce"] = tif.upper()

        # Trigger price (for stop/conditional orders)
        trigger_price = kwargs.pop("trigger_price", None) or kwargs.pop("triggerPrice", None)
        if trigger_price is not None:
            order_params["triggerPrice"] = trigger_price
            # Determine trigger direction
            if side == "buy":
                order_params["triggerDirection"] = 1  # price rises above trigger
            else:
                order_params["triggerDirection"] = 2  # price falls below trigger

        # Trailing stop
        trailing_pct = kwargs.pop("trailing_stop_pct", None) or kwargs.pop("trailingStopPct", None)
        if trailing_pct is not None:
            order_params["trailingStopPct"] = trailing_pct

        # SL/TP via order params (Bybit supports inline TP/SL)
        if sl is not None:
            order_params["stopLoss"] = str(sl)
            order_params["slTriggerBy"] = "MarkPrice"
        if tp is not None:
            order_params["takeProfit"] = str(tp)
            order_params["tpTriggerBy"] = "MarkPrice"

        # Market info for precision
        market = self._exchange.market(sym) if self._exchange else None
        if market:
            amount_precision = market.get("precision", {}).get("amount", 8)
            volume = round(volume, int(amount_precision))

        # Map order_type to CCXT type
        ccxt_type = order_type
        if order_type == "stop":
            ccxt_type = "stop"
            order_params.setdefault("orderFilter", "StopOrder")
        elif order_type == "stop_limit":
            ccxt_type = "limit"
            order_params["orderFilter"] = "StopOrder"
        elif order_type == "take_profit":
            ccxt_type = "take_profit"
        elif order_type == "take_profit_limit":
            ccxt_type = "take_profit_limit"
        elif order_type == "trailing_stop":
            ccxt_type = "market"
            if trailing_pct is None:
                trailing_pct = 0.5  # default 0.5%
            order_params["trailingStopPct"] = trailing_pct

        # Add remaining kwargs as order params
        for key, val in kwargs.items():
            if key not in ("comment", "magic"):
                order_params[key] = val

        # --- Execute ---
        try:
            if ccxt_type == "market":
                if side == "buy":
                    order = self._exchange.create_market_buy_order(
                        sym, volume, params=order_params
                    )
                else:
                    order = self._exchange.create_market_sell_order(
                        sym, volume, params=order_params
                    )
            elif ccxt_type == "limit":
                if side == "buy":
                    order = self._exchange.create_limit_buy_order(
                        sym, volume, price, params=order_params
                    )
                else:
                    order = self._exchange.create_limit_sell_order(
                        sym, volume, price, params=order_params
                    )
            elif ccxt_type in ("stop", "take_profit"):
                if side == "buy":
                    order = self._exchange.create_order(
                        sym, ccxt_type, "buy", volume,
                        params=order_params,
                    )
                else:
                    order = self._exchange.create_order(
                        sym, ccxt_type, "sell", volume,
                        params=order_params,
                    )
            elif ccxt_type in ("stop_limit", "take_profit_limit"):
                # For limit-type conditional orders, use 'limit' as CCXT type
                limit_type = "limit"
                if side == "buy":
                    order = self._exchange.create_order(
                        sym, limit_type, "buy", volume, price,
                        params=order_params,
                    )
                else:
                    order = self._exchange.create_order(
                        sym, limit_type, "sell", volume, price,
                        params=order_params,
                    )
            else:
                raise OrderError(f"Unsupported order type: {order_type}")

            filled = float(order.get("filled", 0) or volume)
            cost = float(order.get("cost", 0))
            avg_price = cost / filled if filled > 0 else (price or 0)

            logger.info(
                f"Bybit order: {side.upper()} {volume} {sym} "
                f"@{avg_price:.4f} (id={order.get('id', '?')}, "
                f"type={order_type}, cat={self.category})"
            )

            # Extract stop loss / take profit IDs if returned
            sl_order_id = None
            tp_order_id = None
            if "stopLossOrderId" in order:
                sl_order_id = str(order["stopLossOrderId"])
            if "takeProfitOrderId" in order:
                tp_order_id = str(order["takeProfitOrderId"])

            return {
                "success": True,
                "order_id": str(order.get("id", "")),
                "order": order,
                "volume": filled,
                "price": avg_price,
                "cost": cost,
                "fee": order.get("fee", {}),
                "status": order.get("status", "closed"),
                "sl_order_id": sl_order_id,
                "tp_order_id": tp_order_id,
            }

        except ccxt.InsufficientFunds as e:
            raise OrderError(f"Insufficient funds: {e}")
        except ccxt.InvalidOrder as e:
            raise OrderError(f"Invalid order: {e}")
        except ccxt.RateLimitExceeded as e:
            logger.warning(f"Rate limit hit: {e}")
            time.sleep(self._exchange.rateLimit / 1000 if self._exchange else 1)
            raise OrderError(f"Rate limit: {e}")
        except ccxt.NetworkError as e:
            raise ConnectionError(f"Network error: {e}")
        except Exception as e:
            raise OrderError(f"Order failed: {e}")

    # ── Positions Override ────────────────────────────────────

    def get_open_positions(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get open positions from Bybit with category support.

        Bybit returns positions with different structure than generic
        CCXT. Key differences:
        - Uses 'size' instead of 'contracts'
        - Has 'side' as string ("Buy"/"Sell") in hedge mode
        - Has 'positionIdx' field (0/1/2)
        - Includes 'unifiedPnl', 'curRealisedPnl'
        - Mark price, liquidation price

        Returns:
            List of position dicts with keys:
            id, ticket, symbol, side, volume, entry_price,
            current_price, pnl, leverage, margin, liquidation_price.
        """
        if not self.ensure_connection():
            return []

        try:
            sym = self._normalise_symbol(symbol) if symbol else None
            params = self._category_params()
            positions = self._exchange.fetch_positions(sym, params=params)
            result = []

            for p in positions:
                size = float(p.get("size", 0) or p.get("contracts", 0))
                if size == 0:
                    continue

                # Determine side
                side_raw = p.get("side", "").upper()
                if side_raw in ("BUY", "LONG"):
                    side = "BUY"
                elif side_raw in ("SELL", "SHORT"):
                    side = "SELL"
                else:
                    # One-way mode: derive from positionIdx or size sign
                    pos_idx = int(p.get("positionIdx", 0))
                    if pos_idx == 2:
                        side = "SELL"
                    elif float(p.get("size", 0)) < 0:
                        side = "SELL"
                    else:
                        side = "BUY"

                pid = str(p.get("id", "") or p.get("positionId", ""))
                if not pid:
                    # Generate composite ID for positions without ID
                    pid = f"{p.get('symbol', '')}_{side}"

                result.append({
                    "id": pid,
                    "ticket": pid,  # Alias for compatibility
                    "symbol": p.get("symbol", ""),
                    "side": side,
                    "volume": abs(size),
                    "entry_price": float(
                        p.get("entryPrice", 0) or p.get("price", 0)
                    ),
                    "current_price": float(
                        p.get("markPrice", 0)
                        or p.get("currentPrice", 0)
                        or p.get("lastPrice", 0)
                    ),
                    "pnl": float(
                        p.get("unrealizedPnl", 0)
                        or p.get("pnl", 0)
                    ),
                    "leverage": float(p.get("leverage", 1)),
                    "margin": float(
                        p.get("initialMargin", 0)
                        or p.get("margin", 0)
                    ),
                    "liquidation_price": float(
                        p.get("liquidationPrice", 0) or 0
                    ),
                    "position_idx": int(p.get("positionIdx", 0)),
                    "position_mode": self.position_mode,
                    "collateral": float(p.get("collateral", 0)),
                    "unrealised_pnl_pct": float(
                        p.get("unrealisedPnlPct", 0)
                    ),
                    "auto_add_margin": int(p.get("autoAddMargin", 0)),
                })

            return result

        except Exception as e:
            logger.error(f"get_open_positions error: {e}")
            return []

    # ── Close Position Override ───────────────────────────────

    def close_position(self, position_id: str) -> Dict[str, Any]:
        """Close a position using Bybit reduce-only order.

        For spot: creates a market sell/buy order.
        For futures: uses reduceOnly + positionIdx for hedge safety.

        Args:
            position_id: Position ID string.

        Returns:
            Dict with result.
        """
        logger.info(f"Closing Bybit position: {position_id}")

        # Find the position
        positions = self.get_open_positions()
        pos = None
        for p in positions:
            if p.get("id") == position_id or str(p.get("id", "")) == position_id:
                pos = p
                break

        if not pos:
            return {"success": False, "error": "Position not found"}

        sym = pos.get("symbol", self.symbol)
        volume = pos.get("volume", 0)
        side = "sell" if pos.get("side") == "BUY" else "buy"

        try:
            result = self.create_order(
                symbol=sym,
                side=side,
                volume=volume,
                order_type="market",
                reduce_only=True,
                positionIdx=pos.get("position_idx", self._position_idx(side)),
            )
            return result
        except Exception as e:
            logger.error(f"close_position error: {e}")
            return {"success": False, "error": str(e)}

    # ── Balance Override ──────────────────────────────────────

    def get_balance(self) -> Dict[str, float]:
        """Get account balance from Bybit.

        For unified margin, returns cross-margin balance.
        Includes wallet balance, available balance, and used margin.

        Returns:
            Dict with balance, equity, margin, free_margin.
        """
        if not self.ensure_connection():
            return {"balance": 0, "equity": 0, "margin": 0, "free_margin": 0}

        try:
            balance = self._exchange.fetch_balance(params={
                "category": self.category,
            })

            # Determine quote currency
            quote = self.symbol.split("/")[-1] if "/" in self.symbol else "USDT"

            total_usd = 0.0
            free_usd = 0.0
            used_usd = 0.0

            if "total" in balance and quote in balance["total"]:
                total_usd = float(balance["total"][quote])
            if "free" in balance and quote in balance["free"]:
                free_usd = float(balance["free"][quote])
            if "used" in balance and quote in balance["used"]:
                used_usd = float(balance["used"][quote])

            # For futures, use 'walletBalance' and 'availableBalance'
            # from the raw response
            raw_info = balance.get("info", {})
            if self.category in ("linear", "inverse"):
                wallet_balance = float(
                    raw_info.get("walletBalance", 0)
                    or raw_info.get("totalWalletBalance", 0)
                    or total_usd
                )
                available = float(
                    raw_info.get("availableBalance", 0)
                    or raw_info.get("availableToWithdraw", 0)
                    or free_usd
                )
                used_margin = wallet_balance - available
                return {
                    "balance": wallet_balance,
                    "equity": total_usd or wallet_balance,
                    "margin": max(0, used_margin),
                    "free_margin": available,
                    "margin_level": raw_info.get("marginLevel", 0),
                    "profit": float(raw_info.get("unrealisedPnl", 0)),
                    "assets": balance,
                }

            return {
                "balance": total_usd,
                "equity": total_usd,
                "margin": used_usd,
                "free_margin": free_usd,
                "margin_level": 0.0,
                "profit": 0.0,
                "assets": balance,
            }

        except Exception as e:
            logger.error(f"get_balance error: {e}")
            return {"balance": 0, "equity": 0, "margin": 0, "free_margin": 0}

    # ── Funding Rate ──────────────────────────────────────────

    def fetch_funding_rate(
        self, symbol: str
    ) -> Dict[str, float]:
        """Fetch current funding rate from Bybit.

        Bybit funds every 8 hours (00:00, 08:00, 16:00 UTC).

        Returns:
            Dict with funding_rate, funding_time, next_funding_time.
        """
        if not self.ensure_connection():
            return {"funding_rate": 0.0, "funding_time": 0, "next_funding_time": 0}

        sym = self._normalise_symbol(symbol)
        try:
            # Use tickers which include funding rate info
            tickers = self._exchange.fetch_tickers(
                sym, params={"category": self.category}
            )
            ticker = tickers.get(sym, {})
            return {
                "funding_rate": float(
                    ticker.get("fundingRate", 0) or 0
                ),
                "funding_time": int(
                    ticker.get("fundingTimestamp", 0) or 0
                ),
                "next_funding_time": int(
                    ticker.get("nextFundingTime", 0) or 0
                ),
            }
        except Exception as e:
            logger.debug(f"fetch_funding_rate error: {e}")
            return {"funding_rate": 0.0, "funding_time": 0, "next_funding_time": 0}

    def fetch_funding_rate_history(
        self, symbol: str, days: int = 30
    ) -> pd.DataFrame:
        """Fetch historical funding rates.

        Args:
            symbol: Trading pair.
            days: How many days of history.

        Returns:
            DataFrame with timestamp and funding_rate columns.
        """
        if not self.ensure_connection():
            return pd.DataFrame()

        sym = self._normalise_symbol(symbol)
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        try:
            if self._exchange and self._exchange.has.get("fetchFundingRateHistory"):
                rates = self._exchange.fetch_funding_rate_history(
                    sym, since=since, params={"category": self.category}
                )
                if rates and len(rates) > 0:
                    rows = [
                        {
                            "timestamp": datetime.fromtimestamp(
                                r["timestamp"] / 1000
                            ),
                            "funding_rate": float(r.get("fundingRate", 0)),
                            "symbol": r.get("symbol", ""),
                        }
                        for r in rates
                    ]
                    df = pd.DataFrame(rows)
                    if len(df) > 0:
                        df = df.set_index("timestamp").sort_index()
                    return df
        except Exception as e:
            logger.debug(f"fetch_funding_rate_history error: {e}")

        return pd.DataFrame()

    # ── Conditional Order ─────────────────────────────────────

    def create_conditional_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        trigger_price: float,
        order_type: str = "stop",
        price: Optional[float] = None,
        reduce_only: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a conditional (trigger) order on Bybit.

        Args:
            symbol: Trading pair.
            side: "buy" or "sell".
            volume: Amount.
            trigger_price: Price that triggers the order.
            order_type: "stop", "stop_limit", "take_profit",
                       "take_profit_limit".
            price: Required for limit-type conditional orders.
            reduce_only: Whether order reduces position (default True).
            **kwargs: Additional params.

        Returns:
            Dict with order result.
        """
        # Defensive: remove keys that are already passed explicitly
        kwargs.pop("trigger_price", None)
        kwargs.pop("triggerPrice", None)
        kwargs.pop("reduce_only", None)

        return self.create_order(
            symbol=symbol,
            side=side,
            volume=volume,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            reduce_only=reduce_only,
            **kwargs,
        )

    # ── Cancel Order Override ─────────────────────────────────

    def cancel_order(
        self, order_id: str, symbol: Optional[str] = None
    ) -> bool:
        """Cancel an order on Bybit with category support."""
        if not self.ensure_connection():
            return False

        sym = self._normalise_symbol(symbol) if symbol else None
        try:
            self._exchange.cancel_order(
                order_id, sym,
                params=self._category_params(),
            )
            logger.info(f"Bybit order {order_id} cancelled")
            return True
        except ccxt.OrderNotFound:
            logger.warning(f"Order {order_id} not found")
            return False
        except Exception as e:
            logger.error(f"cancel_order error: {e}")
            return False

    # ── Symbol Override ───────────────────────────────────────

    def get_symbols_active(self) -> List[str]:
        """Get active symbols filtered by category.

        For linear: returns USDT perpetuals.
        For inverse: returns coin-margined futures.
        For spot: returns all spot pairs.
        """
        all_symbols = super().get_symbols_active()
        if self.category == "linear":
            return [s for s in all_symbols if s.endswith("/USDT")]
        elif self.category == "inverse":
            return [s for s in all_symbols if "/USD" in s.upper()]
        return all_symbols

    # ── Trade History Override ────────────────────────────────

    def get_trade_history(self, days: int = 30) -> pd.DataFrame:
        """Fetch trade history with category support."""
        if not self.ensure_connection():
            return pd.DataFrame()

        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        try:
            trades = self._exchange.fetch_my_trades(
                symbol=self.symbol,
                since=since,
                params=self._category_params(),
            )
            if not trades:
                return pd.DataFrame()

            rows = []
            for t in trades:
                rows.append({
                    "time": datetime.fromtimestamp(t["timestamp"] / 1000),
                    "symbol": t.get("symbol", ""),
                    "side": t.get("side", ""),
                    "type": t.get("type", ""),
                    "volume": float(t.get("amount", 0)),
                    "price": float(t.get("price", 0)),
                    "cost": float(t.get("cost", 0)),
                    "fee": float(t.get("fee", {}).get("cost", 0))
                           if t.get("fee") else 0,
                    "fee_currency": t.get("fee", {}).get("currency", "")
                                    if t.get("fee") else "",
                    "profit": float(t.get("profit", 0) or 0),
                    "order_id": str(t.get("order", "")),
                })

            df = pd.DataFrame(rows)
            if len(df) > 0:
                df = df.sort_values("time", ascending=False)
            return df
        except Exception as e:
            logger.error(f"get_trade_history error: {e}")
            return pd.DataFrame()
