"""
Database schema definitions — all DDL statements for table creation.

Used by ``DatabaseManager._ensure_required_tables()`` in ``database.py``.
"""

from typing import Dict

SCHEMA_TABLES: Dict[str, str] = {
    "risk_state": """
        CREATE TABLE IF NOT EXISTS risk_state (
            id INT PRIMARY KEY DEFAULT 1,
            symbol VARCHAR(20) NOT NULL,
            initial_balance DECIMAL(15,2),
            peak_balance DECIMAL(15,2),
            daily_start_balance DECIMAL(15,2),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CHECK (id = 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "trade_history": """
        CREATE TABLE IF NOT EXISTS trade_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticket BIGINT,
            symbol VARCHAR(20) NOT NULL,
            action VARCHAR(10) NOT NULL,
            volume DECIMAL(10,2) NOT NULL,
            price DECIMAL(15,5) NOT NULL,
            sl DECIMAL(15,5),
            tp DECIMAL(15,5),
            profit DECIMAL(15,5),
            retcode INT,
            comment VARCHAR(255),
            strategy VARCHAR(50),
            signal_val INT DEFAULT 0,
            status VARCHAR(20) DEFAULT 'open',
            entry_time DATETIME NOT NULL,
            exit_time DATETIME,
            exit_price DECIMAL(15,5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_entry_time (entry_time),
            INDEX idx_symbol (symbol),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "signal_log": """
        CREATE TABLE IF NOT EXISTS signal_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp DATETIME NOT NULL,
            source VARCHAR(30) NOT NULL,
            signal_val INT NOT NULL,
            regime VARCHAR(20),
            price DECIMAL(15,5),
            details JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_timestamp (timestamp),
            INDEX idx_source (source)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "performance_log": """
        CREATE TABLE IF NOT EXISTS performance_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            strategy_name VARCHAR(50) NOT NULL,
            regime VARCHAR(20),
            trades_count INT DEFAULT 0,
            total_return DECIMAL(10,2),
            win_rate DECIMAL(5,2),
            max_drawdown DECIMAL(5,2),
            sharpe_ratio DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_strat_date (strategy_name, date),
            INDEX idx_date (date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "equity_snapshots": """
        CREATE TABLE IF NOT EXISTS equity_snapshots (
            id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            balance DECIMAL(15,2) NOT NULL,
            equity DECIMAL(15,2),
            drawdown_pct DECIMAL(5,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_timestamp (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "config_snapshots": """
        CREATE TABLE IF NOT EXISTS config_snapshots (
            id INT AUTO_INCREMENT PRIMARY KEY,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            config_json JSON NOT NULL,
            notes VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "circuit_breaker_log": """
        CREATE TABLE IF NOT EXISTS circuit_breaker_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            triggered_at DATETIME NOT NULL,
            reason VARCHAR(255) NOT NULL,
            drawdown_pct DECIMAL(5,2),
            balance_before DECIMAL(15,2),
            balance_after DECIMAL(15,2),
            auto_reset_at DATETIME,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_triggered_at (triggered_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "health_check_log": """
        CREATE TABLE IF NOT EXISTS health_check_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            checked_at DATETIME NOT NULL,
            status VARCHAR(20) NOT NULL,
            mt5_connected TINYINT(1),
            last_cycle_seconds_ago INT,
            consecutive_errors INT DEFAULT 0,
            error_message VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_checked_at (checked_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "market_data": """
        CREATE TABLE IF NOT EXISTS market_data (
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(30) NOT NULL,
            time DATETIME NOT NULL,
            open DECIMAL(15,5) NOT NULL,
            high DECIMAL(15,5) NOT NULL,
            low DECIMAL(15,5) NOT NULL,
            close DECIMAL(15,5) NOT NULL,
            tick_volume BIGINT DEFAULT 0,
            spread INT DEFAULT 0,
            real_volume BIGINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, timeframe, time),
            INDEX idx_symbol_tf (symbol, timeframe, time)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "hyperopt_results": """
        CREATE TABLE IF NOT EXISTS hyperopt_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            strategy_name VARCHAR(50) NOT NULL,
            best_params JSON NOT NULL,
            best_score DECIMAL(10,4) NOT NULL,
            metrics JSON,
            n_trials INT DEFAULT 0,
            elapsed_seconds DECIMAL(10,2) DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_strategy (strategy_name),
            INDEX idx_score (best_score DESC)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "ml_training_log": """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "settings": """
        CREATE TABLE IF NOT EXISTS settings (
            section     VARCHAR(50) NOT NULL,
            key_name    VARCHAR(50) NOT NULL,
            symbol      VARCHAR(20) NOT NULL DEFAULT '' COMMENT 'empty = global default',
            timeframe   VARCHAR(30) NOT NULL DEFAULT '' COMMENT 'empty = global default',
            value       TEXT,
            value_type  VARCHAR(20) NOT NULL DEFAULT 'string',
            description VARCHAR(255) DEFAULT '',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (section, key_name, symbol, timeframe)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
}
