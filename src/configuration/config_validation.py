"""Configuration validation — validates config values and returns error/warning messages."""

from typing import Any, Dict, List

from src.constants.timeframes import TIMEFRAME_MAP
from src.utils.logging import get_logger

logger = get_logger(__name__)


def validate_config(config: Any) -> List[str]:
    """Validate config values. Returns list of error/warning messages.

    Args:
        config: ConfigManager instance with a ``get()`` method.
    """
    errors: List[str] = []

    symbol = config.get("general", "symbol")
    if not symbol or not isinstance(symbol, str):
        errors.append("general.symbol: must be a non-empty string")

    tf = config.get("general", "timeframe")
    if tf and tf not in TIMEFRAME_MAP:
        errors.append(f"general.timeframe: '{tf}' invalid")

    pos_size = config.get("risk_management", "position_size_pct")
    if pos_size is not None and not (0.01 <= pos_size <= 100):
        errors.append(f"risk_management.position_size_pct: {pos_size} out of range")

    max_dd = config.get("risk_management", "max_drawdown_pct")
    if max_dd is not None and not (0.1 <= max_dd <= 100):
        errors.append(f"risk_management.max_drawdown_pct: {max_dd} out of range")

    max_loss = config.get("risk_management", "max_daily_loss_pct")
    if max_loss is not None and not (0.1 <= max_loss <= 100):
        errors.append(f"risk_management.max_daily_loss_pct: {max_loss} out of range")

    sl = config.get("risk_management", "stop_loss_pct")
    if sl is not None and not (0.01 <= sl <= 50):
        errors.append(f"risk_management.stop_loss_pct: {sl} out of range")

    tp = config.get("risk_management", "take_profit_pct")
    if tp is not None and not (0.01 <= tp <= 100):
        errors.append(f"risk_management.take_profit_pct: {tp} out of range")

    max_pos = config.get("risk_management", "max_open_positions")
    if max_pos is not None and not (1 <= max_pos <= 100):
        errors.append(f"risk_management.max_open_positions: {max_pos} out of range")

    model = config.get("ml", "model_type")
    valid = {"random_forest", "gradient_boosting"}
    if model and model not in valid:
        errors.append(f"ml.model_type: '{model}' not in {valid}")

    bt_bal = config.get("backtest", "initial_balance")
    if bt_bal is not None and bt_bal <= 0:
        errors.append("backtest.initial_balance: must be positive")

    tg_enabled = config.get("notifications", "telegram_enabled")
    if tg_enabled:
        if not config.get("notifications", "telegram_bot_token"):
            errors.append("telegram_bot_token required when telegram_enabled=True")
        if not config.get("notifications", "telegram_chat_id"):
            errors.append("telegram_chat_id required when telegram_enabled=True")

    if errors:
        for e in errors:
            logger.warning(f"Config validation: {e}")
    else:
        logger.info("Config validation passed")
    return errors
