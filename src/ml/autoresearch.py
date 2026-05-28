import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json
import os

class AutoresearchLoop:
    def __init__(self, history_file: str = "trained_models/performance_history.json"):
        self.history_file = history_file
        self.performance_history = []
        self._load_history()
    
    def _load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                self.performance_history = json.load(f)
    
    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(self.performance_history, f, indent=2)
    
    def evaluate_strategy(self, strategy_name: str, return_pct: float, num_trades: int, regime: str) -> Dict:
        score = {
            'strategy': strategy_name,
            'return': return_pct,
            'trades': num_trades,
            'regime': regime,
            'timestamp': datetime.now().isoformat(),
            'sharpe': return_pct / max(num_trades, 1) if num_trades > 0 else 0
        }
        self.performance_history.append(score)
        self._save_history()
        return score
    
    def find_worst_performer(self, regime: str, days: int = 30) -> Dict:
        cutoff = datetime.now() - timedelta(days=days)
        relevant = [h for h in self.performance_history 
                   if h['regime'] == regime and datetime.fromisoformat(h['timestamp']) > cutoff]
        if not relevant:
            return None
        worst = min(relevant, key=lambda x: x['return'])
        return worst
    
    def find_best_performer(self, regime: str, days: int = 30) -> Dict:
        cutoff = datetime.now() - timedelta(days=days)
        relevant = [h for h in self.performance_history 
                   if h['regime'] == regime and datetime.fromisoformat(h['timestamp']) > cutoff]
        if not relevant:
            return None
        best = max(relevant, key=lambda x: x['return'])
        return best
    
    def suggest_improvement(self, worst: Dict) -> Dict:
        suggestions = {
            'MA_Crossover': {'fast_period': lambda x: max(5, x - 2), 'slow_period': lambda x: max(20, x + 5)},
            'RSI': {'period': lambda x: min(20, max(10, x + 2)), 'oversold': lambda x: min(35, x + 5)},
            'MACD': {'fast': lambda x: min(16, max(8, x)), 'slow': lambda x: min(30, max(20, x))},
            'Bollinger': {'period': lambda x: min(25, max(15, x)), 'std_dev': lambda x: min(2.5, max(1.5, x))},
            'Breakout': {'lookback': lambda x: min(30, max(10, x + 5))}
        }
        strategy = worst['strategy']
        if strategy not in suggestions:
            return {}
        return suggestions[strategy]
    
    def get_regime_performance(self, regime: str) -> Dict:
        relevant = [h for h in self.performance_history if h['regime'] == regime]
        if not relevant:
            return {'avg_return': 0, 'total_trades': 0}
        return {
            'avg_return': np.mean([h['return'] for h in relevant]),
            'total_trades': sum([h['trades'] for h in relevant])
        }
