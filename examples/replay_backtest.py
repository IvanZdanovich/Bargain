"""Example: Replay mode for backtesting.

This example demonstrates how to:
1. Record live data for later replay
2. Replay recorded data for backtesting
3. Use replay with consistent timing
"""

import asyncio
import logging
from pathlib import Path
from decimal import Decimal

from src.types import HandlersData, TradeData, CandleData
from src.data_controller.replay import (
    replay_from_file,
    replay_from_records,
    create_replay_recorder,
    start_recording,
    stop_recording,
    record_event,
    save_recording,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# === Simulated Strategy for Backtesting ===

def create_backtest_state() -> dict:
    """Create backtest state container."""
    return {
        "position": Decimal("0"),
        "cash": Decimal("10000"),
        "entry_price": None,
        "trades": [],
        "pnl": Decimal("0"),
    }


def process_trade_backtest(state: dict, trade: dict) -> None:
    """
    Simple momentum strategy for backtest.

    Args:
        state: Backtest state (modified in place).
        trade: Trade data dictionary.
    """
    price = Decimal(str(trade.get("price", trade.get("p", "0"))))

    # Simple logic: buy on first trade if no position
    if state["position"] == 0 and state["cash"] >= price:
        # Buy 0.1 units
        qty = Decimal("0.1")
        cost = price * qty

        if cost <= state["cash"]:
            state["position"] += qty
            state["cash"] -= cost
            state["entry_price"] = price
            state["trades"].append({
                "side": "buy",
                "price": float(price),
                "qty": float(qty),
            })
            logger.info(f"Backtest: BUY 0.1 @ {price}")

    # Sell if we have position and price is 0.5% higher
    elif state["position"] > 0 and state["entry_price"]:
        if price >= state["entry_price"] * Decimal("1.005"):
            # Sell all
            revenue = price * state["position"]
            profit = revenue - (state["entry_price"] * state["position"])

            state["cash"] += revenue
            state["pnl"] += profit
            state["trades"].append({
                "side": "sell",
                "price": float(price),
                "qty": float(state["position"]),
                "profit": float(profit),
            })
            logger.info(f"Backtest: SELL @ {price}, profit: {profit:.2f}")

            state["position"] = Decimal("0")
            state["entry_price"] = None


async def demo_replay_from_fixture():
    """Demonstrate replay from fixture file."""
    logger.info("=== Replay from Fixture File ===")

    # Path to fixture file
    fixture_path = Path(__file__).parent.parent / "tests/data_controller/fixtures/sample_messages.jsonl"

    if not fixture_path.exists():
        logger.warning(f"Fixture file not found: {fixture_path}")
        return

    # Create backtest state
    state = create_backtest_state()

    # Define handlers
    handlers = HandlersData(
        on_trade=lambda d: process_trade_backtest(state, d),
        on_candle=lambda d: logger.debug(f"Candle: {d}"),
    )

    # Replay with instant speed (speed_multiplier=0)
    logger.info("Starting replay...")
    stats = await replay_from_file(
        fixture_path,
        handlers,
        speed_multiplier=0,  # Instant replay for backtest
    )

    # Print results
    print("\n=== Backtest Results ===")
    print(f"Events replayed: trades={stats['trades']}, candles={stats['candles']}")
    print(f"Total trades executed: {len(state['trades'])}")
    print(f"Final position: {state['position']}")
    print(f"Final cash: {state['cash']:.2f}")
    print(f"Total PnL: {state['pnl']:.2f}")


async def demo_replay_from_memory():
    """Demonstrate replay from in-memory records."""
    logger.info("\n=== Replay from In-Memory Records ===")

    # Create synthetic records
    records = [
        {
            "type": "trade",
            "timestamp_ms": 1000,
            "data": {"price": "42000.00", "quantity": "0.5", "side": "buy"},
        },
        {
            "type": "trade",
            "timestamp_ms": 2000,
            "data": {"price": "42100.00", "quantity": "0.3", "side": "sell"},
        },
        {
            "type": "trade",
            "timestamp_ms": 3000,
            "data": {"price": "42200.00", "quantity": "0.8", "side": "buy"},
        },
        {
            "type": "candle",
            "timestamp_ms": 4000,
            "data": {
                "open": "42000.00",
                "high": "42250.00",
                "low": "41950.00",
                "close": "42200.00",
            },
        },
        {
            "type": "trade",
            "timestamp_ms": 5000,
            "data": {"price": "42250.00", "quantity": "1.0", "side": "buy"},
        },
    ]

    # Create state
    state = create_backtest_state()

    # Replay
    handlers = HandlersData(
        on_trade=lambda d: process_trade_backtest(state, d),
    )

    stats = await replay_from_records(records, handlers, speed_multiplier=0)

    print(f"\nReplayed {stats['total']} events")
    print(f"Trades in state: {len(state['trades'])}")


async def demo_recording():
    """Demonstrate recording events for later replay."""
    logger.info("\n=== Recording Demo ===")

    # Create recorder
    recorder = create_replay_recorder()

    # Start recording
    start_recording(recorder)
    logger.info("Recording started...")

    # Simulate receiving events
    import time
    base_time = int(time.time() * 1000)

    # Record some synthetic events
    for i in range(5):
        record_event(
            recorder,
            "trade",
            {
                "symbol": "BTC/USDT",
                "price": str(42000 + i * 10),
                "quantity": "0.1",
                "side": "buy" if i % 2 == 0 else "sell",
            },
            base_time + i * 100,
        )

    # Record a candle
    record_event(
        recorder,
        "candle",
        {
            "symbol": "BTC/USDT",
            "interval": "1m",
            "open": "42000",
            "high": "42050",
            "low": "41990",
            "close": "42040",
        },
        base_time + 500,
    )

    # Stop recording
    records = stop_recording(recorder)
    logger.info(f"Recording stopped. Captured {len(records)} events.")

    # Show recorded events
    print("\n=== Recorded Events ===")
    for record in records:
        print(f"  [{record['type']}] {record['data']}")

    # Save to file (optional)
    # output_path = Path("/tmp/recording.jsonl")
    # count = save_recording(recorder, output_path)
    # logger.info(f"Saved {count} events to {output_path}")


async def main():
    """Main entry point."""
    await demo_replay_from_fixture()
    await demo_replay_from_memory()
    await demo_recording()


if __name__ == "__main__":
    asyncio.run(main())

