# Session Handoff — May 15 2026

## Project
AI Team System v2.2 — Python/FastAPI multi-agent dev platform
Path: /media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system
Repo: github.com/owerevolf/ai-team-system
Branch: main (synced with origin)

## Server
- Running on port 8000 (uvicorn web_ui.app:app)
- Venv: venv_new/ (Python 3.12.3)
- PYTHONPATH=. required
- AI_MODE=cloud, OpenRouter key configured

## What Was Done This Session

### Commit 1: f541477 — FIX: ModelRouter imports
- Fixed NameError in app.py: missing lazy imports of ModelRouter in 3 functions
- agent_query (line 329), teamlead_query (line 482), create_project_stream (line 537)
- Also: welcome.js overlay hide on tab switch, Prompt Architect auto-init

### Commit 2: 68a10a4 — FEAT: ProjectManager Phase 1
- Created modular core/project_manager/ structure:
  - models/ — FileEntry, SymbolEntry, DependencyEdge, Snapshot
  - indexers/ — FileIndexer (recursive scan), DependencyGraph (import graph)
  - extractors/ — SymbolExtractor (regex, fault-tolerant, multi-lang)
  - storage/ — Storage (JSON facts only, no AI opinions)
  - events/ — EventBus (lightweight pub/sub)
  - query/ — QueryEngine (filtered context, 12000 char budget)
- PM = passive observer. Stores facts only. No AI opinions/summaries.
- Agent integration: optional adapter in AgentManager (non-breaking)
- Web UI: 8 repo endpoints (/api/repo/*) via repo_endpoints router
- Config: repo_explorer agent in agent_models.json
- .agents/ added to .gitignore
- Indexing perf: ~2877 files, ~14000 symbols in 1.6s

## Test Status
- 192 passed, 1 failed (test_init_heavy_profile — pre-existing, unrelated)
- PM tests: not yet written (Phase 1 focused on infrastructure)

## Architecture Decisions
- PM is OPTIONAL — if not initialized, system works as before
- All PM changes are ADDITIVE — no existing code was modified in breaking ways
- Context budget enforced: MAX_CONTEXT_CHARS = 12000
- Fault-tolerant: PM never crashes the system (try/except everywhere)
- Only facts stored: file paths, symbols, dependencies, timestamps, hashes

## kimi/ Folder
Contains reference files from GPT analysis:
- ARCHITECTURE/MEGA_PROMPT.md — full PM implementation spec
- ARCHITECTURE/INTEGRATION_GUIDE.md — step-by-step integration
- ARCHITECTURE/01_ARCHITECTURE.md — architecture overview
- core system/ — reference implementations (superseded by our modular version)
- for web ui/ — repo_endpoints.py (integrated)
- promt system/ — skill prompts (integrated)

## Next Steps (Phase 2 — TBD by user)
Possible directions:
- PM validation layer (file existence, import integrity, duplicate symbols)
- PM-aware agent prompts (repo_explorer agent)
- WebSocket real-time updates
- Frontend UI for repo mode
- PM tests

## Key Constraints (from GPT engineering protocol)
- PM = passive observer, NOT AI agent
- No self-improvement, no autonomous rewriting
- Deterministic systems > AI magic
- Stability > cleverness
- Incremental integration only
