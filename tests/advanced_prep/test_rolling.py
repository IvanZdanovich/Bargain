"""
Tests for rolling window functionality.
"""

from decimal import Decimal

import pytest

from src.advanced_prep.rolling import (
    RollingWindow,
    compute_rolling_mean,
    compute_rolling_std,
    compute_z_score,
)


class TestRollingWindow:
    """Tests for RollingWindow class."""

    def test_init(self) -> None:
        """Test initialization."""
        window = RollingWindow(5)
        assert window.size() == 5
        assert window.count() == 0
        assert not window.is_full()

    def test_init_invalid_size(self) -> None:
        """Test initialization with invalid size."""
        with pytest.raises(ValueError):
            RollingWindow(0)
        with pytest.raises(ValueError):
            RollingWindow(-1)

    def test_append(self) -> None:
        """Test appending values."""
        window = RollingWindow(3)
        window.append(Decimal("10"))
        assert window.count() == 1
        window.append(Decimal("20"))
        assert window.count() == 2
        window.append(Decimal("30"))
        assert window.count() == 3
        assert window.is_full()

    def test_append_overflow(self) -> None:
        """Test appending beyond capacity."""
        window = RollingWindow(3)
        window.append(Decimal("10"))
        window.append(Decimal("20"))
        window.append(Decimal("30"))
        window.append(Decimal("40"))  # Should remove 10

        values = window.to_list()
        assert len(values) == 3
        assert values == [Decimal("20"), Decimal("30"), Decimal("40")]

    def test_mean(self) -> None:
        """Test rolling mean."""
        window = RollingWindow(3)
        assert window.mean() == Decimal(0)

        window.append(Decimal("10"))
        assert window.mean() == Decimal("10")

        window.append(Decimal("20"))
        assert window.mean() == Decimal("15")

        window.append(Decimal("30"))
        assert window.mean() == Decimal("20")

    def test_std(self) -> None:
        """Test rolling standard deviation."""
        window = RollingWindow(3)
        assert window.std() == Decimal(0)

        window.append(Decimal("10"))
        assert window.std() == Decimal(0)  # Need at least 2 values

        window.append(Decimal("20"))
        assert window.std() == Decimal("5")

        window.append(Decimal("30"))
        # std([10, 20, 30]) = sqrt((100 + 0 + 100) / 3) = sqrt(200/3) ≈ 8.165
        std_val = window.std()
        assert abs(std_val - Decimal("8.165")) < Decimal("0.01")

    def test_sum(self) -> None:
        """Test rolling sum."""
        window = RollingWindow(3)
        assert window.sum() == Decimal(0)

        window.append(Decimal("10"))
        window.append(Decimal("20"))
        window.append(Decimal("30"))
        assert window.sum() == Decimal("60")

    def test_max_min(self) -> None:
        """Test max and min."""
        window = RollingWindow(3)
        assert window.max() is None
        assert window.min() is None

        window.append(Decimal("20"))
        window.append(Decimal("10"))
        window.append(Decimal("30"))

        assert window.max() == Decimal("30")
        assert window.min() == Decimal("10")

    def test_reset(self) -> None:
        """Test reset functionality."""
        window = RollingWindow(3)
        window.append(Decimal("10"))
        window.append(Decimal("20"))

        window.reset()
        assert window.count() == 0
        assert window.sum() == Decimal(0)


class TestBatchFunctions:
    """Tests for batch rolling functions."""

    def test_compute_rolling_mean(self) -> None:
        """Test rolling mean computation."""
        values = [Decimal(str(x)) for x in [10, 20, 30, 40, 50]]
        result = compute_rolling_mean(values, 3)

        assert len(result) == 3
        assert result[0] == Decimal("20")  # (10+20+30)/3
        assert result[1] == Decimal("30")  # (20+30+40)/3
        assert result[2] == Decimal("40")  # (30+40+50)/3

    def test_compute_rolling_mean_edge_cases(self) -> None:
        """Test rolling mean edge cases."""
        values = [Decimal(str(x)) for x in [10, 20, 30]]

        # Window too large
        assert compute_rolling_mean(values, 5) == []

        # Window zero
        assert compute_rolling_mean(values, 0) == []

    def test_compute_rolling_std(self) -> None:
        """Test rolling standard deviation computation."""
        values = [Decimal(str(x)) for x in [10, 20, 30, 40, 50]]
        result = compute_rolling_std(values, 3)

        assert len(result) == 3
        # First window [10, 20, 30], mean=20, std ≈ 8.165
        assert abs(result[0] - Decimal("8.165")) < Decimal("0.01")

    def test_compute_z_score(self) -> None:
        """Test z-score computation."""
        value = Decimal("30")
        mean = Decimal("20")
        std = Decimal("5")

        z_score = compute_z_score(value, mean, std)
        assert z_score == Decimal("2")

        # Test zero std
        z_score_zero = compute_z_score(value, mean, Decimal(0))
        assert z_score_zero == Decimal(0)

