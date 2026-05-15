# SESSION_HANDOFF — AI Team System

## Проект: AI Team System v2.3
**Путь:** `/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system`
**GitHub:** github.com/owerevolf/ai-team-system

## Что сделано — 7 фаз:

### Phase 1 — Repository Foundation
PM kernel, indexing, retrieval, SQLite storage

### Phase 2 — Repository Intelligence
Incremental indexing (9s→0.6s), AST parsing, git intelligence, impact analysis

### Phase 3 — Engineering Safety
Validation pipeline, architecture rules, risk analysis, safe patching

### Phase 4 — Collaborative Runtime
Task coordination, locking, conflict detection, patch merge, workflows, approvals, audit log

### Phase 5 — Execution Optimization
Multi-stage retrieval, caching, graph optimization, profiling, token economy

### Phase 6 — Platform Governance
20 governance priorities: service boundaries, dependency governance, drift detection, complexity budgets, health scoring, introspection, debuggability, policy engine, operational modes, event governance, change governance, ownership, config governance, failure governance, auditability, observability simplification, simplification detection, governed extensibility, stress tests, long-run stability

### Phase 7 — Real-World Execution & Human Workflow Integration
Git workflow (branch classification, commit parsing, PR generation, merge safety), failure analysis, engineering memory, persistent sessions, execution explainability, workflow templates (8 types), runtime recovery, knowledge graph, trust calibration

## Ключевые цифры:
- **278 тестов**, CI зелёный
- **38+ API endpoints**
- **Индексация:** 2908 файлов за 9s (full) / 0.6s (incremental)
- **Validation:** 0.7s (full) / ~0.1s (incremental)
- **Governance:** 21 модуль, 20 приоритетов
- **Workflow:** 8 шаблонов, git integration, recovery system

## Принципы:
- PM = deterministic engineering control layer, НЕ AI agent
- Deterministic > clever
- Safety > autonomy
- Coordination > complexity
- Trust > autonomy

## Следующие направления (Phase 8):
- Self-hosting workflows (P1) — PM разрабатывает сам себя через governed workflows
- IDE integration (P3) — runtime control panel
- Human approval UX (P4) — grouped approvals, impact visualization
- Domain context layer (P7) — explicit domain contracts
- Multi-user coordination (P13) — user sessions, approval routing
- Operational tooling (P18) — dashboard, inspectors, dependency explorer
- Platform simplification (P20) — dead feature removal, friction reduction

## Архитектура:
```
core/
  project_manager/
    __init__.py          — PM kernel (1276 lines)
    models/              — Data models
    indexers/            — File indexing, git intelligence, file watch
    extractors/          — Symbol extraction
    storage/             — SQLite/JSON storage
    events/              — Event bus
    query/               — Query engine
    validation/          — Validation pipeline
    runtime/
      __init__.py        — Task coordination system
      approval.py        — Approval workflows
      workflows.py       — Workflow pipelines
      patch_merge.py     — Patch merging
      optimization/      — Cache, graph, retrieval, profiling, compression
      git_workflow.py    — Git workflow integration (P2)
      failure_analysis.py — Failure taxonomy (P5)
      engineering_memory.py — Structured memory (P6)
      explainability.py  — Execution explainability (P10)
      workflow_templates.py — 8 reusable templates (P11)
      recovery.py        — Runtime recovery (P12)
      knowledge_graph.py — Engineering knowledge graph (P14)
      trust_calibration.py — Trust scoring (P16)
    session/
      __init__.py        — Engineering session system (P9)
    governance/
      __init__.py        — GovernanceLayer (unified)
      interfaces.py      — Service boundaries (P1)
      dependency_governance.py — Dependency policies (P2)
      drift_detection.py — Architectural drift (P3)
      complexity_budget.py — Complexity budgets (P4)
      health_model.py    — Health scoring (P5)
      introspection.py   — Runtime introspection (P6)
      debuggability.py   — Execution tracing (P7)
      policy_engine.py   — Policy engine (P8)
      operational_modes.py — Operational modes (P9)
      event_governance.py — Event governance (P10)
      change_governance.py — Change tracking (P11)
      ownership.py       — Subsystem ownership (P12)
      config_governance.py — Config governance (P13)
      failure_governance.py — Failure management (P14)
      auditability.py    — Audit log (P15)
      observability.py   — Observability simplification (P16)
      simplification.py  — Dead code detection (P17)
      extensibility.py   — Governed extensibility (P18)
      stress_tests.py    — Stress tests (P19)
      long_run_stability.py — Long-run stability (P20)
  main.py                — AITeamSystem orchestrator
  agent_manager.py       — Agent management
  model_router.py        — Model routing
  database.py            — Database layer
  ...
web_ui/                  — Web UI (FastAPI)
tests/                   — 278 tests
```

## Сервер:
- Port: 8000
- `./venv/bin/python -m uvicorn web_ui.app:app --port 8000`
