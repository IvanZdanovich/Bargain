"""Configuration loading and management.

Provides centralized access to configuration constants loaded from YAML files.
Supports environment variable overrides for sensitive values.

Usage:
    from src.config import get_config, get_secret

    # Access config values
    ws_url = get_config("binance.ws_url")
    rate_limit = get_config("provider_defaults.rate_limit_per_second")

    # Access secrets (from secrets.yaml or environment)
    api_key = get_secret("binance.api_key")
"""

import os
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

# === Configuration Type Definitions ===


class BinanceConfigData(TypedDict):
    """Binance provider configuration."""

    ws_url: str
    ws_url_testnet: str
    rest_url: str
    rest_url_testnet: str
    futures_ws_url: str
    futures_rest_url: str
    http_timeout_s: int
    ws_heartbeat_s: int
    ws_receive_timeout_s: int
    ping_interval_s: int
    rate_limit_retry_default_s: int


class ProviderDefaultsData(TypedDict):
    """Default provider settings."""

    rate_limit_per_second: int
    reconnect_attempts: int
    reconnect_delay_ms: int


class ReliabilityConfigData(TypedDict):
    """Reliability/retry configuration."""

    max_attempts: int
    base_delay_ms: int
    max_delay_ms: int
    failure_threshold: int
    recovery_timeout_s: float


class StorageConfigDefaultsData(TypedDict):
    """Storage default settings."""

    batch_size: int
    flush_interval_ms: int


class ValidationConfigData(TypedDict):
    """Data validation configuration."""

    min_timestamp_ms: int
    max_timestamp_ms: int


class NormalizationConfigData(TypedDict):
    """Symbol normalization configuration."""

    quote_currencies: list[str]


class AppConfigData(TypedDict):
    """Full application configuration."""

    schema_version: str
    binance: BinanceConfigData
    provider_defaults: ProviderDefaultsData
    reliability: ReliabilityConfigData
    storage: StorageConfigDefaultsData
    validation: ValidationConfigData
    normalization: NormalizationConfigData


# === Module State ===

_config: AppConfigData | None = None
_secrets: dict[str, Any] | None = None
_config_dir: Path = Path(__file__).parent.parent / "configs"


def _load_yaml(file_path: Path) -> dict[str, Any]:
    """
    Load YAML file.

    Args:
        file_path: Path to YAML file.

    Returns:
        Parsed YAML content.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    with open(file_path) as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: Path | None = None) -> AppConfigData:
    """
    Load application configuration from YAML file.

    Args:
        config_path: Optional path to config file. Defaults to configs/default.yaml.

    Returns:
        Loaded configuration dictionary.

    Side effects: Caches configuration in module state.
    """
    global _config

    if config_path is None:
        config_path = _config_dir / "default.yaml"

    _config = cast(AppConfigData, _load_yaml(config_path))
    return _config


def load_secrets(secrets_path: Path | None = None) -> dict[str, Any]:
    """
    Load secrets from YAML file.

    Args:
        secrets_path: Optional path to secrets file. Defaults to configs/secrets.yaml.

    Returns:
        Loaded secrets dictionary.

    Side effects: Caches secrets in module state.
    """
    global _secrets

    if secrets_path is None:
        secrets_path = _config_dir / "secrets.yaml"

    _secrets = _load_yaml(secrets_path) if secrets_path.exists() else {}

    return _secrets


def get_config(key: str, default: Any = None) -> Any:
    """
    Get configuration value by dot-notation key.

    Args:
        key: Dot-notation key (e.g., "binance.ws_url").
        default: Default value if key not found.

    Returns:
        Configuration value.

    Example:
        ws_url = get_config("binance.ws_url")
        timeout = get_config("binance.http_timeout_s", 30)
    """
    global _config

    if _config is None:
        load_config()

    value: Any = _config
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default

    return value


def get_secret(key: str, env_override: str | None = None) -> str | None:
    """
    Get secret value, with environment variable override.

    Environment variables take precedence over secrets.yaml.
    Environment variable names are derived from key by converting
    dots to underscores and uppercasing (e.g., "binance.api_key" -> "BINANCE_API_KEY").

    Args:
        key: Dot-notation key (e.g., "binance.api_key").
        env_override: Optional explicit environment variable name.

    Returns:
        Secret value or None if not found.

    Example:
        api_key = get_secret("binance.api_key")
        # Checks BINANCE_API_KEY env var first, then secrets.yaml
    """
    global _secrets

    # Check environment variable first
    if env_override:
        env_value = os.environ.get(env_override)
    else:
        env_key = key.replace(".", "_").upper()
        env_value = os.environ.get(env_key)

    if env_value:
        return env_value

    # Fall back to secrets file
    if _secrets is None:
        load_secrets()

    value: Any = _secrets
    for part in key.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None

    return value if isinstance(value, str) else None


def get_full_config() -> AppConfigData:
    """
    Get full configuration dictionary.

    Returns:
        Complete configuration.
    """
    global _config

    if _config is None:
        load_config()

    assert _config is not None, "Configuration failed to load"
    return _config


def reload_config() -> AppConfigData:
    """
    Reload configuration from disk.

    Returns:
        Reloaded configuration.

    Side effects: Clears and reloads config cache.
    """
    global _config, _secrets
    _config = None
    _secrets = None
    return load_config()


# === Convenience Accessors ===


def get_binance_config() -> BinanceConfigData:
    """Get Binance-specific configuration."""
    return get_config("binance")  # type: ignore


def get_provider_defaults() -> ProviderDefaultsData:
    """Get provider default settings."""
    return get_config("provider_defaults")  # type: ignore


def get_reliability_config() -> ReliabilityConfigData:
    """Get reliability/retry configuration."""
    return get_config("reliability")  # type: ignore


def get_storage_defaults() -> StorageConfigDefaultsData:
    """Get storage default settings."""
    return get_config("storage")  # type: ignore


def get_validation_config() -> ValidationConfigData:
    """Get data validation configuration."""
    return get_config("validation")  # type: ignore


def get_normalization_config() -> NormalizationConfigData:
    """Get symbol normalization configuration."""
    return get_config("normalization")  # type: ignore


def get_schema_version() -> str:
    """Get current schema version."""
    return get_config("schema_version", "1.0.0")  # type: ignore
