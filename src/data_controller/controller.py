"""Unified Data Controller orchestrator.

Coordinates data providers, manages subscriptions, and delivers
normalized market data to downstream components via callbacks or event bus.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Sequence

from src.types import (
    ProviderConfigData,
    SubscriptionConfigData,
    HistoricalRequestData,
    HandlersData,
    OrderBookSnapshotData,
    ProviderStatus,
    ProviderHealthData,
    EventBusConfigData,
    StorageConfigData,
    MarketDataRecord,
    TradeHandlerFn,
    CandleHandlerFn,
    TickHandlerFn,
)
from src.data_controller.providers import binance
from src.data_controller.event_bus import (
    create_event_bus,
    emit_event,
    EVENT_TRADE,
    EVENT_CANDLE,
    EVENT_TICK,
    EVENT_ERROR,
    EVENT_STATUS_CHANGE,
)
from src.data_controller.storage import (
    create_storage_buffer,
    start_storage_buffer,
    stop_storage_buffer,
    buffer_record,
)

logger = logging.getLogger(__name__)


def create_controller(
    provider_configs: Sequence[ProviderConfigData],
    handlers: HandlersData | None = None,
    event_bus_config: EventBusConfigData | None = None,
    storage_config: StorageConfigData | None = None,
) -> dict[str, Any]:
    """
    Create Data Controller state container.

    Args:
        provider_configs: List of provider configurations.
        handlers: Optional event callback handlers.
        event_bus_config: Optional event bus configuration.
        storage_config: Optional storage layer configuration.

    Returns:
        Controller state dictionary.
    """
    providers: dict[str, dict[str, Any]] = {}

    for config in provider_configs:
        name = config["name"]
        if name == "binance" or name.startswith("binance"):
            providers[name] = binance.create_binance_provider(config)
        # Add more providers here as needed
        else:
            logger.warning(f"Unknown provider: {name}")

    # Create internal event bus for routing
    event_bus = create_event_bus()

    # Create storage buffer if configured
    storage_buffer = None
    if storage_config and storage_config.get("enabled", False):
        storage_buffer = create_storage_buffer(storage_config)

    return {
        "providers": providers,
        "handlers": handlers or {},
        "event_bus": event_bus,
        "event_bus_config": event_bus_config,
        "storage_buffer": storage_buffer,
        "storage_config": storage_config,
        "running": False,
        "tasks": [],
        "mode": "live",  # live, historical, replay
    }


async def start_controller(state: dict[str, Any]) -> None:
    """
    Start the Data Controller, connect all providers.

    Args:
        state: Controller state container.

    Side effects: Connects providers, starts event loops.
    """
    state["running"] = True

    # Start storage buffer if configured
    if state.get("storage_buffer"):
        await start_storage_buffer(state["storage_buffer"])

    # Connect all providers
    for name, provider_state in state["providers"].items():
        try:
            if name == "binance" or name.startswith("binance"):
                await binance.connect_binance(provider_state)

                # Start message processing loop
                task = asyncio.create_task(
                    _process_provider_messages(state, name, provider_state)
                )
                state["tasks"].append(task)

            _emit_status_change(state, name, "disconnected", provider_state["status"])
            logger.info(f"Provider {name} started")

        except Exception as e:
            logger.error(f"Failed to start provider {name}: {e}")
            _emit_error(state, name, e)


async def stop_controller(state: dict[str, Any]) -> None:
    """
    Stop the Data Controller gracefully.

    Args:
        state: Controller state container.

    Side effects: Cancels tasks, disconnects providers.
    """
    state["running"] = False

    # Cancel all message processing tasks
    for task in state["tasks"]:
        task.cancel()

    # Wait for tasks to complete
    if state["tasks"]:
        await asyncio.gather(*state["tasks"], return_exceptions=True)
    state["tasks"].clear()

    # Disconnect all providers
    for name, provider_state in state["providers"].items():
        try:
            if name == "binance" or name.startswith("binance"):
                await binance.disconnect_binance(provider_state)
        except Exception as e:
            logger.error(f"Error disconnecting provider {name}: {e}")

    # Stop storage buffer
    if state.get("storage_buffer"):
        await stop_storage_buffer(state["storage_buffer"])

    logger.info("Data Controller stopped")


async def subscribe(
    state: dict[str, Any],
    provider_name: str,
    subscriptions: Sequence[SubscriptionConfigData],
) -> None:
    """
    Subscribe to data streams on a provider.

    Args:
        state: Controller state container.
        provider_name: Target provider name.
        subscriptions: Subscription configurations.

    Raises:
        ValueError: If provider not found.
    """
    provider_state = state["providers"].get(provider_name)
    if not provider_state:
        raise ValueError(f"Unknown provider: {provider_name}")

    if provider_name == "binance" or provider_name.startswith("binance"):
        await binance.subscribe_binance(provider_state, subscriptions)


async def unsubscribe(
    state: dict[str, Any],
    provider_name: str,
    subscriptions: Sequence[SubscriptionConfigData],
) -> None:
    """
    Unsubscribe from data streams on a provider.

    Args:
        state: Controller state container.
        provider_name: Target provider name.
        subscriptions: Subscriptions to cancel.
    """
    provider_state = state["providers"].get(provider_name)
    if not provider_state:
        raise ValueError(f"Unknown provider: {provider_name}")

    if provider_name == "binance" or provider_name.startswith("binance"):
        await binance.unsubscribe_binance(provider_state, subscriptions)


async def fetch_historical(
    state: dict[str, Any],
    provider_name: str,
    request: HistoricalRequestData,
) -> AsyncIterator[MarketDataRecord]:
    """
    Fetch historical data from a provider.

    Args:
        state: Controller state container.
        provider_name: Target provider name.
        request: Historical data request.

    Yields:
        Normalized data records.
    """
    provider_state = state["providers"].get(provider_name)
    if not provider_state:
        raise ValueError(f"Unknown provider: {provider_name}")

    data_type = request["data_type"]

    if provider_name == "binance" or provider_name.startswith("binance"):
        if data_type == "candle":
            async for candle in binance.fetch_binance_historical_candles(
                provider_state, request
            ):
                # Optionally buffer to storage
                if state.get("storage_buffer"):
                    buffer_record(state["storage_buffer"], candle)
                yield candle

        elif data_type == "trade":
            async for trade in binance.fetch_binance_historical_trades(
                provider_state, request
            ):
                if state.get("storage_buffer"):
                    buffer_record(state["storage_buffer"], trade)
                yield trade


async def fetch_orderbook_snapshot(
    state: dict[str, Any],
    provider_name: str,
    symbol: str,
    limit: int = 100,
) -> OrderBookSnapshotData:
    """
    Fetch order book snapshot from a provider.

    Args:
        state: Controller state container.
        provider_name: Target provider name.
        symbol: Trading pair symbol.
        limit: Number of levels.

    Returns:
        Order book snapshot.
    """
    provider_state = state["providers"].get(provider_name)
    if not provider_state:
        raise ValueError(f"Unknown provider: {provider_name}")

    if provider_name == "binance" or provider_name.startswith("binance"):
        return await binance.fetch_binance_orderbook_snapshot(
            provider_state, symbol, limit
        )

    raise ValueError(f"Unsupported provider: {provider_name}")


def get_provider_status(state: dict[str, Any], provider_name: str) -> ProviderStatus:
    """
    Get current status of a provider.

    Args:
        state: Controller state container.
        provider_name: Provider to query.

    Returns:
        Current provider status.
    """
    provider_state = state["providers"].get(provider_name)
    if not provider_state:
        return "disconnected"
    return provider_state["status"]


def get_provider_health(
    state: dict[str, Any], provider_name: str
) -> ProviderHealthData:
    """
    Get health status of a provider.

    Args:
        state: Controller state container.
        provider_name: Provider to query.

    Returns:
        Provider health data.
    """
    provider_state = state["providers"].get(provider_name)
    if not provider_state:
        return ProviderHealthData(
            provider=provider_name,
            status="disconnected",
            last_message_ms=None,
            message_count=0,
            error_count=0,
            reconnect_count=0,
            latency_ms=None,
        )

    if provider_name == "binance" or provider_name.startswith("binance"):
        health = binance.get_binance_health(provider_state)
        return ProviderHealthData(
            provider=health["provider"],
            status=health["status"],
            last_message_ms=health.get("last_message_ms"),
            message_count=health.get("message_count", 0),
            error_count=health.get("error_count", 0),
            reconnect_count=health.get("reconnect_count", 0),
            latency_ms=None,
        )

    return ProviderHealthData(
        provider=provider_name,
        status=provider_state.get("status", "disconnected"),
        last_message_ms=None,
        message_count=0,
        error_count=0,
        reconnect_count=0,
        latency_ms=None,
    )


def get_all_provider_health(state: dict[str, Any]) -> list[ProviderHealthData]:
    """
    Get health status of all providers.

    Args:
        state: Controller state container.

    Returns:
        List of provider health data.
    """
    return [get_provider_health(state, name) for name in state["providers"]]


# === Internal Functions ===


async def _process_provider_messages(
    controller_state: dict[str, Any],
    provider_name: str,
    provider_state: dict[str, Any],
) -> None:
    """
    Process messages from provider and route to handlers/event bus.

    Args:
        controller_state: Controller state.
        provider_name: Name of provider.
        provider_state: Provider state.

    Side effects: Invokes handlers, emits events.
    """

    try:
        if provider_name == "binance" or provider_name.startswith("binance"):
            async for event in binance.iter_binance_messages(provider_state):
                if not controller_state["running"]:
                    break

                event_type = event.get("type")
                data = event.get("data")

                # Route to handlers
                if event_type:
                    _dispatch_event(controller_state, str(event_type), data)

    except asyncio.CancelledError:
        logger.info(f"Message processing cancelled for {provider_name}")
    except Exception as e:
        logger.error(f"Error processing messages from {provider_name}: {e}")
        _emit_error(controller_state, provider_name, e)

        # Attempt reconnection if configured
        if controller_state["running"]:
            try:
                await binance.reconnect_binance(provider_state)
                # Restart message processing
                task = asyncio.create_task(
                    _process_provider_messages(
                        controller_state, provider_name, provider_state
                    )
                )
                controller_state["tasks"].append(task)
            except Exception as reconnect_error:
                logger.error(
                    f"Reconnection failed for {provider_name}: {reconnect_error}"
                )


def _dispatch_event(
    state: dict[str, Any],
    event_type: str,
    data: Any,
) -> None:
    """
    Dispatch event to handlers, event bus, and storage.

    Args:
        state: Controller state.
        event_type: Event type string.
        data: Event data.
    """
    handlers = state["handlers"]
    event_bus = state["event_bus"]
    event_bus_config = state.get("event_bus_config")

    # Buffer to storage
    if state.get("storage_buffer") and data:
        buffer_record(state["storage_buffer"], data)

    # Call direct handlers
    if event_type == "trade":
        if handler := handlers.get("on_trade"):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Trade handler error: {e}")

    elif event_type == "candle":
        if handler := handlers.get("on_candle"):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Candle handler error: {e}")

    elif event_type == "tick":
        if handler := handlers.get("on_tick"):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Tick handler error: {e}")

    elif event_type == "orderbook_snapshot":
        if handler := handlers.get("on_orderbook_snapshot"):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Orderbook snapshot handler error: {e}")

    elif event_type == "orderbook_delta":
        if handler := handlers.get("on_orderbook_delta"):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Orderbook delta handler error: {e}")

    # Emit to internal event bus
    emit_event(event_bus, event_type, {"type": event_type, "data": data})

    # Emit to external event bus if configured
    if event_bus_config and event_bus_config.get("emit"):
        try:
            event_bus_config["emit"](event_type, {"type": event_type, "data": data})
        except Exception as e:
            logger.error(f"External event bus emit error: {e}")


def _emit_status_change(
    state: dict[str, Any],
    provider_name: str,
    old_status: ProviderStatus,
    new_status: ProviderStatus,
) -> None:
    """Emit provider status change event."""
    handlers = state["handlers"]

    if handler := handlers.get("on_status_change"):
        try:
            handler(provider_name, new_status)
        except Exception as e:
            logger.error(f"Status change handler error: {e}")

    emit_event(
        state["event_bus"],
        EVENT_STATUS_CHANGE,
        {
            "provider": provider_name,
            "old_status": old_status,
            "new_status": new_status,
        },
    )


def _emit_error(
    state: dict[str, Any],
    provider_name: str,
    error: Exception,
) -> None:
    """Emit error event."""
    handlers = state["handlers"]

    if handler := handlers.get("on_error"):
        try:
            handler(provider_name, error)
        except Exception as e:
            logger.error(f"Error handler error: {e}")

    emit_event(
        state["event_bus"],
        EVENT_ERROR,
        {
            "provider": provider_name,
            "error_type": type(error).__name__,
            "message": str(error),
        },
    )


# === Convenience Functions for Strategy Integration ===


def create_strategy_feed(
    state: dict[str, Any],
    on_trade: TradeHandlerFn | None = None,
    on_candle: CandleHandlerFn | None = None,
    on_tick: TickHandlerFn | None = None,
) -> dict[str, Any]:
    """
    Create a strategy feed configuration for direct data delivery.

    This provides a simple way to wire market data to strategy components.

    Args:
        state: Controller state.
        on_trade: Trade handler callback.
        on_candle: Candle handler callback.
        on_tick: Tick handler callback.

    Returns:
        Feed subscription handle.
    """
    from src.data_controller.event_bus import subscribe_event

    unsubscribers = []

    if on_trade:

        def trade_callback(e: dict[str, Any]) -> None:
            if data := e.get("data"):
                on_trade(data)

        unsub = subscribe_event(
            state["event_bus"],
            EVENT_TRADE,
            trade_callback,
        )
        unsubscribers.append(unsub)

    if on_candle:

        def candle_callback(e: dict[str, Any]) -> None:
            if data := e.get("data"):
                on_candle(data)

        unsub = subscribe_event(
            state["event_bus"],
            EVENT_CANDLE,
            candle_callback,
        )
        unsubscribers.append(unsub)

    if on_tick:

        def tick_callback(e: dict[str, Any]) -> None:
            if data := e.get("data"):
                on_tick(data)

        unsub = subscribe_event(
            state["event_bus"],
            EVENT_TICK,
            tick_callback,
        )
        unsubscribers.append(unsub)

    return {
        "unsubscribe": lambda: [unsub() for unsub in unsubscribers],
    }
