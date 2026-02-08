"""
Indicator registry and metadata management.

Provides registration, lookup, and validation for indicators with their
parameters and computation functions.
"""

from dataclasses import dataclass
from typing import Any, Callable

from src.types import IndicatorComputeFn


@dataclass
class IndicatorMetadata:
    """Metadata for a registered indicator."""

    name: str
    display_name: str
    description: str
    parameters: dict[str, Any]
    compute_fn: IndicatorComputeFn | Callable[..., Any]
    requires_streaming: bool
    min_periods: int


class IndicatorRegistry:
    """
    Registry for technical indicators.

    Side effects:
        Maintains global registry of indicators.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._indicators: dict[str, IndicatorMetadata] = {}

    def register(self, metadata: IndicatorMetadata) -> None:
        """
        Register indicator with metadata.

        Args:
            metadata: Indicator metadata.

        Side effects:
            Adds indicator to registry.

        Raises:
            ValueError: If indicator already registered.
        """
        if metadata.name in self._indicators:
            raise ValueError(f"Indicator '{metadata.name}' already registered")
        self._indicators[metadata.name] = metadata

    def get(self, name: str) -> IndicatorMetadata | None:
        """
        Get indicator metadata by name.

        Args:
            name: Indicator name.

        Returns:
            IndicatorMetadata or None if not found.
        """
        return self._indicators.get(name)

    def list_indicators(self) -> list[str]:
        """
        List all registered indicator names.

        Returns:
            List of indicator names.
        """
        return list(self._indicators.keys())

    def is_registered(self, name: str) -> bool:
        """
        Check if indicator is registered.

        Args:
            name: Indicator name.

        Returns:
            True if registered.
        """
        return name in self._indicators

    def get_required_periods(self, name: str) -> int:
        """
        Get minimum periods required for indicator.

        Args:
            name: Indicator name.

        Returns:
            Minimum number of periods, or 0 if not found.
        """
        metadata = self.get(name)
        return metadata.min_periods if metadata else 0


# Global registry instance
_global_registry = IndicatorRegistry()


def get_global_registry() -> IndicatorRegistry:
    """
    Get global indicator registry instance.

    Returns:
        Global IndicatorRegistry.
    """
    return _global_registry


def register_indicator(metadata: IndicatorMetadata) -> None:
    """
    Register indicator in global registry.

    Args:
        metadata: Indicator metadata.

    Side effects:
        Adds to global registry.
    """
    _global_registry.register(metadata)


def register_default_indicators() -> None:
    """
    Register default built-in indicators.

    Side effects:
        Populates global registry with standard indicators.
    """
    from src.advanced_prep.indicators import (
        compute_atr_batch,
        compute_ema,
        compute_sma,
        compute_wma,
    )

    indicators = [
        IndicatorMetadata(
            name="sma",
            display_name="Simple Moving Average",
            description="Simple moving average of prices",
            parameters={"period": 20},
            compute_fn=compute_sma,
            requires_streaming=False,
            min_periods=20,
        ),
        IndicatorMetadata(
            name="ema",
            display_name="Exponential Moving Average",
            description="Exponential moving average of prices",
            parameters={"period": 20},
            compute_fn=compute_ema,
            requires_streaming=True,
            min_periods=20,
        ),
        IndicatorMetadata(
            name="wma",
            display_name="Weighted Moving Average",
            description="Weighted moving average of prices",
            parameters={"period": 20},
            compute_fn=compute_wma,
            requires_streaming=False,
            min_periods=20,
        ),
        IndicatorMetadata(
            name="atr",
            display_name="Average True Range",
            description="Average True Range volatility indicator",
            parameters={"period": 14},
            compute_fn=compute_atr_batch,
            requires_streaming=True,
            min_periods=14,
        ),
    ]

    for indicator in indicators:
        try:
            register_indicator(indicator)
        except ValueError:
            # Already registered, skip
            pass

