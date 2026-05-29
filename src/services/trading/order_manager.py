"""
Order management — executes trades (paper, live, OCO, stop-loss-limit).
"""
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.configuration.manager import ConfigManager
from src.exchange.base import IExchange
from src.models.trade import Trade, TradeManager
from src.constants.trading import OrderSide
from src.utils.logging import get_logger
from src.exchange.helpers import default_sl, default_tp

logger = get_logger(__name__)


class OrderManager:
    """Manages trade execution — paper trading, live orders, OCO, stop-loss-limit.

    Mode switching:
      - ``dry-run``: Paper trading, signals logged but no positions opened
      - ``paper``: Full paper trading simulation
      - ``live``: Real money trading via exchange
    """

    def __init__(self, config: ConfigManager, exchange: IExchange,
                 trade_manager: TradeManager,
                 trade_repo=None):
        self.config = config
        self.exchange = exchange
        self.trade_manager = trade_manager
        self.trade_repo = trade_repo  # optional — persist to DB if provided

        self.trading_mode = self.config.get("trading", "mode")
        self.paper_trading = self.trading_mode in ("paper", "dry-run")
        self.paper_initial_balance = self.config.get("trading", "paper_initial_balance")

        self.paper_balance = self.paper_initial_balance
        self.paper_positions: List[Dict] = []
        self._last_paper_trade_time: float = 0
        self._consecutive_errors: int = 0

        # Load open positions from DB for paper trading (Persistence fix)
        if self.paper_trading and self.trade_repo:
            self._load_open_positions_from_db()

    def _load_open_positions_from_db(self):
        """Sync memory with database for paper positions on startup."""
        try:
            open_trades = self.trade_repo.find_open()
            for t in open_trades:
                if t.paper_trade:
                    # Convert model back to dict format for order_manager
                    pos_dict = t.to_dict()
                    # Mapping model keys to dict keys used in order_manager
                    pos_dict["action"] = t.side.value
                    pos_dict["price"] = t.entry_price
                    self.paper_positions.append(pos_dict)
                    # Also register in trade_manager memory
                    self.trade_manager.add_trade(t)
            
            if self.paper_positions:
                logger.info(f"Synced {len(self.paper_positions)} open paper positions from database")
        except Exception as e:
            logger.error(f"Failed to sync paper positions from DB: {e}")

    def execute_trade(self, signal: int, symbol: str,
                      volume: Optional[float] = None,
                      sl: Optional[float] = None,
                      tp: Optional[float] = None) -> Dict:
        """Execute a trade (real or paper depending on config)."""
        if self.trading_mode == "dry-run":
            logger.info(f"[DRY-RUN] Signal={signal}, would trade "
                       f"{volume or self.config.get('trading', 'paper_lot_size')}"
                       f" {symbol}")
            return {"success": True, "dry_run": True, "signal": signal}

        if self.paper_trading:
            vol = volume or self.config.get("trading", "paper_lot_size")
            return self._execute_paper_trade(signal, symbol, vol, sl, tp)

        # Live mode with optional custom order types
        order_cfg = self.config.get("order_types")
        use_custom = isinstance(order_cfg, dict) and order_cfg["custom"]

        if use_custom:
            use_oco = order_cfg["use_oco"]
            use_sll = order_cfg["use_stop_loss_limit"]

            if use_oco and sl is not None and tp is not None:
                return self._execute_oco_trade(signal, symbol, volume, sl, tp)
            if use_sll and sl is not None:
                return self._execute_stop_loss_limit_trade(signal, symbol, volume, sl, tp)

        return self._execute_real_trade(signal, symbol, volume, sl, tp)

    # ── Paper Trading ────────────────────────────────────────

    def _execute_paper_trade(self, signal: int, symbol: str, volume: float,
                              sl: Optional[float] = None,
                              tp: Optional[float] = None) -> Dict:
        max_pos = self.config.get("risk_management", "max_open_positions")
        if len(self.paper_positions) >= max_pos:
            return {"success": False, "error": f"Max paper positions ({max_pos})"}

        order_delay_ms = self.config.get("trading", "paper_order_delay_ms")
        actual_delay = random.uniform(order_delay_ms * 0.5, order_delay_ms * 2.0) / 1000.0
        time.sleep(min(actual_delay, 0.5))

        if time.time() - self._last_paper_trade_time < 10:
            return {"success": False, "error": "Paper cooldown (10s)"}

        price = self._get_price(symbol)
        slippage_pct = self.config.get("backtest", "slippage_pct")
        spread_cost = price.get("ask", 0) - price.get("bid", 0)
        if signal == 1:
            entry = price.get("ask", 0) + spread_cost * 0.5
        else:
            entry = price.get("bid", 0) - spread_cost * 0.5
        slippage = entry * (slippage_pct / 100.0) * random.uniform(0, 1)
        entry = entry + slippage if signal == 1 else entry - slippage
        if entry <= 0:
            return {"success": False, "error": "Invalid price"}

        sl_pct = self.config.get("risk_management", "stop_loss_pct") / 100
        tp_pct = self.config.get("risk_management", "take_profit_pct") / 100
        if sl is None:
            sl = default_sl(entry, "BUY" if signal == 1 else "SELL", sl_pct)
        if tp is None:
            tp = default_tp(entry, "BUY" if signal == 1 else "SELL", tp_pct)

        ticket = random.randint(100000, 999999)
        side = "BUY" if signal == 1 else "SELL"
        trade = {
            "ticket": ticket, "symbol": symbol,
            "action": side, "volume": volume,
            "price": entry, "sl": sl, "tp": tp,
            "profit": 0.0, "signal": signal,
            "comment": f"Paper {side}",
            "entry_time": datetime.now(),
            "paper_trade": 1,
        }
        self.paper_positions.append(trade)
        self._last_paper_trade_time = time.time()

        t = Trade(
            ticket=ticket, symbol=symbol,
            side=OrderSide.BUY if signal == 1 else OrderSide.SELL,
            volume=volume, entry_price=entry,
            entry_time=datetime.now(), sl=sl, tp=tp,
            paper_trade=True, comment=f"Paper {side}",
        )
        self.trade_manager.add_trade(t)

        # Persist to database
        if self.trade_repo:
            try:
                self.trade_repo.save(t)
            except Exception as e:
                logger.warning(f"Failed to persist paper trade to DB: {e}")

        logger.info(f"📝 Paper {side} {volume} {symbol} @ {entry:.2f}")
        return {"success": True, "paper": True, "order": ticket,
                "volume": volume, "price": entry}

    def close_paper_position(self, ticket: int) -> Dict:
        try:
            ticket = int(ticket)
        except (ValueError, TypeError):
            pass
        for pos in list(self.paper_positions):
            if pos["ticket"] == ticket:
                price = self._get_price(pos["symbol"])
                exit_p = price["bid"] if pos["action"] == "BUY" else price["ask"]
                pnl = self._calc_paper_pnl(pos, exit_p)
                pos["profit"] = pnl
                self.paper_balance += pnl
                self.paper_positions.remove(pos)
                self.trade_manager.close_trade(ticket, exit_p, pnl)

                # Persist exit to database
                if self.trade_repo:
                    try:
                        self.trade_repo.update_exit(ticket, exit_p, pnl)
                    except Exception as e:
                        logger.warning(f"Failed to update trade exit in DB: {e}")

                return {"success": True, "order": ticket, "profit": pnl}
        return {"success": False, "error": "Position not found"}

    def update_paper_positions(self) -> None:
        if not self.paper_positions:
            return
        
        # Group positions by symbol to minimize price fetch calls
        symbols = set(pos["symbol"] for pos in self.paper_positions)
        prices = {}
        for sym in symbols:
            try:
                prices[sym] = self.exchange.fetch_ticker(sym)
            except Exception as e:
                logger.error(f"Failed to fetch price for {sym}: {e}")

        for pos in list(self.paper_positions):
            sym = pos["symbol"]
            price = prices.get(sym)
            if not price:
                continue

            is_buy = pos["action"] == "BUY"
            current = price["bid"] if is_buy else price["ask"]
            if is_buy:
                if current <= pos.get("sl", 0) and pos.get("sl", 0) > 0:
                    self.close_paper_position(pos["ticket"])
                    continue
                if current >= pos.get("tp", float("inf")) and pos.get("tp", 0) > 0:
                    self.close_paper_position(pos["ticket"])
                    continue
            else:
                if current >= pos.get("sl", float("inf")) and pos.get("sl", 0) > 0:
                    self.close_paper_position(pos["ticket"])
                    continue
                if current <= pos.get("tp", 0) and pos.get("tp", 0) > 0:
                    self.close_paper_position(pos["ticket"])
                    continue
            pos["current_price"] = current
            pos["profit"] = self._calc_paper_pnl(pos, current)

    def _calc_paper_pnl(self, pos: Dict, exit_price: float) -> float:
        is_buy = pos["action"] == "BUY"
        symbol = pos.get("symbol")
        if not symbol:
             # Fallback to current bot symbol if missing in position dict
             symbol = self.config.get("general", "symbol")
        
        # Try to get contract size from exchange, fallback to config
        try:
            info = self.exchange.get_symbol_info(symbol)
            contract_size = info.get("contract_size", 100.0)
        except Exception:
            contract_size = float(self.config.get("order", "contract_size"))

        commission_pct = self.config.get("backtest", "commission_pct")
        if is_buy:
            pnl = (exit_price - pos["price"]) * pos["volume"] * contract_size
        else:
            pnl = (pos["price"] - exit_price) * pos["volume"] * contract_size
        entry_comm = pos["price"] * pos["volume"] * contract_size * (commission_pct / 100.0)
        exit_comm = exit_price * pos["volume"] * contract_size * (commission_pct / 100.0)
        return pnl - entry_comm - exit_comm

    # ── Live Orders ──────────────────────────────────────────

    def _execute_real_trade(self, signal: int, symbol: str,
                             volume: Optional[float] = None,
                             sl: Optional[float] = None,
                             tp: Optional[float] = None) -> Dict:
        if not self.exchange.ensure_connection():
            return {"success": False, "error": "Exchange not connected"}

        price = self._get_price(symbol)
        if not price or price.get("ask", 0) <= 0 or price.get("bid", 0) <= 0:
            return {"success": False, "error": "Invalid price"}
        entry = price["ask"] if signal == 1 else price["bid"]

        if volume is None:
            vol = self.config.get("trading", "paper_lot_size")
        else:
            vol = volume

        side = "BUY" if signal == 1 else "SELL"
        result = self.exchange.create_order(
            symbol=symbol, side=side, volume=vol,
            sl=sl, tp=tp, comment="AI Robot",
        )
        if result.get("success"):
            self._consecutive_errors = 0
            # Persist live trade to database
            if self.trade_repo:
                try:
                    ticket = result.get("order", 0)
                    t = Trade(
                        ticket=ticket, symbol=symbol,
                        side=OrderSide.BUY if signal == 1 else OrderSide.SELL,
                        volume=vol, entry_price=entry,
                        entry_time=datetime.now(), sl=sl, tp=tp,
                        paper_trade=False, comment="AI Robot",
                    )
                    self.trade_repo.save(t)
                except Exception as e:
                    logger.warning(f"Failed to persist live trade to DB: {e}")
        else:
            self._consecutive_errors += 1
        return result

    def _execute_oco_trade(self, signal: int, symbol: str,
                            volume: Optional[float] = None,
                            sl: Optional[float] = None,
                            tp: Optional[float] = None) -> Dict:
        if not self.exchange.ensure_connection():
            return {"success": False, "error": "Exchange not connected"}

        price = self._get_price(symbol)
        if not price or price.get("ask", 0) <= 0 or price.get("bid", 0) <= 0:
            return {"success": False, "error": "Invalid price"}
        entry = price["ask"] if signal == 1 else price["bid"]

        if volume is None:
            vol = self.config.get("trading", "paper_lot_size")
        else:
            vol = volume

        entry_result = self._execute_real_trade(signal, symbol, volume, sl=None, tp=None)
        if not entry_result.get("success"):
            return entry_result

        try:
            side = "BUY" if signal == 1 else "SELL"
            sl_pct = self.config.get("risk_management", "stop_loss_pct") / 100
            tp_pct = self.config.get("risk_management", "take_profit_pct") / 100
            oco_result = self.exchange.create_oco_order(
                symbol=symbol, side=side, volume=vol,
                price=entry,
                stop_loss_price=sl or default_sl(entry, side, sl_pct),
                take_profit_price=tp or default_tp(entry, side, tp_pct),
            )
            if oco_result.get("success"):
                self._consecutive_errors = 0
                return {**entry_result, "oco": oco_result}
            else:
                logger.warning(f"OCO placement failed: {oco_result}")
                return entry_result
        except NotImplementedError:
            logger.warning("OCO not supported by exchange")
            return entry_result
        except Exception as e:
            logger.error(f"OCO trade failed: {e}")
            return entry_result

    def _execute_stop_loss_limit_trade(self, signal: int, symbol: str,
                                        volume: Optional[float] = None,
                                        sl: Optional[float] = None,
                                        tp: Optional[float] = None) -> Dict:
        if not self.exchange.ensure_connection():
            return {"success": False, "error": "Exchange not connected"}

        entry_side = "BUY" if signal == 1 else "SELL"
        exit_side = "SELL" if signal == 1 else "BUY"

        entry_result = self._execute_real_trade(signal, symbol, volume, sl=None, tp=None)
        if not entry_result.get("success"):
            return entry_result

        price = self._get_price(symbol)
        entry = price["ask"] if signal == 1 else price["bid"]
        if volume is None:
            vol = self.config.get("trading", "paper_lot_size")
        else:
            vol = volume
        sl_pct = self.config.get("risk_management", "stop_loss_pct") / 100
        stop_loss = sl or default_sl(entry, entry_side, sl_pct)
        slip = float(self.config.get("order", "stoploss_limit_slip"))
        limit_price = stop_loss * (1 - slip) if exit_side == "SELL" else stop_loss * (1 + slip)

        try:
            protect_result = self.exchange.create_stop_loss_limit_order(
                symbol=symbol, side=exit_side, volume=vol,
                stop_price=stop_loss, limit_price=limit_price,
            )
            if protect_result.get("success"):
                self._consecutive_errors = 0
                return {**entry_result, "protect_order": protect_result.get("order_id", "")}
            else:
                logger.warning(f"Stop-loss-limit placement failed: {protect_result}")
                return entry_result
        except NotImplementedError:
            logger.warning("Stop-loss-limit not supported by exchange")
            return entry_result
        except Exception as e:
            logger.error(f"Stop-loss-limit failed: {e}")
            return entry_result

    def close_position(self, ticket: int) -> Dict:
        if self.paper_trading:
            return self.close_paper_position(ticket)
        return self.exchange.close_position(str(ticket))

    def _get_price(self, symbol: str) -> Dict[str, float]:
        return self.exchange.fetch_ticker(symbol)
