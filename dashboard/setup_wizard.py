"""Database setup wizard — shown on first run when DB is not available.

Flow:
  1. User enters DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
  2. Test connection to MySQL server
  3. Initialize: create database, run schema, seed settings, write .env
  4. Redirect to main dashboard
"""

import os
from pathlib import Path

import streamlit as st
import mysql.connector


# ── Full schema SQL (from schema.sql) ─────────────────────────

SCHEMA_STATEMENTS = [
    # risk_state
    """CREATE TABLE IF NOT EXISTS risk_state (
        id          INT PRIMARY KEY DEFAULT 1,
        symbol      VARCHAR(20) NOT NULL DEFAULT 'XAUUSD',
        initial_balance     DECIMAL(15,2),
        peak_balance        DECIMAL(15,2),
        daily_start_balance DECIMAL(15,2),
        last_updated        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CHECK (id = 1)
    )""",
    # trade_history
    """CREATE TABLE IF NOT EXISTS trade_history (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        ticket      BIGINT,
        symbol      VARCHAR(20) NOT NULL,
        action      VARCHAR(10) NOT NULL,
        volume      DECIMAL(10,2) NOT NULL,
        price       DECIMAL(15,5) NOT NULL,
        sl          DECIMAL(15,5),
        tp          DECIMAL(15,5),
        profit      DECIMAL(15,5),
        retcode     INT,
        comment     VARCHAR(255),
        strategy    VARCHAR(50),
        signal_val  INT DEFAULT 0,
        status      VARCHAR(20) DEFAULT 'open',
        entry_time  DATETIME NOT NULL,
        exit_time   DATETIME,
        exit_price  DECIMAL(15,5),
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_entry_time (entry_time),
        INDEX idx_symbol (symbol),
        INDEX idx_status (status)
    )""",
    # signal_log
    """CREATE TABLE IF NOT EXISTS signal_log (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        symbol      VARCHAR(20) NOT NULL,
        timestamp   DATETIME NOT NULL,
        source      VARCHAR(30) NOT NULL,
        signal_val  INT NOT NULL,
        regime      VARCHAR(20),
        price       DECIMAL(15,5),
        details     JSON,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_timestamp (timestamp),
        INDEX idx_source (source)
    )""",
    # performance_log
    """CREATE TABLE IF NOT EXISTS performance_log (
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
    )""",
    # equity_snapshots
    """CREATE TABLE IF NOT EXISTS equity_snapshots (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        timestamp   DATETIME NOT NULL,
        balance     DECIMAL(15,2) NOT NULL,
        equity      DECIMAL(15,2),
        drawdown_pct DECIMAL(5,2),
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_timestamp (timestamp)
    )""",
    # config_snapshots
    """CREATE TABLE IF NOT EXISTS config_snapshots (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        saved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        config_json JSON NOT NULL,
        notes       VARCHAR(255)
    )""",
    # circuit_breaker_log
    """CREATE TABLE IF NOT EXISTS circuit_breaker_log (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        triggered_at DATETIME NOT NULL,
        reason       VARCHAR(255) NOT NULL,
        drawdown_pct DECIMAL(5,2),
        balance_before DECIMAL(15,2),
        balance_after  DECIMAL(15,2),
        auto_reset_at DATETIME,
        status       VARCHAR(20) DEFAULT 'active',
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_triggered_at (triggered_at)
    )""",
    # health_check_log
    """CREATE TABLE IF NOT EXISTS health_check_log (
        id                 INT AUTO_INCREMENT PRIMARY KEY,
        checked_at         DATETIME NOT NULL,
        status             VARCHAR(20) NOT NULL,
        mt5_connected      TINYINT(1),
        last_cycle_seconds_ago INT,
        consecutive_errors INT DEFAULT 0,
        error_message      VARCHAR(255),
        created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_checked_at (checked_at)
    )""",
    # market_data
    """CREATE TABLE IF NOT EXISTS market_data (
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    # hyperopt_results
    """CREATE TABLE IF NOT EXISTS hyperopt_results (
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
    )""",
    # settings
    """CREATE TABLE IF NOT EXISTS settings (
        section     VARCHAR(50) NOT NULL,
        key_name    VARCHAR(50) NOT NULL,
        value       TEXT,
        value_type  VARCHAR(20) NOT NULL DEFAULT 'string',
        description VARCHAR(255) DEFAULT '',
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (section, key_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    # paper_trade column — checked via information_schema for compatibility
    # (handled separately in the loop below)
]


# ── Helpers ───────────────────────────────────────────────────

def _write_env(host: str, port: str, user: str, password: str, db_name: str):
    """Write .env file at project root."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    content = (
        "# Database Configuration (auto-generated by setup wizard)\n"
        f"DB_HOST={host}\n"
        f"DB_PORT={port}\n"
        f"DB_USER={user}\n"
        f"DB_PASSWORD={password}\n"
        f"DB_NAME={db_name}\n"
    )
    env_path.write_text(content, encoding="utf-8")


def _test_connection(host: str, port: str, user: str, password: str) -> tuple[bool, str]:
    """Test MySQL connection with given credentials. Returns (ok, message)."""
    try:
        conn = mysql.connector.connect(
            host=host, port=int(port), user=user, password=password,
            connect_timeout=5,
        )
        conn.close()
        return True, "✅ Connected successfully!"
    except mysql.connector.Error as e:
        return False, f"❌ {e.msg} (errno {e.errno})"
    except Exception as e:
        return False, f"❌ {e}"


def _db_exists(host: str, port: str, user: str, password: str, db_name: str) -> bool:
    """Check if a database already exists on the server."""
    try:
        conn = mysql.connector.connect(
            host=host, port=int(port), user=user, password=password,
            connect_timeout=5,
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM information_schema.SCHEMATA "
                       f"WHERE SCHEMA_NAME = %s", (db_name,))
        exists = cursor.fetchone()[0] > 0
        cursor.close()
        conn.close()
        return exists
    except Exception:
        return False


# ── Render Functions ──────────────────────────────────────────

def render_setup_wizard():
    """Main entry point — renders the wizard in place of the dashboard."""
    st.markdown("""
    <div style="text-align:center; padding:2rem 0 0.5rem;">
        <div style="font-size:3.5rem;">🤖</div>
        <h1 style="font-size:1.6rem; font-weight:700; margin:0.3rem 0; letter-spacing:-0.02em;">
            AI Trading Robot
        </h1>
        <p style="opacity:0.5; font-size:0.85rem; margin-bottom:1.5rem;">
            Database Setup Wizard
        </p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.get("setup_step", 1)

    if step == 1:
        _render_step_credentials()
    elif step == 2:
        _render_step_initialize()
    elif step == 3:
        _render_step_complete()


def _render_step_credentials():
    """Step 1: Enter DB credentials and test connection."""
    st.markdown("### Step 1: Database Connection")
    st.markdown("Enter your MySQL database credentials to get started.")

    col1, col2 = st.columns(2)
    with col1:
        host = st.text_input("Host", value="127.0.0.1", key="wiz_host")
        user = st.text_input("User", value="root", key="wiz_user")
    with col2:
        port = st.text_input("Port", value="3306", key="wiz_port")
        password = st.text_input("Password", type="password", value="", key="wiz_password")

    db_name = st.text_input("Database Name", value="trading_bot", key="wiz_dbname",
                            help="This database will be created if it doesn't exist")

    # ── Test Connection ──
    if st.button("🔌 Test Connection", use_container_width=True):
        success, msg = _test_connection(host, port, user, password)
        if success:
            st.success(msg)
            st.session_state["_db_host"] = host
            st.session_state["_db_port"] = port
            st.session_state["_db_user"] = user
            st.session_state["_db_password"] = password
            st.session_state["_db_name"] = db_name
            st.session_state["_conn_ok"] = True
        else:
            st.error(msg)
            st.session_state["_conn_ok"] = False

    # ── Next button (only after successful test) ──
    if st.session_state.get("_conn_ok"):
        existing = _db_exists(host, port, user, password, db_name)
        if existing:
            st.warning(f"⚠️ Database **`{db_name}`** already exists. "
                       "Existing data will be preserved.")
        if st.button("🚀 Initialize Database →", use_container_width=True, type="primary"):
            # Store credentials before moving to step 2
            st.session_state["_db_host"] = host
            st.session_state["_db_port"] = port
            st.session_state["_db_user"] = user
            st.session_state["_db_password"] = password
            st.session_state["_db_name"] = db_name
            st.session_state["setup_step"] = 2
            st.rerun()


def _render_step_initialize():
    """Step 2: Create database, migrate tables, seed settings, write .env."""
    st.markdown("### Step 2: Initializing Database")
    st.markdown("Setting up your database. This will only take a moment...")

    host = st.session_state["_db_host"]
    port = st.session_state["_db_port"]
    user = st.session_state["_db_user"]
    password = st.session_state["_db_password"]
    db_name = st.session_state["_db_name"]

    progress_bar = st.progress(0)
    status = st.empty()

    # ── 2a. Create database ──
    status.info("📦 Creating database (if not exists)...")
    try:
        conn = mysql.connector.connect(
            host=host, port=int(port), user=user, password=password,
            connect_timeout=5,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.close()
        conn.close()
        progress_bar.progress(15)
        status.success("✅ Database ready")
    except mysql.connector.Error as e:
        st.error(f"❌ Failed to create database: {e.msg}")
        if st.button("← Go Back"):
            _reset_wizard()
            st.rerun()
        return

    # ── 2b. Create all tables ──
    status.info("📋 Creating tables...")
    try:
        conn = mysql.connector.connect(
            host=host, port=int(port), user=user, password=password,
            database=db_name, connect_timeout=5,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        total = len(SCHEMA_STATEMENTS)
        for i, sql in enumerate(SCHEMA_STATEMENTS):
            try:
                cursor.execute(sql)
            except mysql.connector.Error as e:
                # Ignore "Duplicate column" or "already exists" errors
                if e.errno not in (1060, 1050):
                    raise
            progress_bar.progress(15 + int(40 * (i + 1) / total))

        # paper_trade column (information_schema check for max compatibility)
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = 'trade_history'
              AND COLUMN_NAME = 'paper_trade'
        """, (db_name,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE trade_history ADD COLUMN paper_trade TINYINT(1) DEFAULT 0")

        cursor.close()
        conn.close()
        status.success("✅ All tables created")
    except mysql.connector.Error as e:
        st.error(f"❌ Failed to create tables: {e.msg}")
        return

    # ── 2c. Set environment vars + write .env ──
    status.info("💾 Writing configuration...")
    os.environ["DB_HOST"] = host
    os.environ["DB_PORT"] = port
    os.environ["DB_USER"] = user
    os.environ["DB_PASSWORD"] = password
    os.environ["DB_NAME"] = db_name
    _write_env(host, port, user, password, db_name)
    progress_bar.progress(70)
    status.success("✅ Configuration saved to .env")

    # ── 2d. Seed default settings ──
    status.info("🌱 Seeding default settings...")
    try:
        from src.persistence.database import DatabaseManager
        # Reset singleton so it picks up our env vars
        import src.persistence.database as db_mod
        db_mod._db_instance = None

        db = DatabaseManager()
        db.connect()     # creates tables if missing, ensures paper_trade column
        db.seed_settings()
        db.close()
        progress_bar.progress(100)
        status.success("✅ Default settings seeded")
    except Exception as e:
        st.error(f"❌ Failed to seed settings: {e}")
        return

    # ── Done ──
    st.session_state["setup_step"] = 3
    st.rerun()


def _render_step_complete():
    """Step 3: Setup complete — launch dashboard."""
    st.balloons()
    st.markdown("""
    <div style="text-align:center; padding:2rem 0;">
        <div style="font-size:3rem;">🎉</div>
        <h2 style="font-size:1.4rem; font-weight:600; margin:0.5rem 0;">
            Setup Complete!
        </h2>
        <p style="opacity:0.6;">
            Your database is ready. Click below to launch the dashboard.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Launch Dashboard", use_container_width=True, type="primary"):
        # Clean up wizard state
        for key in list(st.session_state.keys()):
            if key.startswith("wiz_") or key.startswith("_db_") or key.startswith("setup_"):
                del st.session_state[key]
        st.rerun()


def _reset_wizard():
    """Reset wizard state back to step 1."""
    st.session_state["setup_step"] = 1
    st.session_state["_conn_ok"] = False
