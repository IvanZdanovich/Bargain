"""Unit tests for configuration loading module."""

import os
from unittest.mock import patch

from src.config import (
    get_config,
    get_secret,
    get_schema_version,
    get_binance_config,
    get_provider_defaults,
    get_reliability_config,
    get_storage_defaults,
    get_validation_config,
    get_normalization_config,
    reload_config,
)


class TestGetConfig:
    """Tests for get_config function."""

    def test_get_top_level_key(self):
        """Get top-level configuration value."""
        schema = get_config("schema_version")
        assert schema == "1.0.0"

    def test_get_nested_key(self):
        """Get nested configuration value using dot notation."""
        ws_url = get_config("binance.ws_url")
        assert ws_url == "wss://stream.binance.com:9443/ws"

    def test_get_deeply_nested_key(self):
        """Get deeply nested list value."""
        quote_currencies = get_config("normalization.quote_currencies")
        assert isinstance(quote_currencies, list)
        assert "USDT" in quote_currencies

    def test_get_missing_key_returns_default(self):
        """Missing key returns default value."""
        result = get_config("nonexistent.key", "default_value")
        assert result == "default_value"

    def test_get_missing_key_returns_none_by_default(self):
        """Missing key returns None if no default specified."""
        result = get_config("nonexistent.key")
        assert result is None


class TestGetSecret:
    """Tests for get_secret function."""

    def test_env_variable_override(self):
        """Environment variable takes precedence."""
        with patch.dict(os.environ, {"BINANCE_API_KEY": "test_key_from_env"}):
            result = get_secret("binance.api_key")
            assert result == "test_key_from_env"

    def test_custom_env_variable_name(self):
        """Use explicit environment variable name."""
        with patch.dict(os.environ, {"MY_CUSTOM_VAR": "custom_value"}):
            result = get_secret("binance.api_key", env_override="MY_CUSTOM_VAR")
            assert result == "custom_value"

    def test_missing_secret_returns_none(self):
        """Missing secret returns None."""
        # Ensure env var is not set
        env_key = "NONEXISTENT_SECRET_KEY"
        if env_key in os.environ:
            del os.environ[env_key]

        result = get_secret("nonexistent.secret.key")
        assert result is None


class TestConvenienceAccessors:
    """Tests for convenience accessor functions."""

    def test_get_schema_version(self):
        """Get schema version."""
        version = get_schema_version()
        assert version == "1.0.0"

    def test_get_binance_config(self):
        """Get Binance configuration."""
        config = get_binance_config()
        assert "ws_url" in config
        assert "rest_url" in config
        assert "http_timeout_s" in config
        assert config["http_timeout_s"] == 30

    def test_get_provider_defaults(self):
        """Get provider default settings."""
        defaults = get_provider_defaults()
        assert defaults["rate_limit_per_second"] == 10
        assert defaults["reconnect_attempts"] == 5
        assert defaults["reconnect_delay_ms"] == 1000

    def test_get_reliability_config(self):
        """Get reliability configuration."""
        config = get_reliability_config()
        assert config["max_attempts"] == 5
        assert config["base_delay_ms"] == 1000
        assert config["max_delay_ms"] == 60000
        assert config["failure_threshold"] == 5
        assert config["recovery_timeout_s"] == 60.0

    def test_get_storage_defaults(self):
        """Get storage default settings."""
        defaults = get_storage_defaults()
        assert defaults["batch_size"] == 100
        assert defaults["flush_interval_ms"] == 5000

    def test_get_validation_config(self):
        """Get validation configuration."""
        config = get_validation_config()
        assert config["min_timestamp_ms"] == 1577836800000  # 2020-01-01
        assert config["max_timestamp_ms"] == 4102444800000  # 2100-01-01

    def test_get_normalization_config(self):
        """Get normalization configuration."""
        config = get_normalization_config()
        assert "quote_currencies" in config
        assert "USDT" in config["quote_currencies"]
        assert "USD" in config["quote_currencies"]


class TestReloadConfig:
    """Tests for reload_config function."""

    def test_reload_returns_config(self):
        """Reload returns configuration."""
        config = reload_config()
        assert "schema_version" in config
        assert "binance" in config
