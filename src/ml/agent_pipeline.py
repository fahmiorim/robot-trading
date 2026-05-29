import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from src.configuration.manager import ConfigManager


class AgentPipeline:
    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.agents = {}
        self.results = {}
    
    def scout_agent(self, data: pd.DataFrame) -> Dict[str, Any]:
        sma_fast_period = self.config.get("agent", "sma_fast_period")
        sma_medium_period = self.config.get("agent", "sma_medium_period")
        sma_slow_period = self.config.get("agent", "sma_slow_period")
        vol_window = self.config.get("agent", "volatility_window")
        signals = {}
        sma_fast = data['close'].rolling(sma_fast_period).mean().iloc[-1]
        sma_slow = data['close'].rolling(sma_medium_period).mean().iloc[-1]
        sma_50 = data['close'].rolling(sma_slow_period).mean().iloc[-1]
        price = data['close'].iloc[-1]
        signals['trend'] = 'bullish' if sma_fast > sma_slow else 'bearish'
        signals['momentum'] = (price - sma_50) / sma_50 if sma_50 > 0 else 0
        signals['volatility'] = data['close'].pct_change().rolling(vol_window).std().iloc[-1]
        return signals
    
    def risk_audit_agent(self, signals: Dict) -> Dict:
        position_size = self.config.get("agent", "position_size")
        vol_high = self.config.get("agent", "volatility_high")
        vol_medium = self.config.get("agent", "volatility_medium")
        audit = {'approved': True, 'max_position': position_size, 'risk_level': 'medium'}
        if signals['volatility'] > vol_high:
            audit['approved'] = False
            audit['risk_level'] = 'high'
        elif signals['volatility'] > vol_medium:
            audit['risk_level'] = 'medium'
        else:
            audit['risk_level'] = 'low'
        return audit
    
    def decision_core(self, scout_signals: Dict, risk_audit: Dict, regime: str) -> int:
        if not risk_audit['approved']:
            return 0
        trend = scout_signals['trend']
        momentum = scout_signals['momentum']
        weight_trending = self.config.get("agent", "regime_weight_trending")
        weight_ranging = self.config.get("agent", "regime_weight_ranging")
        weight_choppy = self.config.get("agent", "regime_weight_choppy")
        regime_weights = {
            'trending': weight_trending,
            'ranging': weight_ranging,
            'choppy': weight_choppy
        }
        weight = regime_weights.get(regime, weight_choppy)
        momentum_threshold = self.config.get("agent", "momentum_threshold")
        if trend == 'bullish' and momentum > momentum_threshold * weight:
            return 1
        elif trend == 'bearish' and momentum < -momentum_threshold * weight:
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


_agent_pipeline_instance: Optional[AgentPipeline] = None


def get_agent_signal(data: pd.DataFrame, config: Optional[ConfigManager] = None) -> int:
    """Helper function to run agent pipeline and return signal."""
    global _agent_pipeline_instance
    if _agent_pipeline_instance is None:
        _agent_pipeline_instance = AgentPipeline(config=config)
    elif config is not None:
        _agent_pipeline_instance.config = config

    cfg = _agent_pipeline_instance.config
    from src.analysis.regime import RegimeDetector
    regime_detector = RegimeDetector(
        adx_period=cfg.get("risk_management", "adx_period"),
        adx_threshold=cfg.get("risk_management", "adx_threshold"),
        window_size=cfg.get("risk_management", "window_size"),
        slope_threshold=cfg.get("risk_management", "slope_threshold"),
        volatility_threshold=cfg.get("risk_management", "volatility_threshold"),
    )
    regime = regime_detector.detect_regime(data)
    result = _agent_pipeline_instance.run_pipeline(data, regime)
    return result.get('decision', 0)
