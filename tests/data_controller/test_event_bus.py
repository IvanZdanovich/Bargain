"""Unit tests for event bus."""

import pytest

from src.data_controller.event_bus import (
    create_event_bus,
    emit_event,
    subscribe_event,
    subscribe_event_async,
    get_event_stats,
    clear_subscribers,
    EVENT_TRADE,
    EVENT_CANDLE,
)


class TestEventBus:
    """Tests for event bus functions."""

    def test_create_event_bus(self):
        """Create empty event bus."""
        bus = create_event_bus()

        assert bus["subscribers"] == {}
        assert bus["async_subscribers"] == {}
        assert bus["event_count"] == 0
        assert bus["error_count"] == 0

    def test_subscribe_and_emit(self):
        """Subscribe to event and receive it."""
        bus = create_event_bus()
        received = []

        def handler(data):
            received.append(data)

        subscribe_event(bus, EVENT_TRADE, handler)
        emit_event(bus, EVENT_TRADE, {"price": 100})

        assert len(received) == 1
        assert received[0]["price"] == 100

    def test_multiple_subscribers(self):
        """Multiple subscribers receive same event."""
        bus = create_event_bus()
        received1 = []
        received2 = []

        subscribe_event(bus, EVENT_TRADE, lambda d: received1.append(d))
        subscribe_event(bus, EVENT_TRADE, lambda d: received2.append(d))

        emit_event(bus, EVENT_TRADE, {"price": 100})

        assert len(received1) == 1
        assert len(received2) == 1

    def test_unsubscribe(self):
        """Unsubscribe stops receiving events."""
        bus = create_event_bus()
        received = []

        unsubscribe = subscribe_event(bus, EVENT_TRADE, lambda d: received.append(d))
        emit_event(bus, EVENT_TRADE, {"price": 100})

        unsubscribe()
        emit_event(bus, EVENT_TRADE, {"price": 200})

        assert len(received) == 1
        assert received[0]["price"] == 100

    def test_different_event_types(self):
        """Different event types are isolated."""
        bus = create_event_bus()
        trades = []
        candles = []

        subscribe_event(bus, EVENT_TRADE, lambda d: trades.append(d))
        subscribe_event(bus, EVENT_CANDLE, lambda d: candles.append(d))

        emit_event(bus, EVENT_TRADE, {"type": "trade"})
        emit_event(bus, EVENT_CANDLE, {"type": "candle"})

        assert len(trades) == 1
        assert len(candles) == 1
        assert trades[0]["type"] == "trade"
        assert candles[0]["type"] == "candle"

    def test_error_in_handler_doesnt_stop_others(self):
        """Error in one handler doesn't affect others."""
        bus = create_event_bus()
        received = []

        def bad_handler(data):
            raise ValueError("Test error")

        def good_handler(data):
            received.append(data)

        subscribe_event(bus, EVENT_TRADE, bad_handler)
        subscribe_event(bus, EVENT_TRADE, good_handler)

        emit_event(bus, EVENT_TRADE, {"price": 100})

        assert len(received) == 1
        assert bus["error_count"] == 1

    def test_event_count(self):
        """Event count increments on emit."""
        bus = create_event_bus()

        emit_event(bus, EVENT_TRADE, {})
        emit_event(bus, EVENT_TRADE, {})
        emit_event(bus, EVENT_CANDLE, {})

        assert bus["event_count"] == 3

    def test_get_event_stats(self):
        """Get event statistics."""
        bus = create_event_bus()

        subscribe_event(bus, EVENT_TRADE, lambda d: None)
        subscribe_event(bus, EVENT_TRADE, lambda d: None)
        subscribe_event(bus, EVENT_CANDLE, lambda d: None)

        emit_event(bus, EVENT_TRADE, {})

        stats = get_event_stats(bus)

        assert stats["event_count"] == 1
        assert stats["subscriber_counts"][EVENT_TRADE] == 2
        assert stats["subscriber_counts"][EVENT_CANDLE] == 1

    def test_clear_all_subscribers(self):
        """Clear all subscribers."""
        bus = create_event_bus()
        received = []

        subscribe_event(bus, EVENT_TRADE, lambda d: received.append(d))
        subscribe_event(bus, EVENT_CANDLE, lambda d: received.append(d))

        clear_subscribers(bus)

        emit_event(bus, EVENT_TRADE, {})
        emit_event(bus, EVENT_CANDLE, {})

        assert len(received) == 0

    def test_clear_specific_event_type(self):
        """Clear subscribers for specific event type."""
        bus = create_event_bus()
        trades = []
        candles = []

        subscribe_event(bus, EVENT_TRADE, lambda d: trades.append(d))
        subscribe_event(bus, EVENT_CANDLE, lambda d: candles.append(d))

        clear_subscribers(bus, EVENT_TRADE)

        emit_event(bus, EVENT_TRADE, {})
        emit_event(bus, EVENT_CANDLE, {})

        assert len(trades) == 0
        assert len(candles) == 1

    def test_emit_no_subscribers(self):
        """Emit event with no subscribers doesn't error."""
        bus = create_event_bus()

        # Should not raise
        emit_event(bus, "unknown_event", {"data": "test"})

        assert bus["event_count"] == 1


class TestAsyncEventBus:
    """Tests for async event bus functions."""

    @pytest.mark.asyncio
    async def test_async_subscriber(self):
        """Async subscriber receives events."""
        from src.data_controller.event_bus import emit_event_async

        bus = create_event_bus()
        received = []

        async def async_handler(data):
            received.append(data)

        subscribe_event_async(bus, EVENT_TRADE, async_handler)
        await emit_event_async(bus, EVENT_TRADE, {"price": 100})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_mixed_sync_async_subscribers(self):
        """Mix of sync and async subscribers."""
        from src.data_controller.event_bus import emit_event_async

        bus = create_event_bus()
        sync_received = []
        async_received = []

        def sync_handler(data):
            sync_received.append(data)

        async def async_handler(data):
            async_received.append(data)

        subscribe_event(bus, EVENT_TRADE, sync_handler)
        subscribe_event_async(bus, EVENT_TRADE, async_handler)

        await emit_event_async(bus, EVENT_TRADE, {"price": 100})

        assert len(sync_received) == 1
        assert len(async_received) == 1

