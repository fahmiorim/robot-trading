"""Execution mixin — trade execution methods extracted from TradingController."""

from typing import Any, Dict, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


class ExecutionMixin:
    """Mixin providing trade execution methods for TradingController.

    Requires the host class to have:
        self.config, self.exchange, self.order_manager, self.trade_manager,
        self.trade_execution_service, self.strategy_service, self.symbol
    """

    # ── Trade Execution ──

    def open_trade(self, symbol: str, side: str, volume: float,
                   sl: Optional[float] = None,
                   tp: Optional[float] = None) -> Dict:
        old_symbol = self.symbol
        if symbol != old_symbol:
            self.symbol = symbol
        signal = 1 if side.lower() == "buy" else -1
        try:
            result = self.order_manager.execute_trade(signal, symbol, volume, sl, tp)
            if result.get("success") and "order" in result:
                result["ticket"] = result["order"]
        finally:
            self.symbol = old_symbol
        return result

    def execute_trade(self, signal: int,
                      volume: Optional[float] = None,
                      sl: Optional[float] = None,
                      tp: Optional[float] = None) -> Dict:
        return self.order_manager.execute_trade(signal, self.symbol, volume, sl, tp)

    def close_position(self, ticket: int) -> Dict:
        return self.order_manager.close_position(ticket)

    def update_paper_positions(self):
        """Public method: refresh paper positions from simulated exchange."""
        self.order_manager.update_paper_positions()

    # Keep backward-compat alias
    _update_paper_positions = update_paper_positions

    # ── ROI & DCA (via TradeExecutionService) ──

    def _check_roi_take_profit(self) -> None:
        self.trade_execution_service.check_roi_take_profit(self.paper_trading)

    def _check_dca_opportunity(self) -> Optional[Dict]:
        balance = (self.order_manager.paper_balance
                   if hasattr(self.order_manager, 'paper_balance')
                   else self.config.get("trading", "paper_initial_balance"))
        return self.trade_execution_service.check_dca_opportunity(
            paper_trading=self.paper_trading,
            paper_positions=self.order_manager.paper_positions,
            paper_balance=balance,
        )

    def execute_dca(self, dca_info: Dict) -> Dict:
        return self.trade_execution_service.execute_dca(
            dca_info, self.strategy_service.current_regime,
        )
