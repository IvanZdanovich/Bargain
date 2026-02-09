"""Strategy interface for backtesting and live trading.

Provides:
- Base class for strategies with lifecycle callbacks
- Strategy context for accessing broker, portfolio, and data
- Identical interface for backtest and live modes
"""

from typing import Any

from src.types import CandleData, FillData, OrderData, TickData, TradeData


class StrategyContext:
    """Context object passed to strategy callbacks.

    Provides access to:
    - broker: For placing orders
    - portfolio: Current portfolio state
    - clock: Current simulation time
    - config: Strategy configuration
    - data: Historical data access (optional)
    """

    def __init__(
        self,
        broker: Any,
        portfolio: Any,
        clock: Any,
        config: dict[str, Any] | None = None,
        data: Any = None,
    ):
        """Initialize strategy context.

        Args:
            broker: Broker interface for order placement.
            portfolio: Portfolio state accessor.
            clock: Clock for current time.
            config: Strategy configuration dict.
            data: Optional data accessor for historical lookback.
        """
        self.broker = broker
        self.portfolio = portfolio
        self.clock = clock
        self.config = config or {}
        self.data = data

    @property
    def now(self) -> int:
        """Get current timestamp in milliseconds.

        Returns:
            Current simulation timestamp.
        """
        return int(self.clock.now_ms())


class StrategyBase:
    """Base class for trading strategies.

    Strategies must implement on_bar or on_tick, and optionally
    other lifecycle callbacks. The same strategy code works in
    both backtesting and live trading.

    Example:
        class MomentumStrategy(StrategyBase):
            def on_start(self, context: StrategyContext) -> None:
                self.position = Decimal("0")

            def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
                if self.position == 0:
                    context.broker.market_order(bar["symbol"], "buy", Decimal("1.0"))
                    self.position = Decimal("1.0")
    """

    def on_start(self, context: StrategyContext) -> None:
        """Called once at strategy initialization.

        Use this to initialize strategy state, load parameters, etc.

        Args:
            context: Strategy context with broker, portfolio access.

        Side effects: May initialize strategy state.
        """
        pass

    def on_end(self, context: StrategyContext) -> None:
        """Called once at strategy termination.

        Use this for cleanup, final logging, etc.

        Args:
            context: Strategy context.

        Side effects: May log or cleanup resources.
        """
        pass

    def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
        """Called for each bar/candle event.

        Args:
            context: Strategy context.
            bar: OHLCV candle data.

        Side effects: May place orders via context.broker.
        """
        pass

    def on_tick(self, context: StrategyContext, tick: TickData) -> None:
        """Called for each tick event (best bid/ask).

        Args:
            context: Strategy context.
            tick: Tick data with bid/ask prices.

        Side effects: May place orders via context.broker.
        """
        pass

    def on_trade(self, context: StrategyContext, trade: TradeData) -> None:
        """Called for each market trade event.

        Args:
            context: Strategy context.
            trade: Market trade data.

        Side effects: May place orders via context.broker.
        """
        pass

    def on_fill(self, context: StrategyContext, fill: FillData) -> None:
        """Called when an order is filled.

        Args:
            context: Strategy context.
            fill: Fill event with price, quantity, fees.

        Side effects: May update strategy state or place new orders.
        """
        pass

    def on_order_update(self, context: StrategyContext, order: OrderData) -> None:
        """Called when an order status changes.

        Args:
            context: Strategy context.
            order: Order with updated status.

        Side effects: May log or react to order changes.
        """
        pass


def create_simple_strategy(
    on_bar_fn: Any = None,
    on_tick_fn: Any = None,
    on_start_fn: Any = None,
    on_end_fn: Any = None,
) -> StrategyBase:
    """Create a simple strategy from callback functions.

    Convenience factory for functional-style strategies without
    defining a class.

    Args:
        on_bar_fn: Bar callback function.
        on_tick_fn: Tick callback function.
        on_start_fn: Start callback function.
        on_end_fn: End callback function.

    Returns:
        Strategy instance with specified callbacks.

    Example:
        def my_bar_logic(ctx, bar):
            if bar["close"] > bar["open"]:
                ctx.broker.market_order(bar["symbol"], "buy", Decimal("1.0"))

        strategy = create_simple_strategy(on_bar_fn=my_bar_logic)
    """

    class FunctionalStrategy(StrategyBase):
        def on_start(self, context: StrategyContext) -> None:
            if on_start_fn:
                on_start_fn(context)

        def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
            if on_bar_fn:
                on_bar_fn(context, bar)

        def on_tick(self, context: StrategyContext, tick: TickData) -> None:
            if on_tick_fn:
                on_tick_fn(context, tick)

        def on_end(self, context: StrategyContext) -> None:
            if on_end_fn:
                on_end_fn(context)

    return FunctionalStrategy()
