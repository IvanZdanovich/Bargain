"""Example: RSI Mean Reversion Strategy Backtest.

Demonstrates:
1. Strategy with technical indicators
2. Entry and exit rules
3. Risk management
4. Performance analysis
"""

import logging
from decimal import Decimal

from src.backtesting import StrategyBase, StrategyContext, run_backtest
from src.backtesting.feed import create_feed_from_candles
from src.config import SCHEMA_VERSION
from src.types import BacktestConfigData, CandleData, FillData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def compute_rsi(prices: list[Decimal], period: int = 14) -> Decimal:
    """Compute RSI indicator.

    Args:
        prices: Price history.
        period: RSI period.

    Returns:
        RSI value (0-100).
    """
    if len(prices) < period + 1:
        return Decimal("50")

    # Compute gains and losses
    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(Decimal("0"))
        else:
            gains.append(Decimal("0"))
            losses.append(abs(change))

    # Average gains and losses
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return Decimal("100")

    rs = avg_gain / avg_loss
    rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

    return rsi


class RSIMeanReversionStrategy(StrategyBase):
    """RSI mean reversion strategy.

    Rules:
    - Buy when RSI < 30 (oversold)
    - Sell when RSI > 70 (overbought) or stop loss hit
    - Position sizing: 20% of equity per trade
    - Stop loss: 3%
    """

    def __init__(self, rsi_period: int = 14, oversold: int = 30, overbought: int = 70):
        """Initialize strategy.

        Args:
            rsi_period: RSI calculation period.
            oversold: Oversold threshold.
            overbought: Overbought threshold.
        """
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.prices: list[Decimal] = []
        self.entry_price: Decimal | None = None
        self.stop_loss_pct = Decimal("0.03")
        self.position_size_pct = Decimal("0.20")

    def on_start(self, context: StrategyContext) -> None:
        """Initialize strategy."""
        logger.info(
            f"RSI Strategy starting: period={self.rsi_period}, "
            f"oversold={self.oversold}, overbought={self.overbought}"
        )
        self.prices = []
        self.entry_price = None

    def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
        """Process bar and generate signals."""
        symbol = bar["symbol"]
        close = bar["close"]

        # Update price history
        self.prices.append(close)
        if len(self.prices) > 100:
            self.prices.pop(0)

        # Need enough data for RSI
        if len(self.prices) < self.rsi_period + 1:
            return

        # Compute RSI
        rsi = compute_rsi(self.prices, self.rsi_period)

        # Check position
        position = context.portfolio.get_position(symbol)
        has_position = position is not None and position["quantity"] > 0

        # Entry logic
        if not has_position and rsi < self.oversold:
            # Buy signal: RSI oversold
            equity = context.portfolio.equity
            position_value = equity * self.position_size_pct
            order_size = position_value / close

            if order_size > 0 and position_value <= context.portfolio.cash:
                logger.info(f"BUY signal: {symbol} @ {close} | RSI: {rsi:.2f}")
                context.broker.market_order(
                    symbol=symbol,
                    side="buy",
                    quantity=order_size,
                    timestamp_ms=bar["open_time_ms"],
                )
                self.entry_price = close

        # Exit logic
        elif has_position and position:
            # Exit on overbought
            if rsi > self.overbought:
                logger.info(f"SELL signal (overbought): {symbol} @ {close} | RSI: {rsi:.2f}")
                context.broker.market_order(
                    symbol=symbol,
                    side="sell",
                    quantity=position["quantity"],
                    timestamp_ms=bar["open_time_ms"],
                )
                self.entry_price = None

            # Stop loss
            elif self.entry_price and close < self.entry_price * (
                Decimal("1") - self.stop_loss_pct
            ):
                logger.info(f"SELL signal (stop loss): {symbol} @ {close}")
                context.broker.market_order(
                    symbol=symbol,
                    side="sell",
                    quantity=position["quantity"],
                    timestamp_ms=bar["open_time_ms"],
                )
                self.entry_price = None

    def on_fill(self, context: StrategyContext, fill: FillData) -> None:
        """Handle fill events."""
        logger.info(
            f"Fill: {fill['side'].upper()} {fill['quantity']:.4f} @ ${float(fill['price']):.2f} | "
            f"Fee: ${float(fill['fee']):.2f}"
        )

    def on_end(self, context: StrategyContext) -> None:
        """Strategy cleanup."""
        logger.info("Strategy ending")
        logger.info(f"Final equity: ${float(context.portfolio.equity):.2f}")


def create_trending_candles(count: int = 300) -> list[CandleData]:
    """Create candles with clear trends for RSI signals.

    Args:
        count: Number of candles to create.

    Returns:
        List of synthetic candles.
    """
    import random

    random.seed(42)

    candles: list[CandleData] = []
    base_price = Decimal("40000")
    timestamp = 1640000000000

    price = base_price

    for i in range(count):
        # Create cycles: downtrend -> consolidation -> uptrend -> consolidation
        cycle_position = i % 80

        if cycle_position < 20:
            # Downtrend (will trigger oversold RSI)
            trend = Decimal(str(random.uniform(-100, -50)))
        elif cycle_position < 35:
            # Consolidation
            trend = Decimal(str(random.uniform(-20, 20)))
        elif cycle_position < 55:
            # Uptrend (will trigger overbought RSI)
            trend = Decimal(str(random.uniform(50, 100)))
        else:
            # Consolidation
            trend = Decimal(str(random.uniform(-20, 20)))

        price += trend

        # Ensure price doesn't go too low
        if price < Decimal("30000"):
            price = Decimal("30000")
        if price > Decimal("60000"):
            price = Decimal("60000")

        noise = Decimal(str(random.uniform(-100, 100)))
        open_price = price + noise
        high = price + abs(noise) + Decimal("50")
        low = price - abs(noise) - Decimal("50")
        close = price + Decimal(str(random.uniform(-50, 50)))

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
    """Run RSI backtest example."""
    logger.info("=== RSI Mean Reversion Strategy Backtest ===")

    # Create synthetic trending data
    logger.info("Creating synthetic market data...")
    candles = create_trending_candles(300)
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
        "slippage_bps": Decimal("10"),
        "commission_model": "percentage",
        "commission_rate": Decimal("0.001"),
        "latency_ms": 0,
        "order_matching": "bar_based",
        "max_leverage": Decimal("1.0"),
        "allow_short": False,
        "record_equity_curve": True,
        "record_positions": True,
        "record_orders": True,
        "record_trades": True,
        "log_level": "INFO",
        "random_seed": 42,
    }

    # Create strategy
    strategy = RSIMeanReversionStrategy(rsi_period=14, oversold=30, overbought=70)

    # Run backtest
    logger.info("Running backtest...")
    result = run_backtest(strategy, feed, config)

    # Print results
    print("\n" + "=" * 70)
    print("RSI MEAN REVERSION BACKTEST RESULTS")
    print("=" * 70)

    metrics = result["metrics"]
    print("\n📊 Performance Metrics:")
    print(f"  Total Return:        {float(metrics['total_return']) * 100:>8.2f}%")
    print(f"  Annualized Return:   {float(metrics['annualized_return']) * 100:>8.2f}%")
    print(f"  Sharpe Ratio:        {float(metrics['sharpe_ratio']):>8.2f}")
    print(f"  Max Drawdown:        {float(metrics['max_drawdown']) * 100:>8.2f}%")
    print(f"  Volatility:          {float(metrics['volatility']) * 100:>8.2f}%")

    print("\n📈 Trade Statistics:")
    print(f"  Total Trades:        {metrics['total_trades']:>8}")
    print(f"  Winning Trades:      {metrics['winning_trades']:>8}")
    print(f"  Losing Trades:       {metrics['losing_trades']:>8}")
    print(f"  Win Rate:            {float(metrics['win_rate']) * 100:>8.2f}%")
    print(f"  Average Win:         ${float(metrics['avg_win']):>7.2f}")
    print(f"  Average Loss:        ${float(metrics['avg_loss']):>7.2f}")
    print(f"  Profit Factor:       {float(metrics['profit_factor']):>8.2f}")

    print("\n💰 Equity Summary:")
    if result["equity_curve"]:
        initial = result["equity_curve"][0]["equity"]
        final = result["equity_curve"][-1]["equity"]
        pnl = final - initial
        print(f"  Initial Equity:      ${float(initial):>10.2f}")
        print(f"  Final Equity:        ${float(final):>10.2f}")
        print(f"  Total PnL:           ${float(pnl):>10.2f}")

    print("\n📋 Orders and Fills:")
    print(f"  Total Orders:        {len(result['orders']):>8}")
    print(f"  Total Fills:         {len(result['trades']):>8}")

    print("\n" + "=" * 70)

    # Sample trades
    if result["trades"]:
        print("\n🔄 Recent Trades (last 10):")
        for _i, trade in enumerate(result["trades"][-10:]):
            pnl_str = (
                f"${float(trade['realized_pnl']):>7.2f}" if trade["realized_pnl"] else "   N/A"
            )
            side_emoji = "🟢" if trade["side"] == "buy" else "🔴"
            print(
                f"  {side_emoji} {trade['side'].upper():4s} {float(trade['quantity']):>8.4f} "
                f"@ ${float(trade['price']):>8.2f} | Fee: ${float(trade['fee']):>5.2f} | PnL: {pnl_str}"
            )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
