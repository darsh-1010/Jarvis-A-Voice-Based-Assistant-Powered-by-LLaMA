# Changelog

All notable changes to this project will be documented in this file.

## [2026-06-15] — Self-Improvement Loop, Security Guardrails & LiteLLM Integration
### Added
- **LiteLLM Router Integration**: Added `litellm.Router` in `backend/jarvis/brain.py` for unified multi-provider failover. Automatically routes across Google Gemini, Groq Cloud, and local Ollama if keys are present.
- **LiteLLM Provider Adapter**: Added `LiteLLMProviderWrapper` to adapt LiteLLM Router output to the legacy `BaseProvider` interface for seamless compatibility with intent parsing and tests.
- **Self-Improvement Loop**: Added `TelemetryStore` (`backend/jarvis/memory/telemetry.py`) to log tool executions in a SQLite database, `ReflectionEngine` (`backend/jarvis/memory/reflection.py`) to research task failures via LLM and web search and generate patches, and `GuardrailEngine` (`backend/jarvis/security/guardrails.py`) to validate and apply code patches.
- **5-Layer Security Guardrail Pipeline**:
  - Layer 1: No-go zone directory and filename checks to prevent path traversal and modifications outside of `jarvis/commands/`.
  - Layer 2: AST static analysis to block dangerous constructs (like `eval`, `exec`, shell command execution, or dangerous imports like `os`, `subprocess`).
  - Layer 3: Rate limits and cooldown constraints (minimum 60-min gap, max 3 patches/day per tool).
  - Layer 4: Sibling temp-file atomic write and `py_compile` checks with automatic fallback/recovery.
  - Layer 5: CHANGELOG append and SQLite audit logging.
- **New API Endpoints**: Endpoints for telemetry stats, reflections list, patches list, and manual patch rollback.

### Changed
- Refactored `backend/jarvis/brain.py` to use LiteLLM Router for AI backend, removing deprecated custom provider classes (`GeminiProvider`, `OpenRouterProvider`, `OllamaProvider`).
- Updated `backend/jarvis/config.py` to support Groq model settings and keys (`groq_api_key`, `groq_model`).
- Updated `backend/requirements.txt` to add `litellm==1.89.0`.
- Instrumented `ToolRegistry` (`backend/jarvis/commands/registry.py`) to collect execution metrics and invoke the self-improvement loop in the background.
- Cleaned up typing errors, imports, and MD5 usage in `intent.py` to pass strict `pyright` and `bandit` verification gates.

## [2026-05-10] — AI Intent Routing
### Added
- **`jarvis/intent.py`**: New `IntentRouter` class — uses the active LLM provider to classify any
  natural-language command into a registered tool + extracted parameters, or returns `null` for
  conversational fallback. Provider-agnostic (works with Gemini, OpenRouter, and Ollama).
- **Result Enrichment** (`cli_main.py`): `_enrich_result()` pipeline post-processes tool outputs
  via the LLM — news headlines are summarised into a spoken 2-3 sentence briefing; speed-test
  results are converted into a friendly spoken sentence.
- **Full Tool Registry** (`web.py`, `media.py`): All web and media functions now have
  `@registry.register` decorators, making them discoverable by the IntentRouter.
- `BrainManager.get_active_provider()`: Exposes the provider chain so IntentRouter can reuse it
  without duplicating fallback logic.

### Changed
- Replaced the hardcoded string-matching command dispatcher in `cli_main.py` with the
  AI-powered `IntentRouter` pipeline.
- `config.py`: Removed hardcoded `NEWS_API_KEY` default — must now be set via `.env`.
- `pylintrc`: Added suppression for pre-existing architectural patterns
  (`import-outside-toplevel`, `no-member` cv2 false positives, `wrong-import-position`,
  `unused-import` for side-effect-only registrations).

## [2026-05-10]

### Security & Compliance
- Migrated repository from MIT License to **Business Source License (BSL 1.1)**.
- Implemented strict prohibitions on unauthorized commercial AI/ML training.
- Added `COMMERCIAL_LICENSE.md`, `AI_TRAINING_POLICY.md`, and `NOTICE` files.
- Updated all metadata and source headers to reflect new licensing structure.

## [2026-04-28]
### Added
- New **AI Studio** minimalist frontend design.
- Global `Sidebar` component for improved navigation.
- Dedicated `Tasks` page for monitoring background processes.
- Dedicated `Help` page with voice command library and FAQ.
- `PageWrapper` component for smooth motion transitions between pages.
- Tailwind 4 design system with custom theme tokens (`globals.css`).

### Changed
- Replaced "Zenith" dark-mode HUD with a professional light-mode dashboard.
- Updated `layout.tsx` to support the new sidebar-based multi-page architecture.
- Integrated existing backend logic (Chat, System Stats) into the new dashboard UI.
- Switched from "VoiceOrb" 3D visualization to a minimalist bar-style visualizer.

### Fixed
- Improved frontend navigation state detection using `usePathname`.
- Corrected Tailwind 4 utility definitions for better performance.
