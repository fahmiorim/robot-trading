"""ML package — model, trainer, features, agent pipeline, regime detection, swarm."""

from src.ml.model import MLModel  # noqa: F401
from src.ml.trainer import Trainer  # noqa: F401
from src.ml.agent_pipeline import AgentPipeline  # noqa: F401
from src.ml.regime_detector import RegimeDetector  # noqa: F401
from src.ml.swarm_intelligence import SwarmIntelligence  # noqa: F401
from src.ml.autoresearch import AutoresearchLoop  # noqa: F401


def get_deep_learning_trader(*args, **kwargs):
    """Lazy import to avoid requiring torch at import time."""
    from src.ml.lstm_model import DeepLearningTrader as _DLT  # noqa: F811
    return _DLT(*args, **kwargs)
