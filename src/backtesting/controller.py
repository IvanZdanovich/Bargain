"""Backtesting controller - main entry point for running backtests.

Provides:
- Event-driven backtest execution
- Strategy lifecycle management
- Result collection and metrics computation
- Deterministic simulations with seeded randomness
"""

import logging
from decimal import Decimal
from typing import Any

from src.backtesting.broker import (
    SimulatedBroker,
    apply_slippage_fixed_bps,
    compute_commission_percentage,
)
from src.backtesting.clock import PortfolioAccessor, SimulationClock
from src.backtesting.feed import MarketDataFeed
from src.backtesting.metrics import compute_metrics
from src.backtesting.strategy import StrategyBase, StrategyContext
from src.types import (
    BacktestConfigData,
    BacktestResultData,
    EquityPointData,
    FillData,
    OrderData,
    TradeLogEntryData,
)

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Event-driven backtesting engine.

    Orchestrates:
    - Market data iteration
    - Strategy callback invocation
    - Order execution simulation
    - State recording

    Input: Strategy, market data feed, configuration.
    Output: BacktestResult with metrics and logs.
    Side effects: Runs simulation, logs events.
    """

    def __init__(
        self,
        strategy: StrategyBase,
        feed: MarketDataFeed,
        config: BacktestConfigData,
    ):
        """Initialize backtest engine.

        Args:
            strategy: Strategy instance to test.
            feed: Market data feed.
            config: Backtest configuration.
        """
        self.strategy = strategy
        self.feed = feed
        self.config = config

        # Initialize components
        self.clock = SimulationClock()
        self.broker = self._create_broker()
        self.portfolio = PortfolioAccessor(self.broker)
        self.context = StrategyContext(
            broker=self.broker,
            portfolio=self.portfolio,
            clock=self.clock,
            config=dict(config) if config else None,
        )

        # Recording
        self.equity_curve: list[EquityPointData] = []
        self.debug_traces: list[dict[str, Any]] = []

        # Configure logging
        log_level = config.get("log_level", "INFO")
        logger.setLevel(getattr(logging, log_level, logging.INFO))

    def _create_broker(self) -> SimulatedBroker:
        """Create simulated broker with configuration.

        Returns:
            SimulatedBroker instance.
        """
        initial_cash = self.config.get("initial_cash", Decimal("10000"))
        random_seed = self.config.get("random_seed", 42)
        max_leverage = self.config.get("max_leverage", Decimal("1.0"))
        allow_short = self.config.get("allow_short", False)

        # Slippage function
        slippage_model = self.config.get("slippage_model", "fixed_bps")
        slippage_bps = self.config.get("slippage_bps", Decimal("5"))

        def slippage_fn(order, price, rng):
            if slippage_model == "fixed_bps":
                return apply_slippage_fixed_bps(order, price, slippage_bps, rng)
            return price  # No slippage

        # Commission function
        commission_model = self.config.get("commission_model", "percentage")
        commission_rate = self.config.get("commission_rate", Decimal("0.001"))

        def commission_fn(order, value):
            if commission_model == "percentage":
                return compute_commission_percentage(order, value, commission_rate)
            return Decimal("0")

        broker = SimulatedBroker(
            initial_cash=initial_cash,
            slippage_fn=slippage_fn,
            commission_fn=commission_fn,
            random_seed=random_seed,
            max_leverage=max_leverage,
            allow_short=allow_short,
        )

        # Wire callbacks
        broker.set_on_fill(self._on_fill)
        broker.set_on_order_update(self._on_order_update)

        return broker

    def _on_fill(self, fill: FillData) -> None:
        """Handle fill event from broker.

        Args:
            fill: Fill event.

        Side effects: Invokes strategy callback.
        """
        logger.debug(f"Fill: {fill['symbol']} {fill['side']} {fill['quantity']} @ {fill['price']}")

        # Call strategy callback
        self.strategy.on_fill(self.context, fill)

    def _on_order_update(self, order: OrderData) -> None:
        """Handle order update event from broker.

        Args:
            order: Order with updated status.

        Side effects: Invokes strategy callback.
        """
        logger.debug(f"Order update: {order['order_id']} status={order['status']}")

        # Call strategy callback
        self.strategy.on_order_update(self.context, order)

    def _record_equity_point(self, timestamp_ms: int) -> None:
        """Record equity curve point.

        Args:
            timestamp_ms: Current timestamp.

        Side effects: Appends to equity_curve.
        """
        if not self.config.get("record_equity_curve", True):
            return

        equity = self.broker.get_equity()
        unrealized_pnl = self.portfolio.total_unrealized_pnl
        realized_pnl = self.portfolio.total_realized_pnl

        point: EquityPointData = {
            "timestamp_ms": timestamp_ms,
            "equity": equity,
            "cash": self.broker.cash,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl,
        }

        self.equity_curve.append(point)

    def run(self) -> BacktestResultData:
        """Run backtest simulation.

        Returns:
            BacktestResult with metrics and logs.

        Side effects: Executes full simulation.
        """
        logger.info("Starting backtest simulation")

        # Initialize time range
        time_range = self.feed.get_time_range()
        if time_range:
            start_time, end_time = time_range
            self.clock.update(start_time)
            logger.info(f"Time range: {start_time} to {end_time}")

        # Call strategy.on_start
        self.strategy.on_start(self.context)

        # Record initial equity
        if time_range:
            self._record_equity_point(time_range[0])

        # Main event loop
        event_count = 0
        for event_type, event_data in self.feed:
            event_count += 1

            # Update clock
            if event_type == "candle":
                timestamp = event_data["open_time_ms"]
            elif event_type == "tick" or event_type == "trade":
                timestamp = event_data["timestamp_ms"]
            else:
                continue

            self.clock.update(timestamp)

            # Route event to strategy
            if event_type == "candle":
                self.strategy.on_bar(self.context, event_data)
                # Process broker with bar data
                self.broker.process_bar(event_data, timestamp)

            elif event_type == "tick":
                self.strategy.on_tick(self.context, event_data)
                # Process broker with tick data
                self.broker.process_tick(event_data, timestamp)

            elif event_type == "trade":
                self.strategy.on_trade(self.context, event_data)

            # Record equity snapshot periodically
            if event_count % 100 == 0:
                self._record_equity_point(timestamp)

        # Final equity recording
        if time_range:
            self._record_equity_point(time_range[1])

        # Call strategy.on_end
        self.strategy.on_end(self.context)

        logger.info(f"Backtest complete: {event_count} events processed")

        # Build result
        return self._build_result()

    def _build_result(self) -> BacktestResultData:
        """Build final backtest result.

        Returns:
            BacktestResultData with all outputs.
        """
        # Collect trades from broker fills
        trades: list[TradeLogEntryData] = []
        for fill in self.broker.fills:
            trade: TradeLogEntryData = {
                "trade_id": fill["fill_id"],
                "order_id": fill["order_id"],
                "symbol": fill["symbol"],
                "side": fill["side"],
                "timestamp_ms": fill["timestamp_ms"],
                "price": fill["price"],
                "quantity": fill["quantity"],
                "fee": fill["fee"],
                "slippage": fill["slippage"],
                "realized_pnl": fill["realized_pnl"],
            }
            trades.append(trade)

        # Collect orders
        orders = list(self.broker.filled_orders) + list(self.broker.open_orders.values())

        # Collect positions
        positions = list(self.broker.positions.values())

        # Compute metrics
        initial_cash = self.config.get("initial_cash", Decimal("10000"))
        metrics = compute_metrics(self.equity_curve, trades, initial_cash)

        result: BacktestResultData = {
            "config": dict(self.config),
            "metrics": metrics,
            "equity_curve": (
                self.equity_curve if self.config.get("record_equity_curve", True) else []
            ),
            "positions": positions if self.config.get("record_positions", True) else [],
            "trades": trades if self.config.get("record_trades", True) else [],
            "orders": orders if self.config.get("record_orders", True) else [],
            "debug_traces": self.debug_traces,
        }

        return result


def run_backtest(
    strategy: StrategyBase,
    feed: MarketDataFeed,
    config: BacktestConfigData,
) -> BacktestResultData:
    """Run a backtest simulation.

    Main entry point for backtesting.

    Args:
        strategy: Strategy to test.
        feed: Market data feed.
        config: Backtest configuration.

    Returns:
        BacktestResult with metrics and logs.

    Example:
        config = BacktestConfigData(
            symbols=["BTC/USDT"],
            start_time_ms=1640000000000,
            end_time_ms=1640100000000,
            initial_cash=Decimal("10000"),
            mode="event_driven",
        )

        feed = create_feed_from_file(Path("data.jsonl"))
        result = run_backtest(MyStrategy(), feed, config)
        print(result["metrics"])
    """
    engine = BacktestEngine(strategy, feed, config)
    return engine.run()


def run_backtest_from_file(
    strategy: StrategyBase,
    data_file: Any,
    config: BacktestConfigData,
) -> BacktestResultData:
    """Run backtest loading data from file.

    Convenience wrapper that creates feed from file.

    Args:
        strategy: Strategy to test.
        data_file: Path to data file.
        config: Backtest configuration.

    Returns:
        BacktestResult.
    """
    from pathlib import Path

    from src.backtesting.feed import create_feed_from_file

    feed = create_feed_from_file(
        Path(data_file),
        symbols=config.get("symbols"),
        start_time_ms=config.get("start_time_ms"),
        end_time_ms=config.get("end_time_ms"),
    )

    return run_backtest(strategy, feed, config)
