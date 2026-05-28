import pandas as pd
import numpy as np
from typing import Dict, Any

class AgentPipeline:
    def __init__(self):
        self.agents = {}
        self.results = {}
    
    def scout_agent(self, data: pd.DataFrame) -> Dict[str, Any]:
        signals = {}
        sma_fast = data['close'].rolling(10).mean().iloc[-1]
        sma_slow = data['close'].rolling(30).mean().iloc[-1]
        sma_50 = data['close'].rolling(50).mean().iloc[-1]
        price = data['close'].iloc[-1]
        signals['trend'] = 'bullish' if sma_fast > sma_slow else 'bearish'
        signals['momentum'] = (price - sma_50) / sma_50 if sma_50 > 0 else 0
        signals['volatility'] = data['close'].pct_change().rolling(20).std().iloc[-1]
        return signals
    
    def risk_audit_agent(self, signals: Dict, position_size: float = 0.01) -> Dict:
        audit = {'approved': True, 'max_position': position_size, 'risk_level': 'medium'}
        if signals['volatility'] > 0.02:
            audit['approved'] = False
            audit['risk_level'] = 'high'
        elif signals['volatility'] > 0.01:
            audit['risk_level'] = 'medium'
        else:
            audit['risk_level'] = 'low'
        return audit
    
    def decision_core(self, scout_signals: Dict, risk_audit: Dict, regime: str) -> int:
        if not risk_audit['approved']:
            return 0
        trend = scout_signals['trend']
        momentum = scout_signals['momentum']
        regime_weights = {
            'trending': 1.0,
            'ranging': 0.7,
            'choppy': 0.5
        }
        weight = regime_weights.get(regime, 0.5)
        if trend == 'bullish' and momentum > 0.001 * weight:
            return 1
        elif trend == 'bearish' and momentum < -0.001 * weight:
            return -1
        return 0
    
    def run_pipeline(self, data: pd.DataFrame, regime: str) -> Dict:
        scout = self.scout_agent(data)
        risk = self.risk_audit_agent(scout)
        decision = self.decision_core(scout, risk, regime)
        return {
            'signals': scout,
            'risk': risk,
            'decision': decision,
            'regime': regime
        }


def get_agent_signal(data: pd.DataFrame) -> int:
    """Helper function to run agent pipeline and return signal."""
    from src.analysis.regime import RegimeDetector
    regime = RegimeDetector().detect_regime(data)
    pipeline = AgentPipeline()
    result = pipeline.run_pipeline(data, regime)
    return result.get('decision', 0)
