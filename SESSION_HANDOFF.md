# SESSION_HANDOFF — AI Team System

## Проект: AI Team System v2.7
**Путь:** `/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system`
**GitHub:** github.com/owerevolf/ai-team-system
**Ветка:** main

## Текущее состояние: Phase 11 завершена

### Ключевые цифры:
- **649 тестов** — все зелёные
- **45 модулей** в workspace/, runtime/durability/, runtime/ergonomics/, runtime/trust/
- **38+ API endpoints**
- Сервер работает на порту 8000

### Последние коммиты:
```
9c3213c Phase 11: Adaptive Transparency & Trust Stability (P1-P10)
a432e3d Update SESSION_HANDOFF.md for Phase 10 completion
031b227 Phase 10: Operational Ergonomics & Human Scaling (P1-P7)
```

## Архитектура (что есть):

### core/project_manager/runtime/trust/ (Phase 11 — 10 модулей)
- transparency_contracts.py — Explicit visibility contracts (never hide / can summarize / can delay / can suppress)
- visibility_guarantees.py — Critical event invariants (always shown, never compressed/batched/suppressed)
- adaptation_inspector.py — Why surfaced/hidden/delayed — every adaptation decision explainable
- user_controlled_adaptivity.py — Adjustable operational policy (Beginner/Focused/Expert/Recovery profiles)
- trust_drift_detection.py — Governance fatigue, blind approvals, suppression distrust, recovery avoidance
- explainability_compression.py — Layered explanations (Summary -> Reasoning -> Full Trace), losslessly expandable
- predictable_personality.py — Stable operational identity, bounded adaptivity, style change limits
- audit_visible_automation.py — All automation visible, replayable, attributable, reversible
- governance_pressure.py — Approval fatigue, interruption frequency, cognitive load, trust instability
- simplicity_preservation.py — Complexity budget (operational/cognitive/maintenance/observability cost)

### core/project_manager/runtime/ergonomics/ (Phase 10 — 7 модулей)
- workflow_compression.py, attention_management.py, approval_intelligence.py
- noise_reduction.py, calm_mode.py, intent_centric_ux.py, human_time_protection.py

### core/project_manager/workspace/ (Phase 8 — 20 модулей)
- project_importer.py, project_health.py, repo_repair.py, feature_dev.py
- educational_mode.py, workspace_ux.py, autonomy_guard.py
- project_understanding.py, task_traceability.py, patch_review.py
- session_memory.py, project_templates.py, user_modes.py
- local_first.py, failure_visibility.py, project_sandbox.py
- real_world_testing.py, fun_mode.py

### core/project_manager/runtime/durability/ (Phase 9 — 10 модулей)
- state_lifecycle.py, context_gc.py, recovery_engine.py, large_repo.py
- explainability_layer.py, cognitive_load.py, chaos_testing.py
- observability.py, plugin_boundaries.py, simplification.py

### Существующие модули (Phase 1-7):
- core/project_manager/ — PM kernel, models, indexers, extractors, storage
- core/project_manager/events/ — Event bus
- core/project_manager/query/ — Query engine
- core/project_manager/validation/ — Validation pipeline
- core/project_manager/runtime/ — Recovery, explainability, workflows, git
- core/project_manager/runtime/optimization/ — Cache, graph, retrieval
- core/project_manager/session/ — Session system
- core/project_manager/governance/ — 20 governance modules

## Запуск сервера:
```bash
cd /media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system
./venv/bin/python -m uvicorn web_ui.app:app --port 8000
```

## Запуск тестов:
```bash
./venv/bin/python -m pytest tests/ -x --tb=short
```

## Принципы:
- PM = deterministic engineering control layer, НЕ AI agent
- Deterministic > clever
- Safety > autonomy
- Coordination > complexity
- Usability > enterprise complexity
- State ages, doesn't just accumulate
- GC never breaks replay/recovery
- Every action explains itself
- Signal over noise, user time is expensive
- Calm by default, verbose on demand
- Goals not operations
- Adaptive systems must expose their adaptation rules
- User controls the knobs, runtime stays within bounds
- Trust degradation is a silent failure — detect it early
- Compressed by default, losslessly expandable

## Что делать дальше (Phase 12 — если нужен):

Варианты:
1. **Интеграция Phase 8-11 модулей в web_ui API** — новые endpoints
2. **IDE integration** — runtime control panel
3. **Multi-user coordination** — user sessions, approval routing
4. **Performance optimization** — profiling, bottleneck removal
5. **Documentation** — API docs, user guide

## Критические правила:
- НЕ запускать delegate_task параллельно — модель висит
- Делать ОДНУ задачу за раз, последовательно
- После каждой фазы: тесты → коммит → пуш
- Не превращать в enterprise monster

## Известные проблемы:
- workspace/__init__.py: `ProjectTemplate` импортирован но не критично
- Некоторые LSP warnings в test_workspace.py (type hints) — не влияют на работу
