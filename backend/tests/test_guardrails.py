# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Unit tests for the 5-layer GuardrailEngine."""
import asyncio
import os
import textwrap
from pathlib import Path

import pytest

from jarvis.security.guardrails import (
    AstSafetyGuard,
    GuardrailEngine,
    GuardrailViolation,
    NoGoZoneGuard,
    PatchRequest,
    _COMMANDS_DIR,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_store(tmp_path: Path, mocker):
    """Return a mocked TelemetryStore that passes rate-limit checks."""
    store = mocker.MagicMock()
    store.get_patch_count = mocker.AsyncMock(return_value=0)
    store.get_last_patch_time = mocker.AsyncMock(return_value=0.0)
    store.record_patch = mocker.AsyncMock()
    return store


@pytest.fixture
def engine(mock_store):
    """Return a GuardrailEngine backed by the mock store."""
    return GuardrailEngine(mock_store)


@pytest.fixture
def clean_command_file(tmp_path: Path, mocker) -> Path:
    """
    Create a real .py file inside _COMMANDS_DIR (or a temp subdir that
    is_relative_to succeeds for) so Layer 1 passes in integration tests.
    Uses monkeypatch to redirect _COMMANDS_DIR to tmp_path.
    """
    target = tmp_path / "weather.py"
    target.write_text("# weather stub\n", encoding="utf-8")
    mocker.patch(
        "jarvis.security.guardrails._COMMANDS_DIR",
        tmp_path.resolve(),
    )
    return target


# ── Layer 1: NoGoZoneGuard ────────────────────────────────────────────────────

def test_no_go_zone_blocks_brain_py(tmp_path: Path):
    """Attempting to patch brain.py must raise GuardrailViolation."""
    brain_path = tmp_path / "brain.py"
    brain_path.touch()
    with pytest.raises(GuardrailViolation, match="no-go zone"):
        NoGoZoneGuard.validate(brain_path)


def test_no_go_zone_blocks_env_file(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.touch()
    with pytest.raises(GuardrailViolation):
        NoGoZoneGuard.validate(env_path)


def test_no_go_zone_blocks_guardrails_itself(tmp_path: Path):
    guard_path = tmp_path / "guardrails.py"
    guard_path.touch()
    with pytest.raises(GuardrailViolation, match="no-go zone"):
        NoGoZoneGuard.validate(guard_path)


def test_no_go_zone_blocks_path_outside_commands(tmp_path: Path, mocker):
    """A path outside the commands/ directory must be rejected even without filename match."""
    mocker.patch(
        "jarvis.security.guardrails._COMMANDS_DIR",
        (tmp_path / "commands").resolve(),
    )
    outside = (tmp_path / "other" / "weather.py").resolve()
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.touch()
    with pytest.raises(GuardrailViolation, match="outside the patchable"):
        NoGoZoneGuard.validate(outside)


# ── Layer 2: AstSafetyGuard ───────────────────────────────────────────────────

def test_ast_blocks_eval():
    with pytest.raises(GuardrailViolation, match="eval"):
        AstSafetyGuard.validate("result = eval(user_input)")


def test_ast_blocks_exec():
    with pytest.raises(GuardrailViolation, match="exec"):
        AstSafetyGuard.validate("exec('import os')")


def test_ast_blocks_os_import():
    with pytest.raises(GuardrailViolation, match="import os"):
        AstSafetyGuard.validate("import os\nos.system('ls')")


def test_ast_blocks_subprocess_import():
    with pytest.raises(GuardrailViolation, match="subprocess"):
        AstSafetyGuard.validate(
            "import subprocess\nsubprocess.run(['ls'])"
        )


def test_ast_blocks_shell_true():
    code = textwrap.dedent("""\
        import subprocess
        subprocess.run('ls', shell=True)
    """)
    with pytest.raises(GuardrailViolation):
        AstSafetyGuard.validate(code)


def test_ast_rejects_invalid_syntax():
    with pytest.raises(GuardrailViolation, match="syntax"):
        AstSafetyGuard.validate("def broken(: pass")


def test_ast_passes_clean_code():
    """Clean, compliant code must not raise."""
    clean = textwrap.dedent("""\
        import logging
        from jarvis.logger import log_action

        def get_weather(city: str = "Mumbai") -> str:
            log_action("WEATHER", f"City: {city}", "Fetching weather.")
            return f"Weather for {city}: Sunny, 30°C."
    """)
    AstSafetyGuard.validate(clean)  # Should not raise


# ── Layer 3: Rate Limiter ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_cap(mock_store, mocker):
    """When patch count reaches the daily cap, Layer 3 must block."""
    mock_store.get_patch_count = mocker.AsyncMock(return_value=3)
    engine = GuardrailEngine(mock_store)
    result = await engine.validate_and_apply(
        PatchRequest(
            tool_name="spotify_play",
            target_file=str(_COMMANDS_DIR / "productivity.py"),
            patch_content="# clean",
            backup_dir="/tmp",
            optimization_summary="test",
        )
    )
    assert not result.passed
    assert result.failed_layer == "L3"


@pytest.mark.asyncio
async def test_rate_limiter_blocks_within_cooldown(mock_store, mocker):
    """If last patch was < 3600s ago, Layer 3 must block."""
    import time
    mock_store.get_patch_count = mocker.AsyncMock(return_value=0)
    mock_store.get_last_patch_time = mocker.AsyncMock(
        return_value=time.time() - 10  # only 10 seconds ago
    )
    engine = GuardrailEngine(mock_store)
    result = await engine.validate_and_apply(
        PatchRequest(
            tool_name="spotify_play",
            target_file=str(_COMMANDS_DIR / "productivity.py"),
            patch_content="# clean",
            backup_dir="/tmp",
            optimization_summary="test",
        )
    )
    assert not result.passed
    assert result.failed_layer == "L3"


# ── Full Pipeline ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_valid_patch_passes(
    engine: GuardrailEngine,
    clean_command_file: Path,
    tmp_path: Path,
    mocker,
):
    """A clean patch to a valid command file must pass all 5 layers."""
    mocker.patch(
        "jarvis.security.guardrails.PatchAuditLogger.log",
        return_value=None,
    )
    clean_patch = textwrap.dedent("""\
        # Copyright (c) 2024-2026 Darsh Shah
        import logging
        from jarvis.commands.registry import registry
        from jarvis.logger import log_action

        @registry.register(name="get_weather", description="Get weather.")
        def get_weather(city: str = "Mumbai") -> str:
            log_action("WEATHER", f"City: {city}", "Fetching.")
            return f"Weather OK for {city}."
    """)
    result = await engine.validate_and_apply(
        PatchRequest(
            tool_name="get_weather",
            target_file=str(clean_command_file),
            patch_content=clean_patch,
            backup_dir=str(tmp_path / "backups"),
            optimization_summary="Improved weather error handling.",
        )
    )
    assert result.passed
    assert result.lines_changed >= 0
    assert result.layer_results.get("l1") == "pass"
    assert result.layer_results.get("l2") == "pass"
    assert result.layer_results.get("l4") == "pass"


@pytest.mark.asyncio
async def test_full_pipeline_bad_syntax_restores_backup(
    engine: GuardrailEngine,
    clean_command_file: Path,
    tmp_path: Path,
    mocker,
):
    """A patch with a syntax error must fail at Layer 4 and restore the backup."""
    mocker.patch(
        "jarvis.security.guardrails.AstSafetyGuard.validate",
        return_value=None,
    )
    original_content = clean_command_file.read_text(encoding="utf-8")
    result = await engine.validate_and_apply(
        PatchRequest(
            tool_name="get_weather",
            target_file=str(clean_command_file),
            patch_content="def broken(: pass",   # invalid syntax
            backup_dir=str(tmp_path / "backups"),
            optimization_summary="bad patch",
        )
    )
    assert not result.passed
    assert result.failed_layer == "L4"
    # File must have been restored to original content
    assert clean_command_file.read_text(encoding="utf-8") == original_content
