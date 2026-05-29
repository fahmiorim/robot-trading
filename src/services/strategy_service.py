"""Strategy service — strategy selection, backtesting, regime detection."""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.configuration.manager import ConfigManager
from src.strategy.interface import create_strategies_from_config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class StrategyService:
    """Manages strategy lifecycle: selection, backtesting, validation, regime detection.

    Usage:
        service = StrategyService(config, backtester, analytics_repo)
        results = service.run_backtest_all(data)
        service.detect_regime(data)
    """

    def __init__(self, config: ConfigManager, backtester, analytics_repo=None):
        self.config = config
        self.backtester = backtester
        self.analytics_repo = analytics_repo

        # Strategy state
        self.strategies = create_strategies_from_config(config)
        self.best_strategy_name: Optional[str] = None
        self.best_strategy = None
        self.disabled_strategies: List[str] = []
        self.current_regime: str = "unknown"
        self._last_results: Dict[str, Any] = {}

    # ── Backtesting ──

    def run_backtest_all(self, data: pd.DataFrame, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run backtest on all enabled strategies and determine best performer."""
        results: Dict[str, Any] = {}
        total = len(self.strategies)
        for idx, (name, strategy) in enumerate(self.strategies.items()):
            try:
                signals = strategy.calculate_signals(data)
                result = self.backtester.run(data, signals, name)
                results[name] = result
                logger.info(f"  {name}: return={result['total_return']:.2f}%, "
                           f"trades={result['num_trades']}, "
                           f"wr={result.get('win_rate', 0):.1f}%")
                if callback:
                    try:
                        callback(name, idx + 1, total, result)
                    except Exception as cb_err:
                        logger.warning(f"Backtest callback error for {name}: {cb_err}")
            except Exception as e:
                logger.error(f"  {name}: backtest failed: {e}")

        self.current_regime = self.detect_regime(data)
        logger.info(f"Regime: {self.current_regime.upper()}")

        weights = self._get_regime_weights()
        weighted = {}
        for k, v in results.items():
            weight = weights.get(k, 1.0) # Default to 1.0 if not in weights
            weighted[k] = v.get("total_return", 0) * weight
            
        if weighted:
            best = max(weighted, key=lambda k: weighted[k])
            self.best_strategy_name = best
            self.best_strategy = self.strategies.get(best)
            logger.info(f"Best strategy: {best} (weighted: {weighted[best]:.2f})")

        # Log performance to analytics repo
        if self.analytics_repo:
            try:
                for name, r in results.items():
                    self.analytics_repo.log_performance({
                        "date": datetime.now().date(),
                        "strategy_name": name,
                        "regime": self.current_regime,
                        "trades_count": r["num_trades"],
                        "total_return": r["total_return"],
                        "win_rate": r.get("win_rate", 0),
                        "max_drawdown": r.get("max_drawdown", 0),
                        "sharpe_ratio": r.get("sharpe_ratio", 0),
                    })
            except Exception as e:
                logger.error(f"Log perf failed: {e}")

        self._last_results = results
        return results

    def validate_strategies(self, data: pd.DataFrame) -> Dict[str, bool]:
        """Validate strategies against minimum performance thresholds."""
        if not self.config.get("trading", "strategy_pre_validation"):
            return {n: True for n in self.strategies}

        results: Dict[str, bool] = {}
        self.disabled_strategies = []
        min_trades = self.config.get("trading", "min_backtest_trades")
        min_wr = self.config.get("trading", "min_win_rate")
        max_dd = self.config.get("trading", "max_backtest_drawdown")

        for name, strategy in list(self.strategies.items()):
            try:
                signals = strategy.calculate_signals(data)
                r = self.backtester.run(data, signals, name)
                issues = []
                if r["num_trades"] < min_trades:
                    issues.append(f"trades={r['num_trades']}<{min_trades}")
                if r.get("win_rate", 0) < min_wr:
                    issues.append(f"wr={r['win_rate']:.1f}%<{min_wr}%")
                if r.get("max_drawdown", 0) > max_dd:
                    issues.append(f"dd={r['max_drawdown']:.1f}%>{max_dd}%")
                if issues:
                    logger.warning(f"{name} FAILED: {', '.join(issues)}")
                    self.disabled_strategies.append(name)
                    del self.strategies[name]
                    results[name] = False
                else:
                    results[name] = True
            except Exception as e:
                logger.error(f"{name} error: {e}")
                self.disabled_strategies.append(name)
                del self.strategies[name]
                results[name] = False

        if self.disabled_strategies:
            logger.warning(f"Disabled: {self.disabled_strategies}")
        return results

    # ── Regime Detection ──

    def _get_regime_detector(self):
        """Build a RegimeDetector from config (risk_management section)."""
        from src.analysis.regime import RegimeDetector
        return RegimeDetector(
            adx_period=self.config.get("risk_management", "adx_period"),
            adx_threshold=self.config.get("risk_management", "adx_threshold"),
            window_size=self.config.get("risk_management", "window_size"),
            slope_threshold=self.config.get("risk_management", "slope_threshold"),
            volatility_threshold=self.config.get("risk_management", "volatility_threshold"),
        )

    def detect_regime(self, data: pd.DataFrame) -> str:
        """Detect market regime: trending / ranging / choppy / unknown."""
        if data is None or len(data) < 10:
            return "unknown"
            
        try:
            detector = self._get_regime_detector()
            return detector.detect_regime(data)
        except Exception:
            pass
        try:
            from src.analysis.indicators import calculate_adx
            adx_period = self.config.get("risk_management", "adx_period")
            adx_threshold = self.config.get("risk_management", "adx_threshold")
            window_size = self.config.get("risk_management", "window_size")
            volatility_threshold = self.config.get("risk_management", "volatility_threshold")
            
            if len(data) < adx_period * 2:
                return "unknown"
                
            adx_series = calculate_adx(data["high"], data["low"], data["close"], period=adx_period).dropna()
            if len(adx_series) == 0:
                return "unknown"
            current_adx = adx_series.iloc[-1]
            if current_adx > adx_threshold:
                return "trending"
            
            if len(data) < window_size:
                return "choppy" # Fallback if not enough for volatility

            volatility_series = data["close"].pct_change().rolling(window_size).std().dropna()
            if len(volatility_series) == 0:
                return "choppy"
            volatility = volatility_series.iloc[-1]
            return "ranging" if volatility < volatility_threshold else "choppy"
        except Exception:
            return "unknown"

    # Keep backward-compat alias
    _detect_regime = detect_regime

    def _get_regime_weights(self) -> Dict[str, float]:
        regime = self.current_regime if self.current_regime != "unknown" else "choppy"
        return self.config.get("strategy_weights", regime)

    # ── Status ──

    def get_status(self) -> Dict:
        return {
            "strategies": list(self.strategies.keys()),
            "disabled_strategies": self.disabled_strategies,
            "best_strategy": self.best_strategy_name,
            "current_regime": self.current_regime,
        }
