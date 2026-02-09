"""Simulated broker for backtesting with realistic order execution.

Provides:
- Order submission and tracking
- Realistic fill simulation based on market data
- Configurable slippage and commission models
- Position and cash management
- Order status events
"""

import random
import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import cast

from src.types import (
    CandleData,
    FillData,
    OrderData,
    OrderStatus,
    PositionData,
    Side,
    TickData,
    TimeInForce,
)


def apply_slippage_fixed_bps(
    order: OrderData,
    base_price: Decimal,
    slippage_bps: Decimal,
    rng: random.Random,
) -> Decimal:
    """Apply fixed basis point slippage.

    Args:
        order: Order being filled.
        base_price: Base fill price.
        slippage_bps: Slippage in basis points (100 bps = 1%).
        rng: Random number generator for determinism.

    Returns:
        Price with slippage applied.
    """
    # Slippage hurts: adds to buys, subtracts from sells
    slippage_factor = slippage_bps / Decimal("10000")
    slippage_amount = base_price * slippage_factor

    if order["side"] == "buy":
        return base_price + slippage_amount
    return base_price - slippage_amount


def apply_slippage_percentage(
    order: OrderData,
    base_price: Decimal,
    slippage_pct: Decimal,
    rng: random.Random,
) -> Decimal:
    """Apply percentage-based slippage.

    Args:
        order: Order being filled.
        base_price: Base fill price.
        slippage_pct: Slippage percentage (0.01 = 1%).
        rng: Random number generator.

    Returns:
        Price with slippage applied.
    """
    slippage_amount = base_price * slippage_pct

    if order["side"] == "buy":
        return base_price + slippage_amount
    return base_price - slippage_amount


def compute_commission_percentage(
    order: OrderData,
    fill_value: Decimal,
    commission_rate: Decimal,
) -> Decimal:
    """Compute percentage-based commission.

    Args:
        order: Order being filled.
        fill_value: Notional value of fill.
        commission_rate: Commission rate (0.001 = 0.1%).

    Returns:
        Commission amount.
    """
    return fill_value * commission_rate


def compute_commission_fixed(
    order: OrderData,
    fill_value: Decimal,
    fixed_amount: Decimal,
) -> Decimal:
    """Compute fixed commission per trade.

    Args:
        order: Order being filled.
        fill_value: Notional value of fill.
        fixed_amount: Fixed commission amount.

    Returns:
        Commission amount.
    """
    return fixed_amount


class SimulatedBroker:
    """Simulated broker for backtesting.

    Handles:
    - Order placement and validation
    - Fill simulation based on bar/tick data
    - Position tracking
    - Cash and equity management
    - Slippage and commission application

    Input: Orders from strategy.
    Output: Fill events, position updates.
    Side effects: Updates internal state (positions, cash, orders).
    """

    def __init__(
        self,
        initial_cash: Decimal,
        slippage_fn: Callable[[OrderData, Decimal, random.Random], Decimal] | None = None,
        commission_fn: Callable[[OrderData, Decimal], Decimal] | None = None,
        random_seed: int = 42,
        max_leverage: Decimal = Decimal("1.0"),
        allow_short: bool = False,
    ):
        """Initialize simulated broker.

        Args:
            initial_cash: Starting cash balance.
            slippage_fn: Function to compute slippage.
            commission_fn: Function to compute commissions.
            random_seed: Random seed for deterministic slippage.
            max_leverage: Maximum leverage allowed.
            allow_short: Whether to allow short positions.
        """
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions: dict[str, PositionData] = {}
        self.open_orders: dict[str, OrderData] = {}
        self.filled_orders: list[OrderData] = []
        self.fills: list[FillData] = []
        self.rng = random.Random(random_seed)

        self.slippage_fn = slippage_fn or (
            lambda o, p, r: apply_slippage_fixed_bps(o, p, Decimal("5"), r)
        )
        self.commission_fn = commission_fn or (
            lambda o, v: compute_commission_percentage(o, v, Decimal("0.001"))
        )

        self.max_leverage = max_leverage
        self.allow_short = allow_short

        # Callbacks
        self.on_fill_callback: Callable[[FillData], None] | None = None
        self.on_order_update_callback: Callable[[OrderData], None] | None = None

    def set_on_fill(self, callback: Callable[[FillData], None]) -> None:
        """Set callback for fill events.

        Args:
            callback: Function to call on each fill.
        """
        self.on_fill_callback = callback

    def set_on_order_update(self, callback: Callable[[OrderData], None]) -> None:
        """Set callback for order updates.

        Args:
            callback: Function to call on order status change.
        """
        self.on_order_update_callback = callback

    def market_order(
        self,
        symbol: str,
        side: Side,
        quantity: Decimal,
        timestamp_ms: int,
    ) -> str:
        """Submit a market order.

        Args:
            symbol: Trading symbol.
            side: "buy" or "sell".
            quantity: Order quantity.
            timestamp_ms: Order submission time.

        Returns:
            Order ID.

        Side effects: Creates order, may trigger immediate fill.
        """
        order_id = str(uuid.uuid4())

        order: OrderData = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "status": "new",
            "quantity": quantity,
            "filled_quantity": Decimal("0"),
            "limit_price": None,
            "stop_price": None,
            "time_in_force": "IOC",
            "submit_time_ms": timestamp_ms,
            "update_time_ms": timestamp_ms,
        }

        self.open_orders[order_id] = order
        self._emit_order_update(order)

        return order_id

    def limit_order(
        self,
        symbol: str,
        side: Side,
        quantity: Decimal,
        limit_price: Decimal,
        timestamp_ms: int,
        time_in_force: TimeInForce = "GTC",
    ) -> str:
        """Submit a limit order.

        Args:
            symbol: Trading symbol.
            side: "buy" or "sell".
            quantity: Order quantity.
            limit_price: Limit price.
            timestamp_ms: Order submission time.
            time_in_force: Time in force policy.

        Returns:
            Order ID.

        Side effects: Creates order, queued for matching.
        """
        order_id = str(uuid.uuid4())

        order: OrderData = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "order_type": "limit",
            "status": "new",
            "quantity": quantity,
            "filled_quantity": Decimal("0"),
            "limit_price": limit_price,
            "stop_price": None,
            "time_in_force": time_in_force,
            "submit_time_ms": timestamp_ms,
            "update_time_ms": timestamp_ms,
        }

        self.open_orders[order_id] = order
        self._emit_order_update(order)

        return order_id

    def cancel_order(self, order_id: str, timestamp_ms: int) -> bool:
        """Cancel an open order.

        Args:
            order_id: ID of order to cancel.
            timestamp_ms: Cancellation time.

        Returns:
            True if canceled, False if not found or already filled.

        Side effects: Updates order status, removes from open orders.
        """
        if order_id not in self.open_orders:
            return False

        order = self.open_orders[order_id]

        if order["status"] in ("filled", "canceled", "rejected"):
            return False

        order["status"] = cast(OrderStatus, "canceled")
        order["update_time_ms"] = timestamp_ms
        self._emit_order_update(order)

        del self.open_orders[order_id]
        return True

    def process_bar(self, bar: CandleData, timestamp_ms: int) -> None:
        """Process bar and attempt to fill orders.

        Uses OHLC-based matching:
        - Market orders fill at next bar open
        - Limit buys fill if low <= limit
        - Limit sells fill if high >= limit

        Args:
            bar: OHLCV candle data.
            timestamp_ms: Current simulation time.

        Side effects: May fill orders, update positions, emit fills.
        """
        symbol = bar["symbol"]
        open_price = bar["open"]
        high = bar["high"]
        low = bar["low"]

        # Process open orders for this symbol
        for order_id in list(self.open_orders.keys()):
            order = self.open_orders[order_id]

            if order["symbol"] != symbol:
                continue

            if order["order_type"] == "market":
                # Fill market orders at open
                fill_price = open_price
                self._execute_fill(order, fill_price, order["quantity"], timestamp_ms)

            if order["order_type"] == "limit":
                limit_price = order["limit_price"]
                if limit_price is None:
                    continue

                # Check if limit price was touched
                can_fill = False
                fill_price = limit_price  # Default to limit price
                if order["side"] == "buy" and low <= limit_price:
                    can_fill = True
                    fill_price = min(limit_price, open_price)
                elif order["side"] == "sell" and high >= limit_price:
                    can_fill = True
                    fill_price = max(limit_price, open_price)

                if can_fill:
                    self._execute_fill(order, fill_price, order["quantity"], timestamp_ms)

    def process_tick(self, tick: TickData, timestamp_ms: int) -> None:
        """Process tick and attempt to fill orders.

        Uses bid/ask for more realistic fills:
        - Market buys fill at ask
        - Market sells fill at bid
        - Limit orders check against bid/ask

        Args:
            tick: Tick data with bid/ask.
            timestamp_ms: Current simulation time.

        Side effects: May fill orders, update positions.
        """
        symbol = tick["symbol"]
        bid = tick["bid_price"]
        ask = tick["ask_price"]

        for order_id in list(self.open_orders.keys()):
            order = self.open_orders[order_id]

            if order["symbol"] != symbol:
                continue

            if order["order_type"] == "market":
                fill_price = ask if order["side"] == "buy" else bid
                self._execute_fill(order, fill_price, order["quantity"], timestamp_ms)

            elif order["order_type"] == "limit":
                limit_price = order["limit_price"]
                if limit_price is None:
                    continue

                can_fill = False
                fill_price = limit_price  # Default to limit price
                if order["side"] == "buy" and ask <= limit_price:
                    can_fill = True
                    fill_price = ask
                elif order["side"] == "sell" and bid >= limit_price:
                    can_fill = True
                    fill_price = bid

                if can_fill:
                    self._execute_fill(order, fill_price, order["quantity"], timestamp_ms)

    def _execute_fill(
        self,
        order: OrderData,
        base_price: Decimal,
        quantity: Decimal,
        timestamp_ms: int,
    ) -> None:
        """Execute an order fill with slippage and commissions.

        Args:
            order: Order being filled.
            base_price: Base fill price before slippage.
            quantity: Quantity to fill.
            timestamp_ms: Fill timestamp.

        Side effects: Updates order, positions, cash, emits fill event.
        """
        # Apply slippage
        fill_price = self.slippage_fn(order, base_price, self.rng)
        slippage = abs(fill_price - base_price)

        # Compute value and commission
        fill_value = fill_price * quantity
        commission = self.commission_fn(order, fill_value)

        # Check if we have enough cash for buys
        if order["side"] == "buy":
            total_cost = fill_value + commission
            if total_cost > self.cash:
                # Reject order - insufficient funds
                order["status"] = cast(OrderStatus, "rejected")
                order["update_time_ms"] = timestamp_ms
                self._emit_order_update(order)
                del self.open_orders[order["order_id"]]
                return

        # Update order status
        order["filled_quantity"] += quantity
        if order["filled_quantity"] >= order["quantity"]:
            order["status"] = cast(OrderStatus, "filled")
        else:
            order["status"] = cast(OrderStatus, "partially_filled")
        order["update_time_ms"] = timestamp_ms

        # Compute realized PnL for sells
        realized_pnl: Decimal | None = None
        if order["side"] == "sell":
            position = self.positions.get(order["symbol"])
            if position and position["avg_entry_price"] > 0:
                realized_pnl = (fill_price - position["avg_entry_price"]) * quantity

        # Update position
        self._update_position(
            order["symbol"],
            order["side"],
            quantity,
            fill_price,
            timestamp_ms,
        )

        # Update cash
        if order["side"] == "buy":
            self.cash -= fill_value + commission
        else:
            self.cash += fill_value - commission

        # Create fill event
        fill_id = str(uuid.uuid4())
        fill: FillData = {
            "fill_id": fill_id,
            "order_id": order["order_id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "timestamp_ms": timestamp_ms,
            "price": fill_price,
            "quantity": quantity,
            "fee": commission,
            "slippage": slippage,
            "realized_pnl": realized_pnl,
        }

        self.fills.append(fill)
        self._emit_order_update(order)
        self._emit_fill(fill)

        # Remove from open orders if fully filled
        if order["status"] == "filled":
            self.filled_orders.append(order)
            del self.open_orders[order["order_id"]]

    def _update_position(
        self,
        symbol: str,
        side: Side,
        quantity: Decimal,
        price: Decimal,
        timestamp_ms: int,
    ) -> None:
        """Update position for a fill.

        Args:
            symbol: Symbol.
            side: Buy or sell.
            quantity: Fill quantity.
            price: Fill price.
            timestamp_ms: Timestamp.

        Side effects: Updates or creates position.
        """
        if symbol not in self.positions:
            self.positions[symbol] = {
                "symbol": symbol,
                "quantity": Decimal("0"),
                "avg_entry_price": Decimal("0"),
                "market_price": price,
                "market_value": Decimal("0"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            }

        position = self.positions[symbol]
        old_quantity = position["quantity"]

        if side == "buy":
            new_quantity = old_quantity + quantity
            if old_quantity == 0:
                position["avg_entry_price"] = price
            else:
                total_cost = (old_quantity * position["avg_entry_price"]) + (quantity * price)
                position["avg_entry_price"] = total_cost / new_quantity
            position["quantity"] = new_quantity
        else:
            new_quantity = old_quantity - quantity
            position["quantity"] = new_quantity

            # Compute realized PnL on sells
            if old_quantity > 0:
                realized_pnl = (price - position["avg_entry_price"]) * quantity
                position["realized_pnl"] += realized_pnl

        position["market_price"] = price
        position["market_value"] = position["quantity"] * price

        if position["quantity"] == 0:
            position["avg_entry_price"] = Decimal("0")

    def get_position(self, symbol: str) -> PositionData | None:
        """Get current position for a symbol.

        Args:
            symbol: Symbol to query.

        Returns:
            Position data or None if no position.
        """
        return self.positions.get(symbol)

    def get_all_positions(self) -> dict[str, PositionData]:
        """Get all positions.

        Returns:
            Dictionary mapping symbol to position.
        """
        return self.positions.copy()

    def get_equity(self, market_prices: dict[str, Decimal] | None = None) -> Decimal:
        """Compute current equity (cash + position values).

        Args:
            market_prices: Optional dict of symbol -> current price.

        Returns:
            Total equity.
        """
        equity = self.cash

        for symbol, position in self.positions.items():
            if market_prices and symbol in market_prices:
                price = market_prices[symbol]
            else:
                price = position["market_price"]

            equity += position["quantity"] * price

        return equity

    def _emit_fill(self, fill: FillData) -> None:
        """Emit fill event to callback.

        Args:
            fill: Fill event.
        """
        if self.on_fill_callback:
            self.on_fill_callback(fill)

    def _emit_order_update(self, order: OrderData) -> None:
        """Emit order update event to callback.

        Args:
            order: Order with updated status.
        """
        if self.on_order_update_callback:
            self.on_order_update_callback(order)
