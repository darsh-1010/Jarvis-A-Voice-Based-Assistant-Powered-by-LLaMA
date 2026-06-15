# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Unit tests for TelemetryStore."""
import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from jarvis.memory.telemetry import TelemetryStore, sanitize_for_storage


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Return a fresh temporary SQLite path for each test."""
    return str(tmp_path / "test_telemetry.db")


@pytest.fixture
def store(db_path: str) -> TelemetryStore:
    """Return an initialised TelemetryStore backed by a temp database."""
    return TelemetryStore(db_path)


# ── sanitize_for_storage ──────────────────────────────────────────────────────

def test_sanitize_strips_api_key_pattern():
    raw = "Error: api_key=sk-abcdef1234567890abcdef1234567890abcdef"
    result = sanitize_for_storage(raw)
    assert "sk-" not in result
    assert "[REDACTED]" in result


def test_sanitize_strips_bearer_token():
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    result = sanitize_for_storage(raw)
    assert "eyJ" not in result


def test_sanitize_truncates_long_strings():
    raw = "x" * 5000
    result = sanitize_for_storage(raw)
    assert len(result) == 2000


def test_sanitize_leaves_clean_strings_unchanged():
    raw = "ConnectionError: No active device found."
    result = sanitize_for_storage(raw)
    assert result == raw


# ── record_success ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_success_inserts_row(store: TelemetryStore):
    await store.record_success("spotify_play", 120.5, provider="gemini")
    stats = await store.get_failure_stats()
    tool_stats = next((s for s in stats if s["tool_name"] == "spotify_play"), None)
    assert tool_stats is not None
    assert tool_stats["total"] == 1
    assert tool_stats["failures"] == 0


# ── record_failure ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_failure_inserts_row(store: TelemetryStore):
    trace = await store.record_failure(
        "spotify_play", 300.0, "SpotifyException", "No active device."
    )
    assert trace is not None
    assert trace.tool_name == "spotify_play"
    assert trace.success is False
    assert trace.error_class == "SpotifyException"


@pytest.mark.asyncio
async def test_record_failure_sanitizes_secrets_before_write(
    store: TelemetryStore,
):
    """Secret in the error_msg must not appear in the stored trace."""
    secret_msg = "api_key=sk-verysecretkey1234567890123456789012"
    await store.record_failure("get_weather", 50.0, "AuthError", secret_msg)
    trace = await store.get_last_failure("get_weather")
    assert trace is not None
    assert "sk-" not in trace.error_msg
    assert "[REDACTED]" in trace.error_msg


# ── get_last_failure ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_last_failure_returns_most_recent(store: TelemetryStore):
    await store.record_failure("finance", 10.0, "ValueError", "first")
    await store.record_failure("finance", 20.0, "TypeError", "second")
    trace = await store.get_last_failure("finance")
    assert trace is not None
    assert trace.error_class == "TypeError"


@pytest.mark.asyncio
async def test_get_last_failure_returns_none_for_unknown_tool(
    store: TelemetryStore,
):
    result = await store.get_last_failure("nonexistent_tool")
    assert result is None


# ── get_failure_stats ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_failure_stats_aggregation(store: TelemetryStore):
    await store.record_success("weather", 100.0)
    await store.record_failure("weather", 200.0, "HTTPError", "timeout")
    await store.record_failure("weather", 150.0, "HTTPError", "timeout")
    stats = await store.get_failure_stats()
    weather = next((s for s in stats if s["tool_name"] == "weather"), None)
    assert weather is not None
    assert weather["total"] == 3
    assert weather["failures"] == 2


# ── patch_log ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_and_retrieve_patch(store: TelemetryStore, tmp_path: Path):
    backup = str(tmp_path / "backup.py.bak")
    await store.record_patch(
        tool_name="spotify_play",
        target_file="/commands/productivity.py",
        patch_content="def spotify_play(): pass",
        lines_changed=3,
        guardrail_result={"l1": "pass", "l2": "pass"},
        backup_path=backup,
    )
    patches = await store.get_all_patches()
    assert len(patches) == 1
    assert patches[0]["tool_name"] == "spotify_play"
    assert patches[0]["lines_changed"] == 3


@pytest.mark.asyncio
async def test_get_patch_backup_path_returns_correct_path(
    store: TelemetryStore, tmp_path: Path
):
    backup = str(tmp_path / "my_backup.py.bak")
    await store.record_patch(
        "weather", "/commands/weather.py", "content", 1, {}, backup
    )
    patches = await store.get_all_patches()
    patch_id = patches[0]["id"]
    result = await store.get_patch_backup_path(patch_id)
    assert result == backup
