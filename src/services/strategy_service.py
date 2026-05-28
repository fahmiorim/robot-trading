"""Strategy service — strategy selection, backtesting, regime detection."""

from datetime import datetime
from typing import Any, Dict, List, Optional

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

    def run_backtest_all(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest on all enabled strategies and determine best performer."""
        results: Dict[str, Any] = {}
        for name, strategy in self.strategies.items():
            try:
                signals = strategy.calculate_signals(data)
                result = self.backtester.run(data, signals, name)
                results[name] = result
                logger.info(f"  {name}: return={result['total_return']:.2f}%, "
                           f"trades={result['num_trades']}, "
                           f"wr={result.get('win_rate', 0):.1f}%")
            except Exception as e:
                logger.error(f"  {name}: backtest failed: {e}")

        self.current_regime = self.detect_regime(data)
        logger.info(f"Regime: {self.current_regime.upper()}")

        weights = self._get_regime_weights()
        weighted = {k: v.get("total_return", 0) * weights.get(k, 0.5)
                    for k, v in results.items()}
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

    # ── Regime Detection (public) ──

    def detect_regime(self, data: pd.DataFrame) -> str:
        """Detect market regime: trending / ranging / choppy / unknown."""
        try:
            from src.analysis.regime import RegimeDetector
            detector = RegimeDetector()
            return detector.detect_regime(data)
        except Exception:
            pass
        try:
            from src.analysis.indicators import calculate_adx
            adx = calculate_adx(data["high"], data["low"], data["close"]).dropna()
            if len(adx) == 0:
                return "unknown"
            current_adx = adx.iloc[-1]
            if current_adx > 25:
                return "trending"
            volatility = data["close"].pct_change().rolling(20).std().iloc[-1] or 0
            return "ranging" if volatility < 0.003 else "choppy"
        except Exception:
            return "unknown"

    # Keep backward-compat alias
    _detect_regime = detect_regime

    def _get_regime_weights(self) -> Dict[str, float]:
        return self.config.get("strategy_weights", self.current_regime)

    # ── Status ──

    def get_status(self) -> Dict:
        return {
            "strategies": list(self.strategies.keys()),
            "disabled_strategies": self.disabled_strategies,
            "best_strategy": self.best_strategy_name,
            "current_regime": self.current_regime,
        }
