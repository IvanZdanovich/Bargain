"""Binance data provider implementation.

Provides WebSocket streaming and REST historical fetch
for Binance Spot and Futures markets.

Requires aiohttp: pip install aiohttp
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore

import contextlib

from src.config import (get_binance_config, get_provider_defaults,
                        get_schema_version)
from src.data_controller.normalization import (denormalize_symbol,
                                               normalize_symbol, to_decimal)
from src.data_controller.reliability import (acquire_rate_limit,
                                             create_rate_limiter,
                                             with_exponential_backoff)
from src.types import (CandleData, HistoricalRequestData, OrderBookLevelData,
                       OrderBookSnapshotData, ProviderConfigData, Side,
                       SubscriptionConfigData, TickData, TradeData)

logger = logging.getLogger(__name__)


def create_binance_provider(config: ProviderConfigData) -> dict[str, Any]:
    """
    Create Binance provider state container.

    Args:
        config: Provider configuration.

    Returns:
        Mutable state dict for the provider instance.
    """
    defaults = get_provider_defaults()
    return {
        "config": config,
        "name": config["name"],
        "status": "disconnected",
        "ws_session": None,
        "http_session": None,
        "subscriptions": [],
        "last_sequences": {},
        "reconnect_count": 0,
        "message_count": 0,
        "error_count": 0,
        "last_message_ms": None,
        "rate_limiter": create_rate_limiter(
            config.get("rate_limit_per_second", defaults["rate_limit_per_second"])
        ),
        "listen_key": None,
        "ping_task": None,
    }


# === Pure Parsing Functions ===


def parse_binance_trade(raw: dict[str, Any], provider_name: str) -> TradeData:
    """
    Parse Binance trade message to normalized format.

    Args:
        raw: Raw WebSocket message payload.
        provider_name: Provider identifier.

    Returns:
        Normalized TradeData.

    Note: Pure function, no side effects.
    """
    # Handle both stream format and REST format
    symbol = raw.get("s", raw.get("symbol", ""))
    trade_id = raw.get("t", raw.get("id", 0))
    timestamp = raw.get("T", raw.get("time", 0))
    price = raw.get("p", raw.get("price", "0"))
    quantity = raw.get("q", raw.get("qty", "0"))

    # m=True means buyer is maker, so trade was a sell
    is_buyer_maker = raw.get("m", raw.get("isBuyerMaker", False))
    side: Side = "sell" if is_buyer_maker else "buy"

    return TradeData(
        schema_version=get_schema_version(),
        provider=provider_name,
        symbol=normalize_symbol(symbol, "binance"),
        trade_id=str(trade_id),
        timestamp_ms=timestamp,
        price=to_decimal(price),
        quantity=to_decimal(quantity),
        side=side,
        raw=raw,
    )


def parse_binance_candle(raw: dict[str, Any], provider_name: str) -> CandleData:
    """
    Parse Binance kline message to normalized format.

    Args:
        raw: Raw kline payload (may have nested 'k' key for streams).
        provider_name: Provider identifier.

    Returns:
        Normalized CandleData.
    """
    # Handle both stream format (nested under 'k') and REST format
    k = raw.get("k", raw)

    symbol = k.get("s", k.get("symbol", ""))
    interval = k.get("i", k.get("interval", "1m"))

    # Stream format uses 't', REST format uses list indices or different keys
    open_time = k.get("t", k.get("openTime", k[0] if isinstance(k, list) else 0))
    close_time = k.get("T", k.get("closeTime", k[6] if isinstance(k, list) else 0))

    return CandleData(
        schema_version=get_schema_version(),
        provider=provider_name,
        symbol=normalize_symbol(symbol, "binance"),
        interval=interval,
        open_time_ms=open_time,
        close_time_ms=close_time,
        open=to_decimal(k.get("o", k.get("open", k[1] if isinstance(k, list) else "0"))),
        high=to_decimal(k.get("h", k.get("high", k[2] if isinstance(k, list) else "0"))),
        low=to_decimal(k.get("l", k.get("low", k[3] if isinstance(k, list) else "0"))),
        close=to_decimal(k.get("c", k.get("close", k[4] if isinstance(k, list) else "0"))),
        volume=to_decimal(k.get("v", k.get("volume", k[5] if isinstance(k, list) else "0"))),
        is_closed=k.get("x", True),
        raw=raw,
    )


def parse_binance_candle_rest(
    raw: list, symbol: str, interval: str, provider_name: str
) -> CandleData:
    """
    Parse Binance REST kline response to normalized format.

    Args:
        raw: Raw kline list [open_time, open, high, low, close, volume, close_time, ...].
        symbol: Trading pair symbol.
        interval: Candle interval.
        provider_name: Provider identifier.

    Returns:
        Normalized CandleData.
    """
    return CandleData(
        schema_version=get_schema_version(),
        provider=provider_name,
        symbol=normalize_symbol(symbol, "binance"),
        interval=interval,
        open_time_ms=raw[0],
        close_time_ms=raw[6],
        open=to_decimal(raw[1]),
        high=to_decimal(raw[2]),
        low=to_decimal(raw[3]),
        close=to_decimal(raw[4]),
        volume=to_decimal(raw[5]),
        is_closed=True,
        raw={"kline": raw},  # Wrap list in dict for type consistency
    )


def parse_binance_orderbook_snapshot(
    raw: dict[str, Any],
    symbol: str,
    provider_name: str,
) -> OrderBookSnapshotData:
    """
    Parse Binance depth snapshot to normalized format.

    Args:
        raw: REST API depth response.
        symbol: Trading pair symbol.
        provider_name: Provider identifier.

    Returns:
        Normalized OrderBookSnapshotData.
    """

    def parse_levels(levels: list) -> list[OrderBookLevelData]:
        return [OrderBookLevelData(price=to_decimal(p), quantity=to_decimal(q)) for p, q in levels]

    return OrderBookSnapshotData(
        schema_version=get_schema_version(),
        provider=provider_name,
        symbol=normalize_symbol(symbol, "binance"),
        timestamp_ms=raw.get("E", 0),
        sequence=raw.get("lastUpdateId", 0),
        bids=parse_levels(raw.get("bids", [])),
        asks=parse_levels(raw.get("asks", [])),
        raw=raw,
    )


def parse_binance_ticker(raw: dict[str, Any], provider_name: str) -> TickData:
    """
    Parse Binance 24hr ticker to unified tick format.

    Args:
        raw: Ticker data from REST or stream.
        provider_name: Provider identifier.

    Returns:
        Normalized TickData.
    """
    symbol = raw.get("s", raw.get("symbol", ""))

    return TickData(
        schema_version=get_schema_version(),
        provider=provider_name,
        symbol=normalize_symbol(symbol, "binance"),
        timestamp_ms=raw.get("E", raw.get("closeTime", 0)),
        bid_price=to_decimal(raw.get("b", raw.get("bidPrice", "0"))),
        bid_quantity=to_decimal(raw.get("B", raw.get("bidQty", "0"))),
        ask_price=to_decimal(raw.get("a", raw.get("askPrice", "0"))),
        ask_quantity=to_decimal(raw.get("A", raw.get("askQty", "0"))),
        last_price=to_decimal(raw.get("c", raw.get("lastPrice", "0"))),
        last_quantity=to_decimal(raw.get("Q", raw.get("lastQty", "0"))),
        raw=raw,
    )


# === Connection Functions ===


def _get_ws_url(config: ProviderConfigData) -> str:
    """Get WebSocket URL based on config."""
    binance_cfg = get_binance_config()
    if config.get("testnet", False):
        return binance_cfg["ws_url_testnet"]
    return binance_cfg["ws_url"]


def _get_rest_url(config: ProviderConfigData) -> str:
    """Get REST URL based on config."""
    binance_cfg = get_binance_config()
    if config.get("testnet", False):
        return binance_cfg["rest_url_testnet"]
    return binance_cfg["rest_url"]


async def connect_binance(state: dict[str, Any]) -> None:
    """
    Establish Binance WebSocket and HTTP connections.

    Args:
        state: Provider state container.

    Side effects: Creates aiohttp sessions, updates state.
    Raises: ConnectionError on failure.
    """
    config = state["config"]
    binance_cfg = get_binance_config()
    state["status"] = "connecting"

    try:
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=binance_cfg["http_timeout_s"])
        state["http_session"] = aiohttp.ClientSession(timeout=timeout)

        # Create WebSocket connection
        ws_url = _get_ws_url(config)
        state["ws_session"] = await state["http_session"].ws_connect(
            ws_url,
            heartbeat=binance_cfg["ws_heartbeat_s"],
            receive_timeout=binance_cfg["ws_receive_timeout_s"],
        )

        state["status"] = "connected"
        state["reconnect_count"] = 0

        # Start ping task to keep connection alive
        state["ping_task"] = asyncio.create_task(_ping_loop(state))

        logger.info(f"Binance provider connected to {ws_url}")

    except Exception as e:
        state["status"] = "error"
        state["error_count"] += 1
        logger.error(f"Binance connection failed: {e}")
        raise ConnectionError(f"Failed to connect to Binance: {e}") from e


async def disconnect_binance(state: dict[str, Any]) -> None:
    """
    Close Binance connections gracefully.

    Args:
        state: Provider state container.

    Side effects: Closes sessions, updates state.
    """
    # Cancel ping task
    if state.get("ping_task"):
        state["ping_task"].cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await state["ping_task"]
        state["ping_task"] = None

    # Close WebSocket
    if state.get("ws_session"):
        await state["ws_session"].close()
        state["ws_session"] = None

    # Close HTTP session
    if state.get("http_session"):
        await state["http_session"].close()
        state["http_session"] = None

    state["status"] = "disconnected"
    state["subscriptions"].clear()
    logger.info("Binance provider disconnected")


async def reconnect_binance(state: dict[str, Any]) -> None:
    """
    Reconnect to Binance with backoff.

    Args:
        state: Provider state container.

    Side effects: Disconnects, reconnects, resubscribes.
    """
    config = state["config"]
    old_subscriptions = state["subscriptions"].copy()

    await disconnect_binance(state)
    state["reconnect_count"] += 1

    async def do_reconnect():
        await connect_binance(state)
        if old_subscriptions:
            await subscribe_binance(state, old_subscriptions)

    await with_exponential_backoff(
        operation=do_reconnect,
        max_attempts=config.get("reconnect_attempts", 5),
        base_delay_ms=config.get("reconnect_delay_ms", 1000),
        operation_name="Binance reconnect",
    )


async def _ping_loop(state: dict[str, Any]) -> None:
    """
    Send periodic pings to keep WebSocket alive.

    Args:
        state: Provider state.
    """
    binance_cfg = get_binance_config()
    ping_interval = binance_cfg["ping_interval_s"]

    while state["status"] == "connected":
        try:
            await asyncio.sleep(ping_interval)
            if state["ws_session"] and not state["ws_session"].closed:
                await state["ws_session"].ping()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Ping failed: {e}")


# === Subscription Functions ===


async def subscribe_binance(
    state: dict[str, Any],
    subscriptions: Sequence[SubscriptionConfigData],
) -> None:
    """
    Subscribe to Binance streams.

    Args:
        state: Provider state container.
        subscriptions: List of subscription configs.

    Side effects: Sends subscription message via WebSocket.
    """
    streams = []

    for sub in subscriptions:
        symbol_lower = denormalize_symbol(sub["symbol"], "binance").lower()

        for data_type in sub["data_types"]:
            if data_type == "trade":
                streams.append(f"{symbol_lower}@trade")
            elif data_type == "candle":
                interval = sub.get("interval") or "1m"
                streams.append(f"{symbol_lower}@kline_{interval}")
            elif data_type == "orderbook_delta":
                streams.append(f"{symbol_lower}@depth@100ms")
            elif data_type == "orderbook_snapshot":
                streams.append(f"{symbol_lower}@depth20@1000ms")
            elif data_type == "tick":
                streams.append(f"{symbol_lower}@bookTicker")

    if streams and state.get("ws_session"):
        msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1,
        }
        await state["ws_session"].send_json(msg)
        state["subscriptions"].extend(subscriptions)
        logger.info(f"Subscribed to Binance streams: {streams}")


async def unsubscribe_binance(
    state: dict[str, Any],
    subscriptions: Sequence[SubscriptionConfigData],
) -> None:
    """
    Unsubscribe from Binance streams.

    Args:
        state: Provider state container.
        subscriptions: List of subscriptions to cancel.

    Side effects: Sends unsubscribe message via WebSocket.
    """
    streams = []

    for sub in subscriptions:
        symbol_lower = denormalize_symbol(sub["symbol"], "binance").lower()

        for data_type in sub["data_types"]:
            if data_type == "trade":
                streams.append(f"{symbol_lower}@trade")
            elif data_type == "candle":
                interval = sub.get("interval") or "1m"
                streams.append(f"{symbol_lower}@kline_{interval}")

    if streams and state.get("ws_session"):
        msg = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": 2,
        }
        await state["ws_session"].send_json(msg)

        # Remove from tracked subscriptions
        for sub in subscriptions:
            if sub in state["subscriptions"]:
                state["subscriptions"].remove(sub)

        logger.info(f"Unsubscribed from Binance streams: {streams}")


# === Historical Data Functions ===


async def fetch_binance_historical_candles(
    state: dict[str, Any],
    request: HistoricalRequestData,
) -> AsyncIterator[CandleData]:
    """
    Fetch historical candles from Binance REST API.

    Args:
        state: Provider state container.
        request: Historical request parameters.

    Yields:
        Normalized CandleData records.

    Side effects: HTTP requests to Binance API.
    """
    session = state["http_session"]
    if not session:
        raise RuntimeError("HTTP session not initialized")

    config = state["config"]
    symbol = denormalize_symbol(request["symbol"], "binance")
    interval = request.get("interval") or "1m"
    limit = min(request.get("limit") or 1000, 1000)
    provider_name = state["name"]

    start_time = request["start_time_ms"]
    end_time = request["end_time_ms"]
    base_url = _get_rest_url(config)

    while start_time < end_time:
        await acquire_rate_limit(state["rate_limiter"])

        url = f"{base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
        }

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 429:
                    state["status"] = "rate_limited"
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    state["status"] = "connected"
                    continue

                if resp.status == 418:
                    # IP banned
                    state["status"] = "error"
                    raise RuntimeError("IP banned by Binance")

                resp.raise_for_status()
                data = await resp.json()

        except aiohttp.ClientError as e:
            state["error_count"] += 1
            logger.error(f"Failed to fetch candles: {e}")
            raise

        if not data:
            break

        for kline in data:
            candle = parse_binance_candle_rest(kline, symbol, interval, provider_name)
            yield candle

        # Move to next batch
        last_close_time = data[-1][6]
        start_time = last_close_time + 1

        # Small delay for rate limiting
        await asyncio.sleep(0.1)


async def fetch_binance_historical_trades(
    state: dict[str, Any],
    request: HistoricalRequestData,
) -> AsyncIterator[TradeData]:
    """
    Fetch historical trades from Binance REST API.

    Args:
        state: Provider state container.
        request: Historical request parameters.

    Yields:
        Normalized TradeData records.

    Side effects: HTTP requests to Binance API.
    """
    session = state["http_session"]
    if not session:
        raise RuntimeError("HTTP session not initialized")

    config = state["config"]
    symbol = denormalize_symbol(request["symbol"], "binance")
    limit = min(request.get("limit") or 1000, 1000)
    provider_name = state["name"]

    base_url = _get_rest_url(config)
    from_id: int | None = None

    # Note: Binance aggTrades endpoint supports time range
    start_time = request["start_time_ms"]
    end_time = request["end_time_ms"]

    while True:
        await acquire_rate_limit(state["rate_limiter"])

        url = f"{base_url}/api/v3/aggTrades"
        params: dict[str, Any] = {
            "symbol": symbol,
            "limit": limit,
        }

        if from_id is not None:
            params["fromId"] = from_id
        else:
            params["startTime"] = start_time
            params["endTime"] = end_time

        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 429:
                    state["status"] = "rate_limited"
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    state["status"] = "connected"
                    continue

                resp.raise_for_status()
                data = await resp.json()

        except aiohttp.ClientError as e:
            state["error_count"] += 1
            logger.error(f"Failed to fetch trades: {e}")
            raise

        if not data:
            break

        for raw_trade in data:
            # Check time bounds
            trade_time = raw_trade.get("T", 0)
            if trade_time > end_time:
                return

            trade = TradeData(
                schema_version=get_schema_version(),
                provider=provider_name,
                symbol=normalize_symbol(symbol, "binance"),
                trade_id=str(raw_trade.get("a", 0)),
                timestamp_ms=trade_time,
                price=to_decimal(raw_trade.get("p", "0")),
                quantity=to_decimal(raw_trade.get("q", "0")),
                side="sell" if raw_trade.get("m", False) else "buy",
                raw=raw_trade,
            )
            yield trade

        # Prepare for next batch
        if len(data) < limit:
            break

        from_id = data[-1]["a"] + 1
        await asyncio.sleep(0.1)


async def fetch_binance_orderbook_snapshot(
    state: dict[str, Any],
    symbol: str,
    limit: int = 100,
) -> OrderBookSnapshotData:
    """
    Fetch order book snapshot from Binance REST API.

    Args:
        state: Provider state container.
        symbol: Trading pair symbol.
        limit: Number of levels (5, 10, 20, 50, 100, 500, 1000).

    Returns:
        Normalized OrderBookSnapshotData.
    """
    session = state["http_session"]
    if not session:
        raise RuntimeError("HTTP session not initialized")

    config = state["config"]
    binance_symbol = denormalize_symbol(symbol, "binance")
    base_url = _get_rest_url(config)

    await acquire_rate_limit(state["rate_limiter"])

    url = f"{base_url}/api/v3/depth"
    params = {"symbol": binance_symbol, "limit": limit}

    async with session.get(url, params=params) as resp:
        resp.raise_for_status()
        data = await resp.json()

    return parse_binance_orderbook_snapshot(data, binance_symbol, state["name"])


# === Message Processing ===


async def process_binance_message(
    state: dict[str, Any],
    msg: aiohttp.WSMessage,
) -> dict[str, Any] | None:
    """
    Process a single WebSocket message.

    Args:
        state: Provider state.
        msg: WebSocket message.

    Returns:
        Parsed event dict with 'type' and 'data' keys, or None.
    """
    import time

    if msg.type == aiohttp.WSMsgType.TEXT:
        state["message_count"] += 1
        state["last_message_ms"] = int(time.time() * 1000)

        try:
            data = msg.json()
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None

        # Skip subscription confirmations
        if "result" in data or "id" in data:
            return None

        event_type = data.get("e")
        provider_name = state["name"]

        if event_type == "trade":
            return {
                "type": "trade",
                "data": parse_binance_trade(data, provider_name),
            }

        if event_type == "kline":
            return {
                "type": "candle",
                "data": parse_binance_candle(data, provider_name),
            }

        if event_type == "depthUpdate":
            # Order book delta - needs special handling
            return {
                "type": "orderbook_delta",
                "data": data,
                "provider": provider_name,
            }

        if event_type == "bookTicker":
            return {
                "type": "tick",
                "data": parse_binance_ticker(data, provider_name),
            }

    elif msg.type == aiohttp.WSMsgType.ERROR:
        state["error_count"] += 1
        logger.error(f"WebSocket error: {msg.data}")

    elif msg.type == aiohttp.WSMsgType.CLOSED:
        logger.warning("WebSocket closed")
        state["status"] = "disconnected"

    return None


async def iter_binance_messages(
    state: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """
    Iterate over incoming WebSocket messages.

    Args:
        state: Provider state.

    Yields:
        Parsed event dictionaries.
    """
    ws = state.get("ws_session")
    if not ws:
        return

    try:
        async for msg in ws:
            result = await process_binance_message(state, msg)
            if result:
                yield result
    except asyncio.CancelledError:
        logger.info("Message iteration cancelled")
    except Exception as e:
        state["error_count"] += 1
        logger.error(f"Error iterating messages: {e}")
        raise


def get_binance_health(state: dict[str, Any]) -> dict[str, Any]:
    """
    Get Binance provider health status.

    Args:
        state: Provider state.

    Returns:
        Health status dictionary.
    """
    return {
        "provider": state["name"],
        "status": state["status"],
        "last_message_ms": state.get("last_message_ms"),
        "message_count": state.get("message_count", 0),
        "error_count": state.get("error_count", 0),
        "reconnect_count": state.get("reconnect_count", 0),
        "subscription_count": len(state.get("subscriptions", [])),
    }
