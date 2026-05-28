# AI Trading Robot

Sistem robot trading AI dengan banyak strategi untuk MetaTrader 5.

## Fitur
- **5 Strategi Trading**: Moving Average, RSI, MACD, Bollinger Bands, Breakout
- **Machine Learning**: Random Forest & LSTM untuk prediksi
- **Backtesting**: Evaluasi performa semua strategi
- **Live Trading**: Terhubung langsung ke MT5

## Struktur
```
ai-trading-robot/
├── src/
│   ├── constants/              # Enums, MT5 retcodes, timeframe maps
│   ├── utils/                  # Logging, exceptions, system info
│   ├── domain/                 # Type aliases, Trade/TradeManager models
│   ├── analysis/               # Technical indicators, regime detection
│   ├── strategy/               # Strategy interface & registry
│   │   └── implementations/   # MA Crossover, RSI, MACD, Bollinger, Breakout
│   ├── risk/                   # RiskManager, protection rules
│   ├── trading/                # TradingBot engine, OrderManager, PairlistManager
│   ├── exchange/               # MT5, CCXT, Bybit integrations + helpers
│   ├── backtesting/            # Backtester engine, hyperparameter optimization
│   ├── ml/                     # ML models (RF, LSTM), trainer, features
│   ├── persistence/            # Database, trade history, performance, metrics
│   ├── data/                   # OHLCV data provider
│   ├── rpc/                    # Telegram, WebSocket, REST API backends
│   ├── commands/               # CLI entry point
│   ├── configuration/          # ConfigManager, defaults
│   ├── worker.py               # Background trading worker
│   ├── bot.py                  # [shim] Backward-compat re-exports
│   ├── main.py                 # Entry point → CLI
│   └── __main__.py             # python -m src support
│
├── main.py                     # Root entry point
├── dashboard.py                # Streamlit dashboard
├── start.bat                   # Windows launcher
├── config.json                 # Trading configuration
├── schema.sql                  # Database schema
├── requirements.txt
├── README.md
├── ROADMAP.md
│
├── models/                     # Trained ML models
└── logs/                       # Application logs
```

### Deskripsi Modul
| Modul | Deskripsi |
|---|---|
| `constants/` | Trade mode enums, MT5 retcodes, timeframe mappings |
| `utils/` | Logging, exception classes, system helpers |
| `domain/` | Type aliases (`TradeSignal`, `SignalDict`) & domain models (`Trade`, `TradeManager`) |
| `analysis/` | Technical indicators (RSI, SMA, EMA, ADX, Bollinger) & regime detection |
| `strategy/` | `IStrategy` base class, auto-registry, 5 strategy implementations |
| `risk/` | `RiskManager` (balance/drawdown limits) & `ProtectionManager` |
| `trading/` | `TradingBot` orchestrator, `OrderManager`, `PairlistManager` |
| `exchange/` | Exchange abstractions: MT5, CCXT, Bybit + price/volume helpers |
| `backtesting/` | `Backtester` (SL/TP/commission/slippage simulation) & `Hyperopt` |
| `ml/` | Random Forest & LSTM models, trainer, feature engineering, agent pipeline |
| `persistence/` | `DatabaseManager`, trade history, performance logging, ratio calculators |
| `data/` | `DataProvider` — fetch OHLCV from exchange |
| `rpc/` | Telegram bot, WebSocket server, REST API backends |
| `commands/` | `TradingBotCLI` — interactive command-line interface |
| `configuration/` | `ConfigManager` — nested config with env var overrides |

## Cara Pakai
```python
from src.robot import AIRobot

robot = AIRobot(symbol="XAUUSD")
data = robot.fetch_data(count=2000)
results = robot.run_backtest_all(data)
robot.train_ml_model(data)
signal = robot.get_signal(data, use_ml=True)
```

## Strategi Tersedia
1. **MovingAverageCrossover** - Cross MA cepat & lambat
2. **RSIStrategy** - Overbought/oversold RSI
3. **MACDStrategy** - MACD histogram crossover
4. **BollingerBandsStrategy** - Bounce dari Bollinger Bands
5. **BreakoutStrategy** - Breakout dari range

## Catatan
- Butuh akun MT5 yang terhubung
- Data historis diperlukan untuk training ML
- Backtest menggunakan data dummy, hasil tidak mencerminkan performa riil