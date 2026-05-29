"""Trading controller — thin orchestrator that wires services into trading cycles.

The TradingController is the central hub. It does NOT contain business logic;
instead it delegates to the appropriate service and repository. Exchange creation
and RPC setup are delegated to ExchangeFactory and RPCSetupService respectively.

Usage:
    ctrl = TradingController(config)
    ctrl.run_cycle()
    ctrl.status()
"""

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.configuration.manager import ConfigManager
from src.exchange.factory import ExchangeFactory
from src.exchange.base import IExchange
from src.data.provider import DataProvider
from src.rpc.base import RPCManager
from src.rpc.websocket import set_shared
from src.services.rpc_setup_service import RPCSetupService
from src.services.signal_service import SignalService
from src.services.strategy_service import StrategyService
from src.services.trade_execution_service import TradeExecutionService
from src.services.ml_service import MLService
from src.services.risk_service import RiskService
from src.services.system_service import SystemService
from src.services.notification_service import NotificationService
from src.services.backtest_service import BacktestService
from src.repositories.analytics_repo import AnalyticsRepository
from src.repositories.trade_repo import TradeRepository
from src.services.trading.order_manager import OrderManager
from src.services.trading.lock_manager import LockManager
from src.models.trade import Trade, TradeManager
from src.risk.manager import RiskManager
from src.risk.protection import ProtectionManager
from src.persistence.database import get_db
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradingController:
    """Thin orchestrator — initialises services and runs trading cycles."""

    def __init__(self, config: Optional[ConfigManager] = None,
                 bypass_lock: bool = False):
        self.config = config or ConfigManager()

        # ── PID Lock ──
        self.lock_manager = LockManager(lock_file="bot.lock")
        self.lock_manager.acquire(bypass=bypass_lock)

        self.symbol = self.config.get("general", "symbol")
        self.timeframe = self.config.get("general", "timeframe")

        # ── Trading Mode ──
        mode = self.config.get("trading", "mode")
        if mode is not None:
            self.trading_mode = mode.lower()
            self.paper_trading = self.trading_mode in ("paper", "dry-run")
        else:
            # Fallback: support paper_trading boolean from config
            self.paper_trading = self.config.get("trading", "paper_trading")
            self.trading_mode = "paper" if self.paper_trading else "live"

        # ── Exchange (via factory) ──
        self.exchange = ExchangeFactory.from_config(self.config)

        # ── Core subsystems ──
        self.data_provider = DataProvider(
            self.exchange, self.symbol, self.timeframe,
            default_count=self.config.get("general", "data_count"),
        )
        self.trade_manager = TradeManager()
        self.order_manager = OrderManager(self.config, self.exchange, self.trade_manager)

        self.risk_manager = RiskManager(self.config)
        self.protection_manager = ProtectionManager(self.config)

        # ── Repositories ──
        _db = get_db()
        self.analytics_repo = AnalyticsRepository(db=_db)
        self.trade_repo = TradeRepository(db=_db)

        # Wire trade_repo into order_manager for DB persistence
        self.order_manager.trade_repo = self.trade_repo

        # ── Services ──
        self.signal_service = SignalService()
        self.backtest_service = BacktestService(self.config, self.analytics_repo)
        self.strategy_service = StrategyService(
            self.config, self.backtest_service.engine, self.analytics_repo,
        )
        self.strategies = self.strategy_service.strategies
        self.best_strategy_name = self.strategy_service.best_strategy_name
        self.best_strategy = self.strategy_service.best_strategy
        self.disabled_strategies = self.strategy_service.disabled_strategies
        self.current_regime = self.strategy_service.current_regime
        self.trade_execution_service = TradeExecutionService(
            self.config, self.exchange, self.order_manager,
            self.trade_manager, None,  # rpc set later
        )
        self.ml_service = MLService(
            model_type=self.config.get("ml", "model_type"),
            retrain_interval_hours=self.config.get("ml", "retrain_interval_hours"),
            model_path=self.config.get("ml", "model_path"),
            config=self.config,
        )
        self.risk_service = RiskService(self.config, self.risk_manager, self.protection_manager, self.analytics_repo)
        self.system_service = SystemService()

        # ── RPC / Notifications (via RPCSetupService) ──
        self.rpc = RPCManager()
        self.notification_service = NotificationService(self.rpc)
        self._rpc_setup = RPCSetupService(self.config, self.rpc)
        self._rpc_setup.setup_all(self)
        self.trade_execution_service.rpc = self.rpc

        # ── Register concept drift alert hook ──
        self.ml_service.trainer.on("drift", self._on_concept_drift)

        # ── Cycle tracking ──
        # (State now managed by system_service)

        logger.info(f"Controller ready: {self.symbol}/{self.timeframe}, "
                    f"paper={self.paper_trading}, "
                    f"strategies={list(self.strategies.keys())}")

    # ── State Accessors ──────────────────────────────────────

    @property
    def auto_trading(self) -> bool:
        return self.system_service.auto_trading

    @auto_trading.setter
    def auto_trading(self, value: bool):
        self.system_service.auto_trading = value

    @property
    def stop_buy(self) -> bool:
        return self.system_service.stop_buy

    @stop_buy.setter
    def stop_buy(self, value: bool):
        self.system_service.stop_buy = value

    # ── Data ──

    def fetch_data(self, count: Optional[int] = None,
                   force_refresh: bool = False) -> pd.DataFrame:
        return self.data_provider.fetch(count=count, force_refresh=force_refresh)

    def get_current_price(self) -> Dict[str, float]:
        return self.exchange.fetch_ticker(self.symbol)

        # ── Backtest & Strategy ──

    def run_backtest_all(self, data: pd.DataFrame, callback: Optional[Callable] = None) -> Dict[str, Any]:
        results = self.strategy_service.run_backtest_all(data, callback=callback)
        # Update controller state from strategy service
        self.strategies = self.strategy_service.strategies
        self.best_strategy_name = self.strategy_service.best_strategy_name
        self.best_strategy = self.strategy_service.best_strategy
        self.current_regime = self.strategy_service.current_regime
        return results

    def validate_strategies(self, data: pd.DataFrame) -> Dict[str, bool]:
        result = self.strategy_service.validate_strategies(data)
        self.strategies = self.strategy_service.strategies
        self.disabled_strategies = self.strategy_service.disabled_strategies
        return result

    # ── Signal ──

    def get_signal(self, data: pd.DataFrame,
                   use_ml: bool = False,
                   use_agent: bool = False,
                   use_swarm: bool = False) -> int:
        sig = self.signal_service.get_signal(
            data=data,
            strategies=self.strategies,
            best_strategy=self.strategy_service.best_strategy,
            ml_trainer=self.ml_service.trainer,
            current_regime=self.strategy_service.current_regime,
            use_ml=use_ml,
            use_agent=use_agent,
            use_swarm=use_swarm,
            config=self.config,
        )
        return sig

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

    # ── Trading Cycle ──

    def run_cycle(self, force_refresh: bool = False) -> Dict:
        self.system_service.mark_cycle_start()
        logger.info(f"{'='*40}\nCycle #{self.system_service.cycle_count}")

        # Update Risk Balance and Open Positions before cycle starts
        try:
            if self.paper_trading:
                self.risk_manager.update_balance(self.order_manager.paper_balance)
                self.risk_manager.protection_ctx.open_positions = len(self.order_manager.paper_positions)
            else:
                acc = self.exchange.get_balance()
                if acc.get("balance"):
                    self.risk_manager.update_balance(acc["balance"])
                positions = self.exchange.get_open_positions(self.symbol)
                self.risk_manager.protection_ctx.open_positions = len(positions) if positions else 0
        except Exception as e:
            logger.error(f"Risk balance update failed: {e}")

        try:
            data = self.fetch_data(force_refresh=force_refresh)
        except Exception as e:
            self.system_service.mark_error()
            return {"success": False, "step": "fetch", "error": str(e)}
        try:
            self.run_backtest_all(data)
            if self.system_service.cycle_count == 1:
                self.validate_strategies(data)
        except Exception as e:
            return {"success": False, "step": "backtest", "error": str(e)}
        if self.paper_trading:
            try:
                self._update_paper_positions()
            except Exception as e:
                logger.error(f"Paper update failed: {e}")
        try:
            self._check_roi_take_profit()
        except Exception as e:
            logger.error(f"ROI check failed: {e}")
        try:
            dca_info = self._check_dca_opportunity()
            if dca_info:
                logger.info(f"DCA opportunity: {dca_info}")
                self.execute_dca(dca_info)
        except Exception as e:
            logger.error(f"DCA check failed: {e}")
        use_ml = self.config.get("signals", "use_ml")
        if use_ml:
            try:
                self.ml_service.ensure_trained(data)
                self.ml_service.retrain_if_needed(data)

                # ── Concept drift auto-retrain ────────────────
                # If latest accuracy dropped >5% vs previous runs,
                # force an immediate retrain with fresh data.
                # Guard: only retrain once per session to prevent
                # infinite loops if the market has permanently shifted.
                if self.ml_service.trainer.concept_drifted and not getattr(self, '_drift_retrained', False):
                    logger.warning("Concept drift detected — forcing immediate retrain...")
                    self._drift_retrained = True
                    fresh_data = self.fetch_data(force_refresh=True)
                    self.ml_service.train(fresh_data, save=True)
            except Exception as e:
                logger.warning(f"ML process failed: {e}")
        use_agent = self.config.get("signals", "use_agent")
        use_swarm = self.config.get("signals", "use_swarm")
        signal = self.get_signal(data, use_ml=use_ml,
                                 use_agent=use_agent,
                                 use_swarm=use_swarm)
        labels = {1: "BUY", -1: "SELL", 0: "HOLD"}
        logger.info(f"Signal: {labels.get(signal, '?')}")
        if not self.paper_trading:
            try:
                self.risk_service.update_trailing_stops(self.exchange, self.symbol)
            except Exception:
                pass
        if self.system_service.stop_buy and signal == 1:
            logger.info("Stop-buy active — skipping BUY signal")
            signal = 0
            
        if signal == 0:
            self.system_service.mark_success()
            return {"success": True, "signal": 0, "action": "HOLD",
                    "cycle": self.system_service.cycle_count}

        # --- Risk Check ---
        if not self.risk_service.can_trade():
            reason = self.risk_service.get_daily_stats().get("reason", "Risk limit reached")
            logger.warning(f"Trade blocked by risk service: {reason}")
            return {"success": False, "error": "risk_blocked", "reason": reason}

        result = self.execute_trade(signal)
        if result.get("success"):
            self.system_service.mark_success()
        else:
            self.system_service.mark_error()
            
        logger.info(f"Trade result: {result}")
        return result

    # ── Concept Drift Alert ──

    def _on_concept_drift(self, drift_info: dict) -> None:
        """Called when concept drift is detected after training.
        Broadcasts an alert to all notification backends (Telegram, WebSocket, etc.)."""
        try:
            msg = (
                f"🚨 <b>Concept Drift Detected</b>\n"
                f"Latest accuracy: <b>{drift_info.get('latest_acc', 0):.2%}</b>\n"
                f"Previous avg: <b>{drift_info.get('avg_prev_3', 0):.2%}</b>\n"
                f"Drop: <b style='color:#ef4444;'>{drift_info.get('drop_pct', 0):.1f}%</b>\n"
                f"Auto-retrain akan dijalankan pada siklus berikutnya."
            )
            self.notification_service.broadcast(msg)
        except Exception as e:
            logger.warning(f"Failed to send drift alert: {e}")

    # ── Backward-compat properties ──

    @property
    def paper_positions(self):
        """Backward-compat: dashboard accesses robot.paper_positions."""
        return self.order_manager.paper_positions

    @property
    def paper_balance(self):
        """Backward-compat: dashboard accesses robot.paper_balance."""
        return getattr(self.order_manager, 'paper_balance', self.config.get("trading", "paper_initial_balance"))

    @property
    def cycle_count(self) -> int:
        """Public accessor for dashboard."""
        return self.system_service.cycle_count

    @property
    def consecutive_errors(self) -> int:
        """Public accessor for dashboard."""
        return self.system_service.consecutive_errors

    @property
    def risk(self):
        """Backward-compat: dashboard accesses robot.risk."""
        return self.risk_manager

    @property
    def ml_trainer(self):
        """Backward-compat: dashboard accesses robot.ml_trainer."""
        return self.ml_service.trainer

    def detect_regime(self, data: pd.DataFrame) -> str:
        """Detect market regime from price data."""
        return self.strategy_service.detect_regime(data)

    # Keep backward-compat alias
    _detect_regime = detect_regime

    # ── Status ──

    def status(self) -> Dict:
        """Get full status dict for dashboard and CLI."""
        health = self.system_service.get_health_status()
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "trading_mode": self.trading_mode,
            "strategies": list(self.strategies.keys()),
            "disabled_strategies": getattr(self, 'disabled_strategies', []),
            "best_strategy": self.strategy_service.best_strategy_name,
            "current_regime": self.strategy_service.current_regime,
            "auto_trading": self.auto_trading,
            "risk": self.risk_service.get_state(),
            "paper_trading": self.paper_trading,
            "paper_positions": len(self.order_manager.paper_positions),
            "has_data": self.data_provider.last_data is not None,
            "connection": self.exchange.is_connected(),
            "cycle_count": health["cycle_count"],
            "consecutive_errors": health["consecutive_errors"],
            "last_cycle_time": health["last_cycle_time"],
            "ml_trained": self.ml_service.is_trained,
            "ml_accuracy": self.ml_service.last_accuracy,
            "ml_concept_drifted": self.ml_service.trainer.concept_drifted,

        }

    # ── Cleanup ──

    def cleanup(self):
        """Shut down controller gracefully."""
        logger.info("Shutting down controller...")
        self._rpc_setup.stop_all()
        for backend in self.rpc._backends:
            try:
                if hasattr(backend, "stop_polling"):
                    backend.stop_polling()
            except Exception:
                pass
        self.exchange.disconnect()
        try:
            get_db().close()
        except Exception:
            pass
        self.lock_manager.release()
        logger.info("Controller shutdown complete")
