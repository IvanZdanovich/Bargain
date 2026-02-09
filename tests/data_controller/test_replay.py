"""Unit tests for replay functionality."""

from pathlib import Path

import pytest

from src.data_controller.replay import (create_replay_recorder, record_event,
                                        replay_from_file, replay_from_records,
                                        start_recording, stop_recording)
from src.types import HandlersData

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestReplayFromFile:
    """Tests for replay_from_file function."""

    @pytest.mark.asyncio
    async def test_replay_all_events(self):
        """Replay all events from file."""
        file_path = FIXTURES_DIR / "sample_messages.jsonl"
        trades = []
        candles = []

        handlers = HandlersData(
            on_trade=lambda d: trades.append(d),
            on_candle=lambda d: candles.append(d),
        )

        stats = await replay_from_file(
            file_path,
            handlers,
            speed_multiplier=0,  # Instant replay
        )

        assert stats["trades"] == 4
        assert stats["candles"] == 2

    @pytest.mark.asyncio
    async def test_replay_with_time_filter(self):
        """Replay with start/end time filters."""
        file_path = FIXTURES_DIR / "sample_messages.jsonl"
        trades = []

        handlers = HandlersData(
            on_trade=lambda d: trades.append(d),
        )

        stats = await replay_from_file(
            file_path,
            handlers,
            speed_multiplier=0,
            start_time_ms=1704067200050,
            end_time_ms=1704067260100,
        )

        # Should skip first trade and last candle
        assert stats["trades"] >= 1
        assert stats["skipped"] >= 1


class TestReplayFromRecords:
    """Tests for replay_from_records function."""

    @pytest.mark.asyncio
    async def test_replay_in_memory(self):
        """Replay from in-memory records."""
        records = [
            {
                "type": "trade",
                "timestamp_ms": 1000,
                "data": {"price": 100},
            },
            {
                "type": "trade",
                "timestamp_ms": 2000,
                "data": {"price": 101},
            },
            {
                "type": "candle",
                "timestamp_ms": 3000,
                "data": {"close": 102},
            },
        ]

        trades = []
        candles = []

        handlers = HandlersData(
            on_trade=lambda d: trades.append(d),
            on_candle=lambda d: candles.append(d),
        )

        stats = await replay_from_records(records, handlers, speed_multiplier=0)

        assert stats["trades"] == 2
        assert stats["candles"] == 1
        assert stats["total"] == 3


class TestReplayRecorder:
    """Tests for replay recorder functions."""

    def test_create_recorder(self):
        """Create empty recorder."""
        recorder = create_replay_recorder()

        assert recorder["records"] == []
        assert recorder["recording"] is False
        assert recorder["start_time_ms"] is None

    def test_start_recording(self):
        """Start recording sets flag and timestamp."""
        recorder = create_replay_recorder()

        start_recording(recorder)

        assert recorder["recording"] is True
        assert recorder["start_time_ms"] is not None

    def test_record_event_when_active(self):
        """Record event when recording is active."""
        recorder = create_replay_recorder()
        start_recording(recorder)

        record_event(recorder, "trade", {"price": 100}, 1000)
        record_event(recorder, "candle", {"close": 101}, 2000)

        assert len(recorder["records"]) == 2
        assert recorder["records"][0]["type"] == "trade"
        assert recorder["records"][1]["type"] == "candle"

    def test_record_event_when_inactive(self):
        """Do not record when recording is inactive."""
        recorder = create_replay_recorder()

        record_event(recorder, "trade", {"price": 100}, 1000)

        assert len(recorder["records"]) == 0

    def test_stop_recording(self):
        """Stop recording and return records."""
        recorder = create_replay_recorder()
        start_recording(recorder)

        record_event(recorder, "trade", {"price": 100}, 1000)

        records = stop_recording(recorder)

        assert recorder["recording"] is False
        assert len(records) == 1
        assert records[0]["type"] == "trade"

    def test_start_clears_previous(self):
        """Starting recording clears previous records."""
        recorder = create_replay_recorder()

        start_recording(recorder)
        record_event(recorder, "trade", {"price": 100}, 1000)
        stop_recording(recorder)

        start_recording(recorder)

        assert len(recorder["records"]) == 0
