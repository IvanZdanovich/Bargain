"""
Advanced Data Preparation subsystem.

Transforms raw market data into enriched, multi-timeframe, feature-rich series
for strategy execution.

Key components:
- Resampling: Tick-to-candle conversion
- Indicators: EMA, SMA, ATR, VWAP, etc.
- Transforms: Heiken Ashi, returns, normalization
- Rolling: Efficient window statistics
- Pipelines: Multi-timeframe orchestration
- State: Streaming state management
"""

from src.advanced_prep.indicators import (
    ATRState,
    EMAState,
    compute_atr_batch,
    compute_ema,
    compute_log_return,
    compute_percentage_change,
    compute_rolling_volatility,
    compute_sma,
    compute_true_range,
    compute_vwap_batch,
    compute_wma,
    init_atr_state,
    init_ema_state,
    update_atr_streaming,
    update_ema_streaming,
)
from src.advanced_prep.pipelines import (
    MultiTimeframePipeline,
    PipelineConfig,
    create_pipeline,
)
from src.advanced_prep.registry import (
    IndicatorMetadata,
    IndicatorRegistry,
    get_global_registry,
    register_default_indicators,
    register_indicator,
)
from src.advanced_prep.resampling import (
    CandleResampler,
    format_timeframe,
    parse_timeframe_to_ms,
)
from src.advanced_prep.rolling import (
    RollingWindow,
    compute_rolling_mean,
    compute_rolling_std,
    compute_z_score,
)
from src.advanced_prep.state import (
    IndicatorStates,
    StreamingState,
    TimeframeState,
    create_streaming_state,
    get_indicator_values,
    init_indicator_states,
)
from src.advanced_prep.transforms import (
    compute_candle_body_size,
    compute_candle_range,
    compute_candle_wick_sizes,
    compute_heiken_ashi,
    compute_log_returns_series,
    compute_percentage_returns_series,
    compute_pivot_point,
    compute_support_resistance,
    compute_typical_price,
    is_bearish_candle,
    is_bullish_candle,
    normalize_min_max,
    normalize_z_score,
)
from src.advanced_prep.utils import (
    batch_to_chunks,
    clamp,
    format_decimal,
    is_close,
    round_to_precision,
    safe_divide,
    timestamp_to_candle_open,
    timestamps_aligned,
    validate_non_negative,
    validate_positive,
)

__all__ = [
    # Pipelines
    "MultiTimeframePipeline",
    "PipelineConfig",
    "create_pipeline",
    # Resampling
    "CandleResampler",
    "parse_timeframe_to_ms",
    "format_timeframe",
    # Indicators
    "compute_sma",
    "compute_ema",
    "compute_wma",
    "compute_vwap_batch",
    "compute_atr_batch",
    "compute_true_range",
    "compute_rolling_volatility",
    "compute_percentage_change",
    "compute_log_return",
    "EMAState",
    "ATRState",
    "init_ema_state",
    "init_atr_state",
    "update_ema_streaming",
    "update_atr_streaming",
    # Transforms
    "compute_heiken_ashi",
    "compute_log_returns_series",
    "compute_percentage_returns_series",
    "normalize_min_max",
    "normalize_z_score",
    "compute_typical_price",
    "compute_pivot_point",
    "compute_support_resistance",
    "is_bullish_candle",
    "is_bearish_candle",
    "compute_candle_body_size",
    "compute_candle_wick_sizes",
    "compute_candle_range",
    # Rolling
    "RollingWindow",
    "compute_rolling_mean",
    "compute_rolling_std",
    "compute_z_score",
    # State
    "StreamingState",
    "TimeframeState",
    "IndicatorStates",
    "create_streaming_state",
    "init_indicator_states",
    "get_indicator_values",
    # Registry
    "IndicatorRegistry",
    "IndicatorMetadata",
    "register_indicator",
    "register_default_indicators",
    "get_global_registry",
    # Utils
    "safe_divide",
    "clamp",
    "round_to_precision",
    "is_close",
    "validate_positive",
    "validate_non_negative",
    "format_decimal",
    "timestamp_to_candle_open",
    "timestamps_aligned",
    "batch_to_chunks",
]

