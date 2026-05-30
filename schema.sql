-- AI Trading Robot - MySQL Schema
-- Database: trading_bot

-- ── Risk Manager State ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_state (
    id          INT PRIMARY KEY DEFAULT 1,
    symbol      VARCHAR(20) NOT NULL,
    initial_balance     DECIMAL(15,2),
    peak_balance        DECIMAL(15,2),
    daily_start_balance DECIMAL(15,2),
    last_updated        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (id = 1)  -- singleton row
);

-- ── Trade History ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trade_history (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    ticket      BIGINT,
    symbol      VARCHAR(20) NOT NULL,
    action      VARCHAR(10) NOT NULL,       -- BUY / SELL
    volume      DECIMAL(10,2) NOT NULL,
    price       DECIMAL(15,5) NOT NULL,
    sl          DECIMAL(15,5),
    tp          DECIMAL(15,5),
    profit      DECIMAL(15,5),
    retcode     INT,
    comment     VARCHAR(255),
    strategy    VARCHAR(50),
    signal_val  INT DEFAULT 0,              -- 1=BULL, -1=BEAR, 0=HOLD
    status      VARCHAR(20) DEFAULT 'open', -- open / closed
    entry_time  DATETIME NOT NULL,
    exit_time   DATETIME,
    exit_price  DECIMAL(15,5),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entry_time (entry_time),
    INDEX idx_symbol (symbol),
    INDEX idx_status (status)
);

-- ── Signal Log ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signal_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    symbol      VARCHAR(20) NOT NULL,
    timestamp   DATETIME NOT NULL,
    source      VARCHAR(30) NOT NULL,       -- strategy / ml / agent / swarm
    signal_val  INT NOT NULL,               -- 1 / -1 / 0
    regime      VARCHAR(20),                -- trending / ranging / choppy
    price       DECIMAL(15,5),
    details     JSON,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_source (source)
);

-- ── Strategy Performance Log ─────────────────────────────────
CREATE TABLE IF NOT EXISTS performance_log (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    date            DATE NOT NULL,
    strategy_name   VARCHAR(50) NOT NULL,
    regime          VARCHAR(20),
    trades_count    INT DEFAULT 0,
    total_return    DECIMAL(10,2),
    win_rate        DECIMAL(5,2),
    max_drawdown    DECIMAL(5,2),
    sharpe_ratio    DECIMAL(5,2),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_strat_date (strategy_name, date),
    INDEX idx_date (date)
);

-- ── Equity Snapshots ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equity_snapshots (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    timestamp   DATETIME NOT NULL,
    balance     DECIMAL(15,2) NOT NULL,
    equity      DECIMAL(15,2),
    drawdown_pct DECIMAL(5,2),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp)
);

-- ── Config Snapshots ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS config_snapshots (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    saved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    config_json JSON NOT NULL,
    notes       VARCHAR(255)
);

-- ── Circuit Breaker Log ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS circuit_breaker_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    triggered_at DATETIME NOT NULL,
    reason      VARCHAR(255) NOT NULL,
    drawdown_pct DECIMAL(5,2),
    balance_before DECIMAL(15,2),
    balance_after  DECIMAL(15,2),
    auto_reset_at DATETIME,
    status      VARCHAR(20) DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_triggered_at (triggered_at)
);

-- Paper_trade column + index handled in database.py on connect
-- (MySQL 8.0 doesn't support ADD COLUMN IF NOT EXISTS)

-- ── Health Check Log ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS health_check_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    checked_at  DATETIME NOT NULL,
    status      VARCHAR(20) NOT NULL,       -- healthy / warning / error
    mt5_connected TINYINT(1),
    last_cycle_seconds_ago INT,
    consecutive_errors INT DEFAULT 0,
    error_message VARCHAR(255),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_checked_at (checked_at)
);

-- ── Hyperopt Results ──────────────────────────────────────────
-- ── Market Data Cache ──────────────────────────────────────
-- Cached OHLCV candles per symbol/timeframe to persist across restarts.
-- Avoids re-fetching from MT5 on every dashboard load.
CREATE TABLE IF NOT EXISTS market_data (
    symbol      VARCHAR(20) NOT NULL,
    timeframe   VARCHAR(30) NOT NULL,
    time        DATETIME NOT NULL,
    open        DECIMAL(15,5) NOT NULL,
    high        DECIMAL(15,5) NOT NULL,
    low         DECIMAL(15,5) NOT NULL,
    close       DECIMAL(15,5) NOT NULL,
    tick_volume BIGINT DEFAULT 0,
    spread      INT DEFAULT 0,
    real_volume BIGINT DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, timeframe, time),
    INDEX idx_symbol_tf (symbol, timeframe, time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS hyperopt_results (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    strategy_name   VARCHAR(50) NOT NULL,
    best_params     JSON NOT NULL,
    best_score      DECIMAL(10,4) NOT NULL,
    metrics         JSON,
    n_trials        INT DEFAULT 0,
    elapsed_seconds DECIMAL(10,2) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_strategy (strategy_name),
    INDEX idx_score (best_score DESC)
);

-- ── ML Training Log ────────────────────────────────────────────
-- Tracks every ML model training run: accuracy, class distribution,
-- feature importance, hyperparams, etc. Enables trend analysis and
-- concept drift detection over time.
CREATE TABLE IF NOT EXISTS ml_training_log (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    trained_at          DATETIME NOT NULL,
    model_type          VARCHAR(30) NOT NULL,
    accuracy            DECIMAL(6,4),
    params_used         JSON,
    class_distribution  JSON,
    feature_importance  JSON,
    n_samples           INT,
    data_range_start    DATETIME,
    data_range_end      DATETIME,
    atr_multiplier      DECIMAL(5,2),
    threshold           DECIMAL(6,4),
    data_source         VARCHAR(30) DEFAULT 'mt5',
    symbol              VARCHAR(20),
    timeframe           VARCHAR(20),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_trained_at (trained_at),
    INDEX idx_model_type (model_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Settings ─────────────────────────────────────────────────
-- All configuration values stored in DB instead of hardcoded defaults.
CREATE TABLE IF NOT EXISTS settings (
    section     VARCHAR(50) NOT NULL,
    key_name    VARCHAR(50) NOT NULL,
    symbol      VARCHAR(20) NOT NULL DEFAULT '' COMMENT 'empty = global default',
    timeframe   VARCHAR(30) NOT NULL DEFAULT '' COMMENT 'empty = global default',
    value       TEXT,
    value_type  VARCHAR(20) NOT NULL DEFAULT 'string',  -- string / int / float / bool / json
    description VARCHAR(255) DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (section, key_name, symbol, timeframe)
);

-- ── Seed settings ──────────────────────────────────────────
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'symbol',              '', '', 'XAUUSD',     'string', 'Trading symbol'),
('general', 'timeframe',           '', '', 'TIMEFRAME_M15', 'string', 'Chart timeframe'),
('general', 'auto_trade',          '', '', 'false',      'bool',   'Enable auto trading'),
('general', 'data_count',          '', '', '2000',       'int',    'Candles to fetch (~21 hari M15)'),
('general', 'magic_number',        '', '', '2024',       'int',    'MT5 magic number'),
('general', 'cycle_interval_minutes', '', '', '15',      'int',    'Minutes between auto cycles (1 candle M15)'),
-- exchange (minimal — hanya untuk MT5, UI tab dihapus karena tidak trading crypto)
('exchange', 'type',               '', '', 'mt5',        'string', 'Exchange backend type (mt5 / bybit / ccxt)'),
('exchange', 'default_sl_pct',     '', '', '0.005',      'float',  'Default SL pct (fraction) for retry orders'),
('exchange', 'default_tp_pct',     '', '', '0.01',       'float',  'Default TP pct (fraction) for retry orders'),
-- trading
('trading', 'mode',                '', '', 'live',       'string', 'live / paper / dry-run'),
('trading', 'paper_trading',       '', '', 'false',      'bool',   'Enable paper trading'),
('trading', 'paper_initial_balance','', '', '10000.0',    'float',  'Paper trading starting balance'),
('trading', 'paper_lot_size',      '', '', '0.01',       'float',  'Paper trading lot size'),
('trading', 'paper_order_delay_ms','', '', '500',        'int',    'Paper order delay ms'),
('trading', 'strategy_pre_validation', '', '', 'true',    'bool',   'Validate strategy before trading'),
('trading', 'min_backtest_trades', '', '', '20',         'int',    'Min backtest trades for validation'),
('trading', 'min_win_rate',        '', '', '35.0',       'float',  'Min win rate % for validation'),
('trading', 'max_backtest_drawdown','', '', '30.0',       'float',  'Max backtest drawdown %'),
('trading', 'max_consecutive_losses','', '', '5',         'int',    'Max consecutive losses before stop'),
-- signals
('signals', 'use_ml',               '', '', 'true',       'bool',   'Use ML signals'),
('signals', 'use_agent',            '', '', 'true',       'bool',   'Use agent signals'),
('signals', 'use_swarm',            '', '', 'false',      'bool',   'Use swarm signals'),
('signals', 'consensus_buy_threshold',  '', '', '0.6',    'float',  'Consensus buy threshold (0.6 = kedua sumber harus setuju)'),
('signals', 'consensus_sell_threshold', '', '', '-0.6',   'float',  'Consensus sell threshold (-0.6 = kedua sumber harus setuju)'),
-- risk_management
('risk_management', 'position_size_pct',       '', '', '2.0',  'float', 'Position size %% of balance. Trading M15: 2-3%%.'),
('risk_management', 'max_daily_loss_pct',      '', '', '5.0',  'float', 'Max daily loss %'),
('risk_management', 'max_drawdown_pct',        '', '', '15.0', 'float', 'Max drawdown %. M15: 15% karena swing lebih besar.'),
('risk_management', 'max_open_positions',      '', '', '2',    'int',   'Max concurrent positions. M15: 2 cukup — lebih sedikit setup per hari.'),
('risk_management', 'cooldown_minutes',        '', '', '15',   'int',   'Cooldown between trades. M15: 15 menit = 1 candle — cukup untuk validasi setup baru.'),
('risk_management', 'stop_loss_pct',           '', '', '0.5',  'float', 'Stop loss %. M15 scalping agresif: 0.5%%. RR 1:2 dengan TP 1.0%%.'),
('risk_management', 'take_profit_pct',         '', '', '1.0',  'float', 'Take profit %. M15 scalping agresif: 1.0%%. RR 1:2 dengan SL 0.5%%.'),
('risk_management', 'use_trailing_stop',       '', '', 'false', 'bool',  'Enable trailing stop'),
('risk_management', 'trailing_stop_activation_pct', '', '', '1.0', 'float', 'Trailing stop activation %% untuk M15. Harus < TP (1.0%% agar trailing aktif lebih awal).'),
('risk_management', 'trailing_stop_distance_pct',  '', '', '1.0', 'float', 'Trailing stop distance %. M15: 1%%.'),
('risk_management', 'circuit_breaker_enabled',      '', '', 'true', 'bool',  'Enable circuit breaker'),
('risk_management', 'circuit_breaker_loss_pct',     '', '', '5.0', 'float', 'Circuit breaker loss %. M15: 5% dalam 2 jam sudah warning.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', '', '240', 'int', 'Circuit breaker cooldown. M15: 4 jam untuk cooldown setelah circuit break.'),
('risk_management', 'adx_period',               '', '', '14',    'int',    'ADX calculation period'),
('risk_management', 'adx_threshold',            '', '', '25.0',  'float', 'ADX trending threshold'),
('risk_management', 'window_size',              '', '', '20',    'int',    'Regime detection window'),
('risk_management', 'slope_threshold',          '', '', '0.01',  'float', 'Regime slope threshold'),
('risk_management', 'volatility_threshold',     '', '', '0.015', 'float', 'Low volatility threshold untuk M15. 0.015 (1.5%%) — adaptasi dari M1 karena volatilitas M15 ~3.9x lebih besar per candle.'),
-- backtest
('backtest', 'initial_balance',   '', '', '10000',      'int',    'Backtest starting balance'),
('backtest', 'commission_pct',     '', '', '0.02',       'float',  'Commission %'),
('backtest', 'slippage_pct',       '', '', '0.1',        'float',  'Slippage %'),
-- ml
('ml', 'model_type',               '', '', 'gradient_boosting', 'string', 'ML model type — Gradient Boosting lebih akurat untuk M15 berdasarkan diagnostic test'),
('ml', 'retrain_interval_hours',   '', '', '12',        'int',    'Retrain interval hours. M15: 12 jam — retraining lebih jarang karena candle lebih sedikit.'),
('ml', 'model_path',               '', '', 'trained_models/{symbol}_{timeframe}.pkl', 'string', 'Model file path — {symbol}_{timeframe} resolved dynamically in code'),
('ml', 'n_estimators',             '', '', '100',    'int',    'Number of trees for RF/GB'),
('ml', 'max_depth',                '', '', '4',      'int',    'Max tree depth — 4 untuk M15 (lebih dalam dari M1 karena candle lebih bermakna)'),
('ml', 'min_samples_split',        '', '', '10',     'int',    'Min samples to split a node. M15: 10 — lebih konservatif karena lebih sedikit sampel per hari.'),
('ml', 'classification_threshold', '', '', '0.0',     'float',  'Min return threshold for buy/sell labels. 0.0 = pure ATR-adaptive — threshold dihitung dari ATR%% × atr_multiplier.'),
('ml', 'atr_multiplier',           '', '', '0.25',   'float',  'ATR multiplier for adaptive threshold. M15: 0.25 — cukup untuk menyaring noise sambil tetap mendapat sinyal.'),
-- notifications
('notifications', 'telegram_enabled',    '', '', 'false',  'bool',   'Enable Telegram'),
('notifications', 'telegram_bot_token',  '', '', '',       'string', 'Telegram bot token'),
('notifications', 'telegram_chat_id',    '', '', '',       'string', 'Telegram chat ID'),
('notifications', 'notify_daily_report', '', '', 'true',   'bool',   'Send daily report'),
-- health_check
('health_check', 'enabled',               '', '', 'true',  'bool',   'Enable health check'),
('health_check', 'check_interval_seconds','', '', '60',   'int',    'Health check interval'),
('health_check', 'max_consecutive_errors','', '', '5',    'int',    'Max consecutive errors. M15: 5 cukup — restart lebih cepat saat error beruntun.'),
('health_check', 'max_idle_minutes',      '', '', '60',   'int',    'Max idle minutes. M15: 60 menit = 4 candle tanpa aktivitas — bot mungkin stalled.'),
('health_check', 'auto_restart',           '', '', 'true',  'bool',  'Auto restart on failure'),
-- strategies (per-strategy JSON config)
('strategies', 'MA_Crossover',  '', '', '{"enabled":true,"fast_period":10,"slow_period":25}', 'json', ''),
('strategies', 'RSI',           '', '', '{"enabled":true,"period":9,"overbought":80,"oversold":20}', 'json', ''),
('strategies', 'MACD',          '', '', '{"enabled":true,"fast":12,"slow":26,"signal":9}', 'json', ''),
('strategies', 'Bollinger',     '', '', '{"enabled":true,"period":15,"std_dev":2.0}', 'json', ''),
('strategies', 'Breakout',      '', '', '{"enabled":true,"lookback":15}', 'json', ''),
-- strategy_weights (per-regime weighting)
('strategy_weights', 'trending', '', '', '{"MA_Crossover":1.0,"MACD":0.8,"Breakout":0.6,"RSI":0.3,"Bollinger":0.2}', 'json', ''),
('strategy_weights', 'ranging',  '', '', '{"Bollinger":1.0,"RSI":1.0,"MACD":0.3,"Breakout":0.3,"MA_Crossover":0.2}', 'json', ''),
('strategy_weights', 'choppy',   '', '', '{"RSI":1.0,"Bollinger":0.9,"MACD":0.5,"Breakout":0.1,"MA_Crossover":0.2}', 'json', ''),
-- order_types
('order_types', 'custom',               '', '', 'false', 'bool',  'Enable custom order types'),
('order_types', 'use_stop_loss_limit',  '', '', 'false', 'bool',  'Use stop-loss limit orders'),
('order_types', 'use_oco',              '', '', 'false', 'bool',  'Use OCO orders'),
-- roi
('roi', 'enabled',        '', '', 'true',  'bool', 'Enable ROI take-profit'),
('roi', 'table',          '', '', '[{"minutes":0,"roi_pct":100},{"minutes":15,"roi_pct":1.5},{"minutes":45,"roi_pct":1.0},{"minutes":120,"roi_pct":0.5},{"minutes":480,"roi_pct":0.2}]', 'json', 'ROI tiered table — M15: profit target turun bertahap (1.5% di 15 menit, 1.0% di 45 menit)'),
-- performance
('performance', 'risk_free_rate',   '', '', '0.02',  'float', 'Risk-free rate for Sharpe/Sortino'),
('performance', 'periods_per_year', '', '', '35040', 'int',   'Periods per year for Sharpe/Sortino. 35040 = M15 (96*365).'),
-- protection
('protection', 'max_stoploss',          '', '', '3',    'int',   'Max stoploss losses before halt. M15: 3, karena frekuensi trade lebih rendah (3-5/hari).'),
('protection', 'stoploss_window_hours', '', '', '4',    'int',   'Stoploss guard window hours. M15: 4 jam = 16 candle.'),
-- agent
('agent', 'sma_fast_period',       '', '', '10',    'int',   'SMA fast period'),
('agent', 'sma_medium_period',     '', '', '21',    'int',   'SMA medium period'),
('agent', 'sma_slow_period',       '', '', '30',    'int',   'SMA slow period. M15: 30 candle = 7.5 jam — tren intraday yang solid.'),
('agent', 'volatility_window',     '', '', '20',    'int',   'Volatility rolling window'),
('agent', 'position_size',         '', '', '0.01',  'float', 'Agent position size'),
('agent', 'volatility_high',       '', '', '0.0015',  'float', 'High volatility threshold (P95 XAUUSD M15)'),
('agent', 'volatility_medium',     '', '', '0.0012', 'float', 'Medium volatility threshold (P75 XAUUSD M15)'),
('agent', 'regime_weight_trending','', '', '1.0',   'float', 'Regime weight trending'),
('agent', 'regime_weight_ranging', '', '', '0.7',   'float', 'Regime weight ranging'),
('agent', 'regime_weight_choppy',  '', '', '0.5',   'float', 'Regime weight choppy'),
('agent', 'momentum_threshold',    '', '', '0.001', 'float', 'Momentum threshold'),
-- order
('order', 'contract_size',          '', '', '100.0', 'float', 'Default contract size'),
('order', 'stoploss_limit_slip',   '', '', '0.001', 'float', 'Stop-loss limit order slip distance'),
-- dca
('dca', 'enabled',               '', '', 'false',  'bool',   'Enable DCA'),
('dca', 'max_dca_orders',        '', '', '3',      'int',    'Max DCA orders'),
('dca', 'dca_increment_factor',  '', '', '1.5',    'float',  'DCA size increment'),
('dca', 'dca_trigger_pct',       '', '', '-1.0',   'float',  'DCA trigger %'),
('dca', 'dca_cooldown_minutes',  '', '', '30',     'int',    'DCA cooldown. M15: 30 menit = 2 candle — cukup untuk konfirmasi reversal.'),
('dca', 'dca_position_limit_pct','', '', '20.0',   'float',  'DCA position limit'),
('telegram_cmd', 'enabled',          '', '', 'false', 'bool',   'Enable Telegram commands'),
('telegram_cmd', 'allowed_chat_ids', '', '', '[]',   'json',   'Allowed chat IDs'),
-- rest_api
('rest_api', 'enabled',  '', '', 'false', 'bool',   'Enable REST API'),
('rest_api', 'host',     '', '', '0.0.0.0', 'string', 'REST API host'),
('rest_api', 'port',     '', '', '8000',   'int',    'REST API port'),
('rest_api', 'api_key',  '', '', '',       'string', 'REST API key'),
-- websocket
('websocket', 'host',     '', '', '0.0.0.0', 'string', 'WebSocket server host'),
('websocket', 'port',     '', '', '8765',    'int',    'WebSocket server port'),
-- features (feature engineering periods used by FeatureEngineer)
('features', 'returns_period_1',       '', '', '1',     'int',   'Returns period 1'),
('features', 'ema_fast_period',        '', '', '12',    'int',   'EMA fast period'),
('features', 'ema_slow_period',        '', '', '26',    'int',   'EMA slow period'),
('features', 'rsi_period',             '', '', '14',    'int',   'RSI calculation period'),
('features', 'bb_period',              '', '', '20',    'int',   'Bollinger Bands period'),
('features', 'bb_std_dev',             '', '', '2.0',   'float', 'Bollinger Bands std dev'),
('features', 'macd_fast_period',       '', '', '12',    'int',   'MACD fast EMA period'),
('features', 'macd_slow_period',       '', '', '26',    'int',   'MACD slow EMA period'),
('features', 'macd_signal_period',     '', '', '9',     'int',   'MACD signal line period'),
('features', 'atr_period',             '', '', '14',    'int',   'ATR calculation period'),
('features', 'volatility_window_fast', '', '', '10',    'int',   'Fast volatility rolling window'),
-- ml extras
('ml', 'swarm_learning_rate',          '', '', '0.05',  'float', 'Swarm weight update learning rate');

-- ── Per-Symbol Defaults (symbol, '') ────────────────────────
-- These override global defaults when context is set to a specific symbol.
-- Symbol-only entries apply to all timeframes for that symbol.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- magic_number: different per symbol for MT5
('general', 'magic_number',       'EURUSD', '', '2025', 'int',   'MT5 magic number for EURUSD'),
('general', 'magic_number',       'BTCUSD', '', '2026', 'int',   'MT5 magic number for BTCUSD'),
('general', 'magic_number',       'GBPUSD', '', '2027', 'int',   'MT5 magic number for GBPUSD'),
('general', 'magic_number',       'AUDUSD', '', '2028', 'int',   'MT5 magic number for AUDUSD'),
('general', 'magic_number',       'USDJPY', '', '2029', 'int',   'MT5 magic number for USDJPY');

-- ═══════════════════════════════════════════════════════════════
-- Per-Symbol + Per-Timeframe Defaults (symbol, timeframe)
-- Highest priority — specific combo overrides both symbol-only and timeframe-only.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- EURUSD is less volatile than XAUUSD, so tighter SL/TP across all TFs
-- EURUSD M15
('risk_management', 'stop_loss_pct',           'EURUSD', 'TIMEFRAME_M15', '0.35', 'float', 'SL % EURUSD M15 — tighter than XAUUSD (0.5%) due to lower volatility'),
('risk_management', 'take_profit_pct',         'EURUSD', 'TIMEFRAME_M15', '0.7',  'float', 'TP % EURUSD M15 — RR 1:2'),
('risk_management', 'position_size_pct',       'EURUSD', 'TIMEFRAME_M15', '1.5',  'float', 'Position size % EURUSD M15 — smaller than XAUUSD (2.0%)'),
('agent', 'volatility_high',       'EURUSD', 'TIMEFRAME_M15', '0.0008', 'float', 'Volatility high EURUSD M15 — EURUSD less volatile than XAUUSD (0.0015)'),
('agent', 'volatility_medium',     'EURUSD', 'TIMEFRAME_M15', '0.0005', 'float', 'Volatility medium EURUSD M15'),
('agent', 'momentum_threshold',    'EURUSD', 'TIMEFRAME_M15', '0.0006', 'float', 'Momentum threshold EURUSD M15'),
-- EURUSD H1
('risk_management', 'stop_loss_pct',           'EURUSD', 'TIMEFRAME_H1', '0.7',   'float', 'SL % EURUSD H1'),
('risk_management', 'take_profit_pct',         'EURUSD', 'TIMEFRAME_H1', '1.4',   'float', 'TP % EURUSD H1 — RR 1:2'),
('risk_management', 'position_size_pct',       'EURUSD', 'TIMEFRAME_H1', '2.5',   'float', 'Position size % EURUSD H1'),
('agent', 'volatility_high',       'EURUSD', 'TIMEFRAME_H1', '0.002',  'float', 'Volatility high EURUSD H1'),
('agent', 'volatility_medium',     'EURUSD', 'TIMEFRAME_H1', '0.0012', 'float', 'Volatility medium EURUSD H1'),
('agent', 'momentum_threshold',    'EURUSD', 'TIMEFRAME_H1', '0.001',  'float', 'Momentum threshold EURUSD H1'),
-- BTCUSD M15 (crypto — wider SL/TP due to high volatility)
('risk_management', 'stop_loss_pct',           'BTCUSD', 'TIMEFRAME_M15', '0.8',   'float', 'SL % BTCUSD M15 — wider than XAUUSD due to crypto volatility'),
('risk_management', 'take_profit_pct',         'BTCUSD', 'TIMEFRAME_M15', '1.6',   'float', 'TP % BTCUSD M15 — RR 1:2'),
('risk_management', 'position_size_pct',       'BTCUSD', 'TIMEFRAME_M15', '0.5',   'float', 'Position size % BTCUSD M15 — much smaller due to crypto risk'),
('agent', 'volatility_high',       'BTCUSD', 'TIMEFRAME_M15', '0.003',  'float', 'Volatility high BTCUSD M15'),
('agent', 'volatility_medium',     'BTCUSD', 'TIMEFRAME_M15', '0.002',  'float', 'Volatility medium BTCUSD M15'),
('agent', 'momentum_threshold',    'BTCUSD', 'TIMEFRAME_M15', '0.002',  'float', 'Momentum threshold BTCUSD M15'),
-- paper_lot_size per symbol (different instrument sizes)
('trading', 'paper_lot_size',     'EURUSD', '', '0.01',   'float', 'Paper lot size EURUSD'),
('trading', 'paper_lot_size',     'BTCUSD', '', '0.001',  'float', 'Paper lot size BTCUSD — crypto standard'),
('trading', 'paper_lot_size',     'GBPUSD', '', '0.01',   'float', 'Paper lot size GBPUSD'),
('trading', 'paper_lot_size',     'AUDUSD', '', '0.01',   'float', 'Paper lot size AUDUSD'),
('trading', 'paper_lot_size',     'USDJPY', '', '0.01',   'float', 'Paper lot size USDJPY');

-- ── Timeframe-specific defaults: TIMEFRAME_M1 ──────────────
-- These override global defaults when context is set to M1.
-- Values that differ from M15-optimized global defaults:
-- tighter SL/TP, shorter cooldowns, smaller positions, more aggressive ML.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general (M1 needs more data & shorter cycle)
('general', 'data_count',              '', 'TIMEFRAME_M1', '10000',    'int',   'Candles to fetch (~7 hari M1)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_M1', '1',        'int',   'Minutes between auto cycles (1 candle M1)'),
-- risk_management (M1: tighter SL/TP, shorter cooldown, more positions)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_M1', '1.5',  'float', 'Position size %% of balance. M1: 1.5%% — posisi lebih kecil karena frekuensi lebih tinggi.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_M1', '0.3',  'float', 'Stop loss %. M1 scalping: 0.3%%. RR 1:2 dengan TP 0.6%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_M1', '0.6',  'float', 'Take profit %. M1 scalping: 0.6%%. RR 1:2 dengan SL 0.3%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_M1', '1',    'int',   'Cooldown M1: 1 menit — mencegah overtrading tanpa menghambat scalping frekuensi tinggi.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_M1', '3',    'int',   'Max positions M1: 3 — lebih banyak setup per jam.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_M1', '0.3', 'float', 'Trailing activation M1: 0.3%% — trailing aktif lebih cepat di scalping M1.'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_M1', '0.3', 'float', 'Trailing distance M1: 0.3%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_M1', '3.0', 'float', 'Circuit breaker M1: 3%% — lebih sensitif karena frekuensi trade tinggi.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_M1', '120', 'int', 'CB cooldown M1: 2 jam — recovery lebih cepat.'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_M1', '0.003', 'float', 'Volatility threshold M1: 0.003 (0.3%%) — noise M1 lebih tinggi per candle.'),
-- protection (M1: lebih banyak trade = lebih toleran stoploss)
('protection', 'max_stoploss',          '', 'TIMEFRAME_M1', '5',    'int',   'Max stoploss M1: 5 — lebih toleran karena trade lebih sering.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_M1', '2',    'int',   'Guard window M1: 2 jam — 120 candle M1.'),
-- dca (M1: triggered more aggressively)
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_M1', '3',     'int',    'DCA cooldown M1: 3 menit — agar tidak keburu entry lagi.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_M1', '-0.5',  'float',  'DCA trigger M1: -0.5%% — lebih sensitif untuk M1.'),
-- ml (M1: shallower trees, less retrain interval, lower atr multiplier)
('ml', 'max_depth',                '', 'TIMEFRAME_M1', '3',    'int',    'Max depth M1: 3 — lebih dangkal karena data M1 lebih noisy.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_M1', '0.15', 'float',  'ATR multiplier M1: 0.15 — lebih selektif karena noise lebih tinggi.'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_M1', '6',    'int',    'Retrain M1: 6 jam — retrain lebih sering karena candle lebih banyak.'),
-- agent (M1: shorter SMA periods, tighter momentum, lower volatility thresholds)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_M1', '8',    'int',   'SMA fast M1: 8 — lebih responsif di M1.'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_M1', '20',   'int',   'SMA medium M1: 20.'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_M1', '40',   'int',   'SMA slow M1: 40 = 40 menit — trend jangka pendek M1.'),
('agent', 'volatility_high',       '', 'TIMEFRAME_M1', '0.00039', 'float', 'Volatility high M1: 0.00039 (P95 XAUUSD M1) — hanya 5%% candle tertinggi ditolak.'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_M1', '0.00019', 'float', 'Volatility medium M1: 0.00019 (P75 XAUUSD M1) — 25%% candle medium risk.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_M1', '0.0005', 'float', 'Momentum threshold M1: 0.0005 (0.05%%) — lebih sensitif.'),
-- features (M1: more responsive indicators)
('features', 'rsi_period',         '', 'TIMEFRAME_M1', '9',     'int',   'RSI M1: 9 — lebih sensitif, cocok untuk scalping M1.'),
('features', 'bb_period',          '', 'TIMEFRAME_M1', '15',    'int',   'BB M1: 15 — lebih responsif untuk M1.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_M1', '1.5',  'float',  'BB std dev M1: 1.5 — band lebih ketat di M1.'),
-- health_check (M1: more frequent checks, shorter idle detection)
('health_check', 'check_interval_seconds','', 'TIMEFRAME_M1', '20',   'int',    'Check interval M1: 20 detik — monitor lebih sering karena siklus 1 menit.'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_M1', '10',    'int',    'Max errors M1: 10 — lebih toleran karena lebih banyak siklus.'),
('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_M1', '15',   'int',    'Max idle M1: 15 menit = 15 candle tanpa aktivitas.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_M1', '525600',  'int',   'Periods per year for Sharpe/Sortino. M1 = 525600 (1440*365).');

-- ── Timeframe-specific defaults: TIMEFRAME_M15 ─────────────
-- These mirror the global defaults as explicit M15 overrides.
-- Allows independent customization of M15 without touching global defaults.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_M15', '2000',    'int',   'Candles to fetch (~21 hari M15)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_M15', '15',     'int',   'Minutes between auto cycles (1 candle M15)'),
-- risk_management
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_M15', '2.0',  'float', 'Position size %% of balance. M15: 2-3%%.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_M15', '0.5',  'float', 'Stop loss %. M15: 0.5%%. RR 1:2 dengan TP 1.0%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_M15', '1.0',  'float', 'Take profit %. M15: 1.0%%. RR 1:2 dengan SL 0.5%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_M15', '15',   'int',   'Cooldown M15: 15 menit = 1 candle.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_M15', '2',    'int',   'Max positions M15: 2.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_M15', '1.0', 'float', 'Trailing activation M15: 1.0%%. Harus < TP.'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_M15', '1.0', 'float', 'Trailing distance M15: 1.0%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_M15', '5.0', 'float', 'Circuit breaker M15: 5%%.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_M15', '240', 'int', 'CB cooldown M15: 4 jam.'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_M15', '0.015', 'float', 'Volatility threshold M15: 0.015 (1.5%%).'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_M15', '3',    'int',   'Max stoploss M15: 3.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_M15', '4',    'int',   'Guard window M15: 4 jam = 16 candle.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_M15', '30',    'int',    'DCA cooldown M15: 30 menit = 2 candle.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_M15', '-1.0', 'float',  'DCA trigger M15: -1.0%%.'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_M15', '4',    'int',    'Max depth M15: 4.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_M15', '0.25', 'float',  'ATR multiplier M15: 0.25.'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_M15', '12',   'int',    'Retrain M15: 12 jam.'),
-- agent
('agent', 'sma_fast_period',       '', 'TIMEFRAME_M15', '10',   'int',   'SMA fast M15: 10.'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_M15', '21',   'int',   'SMA medium M15: 21.'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_M15', '30',   'int',   'SMA slow M15: 30 = 7.5 jam.'),
('agent', 'volatility_high',       '', 'TIMEFRAME_M15', '0.0015', 'float', 'Volatility high M15: 0.0015 (P95 XAUUSD M15).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_M15', '0.0012', 'float', 'Volatility medium M15: 0.0012 (P75 XAUUSD M15).'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_M15', '0.001', 'float', 'Momentum threshold M15: 0.001 (0.1%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_M15', '14',    'int',   'RSI M15: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_M15', '20',    'int',   'BB M15: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_M15', '2.0',  'float',  'BB std dev M15: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_M15', '60',   'int',    'Check interval M15: 60 detik.'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_M15', '5',    'int',    'Max errors M15: 5.'),
('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_M15', '60',   'int',    'Max idle M15: 60 menit = 4 candle.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_M15', '35040',  'int',   'Periods per year for Sharpe/Sortino. M15 = 35040 (96*365).');

-- ── Timeframe-specific defaults: TIMEFRAME_M5 ───────────────
-- ⚡ Scalping (5 Menit): between M1 and M15 — moderate scalping.
-- SL/TP wider than M1 but tighter than M15. More positions, faster cycles.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general (M5: 5000 candles ~ 17 hari)
('general', 'data_count',              '', 'TIMEFRAME_M5', '5000',     'int',   'Candles to fetch (~17 hari M5)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_M5', '5',        'int',   'Minutes between auto cycles (1 candle M5)'),
-- risk_management (M5: antara M1 dan M15)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_M5', '1.5',  'float', 'Position size %%. M5: 1.5%% — kompromi antara M1 dan M15.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_M5', '0.4',  'float', 'Stop loss %%. M5 scalping: 0.4%%. RR 1:2 dengan TP 0.8%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_M5', '0.8',  'float', 'Take profit %%. M5 scalping: 0.8%%. RR 1:2 dengan SL 0.4%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_M5', '5',    'int',   'Cooldown M5: 5 menit = 1 candle — cukup untuk validasi setup baru.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_M5', '3',    'int',   'Max positions M5: 3 — antara M1 (3) dan M15 (2).'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_M5', '0.4', 'float', 'Trailing activation M5: 0.4%% — lebih awal dari M15.'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_M5', '0.4', 'float', 'Trailing distance M5: 0.4%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_M5', '3.5', 'float', 'Circuit breaker M5: 3.5%% — antara M1 (3%%) dan M15 (5%%).'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_M5', '150', 'int', 'CB cooldown M5: 150 menit (2.5 jam).'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_M5', '0.005', 'float', 'Volatility threshold M5: 0.005 (0.5%%) — noise M5 lebih rendah dari M1.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_M5', '4',    'int',   'Max stoploss M5: 4 — lebih toleran dari M15 karena lebih sering trade.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_M5', '3',    'int',   'Guard window M5: 3 jam = 36 candle.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_M5', '5',     'int',    'DCA cooldown M5: 5 menit = 1 candle.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_M5', '-0.6',  'float',  'DCA trigger M5: -0.6%% — antara M1 (-0.5%%) dan M15 (-1.0%%).'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_M5', '3',    'int',    'Max depth M5: 3 — sama dengan M1 karena noise masih tinggi.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_M5', '0.18', 'float',  'ATR multiplier M5: 0.18 — antara M1 (0.15) dan M15 (0.25).'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_M5', '8',    'int',    'Retrain M5: 8 jam — retrain lebih sering dari M15.'),
-- agent (M5: SMA antara M1 dan M15)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_M5', '8',    'int',   'SMA fast M5: 8 — sama dengan M1, lebih responsif.'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_M5', '20',   'int',   'SMA medium M5: 20.'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_M5', '30',   'int',   'SMA slow M5: 30 = 150 menit (2.5 jam).'),
('agent', 'volatility_high',       '', 'TIMEFRAME_M5', '0.0008', 'float', 'Volatility high M5: 0.0008 — antara M1 (0.00039) dan M15 (0.0015).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_M5', '0.0005', 'float', 'Volatility medium M5: 0.0005 — antara M1 (0.00019) dan M15 (0.0012).'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_M5', '0.0008', 'float', 'Momentum threshold M5: 0.0008 (0.08%%) — antara M1 dan M15.'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_M5', '9',     'int',   'RSI M5: 9 — lebih sensitif untuk scalping M5.'),
('features', 'bb_period',          '', 'TIMEFRAME_M5', '15',    'int',   'BB M5: 15 — lebih responsif untuk M5.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_M5', '1.5',  'float',  'BB std dev M5: 1.5 — band lebih ketat.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_M5', '30',   'int',    'Check interval M5: 30 detik.'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_M5', '8',    'int',    'Max errors M5: 8 — lebih toleran karena siklus 5 menit.'),
('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_M5', '20',   'int',    'Max idle M5: 20 menit = 4 candle.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_M5', '105120',  'int',   'Periods per year for Sharpe/Sortino. M5 = 105120 (288*365).');

-- ── Timeframe-specific defaults: TIMEFRAME_M30 ──────────────
-- 📊 Day Trading (30 Menit): antara M15 dan H1 — moderate intraday.
-- SL/TP lebih lebar, frekuensi lebih rendah, posisi lebih besar.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_M30', '1500',    'int',   'Candles to fetch (~31 hari M30)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_M30', '30',     'int',   'Minutes between auto cycles (1 candle M30)'),
-- risk_management (M30: moderate intraday)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_M30', '2.5',  'float', 'Position size %%. M30: 2.5%% — lebih besar dari M15.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_M30', '0.7',  'float', 'Stop loss %%. M30: 0.7%%. RR 1:2 dengan TP 1.5%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_M30', '1.5',  'float', 'Take profit %%. M30: 1.5%%. RR 1:2 dengan SL 0.7%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_M30', '30',   'int',   'Cooldown M30: 30 menit = 1 candle.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_M30', '2',    'int',   'Max positions M30: 2 — sama dengan M15 dan H1.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_M30', '0.8', 'float', 'Trailing activation M30: 0.8%% — antara M15 (1.0%%) dan H1 (1.2%%).'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_M30', '0.8', 'float', 'Trailing distance M30: 0.8%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_M30', '6.0', 'float', 'Circuit breaker M30: 6%% — lebih longgar dari M15 (5%%).'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_M30', '480', 'int', 'CB cooldown M30: 480 menit (8 jam) — more meaningful swing.'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_M30', '0.02', 'float', 'Volatility threshold M30: 0.02 (2%%) — noise M30 lebih rendah.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_M30', '3',    'int',   'Max stoploss M30: 3 — sama dengan M15.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_M30', '6',    'int',   'Guard window M30: 6 jam = 12 candle.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_M30', '60',    'int',    'DCA cooldown M30: 60 menit = 2 candle.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_M30', '-1.2', 'float',  'DCA trigger M30: -1.2%% — lebih longgar dari M15 (-1.0%%).'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_M30', '5',    'int',    'Max depth M30: 5 — lebih dalam dari M15.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_M30', '0.35', 'float',  'ATR multiplier M30: 0.35 — antara M15 (0.25) dan H1 (0.4).'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_M30', '16',   'int',    'Retrain M30: 16 jam — lebih jarang dari M15.'),
-- agent (M30: SMA lebih panjang)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_M30', '12',   'int',   'SMA fast M30: 12 — antara M15 (10) dan H1 (14).'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_M30', '25',   'int',   'SMA medium M30: 25 — antara M15 (21) dan H1 (30).'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_M30', '40',   'int',   'SMA slow M30: 40 = 20 jam — tren intraday penuh.'),
('agent', 'volatility_high',       '', 'TIMEFRAME_M30', '0.0025', 'float', 'Volatility high M30: 0.0025 — antara M15 (0.0015) dan H1 (0.004).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_M30', '0.0015', 'float', 'Volatility medium M30: 0.0015.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_M30', '0.0012', 'float', 'Momentum threshold M30: 0.0012 (0.12%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_M30', '14',    'int',   'RSI M30: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_M30', '20',    'int',   'BB M30: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_M30', '2.0',  'float',  'BB std dev M30: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_M30', '90',   'int',    'Check interval M30: 90 detik.'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_M30', '5',    'int',    'Max errors M30: 5.'),('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_M30', '120',  'int',    'Max idle M30: 120 menit = 4 candle.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_M30', '17520',  'int',   'Periods per year for Sharpe/Sortino. M30 = 17520 (48*365).');

-- ── Timeframe-specific defaults: TIMEFRAME_H1 ───────────────
-- 📊 Day Trading (1 Jam): intraday penuh. SL/TP lebih lebar,
-- frekuensi rendah, posisi lebih besar, cooldown 1 jam.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_H1', '1000',     'int',   'Candles to fetch (~42 hari H1)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_H1', '60',       'int',   'Minutes between auto cycles (1 candle H1)'),
-- risk_management (H1: daily trading)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_H1', '3.0',  'float', 'Position size %%. H1: 3.0%% — lebih besar untuk pergerakan lebih bermakna.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_H1', '1.0',  'float', 'Stop loss %%. H1: 1.0%%. RR 1:2 dengan TP 2.0%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_H1', '2.0',  'float', 'Take profit %%. H1: 2.0%%. RR 1:2 dengan SL 1.0%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_H1', '60',   'int',   'Cooldown H1: 60 menit = 1 candle.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_H1', '2',    'int',   'Max positions H1: 2.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_H1', '1.2', 'float', 'Trailing activation H1: 1.2%% — antara M30 (0.8%%) dan H4 (2.0%%).'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_H1', '1.2', 'float', 'Trailing distance H1: 1.2%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_H1', '7.0', 'float', 'Circuit breaker H1: 7%% — lebih longgar dari M30.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_H1', '720', 'int', 'CB cooldown H1: 720 menit (12 jam).'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_H1', '0.03', 'float', 'Volatility threshold H1: 0.03 (3%%) — volatilitas per jam lebih besar.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_H1', '3',    'int',   'Max stoploss H1: 3 — sama dengan M15/M30.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_H1', '8',    'int',   'Guard window H1: 8 jam = 8 candle.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_H1', '120',   'int',    'DCA cooldown H1: 120 menit = 2 candle.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_H1', '-1.5', 'float',  'DCA trigger H1: -1.5%% — lebih longgar dari M30 (-1.2%%).'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_H1', '5',    'int',    'Max depth H1: 5 — sama dengan M30.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_H1', '0.4',  'float',  'ATR multiplier H1: 0.4 — lebih selektif dari M30 (0.35).'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_H1', '18',   'int',    'Retrain H1: 18 jam — retrain lebih jarang.'),
-- agent (H1: SMA lebih panjang)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_H1', '14',   'int',   'SMA fast H1: 14 — antara M30 (12) dan H4 (20).'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_H1', '30',   'int',   'SMA medium H1: 30 — antara M30 (25) dan H4 (50).'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_H1', '50',   'int',   'SMA slow H1: 50 = 50 jam — tren multi-hari.'),
('agent', 'volatility_high',       '', 'TIMEFRAME_H1', '0.004', 'float', 'Volatility high H1: 0.004 — antara M30 (0.0025) dan H4 (0.006).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_H1', '0.0025', 'float', 'Volatility medium H1: 0.0025.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_H1', '0.0015', 'float', 'Momentum threshold H1: 0.0015 (0.15%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_H1', '14',    'int',   'RSI H1: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_H1', '20',    'int',   'BB H1: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_H1', '2.0',  'float',  'BB std dev H1: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_H1', '120',  'int',    'Check interval H1: 120 detik (2 menit).'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_H1', '5',    'int',    'Max errors H1: 5.'),('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_H1', '180',  'int',    'Max idle H1: 180 menit = 3 candle.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_H1', '8760',   'int',   'Periods per year for Sharpe/Sortino. H1 = 8760 (24*365).');

-- ── Timeframe-specific defaults: TIMEFRAME_H4 ───────────────
-- 📈 Swing Trading (4 Jam): swing intra-minggu. SL/TP lebar,
-- cooldown panjang, posisi besar, frekuensi sangat rendah.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_H4', '500',      'int',   'Candles to fetch (~83 hari H4)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_H4', '240',      'int',   'Minutes between auto cycles (1 candle H4)'),
-- risk_management (H4: swing trading)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_H4', '4.0',  'float', 'Position size %%. H4: 4.0%% — posisi lebih besar untuk swing.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_H4', '1.5',  'float', 'Stop loss %%. H4: 1.5%%. RR 1:2 dengan TP 3.0%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_H4', '3.0',  'float', 'Take profit %%. H4: 3.0%%. RR 1:2 dengan SL 1.5%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_H4', '240',  'int',   'Cooldown H4: 240 menit = 1 candle.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_H4', '2',    'int',   'Max positions H4: 2.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_H4', '2.0', 'float', 'Trailing activation H4: 2.0%% — harus < TP (3.0%%).'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_H4', '1.5', 'float', 'Trailing distance H4: 1.5%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_H4', '10.0', 'float', 'Circuit breaker H4: 10%% — swing tolerance lebih besar.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_H4', '1440', 'int', 'CB cooldown H4: 1440 menit (1 hari).'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_H4', '0.04', 'float', 'Volatility threshold H4: 0.04 (4%%) — volatilitas swing lebih besar.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_H4', '3',    'int',   'Max stoploss H4: 3.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_H4', '12',   'int',   'Guard window H4: 12 jam = 3 candle.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_H4', '240',   'int',    'DCA cooldown H4: 240 menit = 1 candle.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_H4', '-2.0', 'float',  'DCA trigger H4: -2.0%% — lebih longgar.'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_H4', '6',    'int',    'Max depth H4: 6 — lebih dalam karena candle lebih bermakna.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_H4', '0.5',  'float',  'ATR multiplier H4: 0.5 — lebih selektif.'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_H4', '24',   'int',    'Retrain H4: 24 jam (1 hari).'),
-- agent (H4: SMA panjang untuk swing)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_H4', '20',   'int',   'SMA fast H4: 20 = 80 jam — antara H1 (14) dan D1 (30).'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_H4', '50',   'int',   'SMA medium H4: 50 = 200 jam (8.3 hari).'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_H4', '100',  'int',   'SMA slow H4: 100 = 400 jam (16.7 hari).'),
('agent', 'volatility_high',       '', 'TIMEFRAME_H4', '0.006', 'float', 'Volatility high H4: 0.006 — antara H1 (0.004) dan D1 (0.012).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_H4', '0.004', 'float', 'Volatility medium H4: 0.004.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_H4', '0.002', 'float', 'Momentum threshold H4: 0.002 (0.2%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_H4', '14',    'int',   'RSI H4: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_H4', '20',    'int',   'BB H4: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_H4', '2.0',  'float',  'BB std dev H4: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_H4', '300',  'int',    'Check interval H4: 300 detik (5 menit).'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_H4', '3',    'int',    'Max errors H4: 3 — lebih ketat karena siklus jarang.'),('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_H4', '360',  'int',    'Max idle H4: 360 menit = 6 jam = 1.5 candle.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_H4', '2190',   'int',   'Periods per year for Sharpe/Sortino. H4 = 2190 (6*365).');

-- ── Timeframe-specific defaults: TIMEFRAME_D1 ───────────────
-- 📈 Swing Trading (Harian): swing multi-hari. SL/TP lebar,
-- posisi besar, maksimal 1 posisi, cooldown 1 hari.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_D1', '200',      'int',   'Candles to fetch (~200 hari D1)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_D1', '1440',     'int',   'Minutes between auto cycles (1 candle D1)'),
-- risk_management (D1: daily swing)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_D1', '5.0',  'float', 'Position size %%. D1: 5.0%% — posisi besar untuk swing multi-hari.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_D1', '2.0',  'float', 'Stop loss %%. D1: 2.0%%. RR 1:2 dengan TP 4.0%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_D1', '4.0',  'float', 'Take profit %%. D1: 4.0%%. RR 1:2 dengan SL 2.0%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_D1', '1440', 'int',   'Cooldown D1: 1440 menit = 1 hari.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_D1', '1',    'int',   'Max positions D1: 1 — fokus pada 1 posisi swing.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_D1', '3.0', 'float', 'Trailing activation D1: 3.0%% — harus < TP (4.0%%).'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_D1', '2.0', 'float', 'Trailing distance D1: 2.0%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_D1', '15.0', 'float', 'Circuit breaker D1: 15%% — toleransi swing besar.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_D1', '2880', 'int', 'CB cooldown D1: 2880 menit (2 hari).'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_D1', '0.05', 'float', 'Volatility threshold D1: 0.05 (5%%) — volatilitas harian besar.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_D1', '2',    'int',   'Max stoploss D1: 2 — lebih ketat karena trade jarang.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_D1', '24',   'int',   'Guard window D1: 24 jam = 1 candle.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_D1', '1440',   'int',    'DCA cooldown D1: 1440 menit = 1 hari.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_D1', '-3.0',  'float',  'DCA trigger D1: -3.0%% — lebih longgar.'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_D1', '6',    'int',    'Max depth D1: 6 — sama dengan H4.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_D1', '0.6',  'float',  'ATR multiplier D1: 0.6 — lebih selektif dari H4 (0.5).'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_D1', '48',   'int',    'Retrain D1: 48 jam (2 hari).'),
-- agent (D1: SMA multi-minggu)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_D1', '30',   'int',   'SMA fast D1: 30 = 30 hari.'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_D1', '50',   'int',   'SMA medium D1: 50 = 50 hari.'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_D1', '100',  'int',   'SMA slow D1: 100 = 100 hari (5 bulan).'),
('agent', 'volatility_high',       '', 'TIMEFRAME_D1', '0.012', 'float', 'Volatility high D1: 0.012 — antara H4 (0.006) dan W1 (0.02).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_D1', '0.008', 'float', 'Volatility medium D1: 0.008.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_D1', '0.003', 'float', 'Momentum threshold D1: 0.003 (0.3%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_D1', '14',    'int',   'RSI D1: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_D1', '20',    'int',   'BB D1: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_D1', '2.0',  'float',  'BB std dev D1: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_D1', '600',  'int',    'Check interval D1: 600 detik (10 menit).'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_D1', '3',    'int',    'Max errors D1: 3.'),('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_D1', '720',  'int',    'Max idle D1: 720 menit = 12 jam = 0.5 candle.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_D1', '365',    'int',   'Periods per year for Sharpe/Sortino. D1 = 365.');

-- ── Timeframe-specific defaults: TIMEFRAME_W1 ───────────────
-- 🎯 Position Trading (Mingguan): posisi jangka panjang.
-- SL/TP sangat lebar, 1 posisi maksimal, cooldown 1 minggu.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_W1', '100',      'int',   'Candles to fetch (~100 minggu = 2 tahun)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_W1', '10080',    'int',   'Minutes between auto cycles (1 candle W1)'),
-- risk_management (W1: position trading)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_W1', '8.0',  'float', 'Position size %%. W1: 8.0%% — posisi besar untuk long-term.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_W1', '3.0',  'float', 'Stop loss %%. W1: 3.0%%. RR 1:2 dengan TP 6.0%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_W1', '6.0',  'float', 'Take profit %%. W1: 6.0%%. RR 1:2 dengan SL 3.0%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_W1', '10080', 'int',  'Cooldown W1: 10080 menit = 1 minggu.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_W1', '1',    'int',   'Max positions W1: 1 — fokus pada 1 posisi jangka panjang.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_W1', '4.0', 'float', 'Trailing activation W1: 4.0%% — harus < TP (6.0%%).'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_W1', '3.0', 'float', 'Trailing distance W1: 3.0%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_W1', '20.0', 'float', 'Circuit breaker W1: 20%% — toleransi posisi besar.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_W1', '10080', 'int', 'CB cooldown W1: 10080 menit (1 minggu).'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_W1', '0.07', 'float', 'Volatility threshold W1: 0.07 (7%%) — volatilitas mingguan besar.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_W1', '2',    'int',   'Max stoploss W1: 2.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_W1', '72',   'int',   'Guard window W1: 72 jam = 3 hari.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_W1', '10080',  'int',    'DCA cooldown W1: 10080 menit = 1 minggu.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_W1', '-5.0',  'float',  'DCA trigger W1: -5.0%%.'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_W1', '6',    'int',    'Max depth W1: 6.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_W1', '0.8',  'float',  'ATR multiplier W1: 0.8 — sangat selektif.'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_W1', '72',   'int',    'Retrain W1: 72 jam (3 hari).'),
-- agent (W1: SMA multi-bulan)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_W1', '30',   'int',   'SMA fast W1: 30 = 30 minggu (7.5 bulan).'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_W1', '50',   'int',   'SMA medium W1: 50 = 50 minggu (~1 tahun).'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_W1', '100',  'int',   'SMA slow W1: 100 = 100 minggu (~2 tahun).'),
('agent', 'volatility_high',       '', 'TIMEFRAME_W1', '0.02', 'float', 'Volatility high W1: 0.02 — antara D1 (0.012) dan MN (0.03).'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_W1', '0.012', 'float', 'Volatility medium W1: 0.012.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_W1', '0.005', 'float', 'Momentum threshold W1: 0.005 (0.5%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_W1', '14',    'int',   'RSI W1: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_W1', '20',    'int',   'BB W1: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_W1', '2.0',  'float',  'BB std dev W1: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_W1', '1800', 'int',    'Check interval W1: 1800 detik (30 menit).'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_W1', '3',    'int',    'Max errors W1: 3.'),('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_W1', '2880', 'int',    'Max idle W1: 2880 menit = 2 hari.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_W1', '52',     'int',   'Periods per year for Sharpe/Sortino. W1 = 52.');

-- ── Timeframe-specific defaults: TIMEFRAME_MN ───────────────
-- 🎯 Position Trading (Bulanan): jangka panjang ekstrim.
-- SL/TP sangat lebar, 1 posisi maksimal, cooldown 1 bulan.
INSERT IGNORE INTO settings (section, key_name, symbol, timeframe, value, value_type, description) VALUES
-- general
('general', 'data_count',              '', 'TIMEFRAME_MN', '50',       'int',   'Candles to fetch (~50 bulan = 4+ tahun)'),
('general', 'cycle_interval_minutes',  '', 'TIMEFRAME_MN', '43200',    'int',   'Minutes between auto cycles (1 candle MN)'),
-- risk_management (MN: long-term position trading)
('risk_management', 'position_size_pct',       '', 'TIMEFRAME_MN', '10.0', 'float', 'Position size %%. MN: 10.0%% — posisi besar untuk investasi jangka panjang.'),
('risk_management', 'stop_loss_pct',           '', 'TIMEFRAME_MN', '5.0',  'float', 'Stop loss %%. MN: 5.0%%. RR 1:2 dengan TP 10.0%%.'),
('risk_management', 'take_profit_pct',         '', 'TIMEFRAME_MN', '10.0', 'float', 'Take profit %%. MN: 10.0%%. RR 1:2 dengan SL 5.0%%.'),
('risk_management', 'cooldown_minutes',        '', 'TIMEFRAME_MN', '43200', 'int',  'Cooldown MN: 43200 menit = 1 bulan.'),
('risk_management', 'max_open_positions',      '', 'TIMEFRAME_MN', '1',    'int',   'Max positions MN: 1 — fokus pada 1 posisi.'),
('risk_management', 'trailing_stop_activation_pct', '', 'TIMEFRAME_MN', '6.0', 'float', 'Trailing activation MN: 6.0%% — harus < TP (10.0%%).'),
('risk_management', 'trailing_stop_distance_pct',  '', 'TIMEFRAME_MN', '4.0', 'float', 'Trailing distance MN: 4.0%%.'),
('risk_management', 'circuit_breaker_loss_pct',     '', 'TIMEFRAME_MN', '25.0', 'float', 'Circuit breaker MN: 25%% — toleransi maksimal.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '', 'TIMEFRAME_MN', '43200', 'int', 'CB cooldown MN: 43200 menit (1 bulan).'),
('risk_management', 'volatility_threshold',     '', 'TIMEFRAME_MN', '0.1', 'float', 'Volatility threshold MN: 0.1 (10%%) — volatilitas bulanan besar.'),
-- protection
('protection', 'max_stoploss',          '', 'TIMEFRAME_MN', '2',    'int',   'Max stoploss MN: 2.'),
('protection', 'stoploss_window_hours', '', 'TIMEFRAME_MN', '168',  'int',   'Guard window MN: 168 jam = 7 hari.'),
-- dca
('dca', 'dca_cooldown_minutes',  '', 'TIMEFRAME_MN', '43200',  'int',    'DCA cooldown MN: 43200 menit = 1 bulan.'),
('dca', 'dca_trigger_pct',       '', 'TIMEFRAME_MN', '-8.0',  'float',  'DCA trigger MN: -8.0%%.'),
-- ml
('ml', 'max_depth',                '', 'TIMEFRAME_MN', '6',    'int',    'Max depth MN: 6.'),
('ml', 'atr_multiplier',           '', 'TIMEFRAME_MN', '1.0',  'float',  'ATR multiplier MN: 1.0 — paling selektif.'),
('ml', 'retrain_interval_hours',   '', 'TIMEFRAME_MN', '168',  'int',    'Retrain MN: 168 jam (7 hari).'),
-- agent (MN: SMA multi-tahun)
('agent', 'sma_fast_period',       '', 'TIMEFRAME_MN', '30',   'int',   'SMA fast MN: 30 = 30 bulan (2.5 tahun).'),
('agent', 'sma_medium_period',     '', 'TIMEFRAME_MN', '50',   'int',   'SMA medium MN: 50 = 50 bulan (~4 tahun).'),
('agent', 'sma_slow_period',       '', 'TIMEFRAME_MN', '100',  'int',   'SMA slow MN: 100 = 100 bulan (~8 tahun).'),
('agent', 'volatility_high',       '', 'TIMEFRAME_MN', '0.03', 'float', 'Volatility high MN: 0.03 — antara W1 (0.02) dan lebih tinggi.'),
('agent', 'volatility_medium',     '', 'TIMEFRAME_MN', '0.02', 'float', 'Volatility medium MN: 0.02.'),
('agent', 'momentum_threshold',    '', 'TIMEFRAME_MN', '0.008', 'float', 'Momentum threshold MN: 0.008 (0.8%%).'),
-- features
('features', 'rsi_period',         '', 'TIMEFRAME_MN', '14',    'int',   'RSI MN: 14 — standar.'),
('features', 'bb_period',          '', 'TIMEFRAME_MN', '20',    'int',   'BB MN: 20 — standar.'),
('features', 'bb_std_dev',         '', 'TIMEFRAME_MN', '2.0',  'float',  'BB std dev MN: 2.0 — standar.'),
-- health_check
('health_check', 'check_interval_seconds','', 'TIMEFRAME_MN', '3600', 'int',    'Check interval MN: 3600 detik (1 jam).'),
('health_check', 'max_consecutive_errors','', 'TIMEFRAME_MN', '3',    'int',    'Max errors MN: 3.'),
('health_check', 'max_idle_minutes',      '', 'TIMEFRAME_MN', '10080', 'int',    'Max idle MN: 10080 menit = 7 hari.'),
('performance', 'periods_per_year', '', 'TIMEFRAME_MN', '12',     'int',   'Periods per year for Sharpe/Sortino. MN = 12.');