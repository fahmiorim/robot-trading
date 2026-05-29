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
-- exchange
('exchange', 'type',               'mt5',        'string', 'Exchange backend type'),
('exchange', 'name',               '',           'string', 'CCXT exchange name'),
('exchange', 'api_key',            '',           'string', 'API key'),
('exchange', 'secret',             '',           'string', 'API secret'),
('exchange', 'password',           '',           'string', 'API password'),
('exchange', 'sandbox',            'true',       'bool',   'Use sandbox/testnet'),
('exchange', 'options',            '{}',         'json',   'Exchange options'),
('exchange', 'bybit',              '{"category":"linear","position_mode":"one-way","default_leverage":5}', 'json', 'Bybit-specific config'),
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
('signals', 'use_ml',               'false',      'bool',   'Use ML signals'),
('signals', 'use_agent',            'false',      'bool',   'Use agent signals'),
('signals', 'use_swarm',            'false',      'bool',   'Use swarm signals'),
('signals', 'consensus_buy_threshold',  '0.3',    'float',  'Consensus buy threshold'),
('signals', 'consensus_sell_threshold', '-0.3',   'float',  'Consensus sell threshold'),
-- risk_management
('risk_management', 'position_size_pct',       '2.0',  'float', 'Position size % of balance'),
('risk_management', 'max_daily_loss_pct',      '5.0',  'float', 'Max daily loss %'),
('risk_management', 'max_drawdown_pct',        '15.0', 'float', 'Max drawdown %'),
('risk_management', 'max_open_positions',      '5',    'int',   'Max concurrent positions'),
('risk_management', 'cooldown_minutes',        '1',    'int',   'Cooldown between trades'),
('risk_management', 'stop_loss_pct',           '1.5',  'float', 'Stop loss %'),
('risk_management', 'take_profit_pct',         '2.0',  'float', 'Take profit %'),
('risk_management', 'use_trailing_stop',       'false', 'bool',  'Enable trailing stop'),
('risk_management', 'trailing_stop_activation_pct', '1.0', 'float', 'Trailing stop activation %'),
('risk_management', 'trailing_stop_distance_pct',  '0.5', 'float', 'Trailing stop distance %'),
('risk_management', 'circuit_breaker_enabled',      'true', 'bool',  'Enable circuit breaker'),
('risk_management', 'circuit_breaker_loss_pct',     '10.0', 'float', 'Circuit breaker loss %'),
('risk_management', 'circuit_breaker_window_minutes', '30', 'int', 'Circuit breaker window'),
('risk_management', 'circuit_breaker_cooldown_minutes', '120', 'int', 'Circuit breaker cooldown'),
('risk_management', 'adx_period',               '14',    'int',    'ADX calculation period'),
('risk_management', 'adx_threshold',            '25.0',  'float', 'ADX trending threshold'),
('risk_management', 'window_size',              '20',    'int',    'Regime detection window'),
('risk_management', 'slope_threshold',          '0.01',  'float', 'Regime slope threshold'),
('risk_management', 'volatility_threshold',     '0.003', 'float', 'Low volatility threshold'),
-- backtest
('backtest', 'initial_balance',     '10000',      'int',    'Backtest starting balance'),
('backtest', 'commission_pct',      '0.02',       'float',  'Commission %'),
('backtest', 'slippage_pct',        '0.1',        'float',  'Slippage %'),
('backtest', 'position_sizing',     'fixed_pct',  'string', 'Position sizing method'),
-- ml
('ml', 'model_type',                'random_forest', 'string', 'ML model type'),
('ml', 'retrain_interval_hours',    '12',         'int',    'Retrain interval hours'),
('ml', 'model_path',                'trained_models/latest_model.pkl', 'string', 'Model file path'),
('ml', 'n_estimators',            '100',    'int',    'Number of trees for RF/GB'),
('ml', 'max_depth',              '5',      'int',    'Max tree depth (None = unlimited, 5-20 recommended)'),
('ml', 'min_samples_split',      '2',      'int',    'Min samples to split a node (2-20, higher = simpler)'),
('ml', 'classification_threshold','0.0',   'float',  'Min return threshold for buy/sell labels (0.0 = pure ATR-adaptive)'),
('ml', 'atr_multiplier',        '0.25',   'float',  'ATR multiplier for adaptive threshold (threshold = ATR/close × this)'),
('ml', 'test_size',              '0.2',    'float',  'Train/test split ratio'),
('ml', 'random_state',           '42',     'int',    'Random seed for reproducibility'),
-- notifications
('notifications', 'telegram_enabled',    'false',  'bool',   'Enable Telegram'),
('notifications', 'telegram_bot_token',  '',       'string', 'Telegram bot token'),
('notifications', 'telegram_chat_id',    '',       'string', 'Telegram chat ID'),
('notifications', 'notify_on_trade',     'true',   'bool',   'Notify on each trade'),
('notifications', 'notify_daily_report', 'true',   'bool',   'Send daily report'),
-- health_check
('health_check', 'enabled',               'true',  'bool',   'Enable health check'),
('health_check', 'check_interval_seconds', '60',   'int',    'Health check interval'),
('health_check', 'max_consecutive_errors', '10',   'int',    'Max consecutive errors'),
('health_check', 'max_idle_minutes',       '15',   'int',    'Max idle minutes'),
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
-- edge
('edge', 'enabled',               'false',      'bool',   'Kelly / position sizing'),
('edge', 'sizing_method',         'kelly',      'string', 'kelly or fixed_pct'),
('edge', 'kelly_fraction',        '0.25',       'float',  'Fractional Kelly'),
('edge', 'min_trades_for_stats',  '10',         'int',    'Min trades for stats'),
('edge', 'kelly_win_loss_ratio',  '2.0',        'float',  'Win/loss ratio'),
('edge', 'kelly_win_rate',        '55.0',       'float',  'Win rate %'),
('edge', 'max_position_size_pct', '10.0',       'float',  'Max position size %'),
-- order_types
('order_types', 'custom',               'false', 'bool',  'Enable custom order types'),
('order_types', 'use_stop_loss_limit',  'false', 'bool',  'Use stop-loss limit orders'),
('order_types', 'use_oco',              'false', 'bool',  'Use OCO orders'),
-- roi
('roi', 'enabled',        'true',  'bool', 'Enable ROI take-profit'),
('roi', 'table',          '[{"minutes":0,"roi_pct":100},{"minutes":3,"roi_pct":2.0},{"minutes":10,"roi_pct":1.0},{"minutes":30,"roi_pct":0.5},{"minutes":60,"roi_pct":0.2},{"minutes":240,"roi_pct":0.1}]', 'json', 'ROI tiered table'),
-- performance
('performance', 'risk_free_rate',    '0.02',  'float', 'Risk-free rate for Sharpe/Sortino'),
('performance', 'periods_per_year',  '365',   'int',   'Periods per year for Sharpe/Sortino'),
-- protection
('protection', 'cooldown_minutes',       '1',    'int',   'Protection cooldown minutes'),
('protection', 'max_stoploss',           '3',    'int',   'Max stoploss losses before halt'),
('protection', 'stoploss_window_hours',  '1',    'int',   'Stoploss guard window hours'),
('protection', 'max_drawdown_pct',       '15.0', 'float', 'Protection max drawdown %'),
-- agent
('agent', 'sma_fast_period',       '10',    'int',   'SMA fast period'),
('agent', 'sma_medium_period',     '30',    'int',   'SMA medium period'),
('agent', 'sma_slow_period',       '50',    'int',   'SMA slow period'),
('agent', 'volatility_window',     '20',    'int',   'Volatility rolling window'),
('agent', 'position_size',         '0.01',  'float', 'Agent position size'),
('agent', 'volatility_high',       '0.02',  'float', 'High volatility threshold'),
('agent', 'volatility_medium',     '0.01',  'float', 'Medium volatility threshold'),
('agent', 'regime_weight_trending','1.0',   'float', 'Regime weight trending'),
('agent', 'regime_weight_ranging', '0.7',   'float', 'Regime weight ranging'),
('agent', 'regime_weight_choppy',  '0.5',   'float', 'Regime weight choppy'),
('agent', 'momentum_threshold',    '0.001', 'float', 'Momentum threshold'),
-- lstm
('lstm', 'sequence_length',         '60',   'int',   'LSTM sequence length'),
('lstm', 'hidden_size',             '50',   'int',   'LSTM hidden size'),
('lstm', 'num_layers',              '2',    'int',   'LSTM number of layers'),
('lstm', 'classification_threshold','0.0',  'float', 'LSTM min classification threshold (overridden by ATR when adaptive)'),
('lstm', 'atr_multiplier',        '0.25', 'float', 'LSTM ATR multiplier for adaptive threshold'),
('lstm', 'epochs',                  '50',   'int',   'LSTM training epochs'),
('lstm', 'batch_size',              '32',   'int',   'LSTM batch size'),
('lstm', 'learning_rate',           '0.001','float', 'LSTM learning rate'),
-- order
('order', 'contract_size',          '100.0', 'float', 'Default contract size'),
('order', 'stoploss_limit_slip',   '0.001', 'float', 'Stop-loss limit order slip distance'),
-- dca
('dca', 'enabled',               'false',  'bool',   'Enable DCA'),
('dca', 'max_dca_orders',        '3',      'int',    'Max DCA orders'),
('dca', 'dca_increment_factor',  '1.5',    'float',  'DCA size increment'),
('dca', 'dca_trigger_pct',       '-1.0',   'float',  'DCA trigger %'),
('dca', 'dca_cooldown_minutes',  '5',      'int',    'DCA cooldown'),
('dca', 'dca_position_limit_pct','20.0',   'float',  'DCA position limit'),
('dca', 'dca_min_profit_pct',    '0.5',    'float',  'DCA min profit %'),
-- pairlist
('pairlist', 'symbols',   '["XAUUSD"]',     'json',  'Base symbols'),
('pairlist', 'blacklist', '[]',             'json',  'Blacklisted symbols'),
('pairlist', 'max_pairs', '10',             'int',   'Max trading pairs'),
-- pairlist_filters
('pairlist_filters', 'volume_enabled',     'false',   'bool',   'Enable volume filter'),
('pairlist_filters', 'volume_min_avg',     '10000.0', 'float',  'Min average volume'),
('pairlist_filters', 'volume_sort',        'false',   'bool',   'Sort by volume'),
('pairlist_filters', 'price_enabled',      'false',   'bool',   'Enable price filter'),
('pairlist_filters', 'price_min',          '0.0',     'float',  'Min price'),
('pairlist_filters', 'price_max',          '100000.0','float',  'Max price'),
('pairlist_filters', 'spread_enabled',     'false',   'bool',   'Enable spread filter'),
('pairlist_filters', 'spread_max_pct',     '0.5',     'float',  'Max spread %'),
('pairlist_filters', 'age_enabled',        'false',   'bool',   'Enable age filter'),
('pairlist_filters', 'age_min_candles',    '100',     'int',    'Min candle age'),
-- telegram_cmd
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
('dashboard', 'port',     '8501',   'int',    'Dashboard server port'),
('dashboard', 'theme',    'dark',   'string', 'Dashboard theme (dark/light)'),
-- features (feature engineering periods used by FeatureEngineer)
('features', 'returns_period_1',        '1',     'int',   'Returns period 1'),
('features', 'returns_period_5',        '5',     'int',   'Returns period 5'),
('features', 'returns_period_10',       '10',    'int',   'Returns period 10'),
('features', 'sma_medium_period',       '20',    'int',   'SMA medium period (features)'),
('features', 'ema_fast_period',         '12',    'int',   'EMA fast period'),
('features', 'ema_slow_period',         '26',    'int',   'EMA slow period'),
('features', 'rsi_period',              '14',    'int',   'RSI calculation period'),
('features', 'bb_period',               '20',    'int',   'Bollinger Bands period'),
('features', 'bb_std_dev',              '2.0',   'float', 'Bollinger Bands std dev'),
('features', 'adx_period',              '14',    'int',   'ADX calculation period'),
('features', 'macd_fast_period',        '12',    'int',   'MACD fast EMA period'),
('features', 'macd_slow_period',        '26',    'int',   'MACD slow EMA period'),
('features', 'macd_signal_period',      '9',     'int',   'MACD signal line period'),
('features', 'atr_period',              '14',    'int',   'ATR calculation period'),
('features', 'volatility_window_fast',  '10',    'int',   'Fast volatility rolling window'),
-- ml extras
('ml', 'swarm_learning_rate',           '0.05',  'float', 'Swarm weight update learning rate'),
-- strategies (flat keys for swarm intelligence)
('strategies', 'ma_fast_period',        '10',    'int',   'MA crossover fast period'),
('strategies', 'ma_slow_period',        '21',    'int',   'MA crossover slow period'),
('strategies', 'rsi_period',            '14',    'int',   'RSI period'),
('strategies', 'rsi_overbought',        '70',    'int',   'RSI overbought level'),
('strategies', 'rsi_oversold',          '30',    'int',   'RSI oversold level'),
('strategies', 'macd_fast_period',      '12',    'int',   'MACD fast EMA'),
('strategies', 'macd_slow_period',      '26',    'int',   'MACD slow EMA'),
('strategies', 'macd_signal_period',    '9',     'int',   'MACD signal line period');
