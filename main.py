#!/usr/bin/env python3
"""
AI Trading Robot - Main Entry Point
Usage:
    python main.py              # Run analysis (no auto-trade)
    python main.py --trade      # Run analysis + auto-trade if enabled
"""
import sys
import time
from src.services.trading.engine import TradingBot as AIRobot
from src.configuration.manager import ConfigManager
from src.persistence.database import DatabaseManager
from src.rpc.telegram import TelegramRPC as TelegramNotifier
from src.utils.logging import get_logger

logger = get_logger("main")


def main(auto_trade_override: bool = False):
    logger.info("=" * 60)
    logger.info("  AI TRADING ROBOT - MULTI STRATEGY SYSTEM")
    logger.info("=" * 60)

    from src.persistence.database import DatabaseManager
    _db = DatabaseManager()
    config = ConfigManager(db=_db)

    # Validate config before starting
    warnings = config.validate()
    for w in warnings:
        logger.warning(f"Config issue: {w}")

    try:
        robot = AIRobot(config=config)
    except RuntimeError as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)
    notifier = None

    # Setup Telegram if enabled
    if config.get("notifications", "telegram_enabled"):
        token = config.get("notifications", "telegram_bot_token")
        chat_id = config.get("notifications", "telegram_chat_id")
        if token and chat_id:
            notifier = TelegramNotifier(token, chat_id)
            logger.info("Telegram notifier initialized")

    try:
        logger.info(f"[1] Fetching market data ({config.get('general', 'symbol')})...")
        data = robot.fetch_data()
        logger.info(f"    Loaded {len(data)} candles")

        logger.info("[2] Running backtest on all strategies...")
        results = robot.run_backtest_all(data)
        logger.info(f"    Detected market regime: {robot.current_regime.upper()}")

        sorted_results = sorted(results.items(), key=lambda x: x[1]['total_return'], reverse=True)
        for name, result in sorted_results:
            logger.info(f"    {name:<25} {result['total_return']:>8.2f}%  "
                       f"{result['num_trades']:>6} trades, "
                       f"win_rate={result.get('win_rate', 0):>5.1f}%, "
                       f"max_dd={result.get('max_drawdown', 0):>5.2f}%")
        logger.info(f"    Best strategy: {robot.best_strategy.name if robot.best_strategy else 'N/A'}")

        logger.info("[3] Training ML model...")
        try:
            accuracy = robot.ml_trainer.train(data)
            logger.info(f"    ML Model accuracy: {accuracy:.2%}")
        except Exception as e:
            logger.warning(f"    ML training skipped: {e}")

        logger.info("[4] Current signals:")
        use_ml = config.get("signals", "use_ml")
        use_agent = config.get("signals", "use_agent")
        use_swarm = config.get("signals", "use_swarm")

        signals = {
            'strategy': robot.get_signal(data),
            'ml': robot.get_signal(data, use_ml=True) if use_ml else 0,
            'agent': robot.get_signal(data, use_agent=True) if use_agent else 0,
            'swarm': robot.get_signal(data, use_swarm=True) if use_swarm else 0
        }
        for name, sig in signals.items():
            label = "BUY" if sig == 1 else "SELL" if sig == -1 else "HOLD"
            logger.info(f"    {name:<10}: {label}")

        buy_votes = sum(1 for v in signals.values() if v == 1)
        sell_votes = sum(1 for v in signals.values() if v == -1)
        total_votes = len(signals)
        buy_ratio = buy_votes / total_votes if total_votes > 0 else 0
        sell_ratio = sell_votes / total_votes if total_votes > 0 else 0

        buy_threshold = config.get("signals", "consensus_buy_threshold")
        sell_threshold = config.get("signals", "consensus_sell_threshold")
        # sell_threshold is stored as negative in config; abs() converts to positive ratio

        if buy_ratio >= buy_threshold:
            consensus = 1
        elif sell_ratio >= abs(sell_threshold):
            consensus = -1
        else:
            consensus = 0
        consensus_label = "BUY" if consensus == 1 else "SELL" if consensus == -1 else "HOLD"
        logger.info(f"    Consensus: {consensus_label} (buy_ratio={buy_ratio:.1%}, sell_ratio={sell_ratio:.1%})")
        logger.info(f"    Consensus thresholds: buy>={buy_threshold:.0%}, sell>={abs(sell_threshold):.0%}")

        # Connection & risk status
        status = {'connected': robot.exchange.is_connected()}
        logger.info(f"[5] Connection: connected={status['connected']}")

        risk_summary = robot.risk.get_status_summary()
        can_trade = risk_summary.get('can_trade', True)
        reason = risk_summary.get('can_trade_reason', '')
        logger.info(f"[6] Risk: DD={risk_summary['drawdown_pct']:.2f}%, "
                    f"daily_loss={risk_summary['daily_loss_pct']:.2f}%, "
                    f"can_trade={can_trade}")

        # Auto-trading
        auto_trade = config.get("general", "auto_trade")
        if auto_trade_override:
            auto_trade = True

        logger.info(f"[7] Auto-trading: enabled={auto_trade}")
        if auto_trade and consensus != 0 and can_trade:
            logger.info(f"    Executing AUTO {consensus_label} order...")
            result = robot.execute_trade(consensus)
            logger.info(f"    Result: {result}")
            if notifier:
                price = robot.get_current_price()['bid']
                notifier.send_trade_alert(config.get("general", "symbol"), consensus, price, "Auto-consensus")
        elif auto_trade and not can_trade:
            logger.warning(f"    Trade blocked: {reason}")

        # Daily report via Telegram
        if notifier and config.get("notifications", "notify_daily_report"):
            best_name = robot.best_strategy.name if robot.best_strategy else "N/A"
            best_return = sorted_results[0][1]['total_return'] if sorted_results else 0
            total_trades = sum(r['num_trades'] for _, r in sorted_results) if sorted_results else 0
            notifier.send_performance_report({
                'total_return': best_return,
                'best_strategy': best_name,
                'num_trades': total_trades
            })

        logger.info("=" * 60)
        logger.info("  Analysis complete!")
        logger.info(f"  Run: streamlit run dashboard.py")
        logger.info("=" * 60)

    finally:
        robot.cleanup()


def _health_check(robot: AIRobot, last_good_cycle: dict) -> dict:
    """
    Health check watchdog. Checks:
    - MT5 connection
    - Time since last successful cycle
    - Consecutive errors
    Returns status dict with 'healthy' bool.
    """
    config = robot.config
    if not config.get("health_check", "enabled"):
        return {'healthy': True, 'action': 'disabled'}

    max_idle = config.get("health_check", "max_idle_minutes")
    max_errors = config.get("health_check", "max_consecutive_errors")
    auto_restart = config.get("health_check", "auto_restart")

    issues = []
    healthy = True

    # 1. Check MT5 connection
    try:
        mt5_connected = robot.exchange.is_connected()
        if not mt5_connected:
            issues.append("MT5 not connected")
            healthy = False
            logger.warning("Health: MT5 disconnected, attempting reconnect...")
            robot.exchange.ensure_connection()
    except Exception as e:
        issues.append(f"Connection check error: {e}")
        healthy = False

    # 2. Check idle time
    idle_minutes = (time.time() - robot._last_cycle_time) / 60
    if idle_minutes > max_idle:
        issues.append(f"Robot idle for {idle_minutes:.0f}min (max: {max_idle}min)")
        healthy = False

    # 3. Check consecutive errors
    if robot._consecutive_errors >= max_errors:
        issues.append(f"{robot._consecutive_errors} consecutive errors (max: {max_errors})")
        healthy = False
        if auto_restart:
            logger.warning("Health: Too many errors, triggering auto-restart of cycle...")
            robot._consecutive_errors = 0  # Reset so retry can happen

    # 4. Log to DB
    try:
        hc_db = DatabaseManager()
        hc_db.log_health_check(
            status='healthy' if healthy else 'error',
            mt5_connected=robot.exchange.is_connected(),
            last_cycle_seconds_ago=int(idle_minutes * 60),
            consecutive_errors=robot._consecutive_errors,
            error_message=issues[0] if issues else None,
        )
        hc_db.close()
    except Exception as e:
        logger.error(f"Failed to log health check: {e}")

    if issues:
        logger.warning(f"Health check issues: {'; '.join(issues)}")
    else:
        logger.debug("Health check: OK")

    return {'healthy': healthy, 'issues': issues, 'action': 'restart' if not healthy and auto_restart else 'none'}


def run_auto_cycle(count: int = -1):
    """
    Run trading cycles continuously with interval.
    Includes health check watchdog that auto-restarts if issues detected.
    """
    logger.info("Starting auto-trade cycle mode...")
    _db_run = DatabaseManager()
    config = ConfigManager(db=_db_run)
    try:
        robot = AIRobot(config=config)
    except RuntimeError as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)
    interval_minutes = config.get("general", "cycle_interval_minutes")
    health_check_interval = config.get("health_check", "check_interval_seconds")
    cycle_count = 0
    last_health_check = time.time()

    try:
        while count < 0 or cycle_count < count:
            cycle_count += 1
            logger.info(f"\n{'#'*60}")
            logger.info(f"  CYCLE #{cycle_count}")
            logger.info(f"{'#'*60}")

            result = robot.run_trading_cycle()
            if result.get('success'):
                logger.info(f"Cycle {cycle_count} completed: {result.get('action', 'OK')}")
                robot._consecutive_errors = 0
            else:
                robot._consecutive_errors += 1
                logger.error(f"Cycle {cycle_count} failed: {result.get('error', 'Unknown')}")

            # Run health check periodically
            if time.time() - last_health_check >= health_check_interval:
                hc = _health_check(robot, result)
                last_health_check = time.time()
                if not hc['healthy'] and hc.get('action') == 'restart':
                    logger.warning("Health check failed — recreating robot...")
                    try:
                        robot.cleanup()
                    except Exception:
                        pass
                    robot = AIRobot(config=config, bypass_lock=True)
                    robot._consecutive_errors = 0
                    logger.info("Robot recreated after health check failure")

            if count != 0:
                logger.info(f"Waiting {interval_minutes} min for next cycle...")
                robot.exchange.wait_for_new_candle(interval_minutes)

    except KeyboardInterrupt:
        logger.info("Auto-cycle interrupted by user")
    finally:
        try:
            robot.cleanup()
        except Exception:
            pass
        logger.info("Auto-cycle mode stopped")


if __name__ == "__main__":
    auto_trade = "--trade" in sys.argv or "-t" in sys.argv
    continuous = "--continuous" in sys.argv or "-c" in sys.argv

    if continuous:
        run_auto_cycle()
    else:
        main(auto_trade_override=auto_trade)