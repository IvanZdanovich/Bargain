"""Example: Simple momentum strategy backtest.

Demonstrates:
1. Creating a custom strategy
2. Loading historical data
3. Running a backtest
4. Analyzing results
"""

import logging
from decimal import Decimal

from src.backtesting import StrategyBase, StrategyContext, run_backtest
from src.backtesting.feed import create_feed_from_candles
from src.types import BacktestConfigData, CandleData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SimpleMomentumStrategy(StrategyBase):
    """Simple momentum strategy.

    Rules:
    - Buy when price crosses above 20-bar moving average
    - Sell when price crosses below 20-bar moving average
    - Only one position at a time
    """

    def __init__(self, window: int = 20):
        """Initialize strategy.

        Args:
            window: Moving average window size.
        """
        self.window = window
        self.prices: list[Decimal] = []
        self.position_symbol: str | None = None

    def on_start(self, context: StrategyContext) -> None:
        """Initialize strategy state.

        Args:
            context: Strategy context.
        """
        logger.info(f"Strategy starting with window={self.window}")
        self.prices = []
        self.position_symbol = None

    def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
        """Process bar and generate signals.

        Args:
            context: Strategy context.
            bar: OHLCV candle.
        """
        symbol = bar["symbol"]
        close = bar["close"]

        # Update price history
        self.prices.append(close)
        if len(self.prices) > self.window:
            self.prices.pop(0)

        # Need enough data for MA
        if len(self.prices) < self.window:
            return

        # Compute moving average
        ma = sum(self.prices) / len(self.prices)

        # Check position
        position = context.portfolio.get_position(symbol)
        has_position = position is not None and position["quantity"] > 0

        # Generate signals
        if not has_position and close > ma * Decimal("1.01"):
            # Buy signal: price 1% above MA
            order_size = context.portfolio.cash * Decimal("0.95") / close
            if order_size > 0:
                logger.info(f"BUY signal: {symbol} @ {close} (MA: {ma:.2f})")
                context.broker.market_order(
                    symbol=symbol,
                    side="buy",
                    quantity=order_size,
                    timestamp_ms=bar["open_time_ms"],
                )
                self.position_symbol = symbol

        elif has_position and close < ma * Decimal("0.99"):
            # Sell signal: price 1% below MA
            if position:
                logger.info(f"SELL signal: {symbol} @ {close} (MA: {ma:.2f})")
                context.broker.market_order(
                    symbol=symbol,
                    side="sell",
                    quantity=position["quantity"],
                    timestamp_ms=bar["open_time_ms"],
                )
                self.position_symbol = None

    def on_end(self, context: StrategyContext) -> None:
        """Cleanup at strategy end.

        Args:
            context: Strategy context.
        """
        logger.info("Strategy ending")
        logger.info(f"Final equity: {context.portfolio.equity}")
        logger.info(f"Final cash: {context.portfolio.cash}")


def create_synthetic_candles() -> list[CandleData]:
    """Create synthetic candle data for testing.

    Returns:
        List of synthetic candles with trend.
    """
    from src.config import SCHEMA_VERSION

    candles: list[CandleData] = []
    base_price = Decimal("40000")
    timestamp = 1640000000000  # 2021-12-20

    # Create trending market: up, consolidation, down, recovery
    for i in range(200):
        # Add trend
        if i < 50:
            # Uptrend
            trend = Decimal(i) * Decimal("10")
        elif i < 100:
            # Consolidation
            trend = Decimal("500")
        elif i < 150:
            # Downtrend
            trend = Decimal("500") - Decimal(i - 100) * Decimal("15")
        else:
            # Recovery
            trend = Decimal("-250") + Decimal(i - 150) * Decimal("12")

        price = base_price + trend

        # Add some noise
        import random

        noise = Decimal(str(random.uniform(-50, 50)))
        open_price = price + noise
        high = price + abs(noise) + Decimal("20")
        low = price - abs(noise) - Decimal("20")
        close = price + Decimal(str(random.uniform(-30, 30)))

        candle: CandleData = {
            "schema_version": SCHEMA_VERSION,
            "provider": "synthetic",
            "symbol": "BTC/USDT",
            "interval": "1h",
            "open_time_ms": timestamp + (i * 3600000),
            "close_time_ms": timestamp + ((i + 1) * 3600000),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": Decimal("100"),
            "is_closed": True,
            "raw": {},
        }

        candles.append(candle)

    return candles


def main():
    """Run backtest example."""
    logger.info("=== Simple Momentum Strategy Backtest ===")

    # Create synthetic data
    logger.info("Creating synthetic market data...")
    candles = create_synthetic_candles()
    logger.info(f"Created {len(candles)} candles")

    # Create market data feed
    feed = create_feed_from_candles(candles)

    # Configure backtest
    config: BacktestConfigData = {
        "symbols": ["BTC/USDT"],
        "start_time_ms": candles[0]["open_time_ms"],
        "end_time_ms": candles[-1]["close_time_ms"],
        "timeframe": "1h",
        "mode": "event_driven",
        "initial_cash": Decimal("10000"),
        "base_currency": "USDT",
        "slippage_model": "fixed_bps",
        "slippage_bps": Decimal("5"),
        "commission_model": "percentage",
        "commission_rate": Decimal("0.001"),
        "latency_ms": 0,
        "order_matching": "bar_based",
        "max_leverage": Decimal("1.0"),
        "max_position_size": Decimal("1000"),
        "max_notional": Decimal("100000"),
        "allow_short": False,
        "record_equity_curve": True,
        "record_positions": True,
        "record_orders": True,
        "record_trades": True,
        "log_level": "INFO",
        "random_seed": 42,
    }

    # Create strategy
    strategy = SimpleMomentumStrategy(window=20)

    # Run backtest
    logger.info("Running backtest...")
    result = run_backtest(strategy, feed, config)

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    metrics = result["metrics"]
    print("\nPerformance Metrics:")
    print(f"  Total Return:        {float(metrics['total_return']) * 100:.2f}%")
    print(f"  Annualized Return:   {float(metrics['annualized_return']) * 100:.2f}%")
    print(f"  Sharpe Ratio:        {float(metrics['sharpe_ratio']):.2f}")
    print(f"  Max Drawdown:        {float(metrics['max_drawdown']) * 100:.2f}%")
    print(f"  Volatility:          {float(metrics['volatility']) * 100:.2f}%")

    print("\nTrade Statistics:")
    print(f"  Total Trades:        {metrics['total_trades']}")
    print(f"  Winning Trades:      {metrics['winning_trades']}")
    print(f"  Losing Trades:       {metrics['losing_trades']}")
    print(f"  Win Rate:            {float(metrics['win_rate']) * 100:.2f}%")
    print(f"  Average Win:         ${float(metrics['avg_win']):.2f}")
    print(f"  Average Loss:        ${float(metrics['avg_loss']):.2f}")
    print(f"  Profit Factor:       {float(metrics['profit_factor']):.2f}")

    print("\nEquity Summary:")
    if result["equity_curve"]:
        initial = result["equity_curve"][0]["equity"]
        final = result["equity_curve"][-1]["equity"]
        print(f"  Initial Equity:      ${float(initial):.2f}")
        print(f"  Final Equity:        ${float(final):.2f}")
        print(f"  Total PnL:           ${float(final - initial):.2f}")

    print("\nOrders and Fills:")
    print(f"  Total Orders:        {len(result['orders'])}")
    print(f"  Total Fills:         {len(result['trades'])}")

    print("\n" + "=" * 60)

    # Sample trades
    if result["trades"]:
        print("\nSample Trades (first 5):")
        for i, trade in enumerate(result["trades"][:5]):
            pnl_str = f"${float(trade['realized_pnl']):.2f}" if trade["realized_pnl"] else "N/A"
            print(
                f"  {i + 1}. {trade['side'].upper():4s} {trade['quantity']:8.4f} "
                f"@ ${float(trade['price']):8.2f} | Fee: ${float(trade['fee']):.2f} | PnL: {pnl_str}"
            )

    # Equity curve sample
    if result["equity_curve"]:
        print("\nEquity Curve (sample every 20 points):")
        for i, point in enumerate(result["equity_curve"][::20]):
            print(
                f"  Step {i * 20:3d}: Equity=${float(point['equity']):10.2f} "
                f"Cash=${float(point['cash']):10.2f} "
                f"PnL=${float(point['realized_pnl']):8.2f}"
            )


if __name__ == "__main__":
    main()
