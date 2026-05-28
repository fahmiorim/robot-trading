"""Trade execution service — order execution, DCA management, ROI take-profit."""

from typing import Any, Callable, Dict, Optional

from src.configuration.manager import ConfigManager
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradeExecutionService:
    """Manages trade execution: order placement, DCA, and ROI take-profit checks.

    Usage:
        service = TradeExecutionService(config, exchange, order_manager, trade_manager)
        result = service.execute_trade(signal=1)
        service.check_roi_take_profit()
        dca = service.check_dca_opportunity()
    """

    def __init__(self, config: ConfigManager, exchange, order_manager, trade_manager,
                 rpc_manager=None):
        self.config = config
        self.exchange = exchange
        self.order_manager = order_manager
        self.trade_manager = trade_manager
        self.rpc = rpc_manager

        from src.trading.dca_manager import DCAManager
        from src.trading.roi_manager import ROIManager
        self.dca_manager = DCAManager(config)
        self.roi_manager = ROIManager(config)

        self._dca_tracker: Dict[str, int] = {}
        self._dca_timestamps: Dict[str, float] = {}

    # ── Basic Trade Execution ──

    def execute_trade(self, signal: int, symbol: str = None,
                      volume: Optional[float] = None,
                      sl: Optional[float] = None,
                      tp: Optional[float] = None) -> Dict:
        """Execute a trade via the order manager."""
        sym = symbol or getattr(self.exchange, 'symbol', 'XAUUSD')
        return self.order_manager.execute_trade(signal, sym, volume, sl, tp)

    def close_position(self, ticket: int) -> Dict:
        """Close a position by ticket number."""
        return self.order_manager.close_position(ticket)

    def get_current_price(self) -> Dict[str, float]:
        """Get current price for the active symbol."""
        symbol = getattr(self.exchange, 'symbol', 'XAUUSD')
        return self.exchange.fetch_ticker(symbol)

    # ── ROI Take-Profit ──

    def check_roi_take_profit(self, paper_trading: bool) -> None:
        """Check and close positions that have reached ROI take-profit."""
        symbol = getattr(self.exchange, 'symbol', 'XAUUSD')
        self.roi_manager.check_take_profit(
            exchange=self.exchange,
            symbol=symbol,
            paper_trading=paper_trading,
            close_position_fn=self.close_position,
        )

    # ── DCA (Dollar Cost Averaging) ──

    def check_dca_opportunity(self, paper_trading: bool,
                              paper_positions: list = None,
                              paper_balance: float = 10000.0) -> Optional[Dict]:
        """Check if there's a DCA opportunity."""
        return self.dca_manager.check_opportunity(
            paper_positions=paper_positions or [],
            get_current_price_fn=self.get_current_price,
            paper_trading=paper_trading,
            paper_balance=paper_balance,
        )

    def execute_dca(self, dca_info: Dict, current_regime: str) -> Dict:
        """Execute a DCA order."""
        return self.dca_manager.execute_dca(
            dca_info=dca_info,
            execute_trade_fn=self.execute_trade,
            rpc_send_trade_alert_fn=self.rpc.send_trade_alert if self.rpc else (lambda *a, **kw: None),
            current_regime=current_regime,
        )
