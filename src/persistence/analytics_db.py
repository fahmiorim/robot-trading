import json
import numpy as np
from datetime import datetime, date
from typing import Any, Dict, List, Optional


def _clean_numpy_types(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _clean_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_clean_numpy_types(x) for x in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return [_clean_numpy_types(x) for x in obj.tolist()]
    return obj

from src.utils.logging import get_logger

logger = get_logger(__name__)


class AnalyticsMixin:
    """Mixin providing analytics operations for DatabaseManager."""

    # ── Performance Log ──────────────────────────────────────

    def log_performance(self, perf: Dict[str, Any]) -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO performance_log
                    (date, strategy_name, regime, trades_count, total_return,
                     win_rate, max_drawdown, sharpe_ratio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    trades_count=VALUES(trades_count), total_return=VALUES(total_return),
                    win_rate=VALUES(win_rate), max_drawdown=VALUES(max_drawdown),
                    sharpe_ratio=VALUES(sharpe_ratio)
            """, (
                perf.get('date', date.today()), perf.get('strategy_name', 'unknown'),
                perf.get('regime'), perf.get('trades_count', 0),
                perf.get('total_return'), perf.get('win_rate'),
                perf.get('max_drawdown'), perf.get('sharpe_ratio'),
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Log performance failed: {e}")
            return False

    # ── Equity Snapshots ─────────────────────────────────────

    def save_equity_snapshot(self, balance: float, equity: Optional[float] = None,
                             drawdown_pct: Optional[float] = None) -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO equity_snapshots (timestamp, balance, equity, drawdown_pct)
                VALUES (%s, %s, %s, %s)
            """, (datetime.now(), balance, equity, drawdown_pct))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Save equity snapshot failed: {e}")
            return False

    def get_equity_curve(self, days: int = 30) -> List[Dict]:
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT timestamp, balance, equity, drawdown_pct
                FROM equity_snapshots
                WHERE timestamp >= NOW() - INTERVAL %s DAY
                ORDER BY timestamp ASC
            """, (days,))
            rows = self._rows_to_dicts(cursor.fetchall())
            cursor.close()
            return rows
        except Exception as e:
            logger.error(f"Get equity curve failed: {e}")
            return []

    # ── Config Snapshots ─────────────────────────────────────

    def save_config_snapshot(self, config_dict: Dict, notes: str = "") -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO config_snapshots (config_json, notes) VALUES (%s, %s)
            """, (json.dumps(config_dict), notes))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Save config snapshot failed: {e}")
            return False

    # ── Circuit Breaker Log ──────────────────────────────────

    def log_circuit_breaker(self, reason: str, drawdown_pct: Optional[float] = None,
                            balance_before: Optional[float] = None,
                            balance_after: Optional[float] = None,
                            cooldown_minutes: int = 120) -> Optional[int]:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO circuit_breaker_log
                    (triggered_at, reason, drawdown_pct, balance_before, balance_after, auto_reset_at)
                VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL %s MINUTE)
            """, (datetime.now(), reason, drawdown_pct, balance_before, balance_after, cooldown_minutes))
            conn.commit()
            cb_id = cursor.lastrowid
            cursor.close()
            return cb_id
        except Exception as e:
            logger.error(f"Log circuit breaker failed: {e}")
            return None

    def is_circuit_breaker_active(self, cooldown_minutes: int = 120) -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            # Use COALESCE for auto_reset_at, if it exists and is in the future, it's active.
            # Otherwise, check the cooldown from triggered_at.
            cursor.execute("""
                SELECT * FROM circuit_breaker_log
                WHERE status='active' AND (
                    (auto_reset_at IS NOT NULL AND auto_reset_at > NOW()) OR
                    (auto_reset_at IS NULL AND triggered_at >= NOW() - INTERVAL %s MINUTE)
                )
                ORDER BY triggered_at DESC LIMIT 1
            """, (cooldown_minutes,))
            row = cursor.fetchone()
            cursor.close()
            return row is not None
        except Exception as e:
            logger.error(f"Check CB active failed: {e}")
            return False

    # ── Hyperopt Results ─────────────────────────────────────

    def save_hyperopt_result(self, strategy_name: str, params: Dict[str, Any],
                             score: float, metrics: Dict[str, Any],
                             n_trials: int, elapsed: float) -> bool:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            clean_params = _clean_numpy_types(params)
            clean_metrics = {k: v for k, v in metrics.items()
                             if k not in ('equity_curve', 'trades')}
            clean_metrics = _clean_numpy_types(clean_metrics)
            cursor.execute("""
                INSERT INTO hyperopt_results
                    (strategy_name, best_params, best_score, metrics,
                     n_trials, elapsed_seconds, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    best_params=VALUES(best_params), best_score=VALUES(best_score),
                    metrics=VALUES(metrics), n_trials=VALUES(n_trials),
                    elapsed_seconds=VALUES(elapsed_seconds), updated_at=NOW()
            """, (
                strategy_name, json.dumps(clean_params), float(score),
                json.dumps(clean_metrics),
                int(n_trials), float(elapsed),
            ))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Save hyperopt result failed: {e}")
            return False

    def get_best_hyperopt_params(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT best_params, best_score FROM hyperopt_results
                WHERE strategy_name=%s ORDER BY best_score DESC LIMIT 1
            """, (strategy_name,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {'params': json.loads(row['best_params']),
                        'score': float(row['best_score'])}
            return None
        except Exception as e:
            logger.error(f"Get hyperopt params failed: {e}")
            return None

    def get_all_hyperopt_results(self) -> List[Dict]:
        """Get all hyperopt results from the database."""
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT strategy_name, best_params, best_score, metrics, n_trials, elapsed_seconds, created_at
                FROM hyperopt_results ORDER BY best_score DESC
            """)
            rows = cursor.fetchall()
            cursor.close()
            result = []
            for row in rows:
                result.append({
                    'strategy_name': row['strategy_name'],
                    'best_params': json.loads(row['best_params']),
                    'best_score': float(row['best_score']),
                    'n_trials': row['n_trials'],
                    'elapsed_seconds': float(row['elapsed_seconds']),
                })
            return result
        except Exception as e:
            logger.error(f"Get all hyperopt results failed: {e}")
            return []

    # ── ML Training Log ─────────────────────────────────────

    def save_ml_training_log(self, log_data: Dict[str, Any]) -> bool:
        """Save an ML training run record to ml_training_log."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            params_json = json.dumps(_clean_numpy_types(log_data.get('params_used', {})))
            class_dist_json = json.dumps(_clean_numpy_types(log_data.get('class_distribution', {})))
            fi_json = json.dumps(_clean_numpy_types(log_data.get('feature_importance', [])))

            cursor.execute("""
                INSERT INTO ml_training_log
                    (trained_at, model_type, accuracy, params_used,
                     class_distribution, feature_importance, n_samples,
                     data_range_start, data_range_end,
                     atr_multiplier, threshold, data_source, symbol, timeframe)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                log_data.get('model_type'),
                log_data.get('accuracy'),
                params_json,
                class_dist_json,
                fi_json,
                log_data.get('n_samples'),
                log_data.get('data_range_start'),
                log_data.get('data_range_end'),
                log_data.get('atr_multiplier'),
                log_data.get('threshold'),
                log_data.get('data_source', 'mt5'),
                log_data.get('symbol'),
                log_data.get('timeframe'),
            ))
            conn.commit()
            cursor.close()
            logger.info(f"ML training log saved: {log_data.get('model_type')} acc={log_data.get('accuracy')}")
            return True
        except Exception as e:
            logger.error(f"Save ML training log failed: {e}")
            return False

    def get_ml_training_log(self, limit: int = 20) -> List[Dict]:
        """Get recent ML training runs, newest first."""
        try:
            conn = self.connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM ml_training_log
                ORDER BY trained_at DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            result = []
            for row in rows:
                entry = dict(row)
                for json_field in ('params_used', 'class_distribution', 'feature_importance'):
                    if isinstance(entry.get(json_field), str):
                        try:
                            entry[json_field] = json.loads(entry[json_field])
                        except Exception:
                            pass
                result.append(self._rows_to_dicts([entry])[0])
            return result
        except Exception as e:
            logger.error(f"Get ML training log failed: {e}")
            return []

    # ── Health Check Log ────────────────────────────────────

    def log_health_check(self, status: str, mt5_connected: bool,
                         last_cycle_seconds_ago: Optional[int] = None,
                         consecutive_errors: int = 0,
                         error_message: Optional[str] = None) -> bool:
        """Log a health check entry to the health_check_log table."""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO health_check_log
                    (checked_at, status, mt5_connected, last_cycle_seconds_ago,
                     consecutive_errors, error_message)
                VALUES (NOW(), %s, %s, %s, %s, %s)
            """, (status, int(mt5_connected), last_cycle_seconds_ago,
                   consecutive_errors, error_message))
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Log health check failed: {e}")
            return False
