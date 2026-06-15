# Antigravity — Code Instructions

These are mandatory instructions for **all code** generated or modified in any project.
Every file, function, and line must comply with these standards.
This document is project-agnostic and should be reusable across all repositories.

---

## 0. No-Go Zones — Never Touch These Autonomously

The following files and directories must **never be modified, deleted, or created** without explicit user instruction:

| Path | Reason |
|------|--------|
| `.env`, `.env.*` | Live secrets — one wrong edit breaks all services |
| `venv/` | Managed by Python tooling, not hand-editable |
| `graphify-out/` | Auto-generated graph — run `graphify update .` after code changes instead |
| `requirements.txt` | Only update after explicit user approval of a new dependency |
| `.gitignore` | Changes here can accidentally expose secrets |
| `pyrightconfig.json`, `.pylintrc` | Linter configs — changing these silently relaxes quality gates |
| `*.migration`, `alembic/versions/` | Database migrations are destructive and irreversible |
| `docker-compose.yml`, `Dockerfile` | Infrastructure changes require explicit user sign-off |

---

## 0.1. General Principles

- **Stability**: Changes must never break existing functionality. Always verify that original code still works correctly after modifications.
- **Minimalist Code**: Always prioritize the smallest effective change. When adding new functionality, achieve the goal with the minimum number of lines possible without sacrificing readability or robustness. Avoid over-engineering.
- **Atomic Tasks**: Break down complex user requests into smaller, manageable sub-tasks. Document these in `task.md` and execute them one by one.
- **Deep Issue Analysis**: If an issue or bug is identified or suggested, do not apply a surface-level fix. Analyze the entire codebase to understand the root cause and propose/implement a solution that addresses the core of the problem.

---

## 0.5. Project Architecture Context

> Read this first. Do not make assumptions about the stack.

- **Language**: Python 3.11+
- **Stack**: FastAPI + Uvicorn (API) · LangChain / LangGraph (LLM orchestration) · Weaviate (vector DB) · Redis (caching/sessions) · APScheduler (scheduled jobs) · Playwright + Camoufox (scraping) · PostgreSQL (relational, via SQLAlchemy) · AWS S3 / boto3 (object storage)
- **Entry points**: `src/api/main.py` (FastAPI app) · `storage_*/` (per-source scraper modules) · `src/scripts/` (one-off CLI scripts)
- **Package structure**: `src/` for application code · `tests/` mirrors `src/` · `storage_<source>/` for each scraper · `config/` for YAML configs
- **Environment**: Docker-containerised (`Dockerfile` + `docker-compose.yml`). Never assume local system state or globally installed packages.
- **Do not infer the stack** — if something is unclear, ask before assuming.

---

## 1. Deep Research & Production-Ready Planning

**For every task or user prompt, you MUST prioritize research and planning:**

- **Selective Web Search**: Use `web_search` and `read_url_content` **only** when: (1) selecting or evaluating a new library, (2) making an architecture-level decision, or (3) implementing a security-sensitive pattern. Do **not** web search for routine bug fixes, refactors, or changes within already-established patterns — it wastes context and adds no value.
- **Production-Ready Evaluation**: Every change must be designed for a production environment. Ask yourself: *"Is this implementation secure, scalable, and the most robust solution for this codebase?"*
- **Implementation Plan**: Create a detailed implementation plan for **non-trivial changes** (new features, architectural decisions, security-sensitive patterns). For routine bug fixes or small refactors within established patterns, execute directly after reading the relevant code.
- **Validation**: Ensure your plan is the "best fit" for the existing architecture, avoiding ad-hoc solutions or over-engineering.

---

## 2. Quality Gates (Non-Negotiable)

Run the full gate sequence **in order** before any submission:

```bash
ruff format src/                                              # 1. Auto-format (replaces black + isort)
ruff check src/ --fix                                         # 2. Lint + auto-fix
pylint src/ --rcfile=.pylintrc                                # 3. Must score 10.00/10.00
pyright src/                                                  # 4. Type check — must exit 0
bandit -r src/ -ll                                            # 5. Security SAST — 0 HIGH or MEDIUM
pytest tests/ --cov=src --cov-fail-under=80 -v --tb=short    # 6. Tests + ≥80% coverage gate
graphify update .                                             # 7. Refresh knowledge graph
```

### Pylint Hard Limits

| Rule | Limit |
|------|-------|
| Max line length | **120 characters** |
| Max function arguments | **6** |
| Max local variables per function | **15** |
| Max return statements | **6** |
| Max branches (if/elif/else) | **12** |
| Max statements per function | **50** |
| Max module lines | **700** |
| Max class attributes | **10** |
| Max parent classes | **7** |

### Absolutely Forbidden

- **Inline pylint disables** — never write `# pylint: disable=...` anywhere. If pylint complains, fix the code.
- **Wildcard imports** — never write `from module import *`.
- **`print()` for logging** — use `logging.getLogger(__name__)` instead.
- **Old-style string formatting** — always use f-strings. No `%` or `.format()`.
- **Names**: never use `foo`, `bar`, `baz`, `tmp`, or `test` as variable names.

### Always Use

- **f-strings** for all string formatting.
- **`with` statements** for all context managers (files, locks, connections).
- **Type hints** on all function signatures (args + return type).
- **4-space indentation** everywhere, no tabs.

---

## 3. Code Clarity

### Naming
- **Functions**: verb-first — `build_system_instruction()`, not `sys_inst()`
- **Variables**: full purpose — `customer_phone`, not `cp` or `phone1`
- **Booleans**: question form — `is_active`, `has_expired`, `should_retry`
- **Constants**: `UPPER_SNAKE_CASE` + a comment explaining *why* that value, not just *what*
- **Allowed short names**: `i`, `j`, `k` (loops), `ex` (exceptions), `_` (throwaway), `pk`, `id`

### Structure
- **One function = one job.** >40 lines → extract helpers.
- **File order**: module docstring → imports (stdlib / third-party / local) → constants → helpers → core logic → `__main__`
- **Comments**: explain **why**, not **what**. Inline comments signal unclear code — refactor instead.

---

## 4. Security

### Secrets Management
- **Never hardcode secrets** — API keys, passwords, tokens, database URIs must always come from `.env` or environment variables.
- Use `os.getenv("KEY")` or `python-dotenv` to load secrets. Never `API_KEY = "sk-abc123..."`.

### Input Validation
- **Validate all external inputs** before processing — API payloads, WebSocket messages, query parameters, file uploads.
- Use Pydantic models for REST endpoint bodies. Never trust raw input.

### Log Sanitization
- **Never log PII or secrets in plain text** — mask before logging.
  ```python
  # GOOD
  logger.info(f"Calling customer: ***{phone_number[-4:]}")
  ```

### Security Scanning
- `bandit -r src/ -ll` must return **0 HIGH or MEDIUM findings** before any submission (catches SQL injection patterns, weak crypto, unsafe subprocess calls).

---

## 5. Robustness & Error Handling

- **Handle edge cases explicitly** — empty inputs, `None` values, zero-length data, missing dict keys.
- **Use `.get()` with defaults** for dicts instead of bare `[]` access where the key might be absent.
- **Log errors with context** — include request IDs, entity identifiers, or other traceable info.
- **Fail gracefully** — catch specific exceptions, log them, and degrade. Never bare `except:`.
  ```python
  # GOOD
  except ConnectionError as exc:
      logger.error(f"[API] Connection failed for request {request_id}: {exc}")
  ```

---

## 6. Logging Standards

- Use `logging.getLogger(__name__)` at module level — never `print()`.
- **Format**: `[ACTION] Key: value | Key: value`
  ```python
  logger.info(f"[USER_CREATED] User: {user_id} | Role: {role}")
  logger.warning(f"[RATE_LIMIT] IP: {masked_ip} | Retry after: {retry_after}s")
  ```
- Log levels: `DEBUG` for traces · `INFO` for lifecycle events · `WARNING` for recoverable issues · `ERROR` for failures.
- Never log PII or secrets (see §4).

---

## 7. Documentation

- **README**: Update when a new module is added, setup steps change, or project structure changes significantly. Always reflects the current state.
- **API docs**: Every REST endpoint needs: HTTP method + path · request schema · response schema + status codes · one `curl` example. Keep in `README.md` or `docs/api.md`.
- **CHANGELOG**: Maintain `CHANGELOG.md`. Format: `## [YYYY-MM-DD]` with `### Added / Changed / Fixed` subsections. One line per change.

---

## 8. Output Quality

- **Type hints** on all function signatures (args + return type).
- **Docstrings** on functions with non-obvious behaviour: Google style (Args / Returns / Raises).
- **Guard clauses** at function start — return early, avoid deep nesting.
- **Consistent error messages** — must be debuggable from logs alone.
- **No dead code** — remove commented-out code, unused imports, and obsolete functions.

---

## 9. Pre-Submission Checklist

Before considering any code change complete:

1. ✅ `ruff format src/ && ruff check src/ --fix` — no remaining errors
2. ✅ Pylint score is **10.00/10.00** (`pylint src/ --rcfile=.pylintrc`)
3. ✅ No `# pylint: disable` comments anywhere
4. ✅ `pyright src/` — must exit 0, no type errors
5. ✅ `bandit -r src/ -ll` — 0 HIGH or MEDIUM findings
6. ✅ All functions have type hints
7. ✅ Complex logic has *why* comments
8. ✅ Variable names are self-documenting
9. ✅ No bare `except:` blocks
10. ✅ Logging uses the `[ACTION] Key: value` format
11. ✅ No secrets or PII in code or logs
12. ✅ External inputs are validated before use
13. ✅ README / CHANGELOG updated if applicable
14. ✅ **Minimalist & Concise**: functionality achieved with the fewest possible lines without sacrificing readability
15. ✅ **Production-Ready**: implementation follows researched best practices
16. ✅ **Clean Workspace**: temporary files, scratch scripts, and verification tests deleted once no longer needed
17. ✅ **Tests Pass + Coverage Gate**: `pytest tests/ --cov=src --cov-fail-under=80 -v --tb=short` — must exit 0
18. ✅ **No Unapproved Dependencies**: `git diff requirements.txt` — any new package must have been explicitly approved
19. ✅ **Git Commit Ready**: commit message follows Conventional Commits format (see §13)
20. ✅ **Knowledge Graph Updated**: `graphify update .` run after all code changes

---

## 10. Knowledge Graph Maintenance

After every significant code change, run `graphify update .` — this auto-updates the architecture graph with zero API cost.

Do **not** manually edit `workflow.md` or `function.md` in `.agents/temp_documentations/`. Those files are deprecated in favour of the graphify graph, which cannot go stale.

### graphify Rules
- **Mandatory Context**: Before answering architecture questions or making changes, read `graphify-out/GRAPH_REPORT.md` for core workflows, "god nodes", and community structures.
- **Efficient Discovery**: Use `graphify query "<question>"` and `graphify explain "<concept>"` to find relevant files. Avoid broad `grep` or `list_dir` exploration.
- **Workflow Navigation**: Use `graphify path "A" "B"` to trace data flows between components.
- **Wiki**: If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw source files.

---

## 11. Testing Standards

Every new function with non-trivial logic **must** have a corresponding test. No exceptions.

### Framework & Commands

```bash
pytest tests/ -v --tb=short                                  # All tests — must exit 0
pytest tests/test_foo.py -v                                  # Single file
pytest tests/ -k "test_name" -v                              # By name pattern
pytest tests/ --cov=src --cov-fail-under=80 --tb=short       # With coverage gate
```

### Conventions

- **File mirror**: `src/foo.py` → `tests/test_foo.py`
- **Naming**: `test_<function>_<scenario>` — e.g., `test_fetch_user_returns_none_when_missing`
- **Pattern**: Always use **Arrange → Act → Assert** in every test body
- **Fixtures**: Use `@pytest.fixture` for shared setup; never copy-paste setup code between tests
- **Coverage gate**: New modules must maintain **≥80% line coverage**. PRs that drop coverage below this threshold are rejected.

### Mocking Rules

- **All external calls must be mocked** — API calls, database queries, file I/O. Tests must run fully offline.
- Use `unittest.mock.patch` or `pytest-mock` (`mocker.patch`) for internal methods.
- Use `pytest-httpx` or `respx` for mocking HTTP requests. Never make a real network call in tests.

---

## 12. Dependency Management

**Never add a new package without explicit user approval.**

1. **Check first**: Verify no already-installed package can do the job.
2. **Ask**: State the package name and reason, then **wait for user approval** before installing.
3. **Pin versions**: After approval, add to `requirements.txt` with a pinned version: `package==x.y.z`.
4. **One commit**: The `pip install` and `requirements.txt` update must happen in the same commit.
5. **Document**: Include the reason for the new dependency in the commit message body.

---

## 13. Git Commit Standards

All commits must follow **Conventional Commits** format.

```
<type>(<scope>): <short description under 72 chars>

[optional body: explain WHY, not WHAT]
```

| Type | When to use |
|------|-------------|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `refactor` | Code restructured, no behaviour change |
| `test` | Adding or fixing tests |
| `docs` | README, CHANGELOG, docstrings only |
| `chore` | Dependency updates, config changes |
| `perf` | Performance improvement |

### Hard Rules

- **Never** commit with messages like `"fix"`, `"update"`, `"wip"`, `"changes"`, or `"misc"`.
- **Never** commit `.env` or `.env.*` files — verify `.gitignore` before every commit.
- **Never** commit directly to `main` — propose the change and let the user decide.
- One logical change per commit. Do not batch unrelated changes.

---

## 14. Post-Task Summary

After every task, respond with **max 5 bullet points**:

```
✅ Done. Here's what changed:
- [What was added/fixed]
- [File(s) modified]
- [Command to verify]
- [Follow-up needed, or "Nothing else needed."]
```

No long explanations, no code dumps, no step-by-step breakdowns unless the user asks.

---

## 15. Token-Saving Commands

### Navigation (use instead of `list_dir` + `read_file` loops)

```bash
graphify query "<question>"           # Ask the knowledge graph directly
graphify explain "<concept>"          # Get a plain-English explanation
graphify path "module_a" "module_b"   # Trace data flow between two modules
```

### Quick File Inspection

```bash
grep -n "def " src/foo.py             # List all functions in a file fast
grep -rn "function_name" src/         # Find where a function is called
git diff --stat HEAD                  # See what files changed, not full diff
git log --oneline -10                 # Recent commits in one line each
```

### Session Health

- **Start a new conversation** when switching to an unrelated task — context rot is real.
- **Do not load entire files** unless necessary — use `grep` to find the relevant function first, then read only those lines.
- **Prefer CLI commands** over tool calls for data-gathering — they're deterministic and cost zero LLM tokens.

### Full Quality Gate Sequence

```bash
ruff format src/                                              # 1. Format
ruff check src/ --fix                                         # 2. Lint + auto-fix
pylint src/ --rcfile=.pylintrc                                # 3. Pylint 10.00/10.00
pyright src/                                                  # 4. Type check
bandit -r src/ -ll                                            # 5. Security SAST
pytest tests/ --cov=src --cov-fail-under=80 -v --tb=short    # 6. Tests + coverage
graphify update .                                             # 7. Refresh graph
```