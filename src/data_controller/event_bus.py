"""Simple event bus for decoupled event emission.

Provides publish/subscribe pattern for market data events,
allowing downstream components (storage, strategies) to subscribe.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Event type constants
EVENT_TRADE = "trade"
EVENT_CANDLE = "candle"
EVENT_TICK = "tick"
EVENT_ORDERBOOK_SNAPSHOT = "orderbook_snapshot"
EVENT_ORDERBOOK_DELTA = "orderbook_delta"
EVENT_ERROR = "error"
EVENT_STATUS_CHANGE = "status_change"
EVENT_HEALTH_UPDATE = "health_update"


def create_event_bus() -> dict[str, Any]:
    """
    Create event bus state container.

    Returns:
        Event bus state dictionary with subscriber lists.
    """
    return {
        "subscribers": {},  # event_type -> list of callbacks
        "async_subscribers": {},  # event_type -> list of async callbacks
        "event_count": 0,
        "error_count": 0,
    }


def subscribe_event(
    bus: dict[str, Any],
    event_type: str,
    callback: Callable[[dict[str, Any]], None],
) -> Callable[[], None]:
    """
    Subscribe to an event type.

    Args:
        bus: Event bus state.
        event_type: Event type to subscribe to.
        callback: Function to call when event fires.

    Returns:
        Unsubscribe function.
    """
    if event_type not in bus["subscribers"]:
        bus["subscribers"][event_type] = []

    bus["subscribers"][event_type].append(callback)

    def unsubscribe() -> None:
        if callback in bus["subscribers"].get(event_type, []):
            bus["subscribers"][event_type].remove(callback)

    return unsubscribe


def subscribe_event_async(
    bus: dict[str, Any],
    event_type: str,
    callback: Callable[[dict[str, Any]], Any],
) -> Callable[[], None]:
    """
    Subscribe to an event type with async callback.

    Args:
        bus: Event bus state.
        event_type: Event type to subscribe to.
        callback: Async function to call when event fires.

    Returns:
        Unsubscribe function.
    """
    if event_type not in bus["async_subscribers"]:
        bus["async_subscribers"][event_type] = []

    bus["async_subscribers"][event_type].append(callback)

    def unsubscribe() -> None:
        if callback in bus["async_subscribers"].get(event_type, []):
            bus["async_subscribers"][event_type].remove(callback)

    return unsubscribe


def emit_event(
    bus: dict[str, Any],
    event_type: str,
    data: dict[str, Any],
) -> None:
    """
    Emit an event to all subscribers (sync).

    Args:
        bus: Event bus state.
        event_type: Event type being emitted.
        data: Event data payload.

    Side effects: Calls all registered callbacks.
    """
    bus["event_count"] += 1

    callbacks = bus["subscribers"].get(event_type, [])
    for callback in callbacks:
        try:
            callback(data)
        except Exception as e:
            bus["error_count"] += 1
            logger.error(f"Error in event subscriber for {event_type}: {e}")


async def emit_event_async(
    bus: dict[str, Any],
    event_type: str,
    data: dict[str, Any],
) -> None:
    """
    Emit an event to all subscribers (async).

    Args:
        bus: Event bus state.
        event_type: Event type being emitted.
        data: Event data payload.

    Side effects: Calls all registered callbacks.
    """
    bus["event_count"] += 1

    # Call sync subscribers first
    callbacks = bus["subscribers"].get(event_type, [])
    for callback in callbacks:
        try:
            callback(data)
        except Exception as e:
            bus["error_count"] += 1
            logger.error(f"Error in sync subscriber for {event_type}: {e}")

    # Then async subscribers
    async_callbacks = bus["async_subscribers"].get(event_type, [])
    if async_callbacks:
        tasks = []
        for callback in async_callbacks:
            try:
                result = callback(data)
                if asyncio.iscoroutine(result):
                    tasks.append(asyncio.create_task(result))
            except Exception as e:
                bus["error_count"] += 1
                logger.error(f"Error in async subscriber for {event_type}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def get_event_stats(bus: dict[str, Any]) -> dict[str, Any]:
    """
    Get event bus statistics.

    Args:
        bus: Event bus state.

    Returns:
        Statistics dictionary.
    """
    subscriber_counts = {
        event_type: len(callbacks) for event_type, callbacks in bus["subscribers"].items()
    }
    async_subscriber_counts = {
        event_type: len(callbacks) for event_type, callbacks in bus["async_subscribers"].items()
    }

    return {
        "event_count": bus["event_count"],
        "error_count": bus["error_count"],
        "subscriber_counts": subscriber_counts,
        "async_subscriber_counts": async_subscriber_counts,
    }


def clear_subscribers(bus: dict[str, Any], event_type: str | None = None) -> None:
    """
    Clear subscribers for an event type or all events.

    Args:
        bus: Event bus state.
        event_type: Specific event type or None for all.
    """
    if event_type is None:
        bus["subscribers"].clear()
        bus["async_subscribers"].clear()
    else:
        bus["subscribers"].pop(event_type, None)
        bus["async_subscribers"].pop(event_type, None)
