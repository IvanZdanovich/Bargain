"""Tests for backtesting controller."""

from decimal import Decimal

import pytest

from src.backtesting import StrategyBase, StrategyContext, run_backtest
from src.backtesting.feed import create_feed_from_candles
from src.config import SCHEMA_VERSION
from src.types import BacktestConfigData, CandleData


class SimpleTestStrategy(StrategyBase):
    """Simple buy-and-hold strategy for testing."""

    def __init__(self):
        self.bought = False

    def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
        if not self.bought and context.portfolio.cash > 0:
            # Buy with 90% of cash
            qty = (context.portfolio.cash * Decimal("0.9")) / bar["close"]
            context.broker.market_order(bar["symbol"], "buy", qty, bar["open_time_ms"])
            self.bought = True


def create_test_candles(count: int = 10) -> list[CandleData]:
    """Create test candle data."""
    candles = []
    base_time = 1640000000000

    for i in range(count):
        candle: CandleData = {
            "schema_version": SCHEMA_VERSION,
            "provider": "test",
            "symbol": "BTC/USDT",
            "interval": "1m",
            "open_time_ms": base_time + (i * 60000),
            "close_time_ms": base_time + ((i + 1) * 60000),
            "open": Decimal("40000") + Decimal(i * 10),
            "high": Decimal("40100") + Decimal(i * 10),
            "low": Decimal("39900") + Decimal(i * 10),
            "close": Decimal("40050") + Decimal(i * 10),
            "volume": Decimal("100"),
            "is_closed": True,
            "raw": {},
        }
        candles.append(candle)

    return candles


def test_basic_backtest():
    """Test basic backtest execution."""
    candles = create_test_candles(10)
    feed = create_feed_from_candles(candles)

    config: BacktestConfigData = {
        "symbols": ["BTC/USDT"],
        "start_time_ms": candles[0]["open_time_ms"],
        "end_time_ms": candles[-1]["close_time_ms"],
        "initial_cash": Decimal("10000"),
        "mode": "event_driven",
        "random_seed": 42,
    }

    strategy = SimpleTestStrategy()
    result = run_backtest(strategy, feed, config)

    assert result is not None
    assert "metrics" in result
    assert "equity_curve" in result
    assert len(result["equity_curve"]) > 0


def test_backtest_metrics():
    """Test backtest produces metrics."""
    candles = create_test_candles(50)
    feed = create_feed_from_candles(candles)

    config: BacktestConfigData = {
        "symbols": ["BTC/USDT"],
        "start_time_ms": candles[0]["open_time_ms"],
        "end_time_ms": candles[-1]["close_time_ms"],
        "initial_cash": Decimal("10000"),
        "mode": "event_driven",
    }

    strategy = SimpleTestStrategy()
    result = run_backtest(strategy, feed, config)

    metrics = result["metrics"]
    assert "total_return" in metrics
    assert "sharpe_ratio" in metrics
    assert "max_drawdown" in metrics
    assert "win_rate" in metrics


def test_backtest_determinism():
    """Test backtest produces deterministic results."""
    candles = create_test_candles(20)
    feed1 = create_feed_from_candles(candles)
    feed2 = create_feed_from_candles(candles)

    config: BacktestConfigData = {
        "symbols": ["BTC/USDT"],
        "start_time_ms": candles[0]["open_time_ms"],
        "end_time_ms": candles[-1]["close_time_ms"],
        "initial_cash": Decimal("10000"),
        "random_seed": 42,
    }

    result1 = run_backtest(SimpleTestStrategy(), feed1, config)
    result2 = run_backtest(SimpleTestStrategy(), feed2, config)

    # Results should be identical
    assert result1["metrics"]["total_return"] == result2["metrics"]["total_return"]
    assert len(result1["trades"]) == len(result2["trades"])
