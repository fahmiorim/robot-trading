"""Background runner for Hyperparameter Optimization."""
import threading
from typing import Any, Dict, Optional, List
import pandas as pd
import numpy as np

from src.configuration.manager import ConfigManager
from src.backtesting.hyperopt import HyperoptEngine
from src.backtesting.engine import Backtester
from src.strategy.interface import IStrategy as BaseStrategy
from src.data.provider import DataProvider
from src.utils.logging import get_logger

logger = get_logger("hyperopt_runner")


class HyperoptRunner:
    """Manages Hyperparameter optimization running in a background thread.

    Thread-safe global singleton that allows multiple Streamlit browser sessions
    to monitor and interact with the same optimization task.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HyperoptRunner, cls).__new__(cls)
                cls._instance._init_runner()
            return cls._instance

    def _init_runner(self):
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.stop_requested = False
        
        # State variables
        self.running = False
        self.status = "idle"  # idle, fetching, optimizing, completed, failed, stopped
        self.error_message = ""
        
        self.strategy = "All"
        self.timeframe = "TIMEFRAME_M5"
        self.candles_count = 10000
        self.trials = 100
        self.optimize_risk = False
        
        # Current progress details
        self.current_strategy = ""
        self.strategy_index = 0
        self.total_strategies = 1
        
        self.current_trial = 0
        self.total_trials = 0
        self.best_score = 0.0
        self.best_params = {}
        self.current_score = 0.0
        self.current_params = {}
        self.convergence_history: List[Dict[str, Any]] = []
        
        # Combined final results
        self.results = {}

    def start(self, config: ConfigManager, robot: Any, strategy: str, timeframe: str, candles_count: int, trials: int, optimize_risk: bool) -> bool:
        """Start hyperopt in a background thread if not already running."""
        with self.lock:
            if self.running:
                logger.warning("Hyperopt is already running.")
                return False
                
            self.running = True
            self.status = "fetching"
            self.error_message = ""
            self.stop_requested = False
            
            self.strategy = strategy
            self.timeframe = timeframe
            self.candles_count = candles_count
            self.trials = trials
            self.optimize_risk = optimize_risk
            
            self.current_strategy = ""
            self.strategy_index = 0
            self.total_strategies = 1
            
            self.current_trial = 0
            self.total_trials = 0
            self.best_score = 0.0
            self.best_params = {}
            self.current_score = 0.0
            self.current_params = {}
            self.convergence_history = []
            self.results = {}
            
            # Start background thread
            self.thread = threading.Thread(
                target=self._run_optimization,
                args=(config, robot),
                daemon=True,
                name="hyperopt-runner"
            )
            self.thread.start()
            logger.info("Hyperopt background thread started.")
            return True

    def stop(self) -> None:
        """Signal the background thread to stop optimization."""
        with self.lock:
            if not self.running:
                return
            self.stop_requested = True
            self.status = "stopping"
            logger.info("Hyperopt stop requested by user.")

    def get_status(self) -> Dict[str, Any]:
        """Return the current status of the hyperopt execution."""
        with self.lock:
            return {
                "running": self.running,
                "status": self.status,
                "error_message": self.error_message,
                "strategy": self.strategy,
                "timeframe": self.timeframe,
                "candles_count": self.candles_count,
                "trials": self.trials,
                "optimize_risk": self.optimize_risk,
                "current_strategy": self.current_strategy,
                "strategy_index": self.strategy_index,
                "total_strategies": self.total_strategies,
                "current_trial": self.current_trial,
                "total_trials": self.total_trials,
                "best_score": self.best_score,
                "best_params": self.best_params,
                "current_score": self.current_score,
                "current_params": self.current_params,
                "convergence_history": list(self.convergence_history),
                "results": dict(self.results),
                "stop_requested": self.stop_requested
            }

    def _run_optimization(self, config: ConfigManager, robot: Any):
        try:
            # 1. Fetch Data
            logger.info(f"Fetching market data for Hyperopt: tf={self.timeframe}, count={self.candles_count}")
            try:
                local_provider = DataProvider(
                    exchange=robot.exchange,
                    symbol=robot.symbol,
                    timeframe=self.timeframe,
                    default_count=self.candles_count
                )
                data = local_provider.fetch(force_refresh=True)
                if data is None or data.empty:
                    raise ValueError("Data market kosong.")
            except Exception as e:
                logger.error(f"Hyperopt data fetch failed: {e}")
                with self.lock:
                    self.status = "failed"
                    self.error_message = f"Gagal mengambil data market: {e}"
                    self.running = False
                return

            if self.stop_requested:
                with self.lock:
                    self.status = "stopped"
                    self.running = False
                return

            # 2. Setup engine
            engine = HyperoptEngine(config, Backtester(config))
            registry = BaseStrategy.get_registry()

            # Determine target strategies
            if self.strategy == "All":
                target_strats = {sid: strat_cls for sid, strat_cls in registry.items() 
                                 if hasattr(strat_cls, 'param_space') and strat_cls.param_space}
            else:
                if self.strategy in registry:
                    target_strats = {self.strategy: registry[self.strategy]}
                else:
                    target_strats = {}

            if not target_strats:
                with self.lock:
                    self.status = "failed"
                    self.error_message = f"Strategi '{self.strategy}' tidak valid atau tidak memiliki parameter space."
                    self.running = False
                return

            with self.lock:
                self.status = "optimizing"
                self.total_strategies = len(target_strats)
                self.strategy_index = 0

            ho_results = {}

            for idx, (sid, strat_cls) in enumerate(target_strats.items()):
                if self.stop_requested:
                    break

                with self.lock:
                    self.current_strategy = sid
                    self.strategy_index = idx + 1
                    self.current_trial = 0
                    self.convergence_history = []
                    # For "All", trials are split, otherwise use total
                    trials_for_this = max(20, self.trials // len(target_strats)) if self.strategy == "All" else self.trials
                    self.total_trials = trials_for_this

                def callback(current, total, best_score, best_params, current_score=0.0, current_params=None):
                    if self.stop_requested:
                        raise InterruptedError("Hyperopt dihentikan oleh pengguna.")
                    
                    with self.lock:
                        self.current_trial = current
                        self.best_score = best_score
                        self.best_params = best_params
                        self.current_score = current_score
                        self.current_params = current_params or best_params
                        self.convergence_history.append({
                            "Trial": current,
                            "Best Score": best_score,
                            "Current Score": current_score
                        })

                try:
                    result = engine.optimize(
                        strat_cls, data,
                        n_trials=self.total_trials,
                        callback=callback,
                        optimize_risk=self.optimize_risk
                    )
                    
                    # Convert numpy objects in best_params to standard python types to avoid serialization issues
                    cleaned_params = {}
                    for k, v in result.best_params.items():
                        cleaned_params[k] = v.item() if hasattr(v, 'item') else v
                    
                    ho_results[sid] = {
                        'params': cleaned_params,
                        'score': result.best_score,
                        'metrics': result.best_results,
                        'n_trials': len(result.trials),
                        'copy_trials': list(result.trials), # backward compatibility
                        'elapsed': result.total_elapsed,
                    }
                except InterruptedError:
                    logger.info(f"Hyperopt optimization for {sid} interrupted.")
                    break
                except Exception as e:
                    logger.error(f"Hyperopt optimization failed for {sid}: {e}")
                    # In "All" mode, log error and continue to the next strategy
                    if self.strategy != "All":
                        with self.lock:
                            self.status = "failed"
                            self.error_message = f"Optimasi {sid} gagal: {e}"
                            self.running = False
                        return

            if self.stop_requested:
                with self.lock:
                    self.status = "stopped"
                    self.running = False
                logger.info("Hyperopt optimization stopped successfully.")
                return

            with self.lock:
                self.results = ho_results
                self.status = "completed"
                self.running = False
                
            logger.info("Hyperopt background optimization completed successfully.")

        except Exception as e:
            logger.error(f"Unexpected error in hyperopt background runner: {e}")
            with self.lock:
                self.status = "failed"
                self.error_message = f"Terjadi kesalahan sistem: {e}"
                self.running = False


def get_hyperopt_runner() -> HyperoptRunner:
    """Return the global HyperoptRunner singleton instance."""
    import sys
    if not hasattr(sys, "_global_hyperopt_runner"):
        sys._global_hyperopt_runner = HyperoptRunner()
    return sys._global_hyperopt_runner
