"""Backtesting subsystem for deterministic historical simulations.

This module provides:
- Event-driven and vectorized backtesting engines
- Simulated broker with realistic order execution
- Market data feeds from historical sources
- Strategy interface identical to live trading
- Performance metrics and analysis tools
- Trade/order logs and debug traces

Example usage:
    from src.backtesting import run_backtest, BacktestConfig
    from src.backtesting.strategy import StrategyBase

    class MyStrategy(StrategyBase):
        def on_bar(self, context, bar):
            context.broker.market_order("BTC/USDT", "buy", Decimal("0.1"))

    config = BacktestConfig(
        symbols=["BTC/USDT"],
        start_time_ms=1640000000000,
        end_time_ms=1640100000000,
        initial_cash=Decimal("10000"),
        mode="event_driven",
    )

    result = await run_backtest(MyStrategy(), config)
    print(result.metrics)
"""

from src.backtesting.broker import SimulatedBroker
from src.backtesting.controller import run_backtest
from src.backtesting.feed import MarketDataFeed
from src.backtesting.metrics import compute_metrics
from src.backtesting.strategy import StrategyBase, StrategyContext

__all__ = [
    "run_backtest",
    "StrategyBase",
    "StrategyContext",
    "SimulatedBroker",
    "MarketDataFeed",
    "compute_metrics",
]

