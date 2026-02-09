"""Tests for backtesting broker."""

from decimal import Decimal

from src.backtesting.broker import (
    SimulatedBroker,
    apply_slippage_fixed_bps,
    apply_slippage_percentage,
    compute_commission_fixed,
    compute_commission_percentage,
)
from src.types import CandleData, OrderData


class TestSlippageFunctions:
    """Tests for slippage calculation functions."""

    def test_apply_slippage_fixed_bps_buy(self):
        """Test fixed BPS slippage on buy orders."""
        import random

        order: OrderData = {
            "order_id": "test1",
            "symbol": "BTC/USDT",
            "side": "buy",
            "order_type": "market",
            "status": "new",
            "quantity": Decimal("1.0"),
            "filled_quantity": Decimal("0"),
            "limit_price": None,
            "stop_price": None,
            "time_in_force": "IOC",
            "submit_time_ms": 0,
            "update_time_ms": 0,
        }

        base_price = Decimal("40000")
        slippage_bps = Decimal("10")  # 10 bps = 0.1%
        rng = random.Random(42)

        result = apply_slippage_fixed_bps(order, base_price, slippage_bps, rng)

        # Buy should increase price
        expected = base_price + (base_price * Decimal("10") / Decimal("10000"))
        assert result == expected
        assert result > base_price

    def test_apply_slippage_fixed_bps_sell(self):
        """Test fixed BPS slippage on sell orders."""
        import random

        order: OrderData = {
            "order_id": "test2",
            "symbol": "BTC/USDT",
            "side": "sell",
            "order_type": "market",
            "status": "new",
            "quantity": Decimal("1.0"),
            "filled_quantity": Decimal("0"),
            "limit_price": None,
            "stop_price": None,
            "time_in_force": "IOC",
            "submit_time_ms": 0,
            "update_time_ms": 0,
        }

        base_price = Decimal("40000")
        slippage_bps = Decimal("10")
        rng = random.Random(42)

        result = apply_slippage_fixed_bps(order, base_price, slippage_bps, rng)

        # Sell should decrease price
        expected = base_price - (base_price * Decimal("10") / Decimal("10000"))
        assert result == expected
        assert result < base_price

    def test_apply_slippage_percentage_buy(self):
        """Test percentage slippage on buy orders."""
        import random

        order: OrderData = {
            "order_id": "test3",
            "symbol": "BTC/USDT",
            "side": "buy",
            "order_type": "market",
            "status": "new",
            "quantity": Decimal("1.0"),
            "filled_quantity": Decimal("0"),
            "limit_price": None,
            "stop_price": None,
            "time_in_force": "IOC",
            "submit_time_ms": 0,
            "update_time_ms": 0,
        }

        base_price = Decimal("40000")
        slippage_pct = Decimal("0.001")  # 0.1%
        rng = random.Random(42)

        result = apply_slippage_percentage(order, base_price, slippage_pct, rng)

        expected = base_price + (base_price * slippage_pct)
        assert result == expected


class TestCommissionFunctions:
    """Tests for commission calculation functions."""

    def test_compute_commission_percentage(self):
        """Test percentage-based commission."""
        order: OrderData = {
            "order_id": "test1",
            "symbol": "BTC/USDT",
            "side": "buy",
            "order_type": "market",
            "status": "new",
            "quantity": Decimal("1.0"),
            "filled_quantity": Decimal("0"),
            "limit_price": None,
            "stop_price": None,
            "time_in_force": "IOC",
            "submit_time_ms": 0,
            "update_time_ms": 0,
        }

        fill_value = Decimal("10000")
        commission_rate = Decimal("0.001")  # 0.1%

        result = compute_commission_percentage(order, fill_value, commission_rate)

        expected = fill_value * commission_rate
        assert result == expected
        assert result == Decimal("10")

    def test_compute_commission_fixed(self):
        """Test fixed commission."""
        order: OrderData = {
            "order_id": "test1",
            "symbol": "BTC/USDT",
            "side": "buy",
            "order_type": "market",
            "status": "new",
            "quantity": Decimal("1.0"),
            "filled_quantity": Decimal("0"),
            "limit_price": None,
            "stop_price": None,
            "time_in_force": "IOC",
            "submit_time_ms": 0,
            "update_time_ms": 0,
        }

        fill_value = Decimal("10000")
        fixed_amount = Decimal("5")

        result = compute_commission_fixed(order, fill_value, fixed_amount)

        assert result == fixed_amount


class TestSimulatedBroker:
    """Tests for SimulatedBroker class."""

    def test_initialization(self):
        """Test broker initialization."""
        broker = SimulatedBroker(
            initial_cash=Decimal("10000"),
            random_seed=42,
        )

        assert broker.cash == Decimal("10000")
        assert broker.initial_cash == Decimal("10000")
        assert len(broker.positions) == 0
        assert len(broker.open_orders) == 0
        assert len(broker.filled_orders) == 0

    def test_market_order_submission(self):
        """Test market order submission."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        order_id = broker.market_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            timestamp_ms=1000,
        )

        assert order_id is not None
        assert order_id in broker.open_orders

        order = broker.open_orders[order_id]
        assert order["symbol"] == "BTC/USDT"
        assert order["side"] == "buy"
        assert order["quantity"] == Decimal("0.1")
        assert order["order_type"] == "market"
        assert order["status"] == "new"

    def test_limit_order_submission(self):
        """Test limit order submission."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        order_id = broker.limit_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            limit_price=Decimal("40000"),
            timestamp_ms=1000,
            time_in_force="GTC",
        )

        assert order_id is not None
        assert order_id in broker.open_orders

        order = broker.open_orders[order_id]
        assert order["order_type"] == "limit"
        assert order["limit_price"] == Decimal("40000")
        assert order["time_in_force"] == "GTC"

    def test_cancel_order(self):
        """Test order cancellation."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        order_id = broker.limit_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            limit_price=Decimal("40000"),
            timestamp_ms=1000,
        )

        success = broker.cancel_order(order_id, timestamp_ms=2000)

        assert success is True
        assert order_id not in broker.open_orders

    def test_cancel_nonexistent_order(self):
        """Test canceling non-existent order."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        success = broker.cancel_order("fake_id", timestamp_ms=1000)

        assert success is False

    def test_process_market_order_fill(self):
        """Test market order fill on bar."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        order_id = broker.market_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            timestamp_ms=1000,
        )

        candle: CandleData = {
            "schema_version": "1.0.0",
            "provider": "test",
            "symbol": "BTC/USDT",
            "interval": "1m",
            "open_time_ms": 1000,
            "close_time_ms": 2000,
            "open": Decimal("40000"),
            "high": Decimal("40100"),
            "low": Decimal("39900"),
            "close": Decimal("40050"),
            "volume": Decimal("100"),
            "is_closed": True,
            "raw": {},
        }

        broker.process_bar(candle, candle["open_time_ms"])

        # Order should be filled
        assert order_id not in broker.open_orders
        assert len(broker.filled_orders) == 1
        assert len(broker.fills) == 1

        # Position should exist
        position = broker.get_position("BTC/USDT")
        assert position is not None
        assert position["quantity"] == Decimal("0.1")

        # Cash should be reduced
        assert broker.cash < Decimal("10000")

    def test_position_tracking_buy(self):
        """Test position tracking on buy."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        broker._update_position(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("40000"),
            timestamp_ms=1000,
        )

        position = broker.get_position("BTC/USDT")
        assert position is not None
        assert position["quantity"] == Decimal("0.1")
        assert position["avg_entry_price"] == Decimal("40000")
        assert position["market_value"] == Decimal("4000")

    def test_position_tracking_sell(self):
        """Test position tracking on sell."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        # First buy
        broker._update_position(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("40000"),
            timestamp_ms=1000,
        )

        # Then sell
        broker._update_position(
            symbol="BTC/USDT",
            side="sell",
            quantity=Decimal("0.05"),
            price=Decimal("41000"),
            timestamp_ms=2000,
        )

        position = broker.get_position("BTC/USDT")
        assert position is not None
        assert position["quantity"] == Decimal("0.05")
        assert position["realized_pnl"] > 0  # Made profit

    def test_position_averaging(self):
        """Test position cost averaging on multiple buys."""
        broker = SimulatedBroker(initial_cash=Decimal("100000"))

        # First buy at 40000
        broker._update_position(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("40000"),
            timestamp_ms=1000,
        )

        # Second buy at 42000
        broker._update_position(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("42000"),
            timestamp_ms=2000,
        )

        position = broker.get_position("BTC/USDT")
        assert position is not None
        assert position["quantity"] == Decimal("0.2")

        # Average should be (40000 + 42000) / 2 = 41000
        assert position["avg_entry_price"] == Decimal("41000")

    def test_get_equity(self):
        """Test equity calculation."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        # Add a position
        broker._update_position(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("40000"),
            timestamp_ms=1000,
        )

        # Deduct cash for purchase
        broker.cash -= Decimal("4000")

        # Equity should be cash + position value
        equity = broker.get_equity()

        expected = Decimal("6000") + Decimal("4000")  # remaining cash + position
        assert equity == expected

    def test_get_equity_with_market_prices(self):
        """Test equity calculation with custom market prices."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        broker._update_position(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("40000"),
            timestamp_ms=1000,
        )

        broker.cash = Decimal("6000")

        # Override market price
        market_prices = {"BTC/USDT": Decimal("45000")}
        equity = broker.get_equity(market_prices)

        # Should use new price
        expected = Decimal("6000") + (Decimal("0.1") * Decimal("45000"))
        assert equity == expected

    def test_callbacks_on_fill(self):
        """Test fill callback is triggered."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        fills = []

        def on_fill(fill):
            fills.append(fill)

        broker.set_on_fill(on_fill)

        order_id = broker.market_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            timestamp_ms=1000,
        )

        candle: CandleData = {
            "schema_version": "1.0.0",
            "provider": "test",
            "symbol": "BTC/USDT",
            "interval": "1m",
            "open_time_ms": 1000,
            "close_time_ms": 2000,
            "open": Decimal("40000"),
            "high": Decimal("40100"),
            "low": Decimal("39900"),
            "close": Decimal("40050"),
            "volume": Decimal("100"),
            "is_closed": True,
            "raw": {},
        }

        broker.process_bar(candle, candle["open_time_ms"])

        assert len(fills) == 1
        assert fills[0]["order_id"] == order_id

    def test_callbacks_on_order_update(self):
        """Test order update callback is triggered."""
        broker = SimulatedBroker(initial_cash=Decimal("10000"))

        updates = []

        def on_update(order):
            updates.append(order)

        broker.set_on_order_update(on_update)

        broker.market_order(
            symbol="BTC/USDT",
            side="buy",
            quantity=Decimal("0.1"),
            timestamp_ms=1000,
        )

        # Should have received update on order creation
        assert len(updates) >= 1
        assert updates[0]["status"] == "new"
