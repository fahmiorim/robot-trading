"""Technical analysis — indicators and market regime detection."""

from src.analysis.indicators import (
    calculate_rsi,
    calculate_sma,
    calculate_ema,
    calculate_bollinger_bands,
    calculate_adx,
    calculate_macd,
    calculate_atr,
)
from src.analysis.regime import RegimeDetector, DEFAULT_STRATEGY_WEIGHTS
from src.analysis.performance import (
    calculate_sharpe_ratio, calculate_sortino_ratio, calculate_calmar_ratio,
    calculate_max_drawdown, calculate_win_rate, calculate_profit_factor,
    calculate_avg_holding_time, build_equity_curve, summarize_trades,
    calculate_cagr, calculate_sqn, calculate_expectancy,
    calculate_streaks, calculate_monthly_returns, calculate_time_in_market,
)

__all__ = [
    "calculate_rsi", "calculate_sma", "calculate_ema",
    "calculate_bollinger_bands", "calculate_adx", "calculate_macd", "calculate_atr",
    "RegimeDetector", "DEFAULT_STRATEGY_WEIGHTS",
    "calculate_sharpe_ratio", "calculate_sortino_ratio", "calculate_calmar_ratio",
    "calculate_max_drawdown", "calculate_win_rate", "calculate_profit_factor",
    "calculate_avg_holding_time", "build_equity_curve", "summarize_trades",
    "calculate_cagr", "calculate_sqn", "calculate_expectancy",
    "calculate_streaks", "calculate_monthly_returns", "calculate_time_in_market",
]
