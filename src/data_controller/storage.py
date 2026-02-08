"""Storage integration for persisting market data.

Provides buffered async writes to downstream storage layers.
Uses async iterator pattern for streaming data to storage.
"""

import asyncio
import logging
from typing import Any, Sequence

from src.types import MarketDataRecord, StorageConfigData
from src.config import get_storage_defaults

logger = logging.getLogger(__name__)


def create_storage_buffer(
    config: StorageConfigData,
) -> dict[str, Any]:
    """
    Create storage buffer state.

    Args:
        config: Storage configuration.

    Returns:
        Storage buffer state dictionary.
    """
    return {
        "config": config,
        "buffer": [],
        "write_count": 0,
        "error_count": 0,
        "last_flush_ms": 0,
        "flush_task": None,
        "running": False,
    }


async def start_storage_buffer(state: dict[str, Any]) -> None:
    """
    Start the storage buffer flush loop.

    Args:
        state: Storage buffer state.

    Side effects: Starts background flush task.
    """
    if not state["config"].get("enabled", False):
        logger.info("Storage buffer disabled")
        return

    state["running"] = True
    state["flush_task"] = asyncio.create_task(_flush_loop(state))
    logger.info("Storage buffer started")


async def stop_storage_buffer(state: dict[str, Any]) -> None:
    """
    Stop the storage buffer, flushing remaining data.

    Args:
        state: Storage buffer state.

    Side effects: Cancels flush task, flushes buffer.
    """
    state["running"] = False

    if state["flush_task"]:
        state["flush_task"].cancel()
        try:
            await state["flush_task"]
        except asyncio.CancelledError:
            pass

    # Final flush
    await flush_buffer(state)
    logger.info("Storage buffer stopped")


def buffer_record(state: dict[str, Any], record: MarketDataRecord) -> None:
    """
    Add a record to the storage buffer.

    Args:
        state: Storage buffer state.
        record: Market data record to buffer.

    Side effects: Appends to buffer.
    """
    if not state["config"].get("enabled", False):
        return

    state["buffer"].append(record)

    # Check if we should flush immediately
    storage_defaults = get_storage_defaults()
    batch_size = state["config"].get("batch_size", storage_defaults["batch_size"])
    if len(state["buffer"]) >= batch_size:
        asyncio.create_task(flush_buffer(state))


async def flush_buffer(state: dict[str, Any]) -> None:
    """
    Flush buffered records to storage.

    Args:
        state: Storage buffer state.

    Side effects: Writes to storage, clears buffer.
    """
    if not state["buffer"]:
        return

    records = state["buffer"].copy()
    state["buffer"].clear()

    batch_write = state["config"].get("batch_write")
    write = state["config"].get("write")

    try:
        if batch_write:
            await batch_write(records)
            state["write_count"] += len(records)
        elif write:
            for record in records:
                await write(record)
                state["write_count"] += 1
    except Exception as e:
        state["error_count"] += 1
        logger.error(f"Storage write failed: {e}")
        # Re-add records to buffer for retry
        state["buffer"].extend(records)

    import time
    state["last_flush_ms"] = int(time.time() * 1000)


async def _flush_loop(state: dict[str, Any]) -> None:
    """
    Background flush loop.

    Args:
        state: Storage buffer state.
    """
    storage_defaults = get_storage_defaults()
    flush_interval_ms = state["config"].get(
        "flush_interval_ms", storage_defaults["flush_interval_ms"]
    )
    flush_interval_s = flush_interval_ms / 1000

    while state["running"]:
        try:
            await asyncio.sleep(flush_interval_s)
            await flush_buffer(state)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Flush loop error: {e}")


def get_storage_stats(state: dict[str, Any]) -> dict[str, Any]:
    """
    Get storage buffer statistics.

    Args:
        state: Storage buffer state.

    Returns:
        Statistics dictionary.
    """
    return {
        "buffer_size": len(state["buffer"]),
        "write_count": state["write_count"],
        "error_count": state["error_count"],
        "last_flush_ms": state["last_flush_ms"],
        "running": state["running"],
    }


async def pipe_to_storage(
    records: Sequence[MarketDataRecord],
    config: StorageConfigData,
) -> int:
    """
    Pipe a sequence of records directly to storage.

    Args:
        records: Records to store.
        config: Storage configuration.

    Returns:
        Number of records written.

    Side effects: Writes to storage.
    """
    if not config.get("enabled", False):
        return 0

    batch_write = config.get("batch_write")
    write = config.get("write")
    count = 0

    try:
        if batch_write:
            await batch_write(records)
            count = len(records)
        elif write:
            for record in records:
                await write(record)
                count += 1
    except Exception as e:
        logger.error(f"Pipe to storage failed: {e}")

    return count

