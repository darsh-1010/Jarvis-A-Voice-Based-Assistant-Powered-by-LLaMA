# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""SQLite WAL-backed telemetry store for Jarvis task execution traces and patch history."""

import asyncio
import hashlib
import json
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from jarvis.logger import log_action


# Patterns that indicate secrets — matched case-insensitively against error strings.
# We redact anything that looks like an API key, token, or password before storage.
_SECRET_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(token\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(password\s*[:=]\s*)\S+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)\S+"),
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Google API key pattern
    re.compile(r"sk-[A-Za-z0-9]{32,}"),  # OpenAI key pattern
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
)

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS task_traces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT    NOT NULL,
    tool_name   TEXT    NOT NULL,
    command_raw TEXT,
    success     INTEGER NOT NULL,
    duration_ms REAL,
    error_class TEXT,
    error_msg   TEXT,
    provider    TEXT,
    token_count INTEGER,
    created_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tool_ts ON task_traces(tool_name, created_at);

CREATE TABLE IF NOT EXISTS patch_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name        TEXT    NOT NULL,
    target_file      TEXT    NOT NULL,
    patch_hash       TEXT    NOT NULL,
    lines_changed    INTEGER,
    guardrail_result TEXT,
    backup_path      TEXT,
    applied_at       REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_patch_tool ON patch_log(tool_name, applied_at);
"""


@dataclass
class TaskTrace:
    """Immutable snapshot of a single tool-invocation trace."""

    task_id: str
    tool_name: str
    success: bool
    duration_ms: float
    command_raw: str = ""
    error_class: str = ""
    error_msg: str = ""
    provider: str = ""
    token_count: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class PatchRecord:
    """One row from the patch_log table."""

    patch_id: int
    tool_name: str
    target_file: str
    patch_hash: str
    lines_changed: int
    guardrail_result: dict
    backup_path: str
    applied_at: float


def sanitize_for_storage(raw: str) -> str:
    """
    Strip secrets and PII from an error string before persisting.

    Applies each compiled secret pattern as a substitution, replacing the
    sensitive value with a fixed placeholder. Truncates to 2000 chars to
    avoid storing excessively large LLM outputs.

    Args:
        raw: The raw error or message string to sanitize.

    Returns:
        Sanitized string safe for database storage.
    """
    sanitized = raw
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(r"[REDACTED]", sanitized)
    return sanitized[:2000]


class TelemetryStore:
    """
    SQLite WAL-backed store for task execution traces and patch history.

    All I/O is wrapped in asyncio.to_thread() so the event loop is never
    blocked. The WAL journal mode allows concurrent readers during writes.
    """

    def __init__(self, db_path: str) -> None:
        """
        Initialize TelemetryStore and ensure schema is created.

        Args:
            db_path: Absolute or relative path to the SQLite file.
        """
        resolved = Path(db_path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(resolved)
        self._init_schema()
        log_action(
            "TELEMETRY_INIT",
            f"DB: {self._db_path}",
            "Task telemetry store ready.",
        )

    def _connect(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection in WAL mode."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._connect() as conn:
            conn.executescript(_DDL)

    # ── Synchronous write helpers (called via to_thread) ──────────────────

    def _write_trace(self, trace: TaskTrace) -> None:
        """Insert one TaskTrace row synchronously."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO task_traces
                   (task_id, tool_name, command_raw, success, duration_ms,
                    error_class, error_msg, provider, token_count, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    trace.task_id,
                    trace.tool_name,
                    trace.command_raw,
                    int(trace.success),
                    trace.duration_ms,
                    trace.error_class,
                    sanitize_for_storage(trace.error_msg),
                    trace.provider,
                    trace.token_count,
                    trace.created_at,
                ),
            )

    def _write_patch(
        self,
        tool_name: str,
        target_file: str,
        patch_content: str,
        lines_changed: int,
        guardrail_result: dict,
        backup_path: str,
    ) -> None:
        """Insert one patch_log row synchronously."""
        patch_hash = hashlib.sha256(patch_content.encode()).hexdigest()[:16]
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO patch_log
                   (tool_name, target_file, patch_hash, lines_changed,
                    guardrail_result, backup_path, applied_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    tool_name,
                    target_file,
                    patch_hash,
                    lines_changed,
                    json.dumps(guardrail_result),
                    backup_path,
                    time.time(),
                ),
            )

    def _query_failure_count(self, tool_name: str, window_seconds: float) -> int:
        """Return the number of failures for a tool within the time window."""
        cutoff = time.time() - window_seconds
        with self._connect() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM task_traces
                   WHERE tool_name=? AND success=0 AND created_at>=?""",
                (tool_name, cutoff),
            ).fetchone()
        return int(row[0]) if row else 0

    def _query_last_failure(self, tool_name: str) -> Optional[TaskTrace]:
        """Return the most recent failure trace for a tool, or None."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM task_traces
                   WHERE tool_name=? AND success=0
                   ORDER BY created_at DESC LIMIT 1""",
                (tool_name,),
            ).fetchone()
        if not row:
            return None
        return TaskTrace(
            task_id=row["task_id"],
            tool_name=row["tool_name"],
            success=False,
            duration_ms=row["duration_ms"] or 0.0,
            command_raw=row["command_raw"] or "",
            error_class=row["error_class"] or "",
            error_msg=row["error_msg"] or "",
            provider=row["provider"] or "",
            token_count=row["token_count"] or 0,
            created_at=row["created_at"],
        )

    def _query_failure_stats(self) -> List[dict]:
        """Return per-tool aggregated failure stats for all recorded tools."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT tool_name,
                          COUNT(*) AS total,
                          SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) AS failures,
                          AVG(duration_ms) AS avg_ms
                   FROM task_traces
                   GROUP BY tool_name
                   ORDER BY failures DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def _query_patch_count(self, tool_name: str, window_seconds: float) -> int:
        """Return how many patches were applied to a tool within the window."""
        cutoff = time.time() - window_seconds
        with self._connect() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM patch_log
                   WHERE tool_name=? AND applied_at>=?""",
                (tool_name, cutoff),
            ).fetchone()
        return int(row[0]) if row else 0

    def _query_last_patch_time(self, tool_name: str) -> float:
        """Return Unix timestamp of the most recent patch for a tool, or 0."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT MAX(applied_at) FROM patch_log WHERE tool_name=?""",
                (tool_name,),
            ).fetchone()
        return float(row[0]) if row and row[0] else 0.0

    def _query_all_patches(self) -> List[dict]:
        """Return full patch audit log, most recent first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM patch_log ORDER BY applied_at DESC"
            ).fetchall()
        result = []
        for row in rows:
            entry = dict(row)
            try:
                entry["guardrail_result"] = json.loads(
                    entry.get("guardrail_result") or "{}"
                )
            except json.JSONDecodeError:
                entry["guardrail_result"] = {}
            result.append(entry)
        return result

    def _query_patch_backup(self, patch_id: int) -> Optional[str]:
        """Return the backup_path for a given patch_id, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT backup_path FROM patch_log WHERE id=?", (patch_id,)
            ).fetchone()
        return str(row["backup_path"]) if row and row["backup_path"] else None

    # ── Async public API ──────────────────────────────────────────────────

    async def record_success(
        self,
        tool_name: str,
        duration_ms: float,
        provider: str = "",
        token_count: int = 0,
        command_raw: str = "",
    ) -> None:
        """Record a successful tool invocation asynchronously."""
        trace = TaskTrace(
            task_id=uuid.uuid4().hex[:8],
            tool_name=tool_name,
            success=True,
            duration_ms=duration_ms,
            command_raw=command_raw,
            provider=provider,
            token_count=token_count,
        )
        await asyncio.to_thread(self._write_trace, trace)

    async def record_failure(
        self,
        tool_name: str,
        duration_ms: float,
        error_class: str,
        error_msg: str,
        command_raw: str = "",
    ) -> TaskTrace:
        """
        Record a failed tool invocation asynchronously.

        Returns:
            The TaskTrace that was persisted (used by ReflectionEngine).
        """
        trace = TaskTrace(
            task_id=uuid.uuid4().hex[:8],
            tool_name=tool_name,
            success=False,
            duration_ms=duration_ms,
            command_raw=command_raw,
            error_class=error_class,
            error_msg=error_msg,
        )
        await asyncio.to_thread(self._write_trace, trace)
        log_action(
            "TELEMETRY_FAILURE",
            f"Tool: {tool_name} | Error: {error_class} | Dur: {duration_ms:.0f}ms",
            f"Recorded failure for {tool_name} — triggering self-analysis.",
        )
        return trace

    async def record_patch(
        self,
        tool_name: str,
        target_file: str,
        patch_content: str,
        lines_changed: int,
        guardrail_result: dict,
        backup_path: str,
    ) -> None:
        """Record an applied code patch asynchronously."""
        await asyncio.to_thread(
            self._write_patch,
            tool_name,
            target_file,
            patch_content,
            lines_changed,
            guardrail_result,
            backup_path,
        )

    async def get_last_failure(self, tool_name: str) -> Optional[TaskTrace]:
        """Return the most recent failure trace for a tool."""
        return await asyncio.to_thread(self._query_last_failure, tool_name)

    async def get_failure_stats(self) -> List[dict]:
        """Return per-tool aggregated stats for the /memory/stats endpoint."""
        return await asyncio.to_thread(self._query_failure_stats)

    async def get_patch_count(self, tool_name: str, window_seconds: float) -> int:
        """Return how many patches were applied within the given time window."""
        return await asyncio.to_thread(
            self._query_patch_count, tool_name, window_seconds
        )

    async def get_last_patch_time(self, tool_name: str) -> float:
        """Return the Unix timestamp of the last patch for a tool."""
        return await asyncio.to_thread(self._query_last_patch_time, tool_name)

    async def get_all_patches(self) -> List[dict]:
        """Return the full patch audit log."""
        return await asyncio.to_thread(self._query_all_patches)

    async def get_patch_backup_path(self, patch_id: int) -> Optional[str]:
        """Return the backup file path for a given patch ID."""
        return await asyncio.to_thread(self._query_patch_backup, patch_id)
