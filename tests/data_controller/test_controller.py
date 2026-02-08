"""Unit tests for controller orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.types import ProviderConfigData, HandlersData
from src.data_controller.controller import (
    create_controller,
    get_provider_status,
    get_provider_health,
    get_all_provider_health,
)


@pytest.fixture
def binance_config() -> ProviderConfigData:
    """Create test Binance provider config."""
    return ProviderConfigData(
        name="binance",
        api_key=None,
        api_secret=None,
        testnet=True,
        rate_limit_per_second=10,
        reconnect_attempts=3,
        reconnect_delay_ms=100,
    )


@pytest.fixture
def handlers() -> HandlersData:
    """Create test handlers."""
    return HandlersData(
        on_trade=MagicMock(),
        on_candle=MagicMock(),
        on_error=MagicMock(),
        on_status_change=MagicMock(),
    )


class TestCreateController:
    """Tests for create_controller function."""

    def test_create_with_single_provider(self, binance_config, handlers):
        """Create controller with one provider."""
        controller = create_controller([binance_config], handlers)

        assert "providers" in controller
        assert "binance" in controller["providers"]
        assert controller["handlers"] == handlers
        assert controller["running"] is False
        assert controller["mode"] == "live"

    def test_create_with_multiple_providers(self, handlers):
        """Create controller with multiple providers."""
        configs = [
            ProviderConfigData(
                name="binance",
                api_key=None,
                api_secret=None,
                testnet=True,
                rate_limit_per_second=10,
                reconnect_attempts=3,
                reconnect_delay_ms=100,
            ),
            ProviderConfigData(
                name="binance_futures",
                api_key=None,
                api_secret=None,
                testnet=True,
                rate_limit_per_second=10,
                reconnect_attempts=3,
                reconnect_delay_ms=100,
            ),
        ]

        controller = create_controller(configs, handlers)

        assert "binance" in controller["providers"]
        assert "binance_futures" in controller["providers"]

    def test_create_with_no_handlers(self, binance_config):
        """Create controller without handlers."""
        controller = create_controller([binance_config])

        assert controller["handlers"] == {}

    def test_create_with_event_bus(self, binance_config):
        """Create controller with event bus config."""
        event_bus_config = {
            "emit": MagicMock(),
        }

        controller = create_controller(
            [binance_config],
            event_bus_config=event_bus_config,
        )

        assert controller["event_bus_config"] == event_bus_config

    def test_create_with_storage(self, binance_config):
        """Create controller with storage config."""
        storage_config = {
            "enabled": True,
            "batch_size": 100,
            "write": AsyncMock(),
        }

        controller = create_controller(
            [binance_config],
            storage_config=storage_config,
        )

        assert controller["storage_buffer"] is not None

    def test_unknown_provider_logged(self, handlers):
        """Unknown provider is logged but doesn't crash."""
        config = ProviderConfigData(
            name="unknown_provider",
            api_key=None,
            api_secret=None,
            testnet=True,
            rate_limit_per_second=10,
            reconnect_attempts=3,
            reconnect_delay_ms=100,
        )

        controller = create_controller([config], handlers)

        assert "unknown_provider" not in controller["providers"]


class TestGetProviderStatus:
    """Tests for get_provider_status function."""

    def test_get_existing_provider_status(self, binance_config):
        """Get status of existing provider."""
        controller = create_controller([binance_config])

        status = get_provider_status(controller, "binance")

        assert status == "disconnected"

    def test_get_unknown_provider_status(self, binance_config):
        """Get status of unknown provider returns disconnected."""
        controller = create_controller([binance_config])

        status = get_provider_status(controller, "unknown")

        assert status == "disconnected"


class TestGetProviderHealth:
    """Tests for get_provider_health function."""

    def test_get_existing_provider_health(self, binance_config):
        """Get health of existing provider."""
        controller = create_controller([binance_config])

        health = get_provider_health(controller, "binance")

        assert health["provider"] == "binance"
        assert health["status"] == "disconnected"
        assert health["message_count"] == 0
        assert health["error_count"] == 0

    def test_get_unknown_provider_health(self, binance_config):
        """Get health of unknown provider returns default."""
        controller = create_controller([binance_config])

        health = get_provider_health(controller, "unknown")

        assert health["provider"] == "unknown"
        assert health["status"] == "disconnected"


class TestGetAllProviderHealth:
    """Tests for get_all_provider_health function."""

    def test_get_all_health(self):
        """Get health of all providers."""
        configs = [
            ProviderConfigData(
                name="binance",
                api_key=None,
                api_secret=None,
                testnet=True,
                rate_limit_per_second=10,
                reconnect_attempts=3,
                reconnect_delay_ms=100,
            ),
            ProviderConfigData(
                name="binance_testnet",
                api_key=None,
                api_secret=None,
                testnet=True,
                rate_limit_per_second=10,
                reconnect_attempts=3,
                reconnect_delay_ms=100,
            ),
        ]

        controller = create_controller(configs)

        health_list = get_all_provider_health(controller)

        assert len(health_list) == 2
        provider_names = [h["provider"] for h in health_list]
        assert "binance" in provider_names
        assert "binance_testnet" in provider_names
