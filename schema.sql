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
    value       TEXT,
    value_type  VARCHAR(20) NOT NULL DEFAULT 'string',  -- string / int / float / bool / json
    description VARCHAR(255) DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (section, key_name)
);

-- ── Seed settings ──────────────────────────────────────────
INSERT IGNORE INTO settings (section, key_name, value, value_type, description) VALUES
-- general
('general', 'symbol',              'XAUUSD',     'string', 'Trading symbol'),
('general', 'timeframe',           'TIMEFRAME_M1', 'string', 'Chart timeframe'),
('general', 'auto_trade',          'false',      'bool',   'Enable auto trading'),
('general', 'data_count',          '2000',       'int',    'Candles to fetch'),
('general', 'magic_number',        '2024',       'int',    'MT5 magic number'),
('general', 'cycle_interval_minutes', '1',       'int',    'Minutes between auto cycles'),
-- exchange (minimal — hanya untuk MT5, UI tab dihapus karena tidak trading crypto)
('exchange', 'type',               'mt5',        'string', 'Exchange backend type (mt5 / bybit / ccxt)'),
('exchange', 'default_sl_pct',     '0.005',      'float',  'Default SL pct (fraction) for retry orders'),
('exchange', 'default_tp_pct',     '0.01',       'float',  'Default TP pct (fraction) for retry orders'),
-- trading
('trading', 'mode',                 'live',       'string', 'live / paper / dry-run'),
('trading', 'paper_trading',        'false',      'bool',   'Enable paper trading'),
('trading', 'paper_initial_balance','10000.0',    'float',  'Paper trading starting balance'),
('trading', 'paper_lot_size',       '0.01',       'float',  'Paper trading lot size'),
('trading', 'paper_order_delay_ms', '500',        'int',    'Paper order delay ms'),
('trading', 'strategy_pre_validation', 'true',    'bool',   'Validate strategy before trading'),
('trading', 'min_backtest_trades',  '20',         'int',    'Min backtest trades for validation'),
('trading', 'min_win_rate',         '35.0',       'float',  'Min win rate % for validation'),
('trading', 'max_backtest_drawdown','30.0',       'float',  'Max backtest drawdown %'),
('trading', 'max_consecutive_losses','5',         'int',    'Max consecutive losses before stop'),
-- signals
('signals', 'use_ml',               'true',       'bool',   'Use ML signals'),
('signals', 'use_agent',            'true',       'bool',   'Use agent signals'),
('signals', 'use_swarm',            'false',      'bool',   'Use swarm signals'),
('signals', 'consensus_buy_threshold',  '0.6',    'float',  'Consensus buy threshold (0.6 = kedua sumber harus setuju)'),
('signals', 'consensus_sell_threshold', '-0.6',   'float',  'Consensus sell threshold (-0.6 = kedua sumber harus setuju)'),
-- risk_management
('risk_management', 'position_size_pct',       '1.5',  'float', 'Position size %% of balance. Scalping M1-M15: 1-2%%.'),
('risk_management', 'max_daily_loss_pct',      '5.0',  'float', 'Max daily loss %'),
('risk_management', 'max_drawdown_pct',        '10.0', 'float', 'Max drawdown %. Scalping: 10% sudah sangat agresif.'),
('risk_management', 'max_open_positions',      '3',    'int',   'Max concurrent positions. Scalping M1-M15: 2-3 cukup.'),
('risk_management', 'cooldown_minutes',        '1',    'int',   'Cooldown between trades. M1: 1 menit — cukup untuk mencegah overtrading tanpa menghambat scalping frekuensi tinggi.'),
('risk_management', 'stop_loss_pct',           '0.5',  'float', 'Stop loss %. Scalping M1-M15: 0.3-0.8%.'),
('risk_management', 'take_profit_pct',         '0.8',  'float', 'Take profit %. Scalping M1: 0.5-0.8%%, M5-M15: 0.8-1.5%%.'),
('risk_management', 'use_trailing_stop',       'false', 'bool',  'Enable trailing stop'),
('risk_management', 'trailing_stop_activation_pct', '0.5', 'float', 'Trailing stop activation %% untuk M1-M15. Harus < TP (0.5%% agar trailing aktif lebih awal).'),
('risk_management', 'trailing_stop_distance_pct',  '0.5', 'float', 'Trailing stop distance %'),
('risk_management', 'circuit_breaker_enabled',      'true', 'bool',  'Enable circuit breaker'),
('risk_management', 'circuit_breaker_loss_pct',     '5.0', 'float', 'Circuit breaker loss %. M1: 5% dalam 30 menit sudah warning.'),
('risk_management', 'circuit_breaker_cooldown_minutes', '60', 'int', 'Circuit breaker cooldown. M1: 60 menit cukup untuk cooldown.'),
('risk_management', 'adx_period',               '14',    'int',    'ADX calculation period'),
('risk_management', 'adx_threshold',            '25.0',  'float', 'ADX trending threshold'),
('risk_management', 'window_size',              '20',    'int',    'Regime detection window'),
('risk_management', 'slope_threshold',          '0.01',  'float', 'Regime slope threshold'),
('risk_management', 'volatility_threshold',     '0.005', 'float', 'Low volatility threshold untuk M1-M15. 0.005 (0.5%%) mengurangi false choppy classification akibat noise tinggi.'),
-- backtest
('backtest', 'initial_balance',     '10000',      'int',    'Backtest starting balance'),
('backtest', 'commission_pct',      '0.02',       'float',  'Commission %'),
('backtest', 'slippage_pct',        '0.1',        'float',  'Slippage %'),
-- ml
('ml', 'model_type',                'gradient_boosting', 'string', 'ML model type — Gradient Boosting lebih akurat untuk M1 scalping berdasarkan diagnostic test'),
('ml', 'retrain_interval_hours',    '4',         'int',    'Retrain interval hours. Scalping M1-M15: 4 jam — lebih responsif.'),
('ml', 'model_path',                'trained_models/latest_model.pkl', 'string', 'Model file path'),
('ml', 'n_estimators',            '100',    'int',    'Number of trees for RF/GB'),
('ml', 'max_depth',              '3',      'int',    'Max tree depth — 3 direkomendasikan untuk GradientBoosting M1 (lebih generalize dari 5)'),
('ml', 'min_samples_split',      '5',      'int',    'Min samples to split a node. Scalping M1-M15: 5-10 untuk mengurangi overfitting di M1.'),
('ml', 'classification_threshold','0.0',     'float',  'Min return threshold for buy/sell labels. 0.0 = pure ATR-adaptive — threshold dihitung dari ATR%% × atr_multiplier.'),
('ml', 'atr_multiplier',        '0.20',   'float',  'ATR multiplier for adaptive threshold. Scalping M1-M15: 0.15-0.20 — lebih banyak sinyal tanpa noise.'),
-- notifications
('notifications', 'telegram_enabled',    'false',  'bool',   'Enable Telegram'),
('notifications', 'telegram_bot_token',  '',       'string', 'Telegram bot token'),
('notifications', 'telegram_chat_id',    '',       'string', 'Telegram chat ID'),
('notifications', 'notify_daily_report', 'true',   'bool',   'Send daily report'),
-- health_check
('health_check', 'enabled',               'true',  'bool',   'Enable health check'),
('health_check', 'check_interval_seconds', '60',   'int',    'Health check interval'),
('health_check', 'max_consecutive_errors', '5',    'int',    'Max consecutive errors. Scalping M1: 5 cukup — restart lebih cepat saat error beruntun.'),
('health_check', 'max_idle_minutes',       '5',    'int',    'Max idle minutes. Scalping M1: 5 menit — jika 5 cycle tanpa trade, bot dicurigai stalled.'),
('health_check', 'auto_restart',           'true',  'bool',  'Auto restart on failure'),
-- strategies (per-strategy JSON config)
('strategies', 'MA_Crossover',  '{"enabled":true,"fast_period":10,"slow_period":25}', 'json', ''),
('strategies', 'RSI',           '{"enabled":true,"period":9,"overbought":80,"oversold":20}', 'json', ''),
('strategies', 'MACD',          '{"enabled":true,"fast":12,"slow":26,"signal":9}', 'json', ''),
('strategies', 'Bollinger',     '{"enabled":true,"period":15,"std_dev":2.0}', 'json', ''),
('strategies', 'Breakout',      '{"enabled":true,"lookback":15}', 'json', ''),
-- strategy_weights (per-regime weighting)
('strategy_weights', 'trending', '{"MA_Crossover":1.0,"MACD":0.8,"Breakout":0.6,"RSI":0.3,"Bollinger":0.2}', 'json', ''),
('strategy_weights', 'ranging',  '{"Bollinger":1.0,"RSI":1.0,"MACD":0.3,"Breakout":0.3,"MA_Crossover":0.2}', 'json', ''),
('strategy_weights', 'choppy',   '{"RSI":1.0,"Bollinger":0.9,"MACD":0.5,"Breakout":0.1,"MA_Crossover":0.2}', 'json', ''),
-- order_types
('order_types', 'custom',               'false', 'bool',  'Enable custom order types'),
('order_types', 'use_stop_loss_limit',  'false', 'bool',  'Use stop-loss limit orders'),
('order_types', 'use_oco',              'false', 'bool',  'Use OCO orders'),
-- roi
('roi', 'enabled',        'true',  'bool', 'Enable ROI take-profit'),
('roi', 'table',          '[{"minutes":0,"roi_pct":100},{"minutes":3,"roi_pct":0.8},{"minutes":10,"roi_pct":0.5},{"minutes":30,"roi_pct":0.3},{"minutes":60,"roi_pct":0.2},{"minutes":240,"roi_pct":0.1}]', 'json', 'ROI tiered table — scalping M1: profit target turun cepat (0.8% di 3 menit, 0.5% di 10 menit)'),
-- performance
('performance', 'risk_free_rate',    '0.02',  'float', 'Risk-free rate for Sharpe/Sortino'),
('performance', 'periods_per_year',  '525600', 'int',   'Periods per year for Sharpe/Sortino. 525600 = M1 (60*24*365).'),
-- protection
('protection', 'max_stoploss',           '5',    'int',   'Max stoploss losses before halt. Scalping M1: 5-8, karena frekuensi trade tinggi (10+/jam).'),
('protection', 'stoploss_window_hours',  '1',    'int',   'Stoploss guard window hours'),
-- agent
('agent', 'sma_fast_period',       '10',    'int',   'SMA fast period'),
('agent', 'sma_medium_period',     '21',    'int',   'SMA medium period'),
('agent', 'sma_slow_period',       '30',    'int',   'SMA slow period. M1: 30 candle = 30 menit — responsif untuk scalping.'),
('agent', 'volatility_window',     '20',    'int',   'Volatility rolling window'),
('agent', 'position_size',         '0.01',  'float', 'Agent position size'),
('agent', 'volatility_high',       '0.00039',  'float', 'High volatility threshold (P95 XAUUSD M1)'),
('agent', 'volatility_medium',     '0.000307', 'float', 'Medium volatility threshold (P75 XAUUSD M1)'),
('agent', 'regime_weight_trending','1.0',   'float', 'Regime weight trending'),
('agent', 'regime_weight_ranging', '0.7',   'float', 'Regime weight ranging'),
('agent', 'regime_weight_choppy',  '0.5',   'float', 'Regime weight choppy'),
('agent', 'momentum_threshold',    '0.001', 'float', 'Momentum threshold'),
-- order
('order', 'contract_size',          '100.0', 'float', 'Default contract size'),
('order', 'stoploss_limit_slip',   '0.001', 'float', 'Stop-loss limit order slip distance'),
-- dca
('dca', 'enabled',               'false',  'bool',   'Enable DCA'),
('dca', 'max_dca_orders',        '3',      'int',    'Max DCA orders'),
('dca', 'dca_increment_factor',  '1.5',    'float',  'DCA size increment'),
('dca', 'dca_trigger_pct',       '-1.0',   'float',  'DCA trigger %'),
('dca', 'dca_cooldown_minutes',  '3',      'int',    'DCA cooldown. M1: 3 menit cukup untuk scalping.'),
('dca', 'dca_position_limit_pct','20.0',   'float',  'DCA position limit'),
('telegram_cmd', 'enabled',          'false', 'bool',   'Enable Telegram commands'),
('telegram_cmd', 'allowed_chat_ids', '[]',   'json',   'Allowed chat IDs'),
-- rest_api
('rest_api', 'enabled',  'false', 'bool',   'Enable REST API'),
('rest_api', 'host',     '0.0.0.0', 'string', 'REST API host'),
('rest_api', 'port',     '8000',   'int',    'REST API port'),
('rest_api', 'api_key',  '',       'string', 'REST API key'),
-- websocket
('websocket', 'host',     '0.0.0.0', 'string', 'WebSocket server host'),
('websocket', 'port',     '8765',    'int',    'WebSocket server port'),
-- dashboard
-- features (feature engineering periods used by FeatureEngineer)
('features', 'returns_period_1',        '1',     'int',   'Returns period 1'),
('features', 'ema_fast_period',         '12',    'int',   'EMA fast period'),
('features', 'ema_slow_period',         '26',    'int',   'EMA slow period'),
('features', 'rsi_period',              '14',    'int',   'RSI calculation period'),
('features', 'bb_period',               '20',    'int',   'Bollinger Bands period'),
('features', 'bb_std_dev',              '2.0',   'float', 'Bollinger Bands std dev'),
('features', 'macd_fast_period',        '12',    'int',   'MACD fast EMA period'),
('features', 'macd_slow_period',        '26',    'int',   'MACD slow EMA period'),
('features', 'macd_signal_period',      '9',     'int',   'MACD signal line period'),
('features', 'atr_period',              '14',    'int',   'ATR calculation period'),
('features', 'volatility_window_fast',  '10',    'int',   'Fast volatility rolling window'),
-- ml extras
('ml', 'swarm_learning_rate',           '0.05',  'float', 'Swarm weight update learning rate');
