# SESSION_HANDOFF — AI Team System

## Проект: AI Team System v2.6
**Путь:** `/media/aram/28c41f20-b9ef-4ac3-90f6-8f877a30e33c/owerevolf/ai teem/ai-team-system`
**GitHub:** github.com/owerevolf/ai-team-system
**Ветка:** main

## Текущее состояние: Phase 10 завершена

### Ключевые цифры:
- **540 тестов** — все зелёные
- **35 модулей** в workspace/, runtime/durability/, runtime/ergonomics/
- **38+ API endpoints**
- Сервер работает на порту 8000

### Последние коммиты:
```
031b227 Phase 10: Operational Ergonomics & Human Scaling (P1-P7)
2fb0f07 Prepare SESSION_HANDOFF for next session
8d1a19f Update SESSION_HANDOFF.md for Phase 9 completion
3e558c2 Phase 9: Runtime Durability & Operational Resilience (P1-P10)
```

## Архитектура (что есть):

### core/project_manager/runtime/ergonomics/ (Phase 10 — 7 модулей)
- workflow_compression.py — Сжатие runtime graph в digestible views (3 levels)
- attention_management.py — Priority-based attention что важно сейчас
- approval_intelligence.py — Smart batching, grouping, risk-tiering
- noise_reduction.py — Suppress redundant explanations/telemetry/alerts
- calm_mode.py — Minimal operational mode (Full/Reduced/Calm/Silent)
- intent_centric_ux.py — "What do you want to do?" vs "manage runtime"
- human_time_protection.py — Focus blocks, batch interruptions

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

## Что делать дальше (Phase 11 — если нужен):

Варианты:
1. **Интеграция Phase 8/9/10 модулей в web_ui API** — новые endpoints
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
