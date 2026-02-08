"""Example: Live tick ingestion workflow.

This example demonstrates how to:
1. Create a Data Controller
2. Connect to Binance
3. Subscribe to trade streams
4. Process incoming trades
"""

import asyncio
import logging
from decimal import Decimal

from src.types import (
    ProviderConfigData,
    SubscriptionConfigData,
    HandlersData,
    TradeData,
    CandleData,
)
from src.data_controller.controller import (
    create_controller,
    start_controller,
    stop_controller,
    subscribe,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# === Trade Handler ===

def handle_trade(trade: TradeData) -> None:
    """
    Process incoming trade.

    Args:
        trade: Normalized trade data.
    """
    print(
        f"Trade: {trade['symbol']} {trade['side'].upper()} "
        f"{trade['quantity']} @ {trade['price']}"
    )


def handle_candle(candle: CandleData) -> None:
    """
    Process incoming candle.

    Args:
        candle: Normalized candle data.
    """
    status = "CLOSED" if candle["is_closed"] else "OPEN"
    print(
        f"Candle [{status}]: {candle['symbol']} {candle['interval']} "
        f"O={candle['open']} H={candle['high']} L={candle['low']} C={candle['close']}"
    )


def handle_error(provider: str, error: Exception) -> None:
    """Handle provider errors."""
    logger.error(f"Error from {provider}: {error}")


def handle_status_change(provider: str, status: str) -> None:
    """Handle provider status changes."""
    logger.info(f"Provider {provider} status: {status}")


async def main():
    """Main entry point."""
    # Configure provider
    config = ProviderConfigData(
        name="binance",
        api_key=None,  # Not needed for public streams
        api_secret=None,
        testnet=False,  # Use mainnet for real data
        rate_limit_per_second=10,
        reconnect_attempts=5,
        reconnect_delay_ms=1000,
    )

    # Configure handlers
    handlers = HandlersData(
        on_trade=handle_trade,
        on_candle=handle_candle,
        on_error=handle_error,
        on_status_change=handle_status_change,
    )

    # Create controller
    controller = create_controller([config], handlers)

    try:
        # Start controller (connects to provider)
        logger.info("Starting Data Controller...")
        await start_controller(controller)

        # Subscribe to streams
        logger.info("Subscribing to streams...")
        await subscribe(
            controller,
            "binance",
            [
                SubscriptionConfigData(
                    symbol="BTC/USDT",
                    data_types=["trade", "candle"],
                    interval="1m",
                ),
                SubscriptionConfigData(
                    symbol="ETH/USDT",
                    data_types=["trade"],
                    interval=None,
                ),
            ],
        )

        # Run for 60 seconds
        logger.info("Listening for 60 seconds...")
        await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Cleanup
        logger.info("Stopping Data Controller...")
        await stop_controller(controller)
        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())

