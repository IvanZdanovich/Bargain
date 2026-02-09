"""Data Controller subsystem for market data ingestion and normalization.

This module provides:
- Unified market data ingestion from multiple providers
- WebSocket streaming and REST historical fetch
- Data normalization and validation
- Event bus for downstream component integration
- Storage integration for persistence
- Replay mode for backtesting

Example usage:
    from src.data_controller import (
        create_controller,
        start_controller,
        stop_controller,
        subscribe,
    )
    from src.types import ProviderConfigData, SubscriptionConfigData, HandlersData

    config = ProviderConfigData(
        name="binance",
        api_key=None,
        api_secret=None,
        testnet=False,
        rate_limit_per_second=10,
        reconnect_attempts=5,
        reconnect_delay_ms=1000,
    )

    handlers = HandlersData(on_trade=lambda t: print(t))
    controller = create_controller([config], handlers)
    await start_controller(controller)
    await subscribe(controller, "binance", [
        SubscriptionConfigData(symbol="BTC/USDT", data_types=["trade"], interval=None)
    ])
"""

from src.data_controller.controller import (
                                            create_controller,
                                            create_strategy_feed,
                                            fetch_historical,
                                            fetch_orderbook_snapshot,
                                            get_all_provider_health,
                                            get_provider_health,
                                            get_provider_status,
                                            start_controller,
                                            stop_controller,
                                            subscribe,
                                            unsubscribe,
)
from src.data_controller.event_bus import (
                                            EVENT_CANDLE,
                                            EVENT_ERROR,
                                            EVENT_ORDERBOOK_DELTA,
                                            EVENT_ORDERBOOK_SNAPSHOT,
                                            EVENT_STATUS_CHANGE,
                                            EVENT_TICK,
                                            EVENT_TRADE,
                                            clear_subscribers,
                                            create_event_bus,
                                            emit_event,
                                            emit_event_async,
                                            get_event_stats,
                                            subscribe_event,
                                            subscribe_event_async,
)
from src.data_controller.replay import (
                                            create_replay_recorder,
                                            record_event,
                                            replay_from_file,
                                            replay_from_records,
                                            replay_iterator,
                                            save_recording,
                                            start_recording,
                                            stop_recording,
)
from src.data_controller.storage import (
                                            buffer_record,
                                            create_storage_buffer,
                                            flush_buffer,
                                            get_storage_stats,
                                            pipe_to_storage,
                                            start_storage_buffer,
                                            stop_storage_buffer,
)

__all__ = [
    # Controller
    "create_controller",
    "start_controller",
    "stop_controller",
    "subscribe",
    "unsubscribe",
    "fetch_historical",
    "fetch_orderbook_snapshot",
    "get_provider_status",
    "get_provider_health",
    "get_all_provider_health",
    "create_strategy_feed",
    # Event Bus
    "create_event_bus",
    "emit_event",
    "emit_event_async",
    "subscribe_event",
    "subscribe_event_async",
    "get_event_stats",
    "clear_subscribers",
    "EVENT_TRADE",
    "EVENT_CANDLE",
    "EVENT_TICK",
    "EVENT_ORDERBOOK_SNAPSHOT",
    "EVENT_ORDERBOOK_DELTA",
    "EVENT_ERROR",
    "EVENT_STATUS_CHANGE",
    # Replay
    "replay_from_file",
    "replay_from_records",
    "replay_iterator",
    "create_replay_recorder",
    "start_recording",
    "stop_recording",
    "record_event",
    "save_recording",
    # Storage
    "create_storage_buffer",
    "start_storage_buffer",
    "stop_storage_buffer",
    "buffer_record",
    "flush_buffer",
    "get_storage_stats",
    "pipe_to_storage",
]
