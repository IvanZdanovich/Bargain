"""Replay mode for backtesting with recorded data.

Provides deterministic replay of recorded market data
with configurable playback speed.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

from src.types import (
    DataType,
    HandlersData,
)

logger = logging.getLogger(__name__)


async def replay_from_file(
    file_path: Path,
    handlers: HandlersData,
    speed_multiplier: float = 1.0,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> dict[str, int]:
    """
    Replay recorded data from JSON Lines file.

    Args:
        file_path: Path to JSONL file with recorded messages.
        handlers: Event callbacks to invoke.
        speed_multiplier: Playback speed (1.0 = realtime, 0 = instant).
        start_time_ms: Optional start time filter.
        end_time_ms: Optional end time filter.

    Returns:
        Statistics dict with counts by event type.

    Side effects: Invokes handlers, simulates timing.
    """
    last_timestamp: int | None = None
    stats: dict[str, int] = {
        "trades": 0,
        "candles": 0,
        "ticks": 0,
        "orderbook_snapshots": 0,
        "orderbook_deltas": 0,
        "skipped": 0,
    }

    with open(file_path) as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)
            timestamp = record.get("timestamp_ms", 0)

            # Apply time filters
            if start_time_ms and timestamp < start_time_ms:
                stats["skipped"] += 1
                continue
            if end_time_ms and timestamp > end_time_ms:
                break

            # Simulate timing
            if last_timestamp is not None and speed_multiplier > 0:
                delay = (timestamp - last_timestamp) / 1000 / speed_multiplier
                if delay > 0:
                    await asyncio.sleep(delay)

            last_timestamp = timestamp

            # Route by type
            data_type = record.get("type")

            if data_type == "trade":
                stats["trades"] += 1
                trade_handler = handlers.get("on_trade")
                if trade_handler:
                    trade_handler(record.get("data", {}))

            elif data_type == "candle":
                stats["candles"] += 1
                candle_handler = handlers.get("on_candle")
                if candle_handler:
                    candle_handler(record.get("data", {}))

            elif data_type == "tick":
                stats["ticks"] += 1
                tick_handler = handlers.get("on_tick")
                if tick_handler:
                    tick_handler(record.get("data", {}))

            elif data_type == "orderbook_snapshot":
                stats["orderbook_snapshots"] += 1
                snapshot_handler = handlers.get("on_orderbook_snapshot")
                if snapshot_handler:
                    snapshot_handler(record.get("data", {}))

            elif data_type == "orderbook_delta":
                stats["orderbook_deltas"] += 1
                delta_handler = handlers.get("on_orderbook_delta")
                if delta_handler:
                    delta_handler(record.get("data", {}))

    return stats


async def replay_from_records(
    records: list[dict[str, Any]],
    handlers: HandlersData,
    speed_multiplier: float = 1.0,
) -> dict[str, int]:
    """
    Replay from in-memory records.

    Args:
        records: List of recorded event dicts.
        handlers: Event callbacks.
        speed_multiplier: Playback speed.

    Returns:
        Statistics dict.
    """
    stats: dict[str, int] = {
        "trades": 0,
        "candles": 0,
        "total": 0,
    }
    last_timestamp: int | None = None

    for record in records:
        timestamp = record.get("timestamp_ms", 0)
        stats["total"] += 1

        # Simulate timing
        if last_timestamp is not None and speed_multiplier > 0:
            delay = (timestamp - last_timestamp) / 1000 / speed_multiplier
            if delay > 0:
                await asyncio.sleep(delay)

        last_timestamp = timestamp

        data_type = record.get("type")

        if data_type == "trade":
            stats["trades"] += 1
            trade_handler = handlers.get("on_trade")
            if trade_handler:
                trade_handler(record.get("data", {}))

        elif data_type == "candle":
            stats["candles"] += 1
            candle_handler = handlers.get("on_candle")
            if candle_handler:
                candle_handler(record.get("data", {}))

        # Yield control
        await asyncio.sleep(0)

    return stats


async def replay_iterator(
    file_path: Path,
    data_types: list[DataType] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Iterate over recorded data as async generator.

    Args:
        file_path: Path to JSONL file.
        data_types: Optional filter for specific types.

    Yields:
        Recorded event dictionaries.
    """
    with open(file_path) as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            if data_types and record.get("type") not in data_types:
                continue

            yield record
            await asyncio.sleep(0)  # Yield control


def create_replay_recorder() -> dict[str, Any]:
    """
    Create a recorder state for capturing live data.

    Returns:
        Recorder state dictionary.
    """
    return {
        "records": [],
        "recording": False,
        "start_time_ms": None,
    }


def start_recording(state: dict[str, Any]) -> None:
    """
    Start recording events.

    Args:
        state: Recorder state.
    """
    import time

    state["recording"] = True
    state["start_time_ms"] = int(time.time() * 1000)
    state["records"].clear()


def stop_recording(state: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Stop recording and return captured events.

    Args:
        state: Recorder state.

    Returns:
        List of recorded events.
    """
    state["recording"] = False
    return cast(list[dict[str, Any]], state["records"].copy())


def record_event(
    state: dict[str, Any],
    event_type: str,
    data: dict[str, Any],
    timestamp_ms: int,
) -> None:
    """
    Record an event if recording is active.

    Args:
        state: Recorder state.
        event_type: Event type string.
        data: Event data payload.
        timestamp_ms: Event timestamp.
    """
    if not state["recording"]:
        return

    state["records"].append(
        {
            "type": event_type,
            "timestamp_ms": timestamp_ms,
            "data": data,
        }
    )


def save_recording(
    state: dict[str, Any],
    file_path: Path,
) -> int:
    """
    Save recorded events to JSONL file.

    Args:
        state: Recorder state.
        file_path: Output file path.

    Returns:
        Number of events saved.
    """
    records = state["records"]

    with open(file_path, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    return len(records)
