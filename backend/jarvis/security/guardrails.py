# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""
5-layer security guardrail pipeline for autonomous code patching.

This module is intentionally excluded from the self-improvement loop's
patchable scope — it cannot modify its own constraints.

Layers (in order):
  1. NoGoZoneGuard     — allowlist/denylist path enforcement
  2. AstSafetyGuard    — AST static analysis of generated Python
  3. PatchRateLimiter  — per-tool cooldown and daily cap
  4. AtomicPatcher     — backup → write → compile-verify → restore-on-fail
  5. PatchAuditLogger  — SQLite + CHANGELOG.md entry
"""

import ast
import logging
import os
import py_compile
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jarvis.logger import log_action


# ── Immutable security constants ──────────────────────────────────────────────
# Resolved at import time so they cannot be overwritten by a patched module.

# Only files inside this directory may be patched.
_COMMANDS_DIR: Path = (Path(__file__).parent.parent / "commands").resolve()

# Files that must never be touched, regardless of their location.
_NO_GO_FILENAMES: frozenset = frozenset(
    {
        "brain.py",
        "config.py",
        "intent.py",
        "logger.py",
        "audio.py",
        "settings_manager.py",
        "__init__.py",
        "registry.py",
        ".env",
        ".env.example",
        "requirements.txt",
        "requirements-dev.txt",
        "docker-compose.yml",
        "Dockerfile",
        "pylintrc",
        "pytest.ini",
        "guardrails.py",  # The guardrails cannot patch themselves
        "telemetry.py",  # Telemetry store must not be self-modified
        "reflection.py",  # Reflection engine must not be self-modified
    }
)

# AST node names that signal a dangerous import.
_FORBIDDEN_IMPORTS: frozenset = frozenset(
    {
        "os",
        "subprocess",
        "sys",
        "shutil",
        "socket",
        "ctypes",
        "pickle",
        "marshal",
        "importlib",
        "pathlib",
        "builtins",
        "threading",
        "multiprocessing",
        "runpy",
        "pty",
        "atexit",
        "signal",
    }
)

# Built-in function names the LLM must not call.
_FORBIDDEN_CALLS: frozenset = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "vars",
        "globals",
        "locals",
        "dir",
        "input",
    }
)


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class GuardrailResult:
    """Outcome of the full 5-layer guardrail pipeline."""

    passed: bool
    failed_layer: Optional[str] = None
    reason: str = ""
    backup_path: str = ""
    lines_changed: int = 0
    layer_results: dict = field(default_factory=dict)


@dataclass
class PatchRequest:
    """
    Bundles all parameters for a single autonomous patch attempt.

    Using a dataclass avoids the R0917 too-many-positional-arguments
    violation on validate_and_apply while keeping the call-site readable.
    """

    tool_name: str
    target_file: str
    patch_content: str
    backup_dir: str
    optimization_summary: str


class GuardrailViolation(Exception):
    """Raised internally when a layer detects a violation."""


# ── Layer 1: No-Go Zone Guard ─────────────────────────────────────────────────


class NoGoZoneGuard:
    """
    Enforces that patches only target files inside the commands directory
    and that the filename is not on the protected list.

    Uses pathlib.resolve() + is_relative_to() to prevent all path traversal
    attacks (e.g. ../../.env, symlink escapes).
    """

    @staticmethod
    def validate(target_path: Path) -> None:
        """
        Raise GuardrailViolation if the path violates any no-go rule.

        Args:
            target_path: The resolved absolute path of the file to patch.

        Raises:
            GuardrailViolation: If the path is protected or outside commands/.
        """
        resolved = target_path.resolve()

        # Rule 1: Filename must not be on the denylist
        if resolved.name in _NO_GO_FILENAMES:
            raise GuardrailViolation(
                f"[L1] '{resolved.name}' is in the no-go zone — patch rejected."
            )

        # Rule 2: Path must be inside the commands directory (anti-traversal)
        if not resolved.is_relative_to(_COMMANDS_DIR):
            raise GuardrailViolation(
                f"[L1] '{resolved}' is outside the patchable commands/ directory."
            )

        log_action(
            "GUARDRAIL_L1_PASS",
            f"Path: {resolved.name}",
            "No-go zone check passed.",
            level=logging.DEBUG,
        )


# ── Layer 2: AST Static Analysis ─────────────────────────────────────────────


class _ForbiddenNodeVisitor(ast.NodeVisitor):
    """AST visitor that raises on any forbidden import or function call."""

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """Block any import of a forbidden module."""
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in _FORBIDDEN_IMPORTS:
                raise GuardrailViolation(
                    f"[L2] Forbidden import detected: 'import {alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """Block 'from <forbidden> import ...' statements."""
        module_root = (node.module or "").split(".")[0]
        if module_root in _FORBIDDEN_IMPORTS:
            raise GuardrailViolation(
                f"[L2] Forbidden import detected: 'from {node.module} import ...'"
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Block calls to dangerous built-ins."""
        func_name = self._extract_call_name(node)
        if func_name in _FORBIDDEN_CALLS:
            raise GuardrailViolation(
                f"[L2] Forbidden function call detected: '{func_name}()'"
            )
        # Block shell=True in any keyword argument (subprocess injection)
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant):
                if kw.value.value is True:
                    raise GuardrailViolation(
                        "[L2] shell=True detected — command injection risk."
                    )
        self.generic_visit(node)

    @staticmethod
    def _extract_call_name(node: ast.Call) -> str:
        """Extract a best-effort string name from a Call node's func."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""


class AstSafetyGuard:
    """Parses the patch content and walks the AST for forbidden patterns."""

    @staticmethod
    def validate(patch_content: str) -> None:
        """
        Parse and statically analyse the patch content.

        Args:
            patch_content: Raw Python source code of the proposed patch.

        Raises:
            GuardrailViolation: If any forbidden construct is found.
            GuardrailViolation: If the code cannot be parsed at all.
        """
        try:
            tree = ast.parse(patch_content)
        except SyntaxError as exc:
            raise GuardrailViolation(
                f"[L2] Patch contains invalid Python syntax: {exc}"
            ) from exc

        _ForbiddenNodeVisitor().visit(tree)
        log_action(
            "GUARDRAIL_L2_PASS",
            "AST analysis clean",
            "Static code analysis passed.",
            level=logging.DEBUG,
        )


# ── Layer 3: Patch Rate Limiter ───────────────────────────────────────────────


class PatchRateLimiter:
    """
    Enforces a per-tool daily patch cap and minimum cooldown between patches.

    Queries the SQLite patch_log table via the shared TelemetryStore.
    Avoids circular imports by accepting the store as a constructor argument.
    """

    # Max patches per tool within a 24-hour window.
    _MAX_PATCHES_PER_DAY: int = 3
    # Minimum gap between consecutive patches to the same tool (seconds).
    _MIN_COOLDOWN_SECONDS: float = 3600.0  # 1 hour

    def __init__(self, telemetry_store) -> None:
        """
        Args:
            telemetry_store: An initialised TelemetryStore instance.
        """
        self._store = telemetry_store

    async def validate(self, tool_name: str) -> None:
        """
        Check daily cap and cooldown for the tool.

        Args:
            tool_name: The tool being patched.

        Raises:
            GuardrailViolation: If the cap or cooldown is exceeded.
        """
        window = 86400.0  # 24 hours in seconds
        patch_count = await self._store.get_patch_count(tool_name, window)
        if patch_count >= self._MAX_PATCHES_PER_DAY:
            raise GuardrailViolation(
                f"[L3] Daily patch cap ({self._MAX_PATCHES_PER_DAY}) reached "
                f"for '{tool_name}'."
            )

        last_patch_time = await self._store.get_last_patch_time(tool_name)
        elapsed = time.time() - last_patch_time
        if elapsed < self._MIN_COOLDOWN_SECONDS:
            remaining = int(self._MIN_COOLDOWN_SECONDS - elapsed)
            raise GuardrailViolation(
                f"[L3] Cooldown active for '{tool_name}' — {remaining}s remaining."
            )

        log_action(
            "GUARDRAIL_L3_PASS",
            f"Tool: {tool_name} | Patches today: {patch_count}",
            "Rate-limit check passed.",
            level=logging.DEBUG,
        )


# ── Layer 4: Atomic Patcher ───────────────────────────────────────────────────


class AtomicPatcher:
    """
    Safely applies a code patch using the write-rename pattern.

    Write order:
      1. Create a timestamped backup of the original file.
      2. Write patch to a sibling .tmp file.
      3. Compile .tmp with py_compile to catch syntax errors.
      4. os.replace(tmp, target) — atomic on POSIX and Windows NTFS.
      5. On any compile failure: restore from backup automatically.
    """

    def __init__(self, backup_dir: str) -> None:
        """
        Args:
            backup_dir: Directory where timestamped backups are written.
        """
        self._backup_dir = Path(backup_dir).resolve()
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def apply(self, target_path: Path, patch_content: str) -> tuple[str, int]:
        """
        Apply the patch atomically.

        Args:
            target_path: The resolved path of the file to patch.
            patch_content: The complete new file content to write.

        Returns:
            Tuple of (backup_path_str, lines_changed).

        Raises:
            GuardrailViolation: If compile-check fails (auto-restores first).
        """
        timestamp = int(time.time())
        backup_name = f"{target_path.stem}_{timestamp}.py.bak"
        backup_path = self._backup_dir / backup_name

        # Step 1: Backup original
        shutil.copy2(target_path, backup_path)
        log_action(
            "GUARDRAIL_BACKUP",
            f"Backed up: {target_path.name} → {backup_path.name}",
            "Original file backed up before patching.",
        )

        original_lines = target_path.read_text(encoding="utf-8").splitlines()
        new_lines = patch_content.splitlines()
        lines_changed = abs(len(new_lines) - len(original_lines))

        # Step 2: Write to a temp file in the same directory (ensures same fs)
        tmp_fd, tmp_path_str = tempfile.mkstemp(
            suffix=".tmp.py", dir=target_path.parent
        )
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(patch_content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())

            # Step 3: Compile-check
            try:
                py_compile.compile(tmp_path_str, doraise=True)
            except py_compile.PyCompileError as exc:
                tmp_path.unlink(missing_ok=True)
                shutil.copy2(backup_path, target_path)
                raise GuardrailViolation(
                    f"[L4] Patch failed compile check — auto-restored: {exc}"
                ) from exc

            # Step 4: Atomic replace
            os.replace(tmp_path_str, target_path)

        except GuardrailViolation:
            raise
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            shutil.copy2(backup_path, target_path)
            raise GuardrailViolation(
                f"[L4] Unexpected error during patch — auto-restored: {exc}"
            ) from exc

        log_action(
            "GUARDRAIL_L4_PASS",
            f"Applied patch to {target_path.name} | Lines delta: {lines_changed}",
            f"Code patch applied atomically to {target_path.name}.",
        )
        return str(backup_path), lines_changed


# ── Layer 5: Patch Audit Logger ───────────────────────────────────────────────


class PatchAuditLogger:
    """Appends one structured entry to CHANGELOG.md after a successful patch."""

    # Resolved once at class load — never changes at runtime.
    _CHANGELOG_PATH: Path = (
        Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
    ).resolve()

    @staticmethod
    def log(tool_name: str, target_file: str, reason: str) -> None:
        """
        Append a Conventional-Commits-style entry to CHANGELOG.md.

        Args:
            tool_name:   The tool whose command file was patched.
            target_file: Basename of the file that was modified.
            reason:      One-line summary of the optimization applied.
        """
        import datetime

        date_str = datetime.date.today().isoformat()
        entry = (
            f"\n### [{date_str}] — Self-Optimization\n"
            f"- **perf({tool_name})**: {reason} "
            f"(auto-patched `{target_file}`)\n"
        )
        try:
            with open(
                PatchAuditLogger._CHANGELOG_PATH, "a", encoding="utf-8"
            ) as changelog:
                changelog.write(entry)
            log_action(
                "GUARDRAIL_L5_CHANGELOG",
                f"Appended entry for {tool_name}",
                "Patch recorded in CHANGELOG.",
                level=logging.DEBUG,
            )
        except OSError as exc:
            # Non-fatal — log but don't block the patch
            log_action(
                "GUARDRAIL_L5_WARN",
                f"CHANGELOG write failed: {exc}",
                "Could not update CHANGELOG — patch still applied.",
                level=logging.WARNING,
            )


# ── Composite GuardrailEngine ─────────────────────────────────────────────────


class GuardrailEngine:
    """
    Orchestrates all 5 security layers in sequence.

    The engine is the single callable surface for the ReflectionEngine —
    all security decisions flow through here.
    """

    def __init__(self, telemetry_store) -> None:
        """
        Args:
            telemetry_store: Shared TelemetryStore instance.
        """
        self._rate_limiter = PatchRateLimiter(telemetry_store)
        self._store = telemetry_store
        log_action(
            "GUARDRAIL_INIT",
            f"Commands dir: {_COMMANDS_DIR}",
            "Security guardrail engine initialised.",
        )

    async def validate_and_apply(self, request: PatchRequest) -> GuardrailResult:
        """
        Run Layers 1–5 and apply the patch if all pass.

        Args:
            request: A PatchRequest dataclass bundling all patch parameters.

        Returns:
            GuardrailResult indicating pass/fail with details.
        """
        target_path = Path(request.target_file).resolve()
        layer_results: dict = {}

        # Layer 1 — No-Go Zone
        try:
            NoGoZoneGuard.validate(target_path)
            layer_results["l1"] = "pass"
        except GuardrailViolation as exc:
            log_action(
                "GUARDRAIL_BLOCK",
                f"L1 violation for '{request.tool_name}': {exc}",
                f"Security block: {exc}",
                level=logging.WARNING,
            )
            return GuardrailResult(
                passed=False,
                failed_layer="L1",
                reason=str(exc),
                layer_results=layer_results,
            )

        # Layer 2 — AST Static Analysis
        try:
            AstSafetyGuard.validate(request.patch_content)
            layer_results["l2"] = "pass"
        except GuardrailViolation as exc:
            log_action(
                "GUARDRAIL_BLOCK",
                f"L2 violation for '{request.tool_name}': {exc}",
                f"Security block — dangerous code detected: {exc}",
                level=logging.WARNING,
            )
            return GuardrailResult(
                passed=False,
                failed_layer="L2",
                reason=str(exc),
                layer_results=layer_results,
            )

        # Layer 3 — Rate Limit + Cooldown
        try:
            await self._rate_limiter.validate(request.tool_name)
            layer_results["l3"] = "pass"
        except GuardrailViolation as exc:
            log_action(
                "GUARDRAIL_BLOCK",
                f"L3 rate-limit for '{request.tool_name}': {exc}",
                f"Patch rate-limited: {exc}",
                level=logging.INFO,
            )
            return GuardrailResult(
                passed=False,
                failed_layer="L3",
                reason=str(exc),
                layer_results=layer_results,
            )

        # Layer 4 — Atomic Backup + Write + Compile Verify
        patcher = AtomicPatcher(request.backup_dir)
        try:
            backup_path, lines_changed = patcher.apply(
                target_path, request.patch_content
            )
            layer_results["l4"] = "pass"
        except GuardrailViolation as exc:
            log_action(
                "GUARDRAIL_BLOCK",
                f"L4 compile/write failure for '{request.tool_name}': {exc}",
                f"Patch rejected — syntax error or write failure: {exc}",
                level=logging.ERROR,
            )
            return GuardrailResult(
                passed=False,
                failed_layer="L4",
                reason=str(exc),
                layer_results=layer_results,
            )

        # Layer 5 — Audit Log
        PatchAuditLogger.log(
            request.tool_name, target_path.name, request.optimization_summary
        )
        layer_results["l5"] = "pass"

        await self._store.record_patch(
            tool_name=request.tool_name,
            target_file=str(target_path),
            patch_content=request.patch_content,
            lines_changed=lines_changed,
            guardrail_result=layer_results,
            backup_path=backup_path,
        )

        log_action(
            "GUARDRAIL_APPLIED",
            f"Tool: {request.tool_name} | File: {target_path.name} | Lines Δ: {lines_changed}",
            f"Self-optimization applied to {target_path.name}.",
        )
        return GuardrailResult(
            passed=True,
            backup_path=backup_path,
            lines_changed=lines_changed,
            layer_results=layer_results,
        )
