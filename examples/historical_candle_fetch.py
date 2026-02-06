"""Example: Historical candle fetch workflow.

This example demonstrates how to:
1. Create a Data Controller
2. Fetch historical candles from Binance
3. Process and store the data
"""

import asyncio
import logging
from datetime import datetime, timedelta

from src.types import (
    ProviderConfigData,
    HistoricalRequestData,
    HandlersData,
    CandleData,
)
from src.data_controller.controller import (
    create_controller,
    start_controller,
    stop_controller,
    fetch_historical,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def format_timestamp(timestamp_ms: int) -> str:
    """Format timestamp for display."""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M")


async def main():
    """Main entry point."""
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

    # Create controller (no handlers needed for historical)
    controller = create_controller([config], HandlersData())

    try:
        # Start controller
        logger.info("Starting Data Controller...")
        await start_controller(controller)

        # Define time range (last 24 hours)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        # Create historical request
        request = HistoricalRequestData(
            symbol="BTC/USDT",
            data_type="candle",
            start_time_ms=int(start_time.timestamp() * 1000),
            end_time_ms=int(end_time.timestamp() * 1000),
            interval="1h",
            limit=1000,
        )

        logger.info(
            f"Fetching candles from {start_time.isoformat()} "
            f"to {end_time.isoformat()}"
        )

        # Fetch and process candles
        candles: list[CandleData] = []

        async for candle in fetch_historical(controller, "binance", request):
            candles.append(candle)

            # Print progress
            if len(candles) % 10 == 0:
                logger.info(f"Fetched {len(candles)} candles...")

        # Summary
        logger.info(f"\nFetched {len(candles)} candles total")

        if candles:
            print("\n=== Sample Candles ===")
            for candle in candles[:5]:
                print(
                    f"{format_timestamp(candle['open_time_ms'])} | "
                    f"O: {candle['open']:>10} | "
                    f"H: {candle['high']:>10} | "
                    f"L: {candle['low']:>10} | "
                    f"C: {candle['close']:>10} | "
                    f"V: {candle['volume']:>12}"
                )

            if len(candles) > 5:
                print(f"... and {len(candles) - 5} more candles")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Stopping Data Controller...")
        await stop_controller(controller)
        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())

