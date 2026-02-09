"""Tests for backtesting metrics computation."""

from decimal import Decimal

from src.backtesting.metrics import (
    compute_annualized_return,
    compute_max_drawdown,
    compute_profit_factor,
    compute_sharpe_ratio,
    compute_total_return,
    compute_volatility,
    compute_win_rate,
)
from src.types import EquityPointData, TradeLogEntryData


class TestTotalReturn:
    """Tests for total return computation."""

    def test_positive_return(self):
        """Test positive return calculation."""
        initial = Decimal("10000")
        final = Decimal("12000")

        result = compute_total_return(initial, final)

        assert result == Decimal("0.2")  # 20% return

    def test_negative_return(self):
        """Test negative return calculation."""
        initial = Decimal("10000")
        final = Decimal("8000")

        result = compute_total_return(initial, final)

        assert result == Decimal("-0.2")  # -20% return

    def test_zero_return(self):
        """Test zero return calculation."""
        initial = Decimal("10000")
        final = Decimal("10000")

        result = compute_total_return(initial, final)

        assert result == Decimal("0")

    def test_zero_initial_equity(self):
        """Test with zero initial equity."""
        result = compute_total_return(Decimal("0"), Decimal("10000"))

        assert result == Decimal("0")


class TestAnnualizedReturn:
    """Tests for annualized return computation."""

    def test_one_year_period(self):
        """Test annualized return for exactly one year."""
        total_return = Decimal("0.2")  # 20% return
        duration_ms = 365 * 24 * 60 * 60 * 1000  # 1 year

        result = compute_annualized_return(total_return, duration_ms)

        # 20% over 1 year = 20% annualized
        assert abs(result - Decimal("0.2")) < Decimal("0.01")

    def test_half_year_period(self):
        """Test annualized return for half year."""
        total_return = Decimal("0.1")  # 10% return
        duration_ms = 182 * 24 * 60 * 60 * 1000  # ~6 months

        result = compute_annualized_return(total_return, duration_ms)

        # 10% over 6 months should be > 20% annualized (compounding)
        assert result > Decimal("0.2")


class TestVolatility:
    """Tests for volatility computation."""

    def test_zero_volatility(self):
        """Test volatility with constant equity."""
        equity_curve: list[EquityPointData] = [
            {
                "timestamp_ms": 1000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 2000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 3000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
        ]

        result = compute_volatility(equity_curve)

        assert result == Decimal("0")

    def test_positive_volatility(self):
        """Test volatility with varying equity."""
        equity_curve: list[EquityPointData] = [
            {
                "timestamp_ms": 1000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 2000,
                "equity": Decimal("11000"),
                "cash": Decimal("11000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 3000,
                "equity": Decimal("9000"),
                "cash": Decimal("9000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 4000,
                "equity": Decimal("12000"),
                "cash": Decimal("12000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
        ]

        result = compute_volatility(equity_curve)

        assert result > Decimal("0")

    def test_insufficient_data(self):
        """Test volatility with insufficient data points."""
        equity_curve: list[EquityPointData] = [
            {
                "timestamp_ms": 1000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
        ]

        result = compute_volatility(equity_curve)

        assert result == Decimal("0")


class TestSharpeRatio:
    """Tests for Sharpe ratio computation."""

    def test_positive_sharpe(self):
        """Test Sharpe ratio with positive returns."""
        annualized_return = Decimal("0.2")  # 20% return
        volatility = Decimal("0.15")  # 15% volatility
        risk_free_rate = Decimal("0.02")  # 2% risk-free

        result = compute_sharpe_ratio(annualized_return, volatility, risk_free_rate)

        # (0.20 - 0.02) / 0.15 = 1.2
        expected = (annualized_return - risk_free_rate) / volatility
        assert result == expected
        assert result > Decimal("0")

    def test_zero_volatility(self):
        """Test Sharpe ratio with zero volatility."""
        annualized_return = Decimal("0.1")
        volatility = Decimal("0")

        result = compute_sharpe_ratio(annualized_return, volatility)

        # Zero volatility should return 0
        assert result == Decimal("0")


class TestMaxDrawdown:
    """Tests for maximum drawdown computation."""

    def test_no_drawdown(self):
        """Test with monotonically increasing equity."""
        equity_curve: list[EquityPointData] = [
            {
                "timestamp_ms": 1000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 2000,
                "equity": Decimal("11000"),
                "cash": Decimal("11000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 3000,
                "equity": Decimal("12000"),
                "cash": Decimal("12000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
        ]

        drawdown, duration = compute_max_drawdown(equity_curve)

        assert drawdown == Decimal("0")
        assert duration == 0

    def test_simple_drawdown(self):
        """Test with simple drawdown."""
        equity_curve: list[EquityPointData] = [
            {
                "timestamp_ms": 1000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 2000,
                "equity": Decimal("12000"),
                "cash": Decimal("12000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 3000,
                "equity": Decimal("9000"),
                "cash": Decimal("9000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 4000,
                "equity": Decimal("13000"),
                "cash": Decimal("13000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
        ]

        drawdown, duration = compute_max_drawdown(equity_curve)

        # From 12000 to 9000 = 25% drawdown
        expected_drawdown = (Decimal("12000") - Decimal("9000")) / Decimal("12000")
        assert abs(drawdown - expected_drawdown) < Decimal("0.001")
        assert duration > 0

    def test_multiple_drawdowns(self):
        """Test with multiple drawdowns, returns maximum."""
        equity_curve: list[EquityPointData] = [
            {
                "timestamp_ms": 1000,
                "equity": Decimal("10000"),
                "cash": Decimal("10000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 2000,
                "equity": Decimal("9000"),
                "cash": Decimal("9000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },  # 10% DD
            {
                "timestamp_ms": 3000,
                "equity": Decimal("11000"),
                "cash": Decimal("11000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
            {
                "timestamp_ms": 4000,
                "equity": Decimal("8000"),
                "cash": Decimal("8000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },  # 27% DD
            {
                "timestamp_ms": 5000,
                "equity": Decimal("12000"),
                "cash": Decimal("12000"),
                "unrealized_pnl": Decimal("0"),
                "realized_pnl": Decimal("0"),
            },
        ]

        drawdown, duration = compute_max_drawdown(equity_curve)

        # Should return the larger drawdown (from 11000 to 8000)
        expected_drawdown = (Decimal("11000") - Decimal("8000")) / Decimal("11000")
        assert abs(drawdown - expected_drawdown) < Decimal("0.001")


class TestWinRate:
    """Tests for win rate computation."""

    def test_all_winning_trades(self):
        """Test with all profitable trades."""
        trades: list[TradeLogEntryData] = [
            {
                "trade_id": "t1",
                "order_id": "o1",
                "timestamp_ms": 2000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("42000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("2000"),
            },
            {
                "trade_id": "t2",
                "order_id": "o2",
                "timestamp_ms": 4000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("41000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("1000"),
            },
        ]

        result = compute_win_rate(trades)

        assert result == Decimal("1.0")  # 100% win rate

    def test_all_losing_trades(self):
        """Test with all losing trades."""
        trades: list[TradeLogEntryData] = [
            {
                "trade_id": "t1",
                "order_id": "o1",
                "timestamp_ms": 2000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("38000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("-2000"),
            },
        ]

        result = compute_win_rate(trades)

        assert result == Decimal("0")  # 0% win rate

    def test_mixed_trades(self):
        """Test with mixed winning and losing trades."""
        trades: list[TradeLogEntryData] = [
            {
                "trade_id": "t1",
                "order_id": "o1",
                "timestamp_ms": 2000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("42000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("2000"),
            },
            {
                "trade_id": "t2",
                "order_id": "o2",
                "timestamp_ms": 4000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("38000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("-2000"),
            },
            {
                "trade_id": "t3",
                "order_id": "o3",
                "timestamp_ms": 6000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("41000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("1000"),
            },
        ]

        result = compute_win_rate(trades)

        # 2 winners out of 3 = 66.67%
        expected = Decimal("2") / Decimal("3")
        assert abs(result - expected) < Decimal("0.001")

    def test_empty_trades(self):
        """Test with no trades."""
        result = compute_win_rate([])

        assert result == Decimal("0")


class TestProfitFactor:
    """Tests for profit factor computation."""

    def test_positive_profit_factor(self):
        """Test profit factor with wins and losses."""
        trades: list[TradeLogEntryData] = [
            {
                "trade_id": "t1",
                "order_id": "o1",
                "timestamp_ms": 2000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("42000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("2000"),
            },
            {
                "trade_id": "t2",
                "order_id": "o2",
                "timestamp_ms": 4000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("38000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("-1000"),
            },
        ]

        result = compute_profit_factor(trades)

        # Profit factor = gross profit / gross loss = 2000 / 1000 = 2.0
        assert result == Decimal("2.0")

    def test_only_winners(self):
        """Test profit factor with only winning trades."""
        trades: list[TradeLogEntryData] = [
            {
                "trade_id": "t1",
                "order_id": "o1",
                "timestamp_ms": 2000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("42000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("2000"),
            },
        ]

        result = compute_profit_factor(trades)

        # No losses = high profit factor
        assert result > Decimal("0")

    def test_only_losers(self):
        """Test profit factor with only losing trades."""
        trades: list[TradeLogEntryData] = [
            {
                "trade_id": "t1",
                "order_id": "o1",
                "timestamp_ms": 2000,
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": Decimal("38000"),
                "quantity": Decimal("1"),
                "fee": Decimal("10"),
                "slippage": Decimal("0"),
                "realized_pnl": Decimal("-2000"),
            },
        ]

        result = compute_profit_factor(trades)

        # No profits = 0 profit factor
        assert result == Decimal("0")
