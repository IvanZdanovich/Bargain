"""Example: Event bus integration for downstream components.

This example demonstrates how to:
1. Use the event bus for decoupled event handling
2. Integrate with a strategy component
3. Integrate with a storage layer
"""

import asyncio
import logging
from typing import Any

from src.types import (
    ProviderConfigData,
    SubscriptionConfigData,
    HandlersData,
    TradeData,
    CandleData,
    StorageConfigData,
)
from src.data_controller.controller import (
    create_controller,
    start_controller,
    stop_controller,
    subscribe,
    create_strategy_feed,
)
from src.data_controller.event_bus import (
    subscribe_event,
    EVENT_TRADE,
    EVENT_CANDLE,
    EVENT_ERROR,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# === Simulated Strategy Component ===

class SimpleMovingAverageStrategy:
    """
    Simple strategy that tracks moving average of prices.

    Note: This is a class for demonstration, but the actual
    signal generation uses pure functions internally.
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.prices: list[float] = []
        self.signals: list[dict] = []

    def on_trade(self, trade: TradeData) -> None:
        """Process trade and generate signals."""
        price = float(trade["price"])
        self.prices.append(price)

        # Keep only window_size prices
        if len(self.prices) > self.window_size:
            self.prices = self.prices[-self.window_size :]

        # Calculate moving average
        if len(self.prices) >= self.window_size:
            ma = sum(self.prices) / len(self.prices)

            # Simple signal: price above MA = bullish
            if price > ma * 1.001:  # 0.1% above MA
                signal = {
                    "symbol": trade["symbol"],
                    "side": "buy",
                    "price": price,
                    "ma": ma,
                    "timestamp_ms": trade["timestamp_ms"],
                }
                self.signals.append(signal)
                logger.info(f"Signal: BUY {trade['symbol']} @ {price:.2f} (MA: {ma:.2f})")
            elif price < ma * 0.999:  # 0.1% below MA
                signal = {
                    "symbol": trade["symbol"],
                    "side": "sell",
                    "price": price,
                    "ma": ma,
                    "timestamp_ms": trade["timestamp_ms"],
                }
                self.signals.append(signal)
                logger.info(f"Signal: SELL {trade['symbol']} @ {price:.2f} (MA: {ma:.2f})")


# === Simulated Storage Layer ===

class InMemoryStorage:
    """Simple in-memory storage for demonstration."""

    def __init__(self):
        self.trades: list[TradeData] = []
        self.candles: list[CandleData] = []

    async def write_trade(self, trade: TradeData) -> None:
        """Store a trade."""
        self.trades.append(trade)

    async def write_candle(self, candle: CandleData) -> None:
        """Store a candle."""
        self.candles.append(candle)

    def get_stats(self) -> dict[str, int]:
        """Get storage statistics."""
        return {
            "trades": len(self.trades),
            "candles": len(self.candles),
        }


async def main():
    """Main entry point."""
    # Initialize components
    strategy = SimpleMovingAverageStrategy(window_size=10)
    storage = InMemoryStorage()

    # Configure provider
    config = ProviderConfigData(
        name="binance",
        api_key=None,
        api_secret=None,
        testnet=False,
        rate_limit_per_second=10,
        reconnect_attempts=5,
        reconnect_delay_ms=1000,
    )

    # Create controller with storage integration
    storage_config = StorageConfigData(
        enabled=True,
        batch_size=50,
        flush_interval_ms=5000,
        write=storage.write_trade,  # Single record write
    )

    controller = create_controller(
        [config],
        handlers=HandlersData(),  # No direct handlers
        storage_config=storage_config,
    )

    try:
        # Start controller
        logger.info("Starting Data Controller with event bus integration...")
        await start_controller(controller)

        # === Method 1: Direct event bus subscription ===

        # Subscribe strategy to trade events via event bus
        unsubscribe_strategy = subscribe_event(
            controller["event_bus"],
            EVENT_TRADE,
            lambda e: strategy.on_trade(e["data"]) if e.get("data") else None,
        )

        # Subscribe to errors for logging
        subscribe_event(
            controller["event_bus"],
            EVENT_ERROR,
            lambda e: logger.error(f"Error event: {e}"),
        )

        # === Method 2: Using create_strategy_feed helper ===
        # (Alternative approach - commented out to avoid duplicate handling)
        #
        # feed = create_strategy_feed(
        #     controller,
        #     on_trade=strategy.on_trade,
        # )

        # Subscribe to market data
        await subscribe(
            controller,
            "binance",
            [
                SubscriptionConfigData(
                    symbol="BTC/USDT",
                    data_types=["trade"],
                    interval=None,
                ),
            ],
        )

        # Run for 30 seconds
        logger.info("Running for 30 seconds...")
        await asyncio.sleep(30)

        # Print summary
        print("\n=== Summary ===")
        print(f"Strategy signals generated: {len(strategy.signals)}")
        print(f"Storage stats: {storage.get_stats()}")

        if strategy.signals:
            print("\n=== Last 5 Signals ===")
            for signal in strategy.signals[-5:]:
                print(
                    f"  {signal['side'].upper()} {signal['symbol']} "
                    f"@ {signal['price']:.2f} (MA: {signal['ma']:.2f})"
                )

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Cleanup
        logger.info("Stopping Data Controller...")
        await stop_controller(controller)
        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())

