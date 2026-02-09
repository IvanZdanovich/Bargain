"""Clock and portfolio accessors for backtesting.

Provides:
- Simulation clock for deterministic time
- Portfolio state accessor
- Shared interfaces for backtest and live
"""

from decimal import Decimal
from typing import Any

from src.types import PositionData


class SimulationClock:
    """Clock for deterministic simulation time.

    Input: Time updates from simulation engine.
    Output: Current timestamp queries.
    Side effects: None (pure state accessor).
    """

    def __init__(self, initial_time_ms: int = 0):
        """Initialize simulation clock.

        Args:
            initial_time_ms: Starting timestamp.
        """
        self._current_time_ms = initial_time_ms

    def now_ms(self) -> int:
        """Get current simulation time in milliseconds.

        Returns:
            Current timestamp.
        """
        return self._current_time_ms

    def update(self, timestamp_ms: int) -> None:
        """Update simulation time.

        Args:
            timestamp_ms: New timestamp.

        Side effects: Updates internal time.
        """
        self._current_time_ms = timestamp_ms


class PortfolioAccessor:
    """Portfolio state accessor for strategies.

    Provides read-only access to portfolio state including
    cash, equity, positions, and PnL.

    Input: Broker state.
    Output: Portfolio queries.
    Side effects: None (read-only).
    """

    def __init__(self, broker: Any):
        """Initialize portfolio accessor.

        Args:
            broker: Broker instance with portfolio state.
        """
        self._broker = broker

    @property
    def cash(self) -> Decimal:
        """Get current cash balance.

        Returns:
            Cash balance.
        """
        return Decimal(self._broker.cash)

    @property
    def equity(self) -> Decimal:
        """Get current total equity.

        Returns:
            Total equity (cash + position values).
        """
        return Decimal(self._broker.get_equity())

    def get_position(self, symbol: str) -> PositionData | None:
        """Get position for a symbol.

        Args:
            symbol: Symbol to query.

        Returns:
            Position data or None if no position.
        """
        pos = self._broker.get_position(symbol)
        return pos if pos is not None else None

    def get_all_positions(self) -> dict[str, PositionData]:
        """Get all positions.

        Returns:
            Dictionary mapping symbol to position data.
        """
        return dict(self._broker.get_all_positions())

    def get_position_quantity(self, symbol: str) -> Decimal:
        """Get position quantity for a symbol.

        Args:
            symbol: Symbol to query.

        Returns:
            Position quantity (0 if no position).
        """
        position = self.get_position(symbol)
        return position["quantity"] if position else Decimal("0")

    def has_position(self, symbol: str) -> bool:
        """Check if a position exists for a symbol.

        Args:
            symbol: Symbol to check.

        Returns:
            True if position exists and quantity != 0.
        """
        position = self.get_position(symbol)
        return position is not None and position["quantity"] != 0

    @property
    def total_realized_pnl(self) -> Decimal:
        """Get total realized PnL across all positions.

        Returns:
            Total realized PnL.
        """
        total = Decimal("0")
        for position in self._broker.positions.values():
            total += position["realized_pnl"]
        return total

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized PnL across all positions.

        Returns:
            Total unrealized PnL.
        """
        total = Decimal("0")
        for _symbol, position in self._broker.positions.items():
            if position["quantity"] != 0:
                pnl = (position["market_price"] - position["avg_entry_price"]) * position[
                    "quantity"
                ]
                total += pnl
        return total
