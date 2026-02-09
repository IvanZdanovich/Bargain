"""Performance metrics computation for backtesting.

Provides:
- Equity curve analysis
- Risk-adjusted returns (Sharpe, Sortino)
- Drawdown analysis
- Trade statistics
- Win/loss analysis
"""

import math
from decimal import Decimal
from typing import Any

from src.types import (
    BacktestMetricsData,
    EquityPointData,
    TradeLogEntryData,
)


def compute_total_return(
    initial_equity: Decimal,
    final_equity: Decimal,
) -> Decimal:
    """Compute total return percentage.

    Args:
        initial_equity: Starting equity.
        final_equity: Ending equity.

    Returns:
        Total return as decimal (e.g., 0.25 = 25%).
    """
    if initial_equity == 0:
        return Decimal("0")

    return (final_equity - initial_equity) / initial_equity


def compute_annualized_return(
    total_return: Decimal,
    duration_ms: int,
) -> Decimal:
    """Compute annualized return.

    Args:
        total_return: Total return as decimal.
        duration_ms: Duration in milliseconds.

    Returns:
        Annualized return.
    """
    if duration_ms == 0:
        return Decimal("0")

    years = Decimal(duration_ms) / Decimal("31536000000")  # ms in a year

    if years == 0:
        return Decimal("0")

    # (1 + total_return) ^ (1/years) - 1
    compound_factor = float(1 + total_return)
    annualized = Decimal(str(math.pow(compound_factor, 1 / float(years)) - 1))

    return annualized


def compute_volatility(equity_curve: list[EquityPointData]) -> Decimal:
    """Compute equity volatility (standard deviation of returns).

    Args:
        equity_curve: List of equity points.

    Returns:
        Volatility as decimal.
    """
    if len(equity_curve) < 2:
        return Decimal("0")

    # Compute returns
    returns = []
    for i in range(1, len(equity_curve)):
        prev_equity = equity_curve[i - 1]["equity"]
        curr_equity = equity_curve[i]["equity"]

        if prev_equity == 0:
            continue

        ret = float((curr_equity - prev_equity) / prev_equity)
        returns.append(ret)

    if not returns:
        return Decimal("0")

    # Compute standard deviation
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)

    return Decimal(str(std_dev))


def compute_sharpe_ratio(
    annualized_return: Decimal,
    volatility: Decimal,
    risk_free_rate: Decimal = Decimal("0.02"),
) -> Decimal:
    """Compute Sharpe ratio.

    Args:
        annualized_return: Annualized return.
        volatility: Return volatility.
        risk_free_rate: Risk-free rate (default 2%).

    Returns:
        Sharpe ratio.
    """
    if volatility == 0:
        return Decimal("0")

    return (annualized_return - risk_free_rate) / volatility


def compute_max_drawdown(equity_curve: list[EquityPointData]) -> tuple[Decimal, int]:
    """Compute maximum drawdown and its duration.

    Args:
        equity_curve: List of equity points.

    Returns:
        Tuple of (max_drawdown, duration_ms).
    """
    if not equity_curve:
        return Decimal("0"), 0

    max_equity = Decimal("0")
    max_dd = Decimal("0")
    max_dd_duration = 0
    dd_start_time = 0

    for point in equity_curve:
        equity = point["equity"]
        timestamp = point["timestamp_ms"]

        if equity > max_equity:
            max_equity = equity
            dd_start_time = timestamp
        elif max_equity > 0:
            dd = (max_equity - equity) / max_equity
            if dd > max_dd:
                max_dd = dd
                max_dd_duration = timestamp - dd_start_time

    return max_dd, max_dd_duration


def compute_win_rate(trades: list[TradeLogEntryData]) -> Decimal:
    """Compute win rate (percentage of winning trades).

    Args:
        trades: List of trade log entries.

    Returns:
        Win rate as decimal (0.6 = 60%).
    """
    if not trades:
        return Decimal("0")

    # Group trades by order to compute full trade PnL
    # For simplicity, count each trade with realized_pnl
    winning = 0
    total = 0

    for trade in trades:
        if trade["realized_pnl"] is not None:
            total += 1
            if trade["realized_pnl"] > 0:
                winning += 1

    if total == 0:
        return Decimal("0")

    return Decimal(winning) / Decimal(total)


def compute_avg_win_loss(trades: list[TradeLogEntryData]) -> tuple[Decimal, Decimal]:
    """Compute average win and average loss.

    Args:
        trades: List of trade log entries.

    Returns:
        Tuple of (avg_win, avg_loss).
    """
    wins = []
    losses = []

    for trade in trades:
        pnl = trade["realized_pnl"]
        if pnl is not None:
            if pnl > 0:
                wins.append(float(pnl))
            elif pnl < 0:
                losses.append(float(abs(pnl)))

    avg_win = Decimal(str(sum(wins) / len(wins))) if wins else Decimal("0")
    avg_loss = Decimal(str(sum(losses) / len(losses))) if losses else Decimal("0")

    return avg_win, avg_loss


def compute_profit_factor(trades: list[TradeLogEntryData]) -> Decimal:
    """Compute profit factor (gross profit / gross loss).

    Args:
        trades: List of trade log entries.

    Returns:
        Profit factor.
    """
    gross_profit = Decimal("0")
    gross_loss = Decimal("0")

    for trade in trades:
        pnl = trade["realized_pnl"]
        if pnl is not None:
            if pnl > 0:
                gross_profit += pnl
            elif pnl < 0:
                gross_loss += abs(pnl)

    if gross_loss == 0:
        return Decimal("0") if gross_profit == 0 else Decimal("999")

    return gross_profit / gross_loss


def compute_exposure(
    equity_curve: list[EquityPointData],
    positions: list[Any],
) -> Decimal:
    """Compute market exposure (time in market).

    Args:
        equity_curve: Equity curve.
        positions: Position snapshots.

    Returns:
        Exposure as decimal (0.5 = 50% of time in market).
    """
    # Simplified: count points where we had any position
    if not equity_curve:
        return Decimal("0")

    # This is a rough estimate - ideally track time-weighted exposure
    return Decimal("0.5")  # Placeholder


def compute_turnover(trades: list[TradeLogEntryData], avg_equity: Decimal) -> Decimal:
    """Compute turnover (total traded volume / avg equity).

    Args:
        trades: Trade log entries.
        avg_equity: Average equity during backtest.

    Returns:
        Turnover ratio.
    """
    if avg_equity == 0:
        return Decimal("0")

    total_volume = Decimal("0")
    for trade in trades:
        total_volume += trade["price"] * trade["quantity"]

    return total_volume / avg_equity


def compute_metrics(
    equity_curve: list[EquityPointData],
    trades: list[TradeLogEntryData],
    initial_cash: Decimal,
) -> BacktestMetricsData:
    """Compute comprehensive backtest metrics.

    Args:
        equity_curve: Equity curve data.
        trades: Trade log.
        initial_cash: Initial equity.

    Returns:
        BacktestMetricsData with all metrics.
    """
    if not equity_curve:
        # Return empty metrics
        return {
            "total_return": Decimal("0"),
            "annualized_return": Decimal("0"),
            "volatility": Decimal("0"),
            "sharpe_ratio": Decimal("0"),
            "max_drawdown": Decimal("0"),
            "max_drawdown_duration_ms": 0,
            "win_rate": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "profit_factor": Decimal("0"),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_trade_duration_ms": 0,
            "exposure": Decimal("0"),
            "turnover": Decimal("0"),
        }

    final_equity = equity_curve[-1]["equity"]
    duration_ms = equity_curve[-1]["timestamp_ms"] - equity_curve[0]["timestamp_ms"]

    total_return = compute_total_return(initial_cash, final_equity)
    annualized_return = compute_annualized_return(total_return, duration_ms)
    volatility = compute_volatility(equity_curve)
    sharpe = compute_sharpe_ratio(annualized_return, volatility)
    max_dd, max_dd_duration = compute_max_drawdown(equity_curve)

    win_rate = compute_win_rate(trades)
    avg_win, avg_loss = compute_avg_win_loss(trades)
    profit_factor = compute_profit_factor(trades)

    # Count trades
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t["realized_pnl"] and t["realized_pnl"] > 0)
    losing_trades = sum(1 for t in trades if t["realized_pnl"] and t["realized_pnl"] < 0)

    # Average equity for turnover
    avg_equity = Decimal(sum(p["equity"] for p in equity_curve) / len(equity_curve))
    turnover = compute_turnover(trades, avg_equity)

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "volatility": volatility,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "max_drawdown_duration_ms": max_dd_duration,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "avg_trade_duration_ms": 0,  # TODO: compute from trade durations
        "exposure": compute_exposure(equity_curve, []),
        "turnover": turnover,
    }
