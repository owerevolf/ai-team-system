# 🤖 AI Team System v2.0

**AI Engineering Workspace** — мультиагентная платформа разработки с controlled execution runtime.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Tests](https://img.shields.io/badge/Tests-1140%20passed-brightgreen.svg)
![Phases](https://img.shields.io/badge/Phases-19A--19D-blue.svg)

---

## ⚡ Быстрый старт (2 минуты)

### Linux / macOS
```bash
git clone https://github.com/owerevolf/ai-team-system.git
cd ai-team-system
chmod +x scripts/launcher.sh
./scripts/launcher.sh
```

### Windows
```powershell
scripts\install.ps1
```

После установки браузер откроется автоматически на **http://localhost:8000**

---

## 🌟 Что умеет AI Team System?

| Фича | Описание |
|------|----------|
| 🎓 Learn Mode | 5-шаговый тур с аналогиями из жизни |
| 🛠 Developer Mode | AI Engineering Workspace с orchestration runtime |
| 🤖 7 AI-агентов | TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist |
| 🧠 Project Brain | Единый источник правды для всех агентов |
| 📋 Patch Engine | Изменения ТОЛЬКО через patches (никаких direct writes) |
| 🔒 Safe Review | Validation layer: forbidden files, scope, dangerous patterns |
| 👤 Approval Flow | Human approval для всех изменений |
| 🏗 Workspace Runtime | Isolated workspaces с snapshots и rollback |
| 🔍 Repo Scanner | Автоматическое понимание проекта |
| 📚 Knowledge Index | Context compression для LLM |
| 🧪 Execution Sandbox | Governed execution boundary |
| 💻 Safe Terminal | Whitelist команд, blacklist опасных операций |
| 🧠 Обучалка промтов | Prompt Architect учит собирать мысли, контекст, ТЗ |
| 🧠 Авто-детект железа | Выбор модели по VRAM/RAM |
| 💬 Оффлайн-первый | Работает через Ollama без интернета |
| ☁️ Мульти-провайдер | OpenRouter, Ollama, OmniRoute — fallback цепочки |
| 📥 Экспорт уроков | Markdown-гайды с примерами |
| ⚡ SSE-стриминг | Ответы в реальном времени |
| 🎭 4 уровня сложности | zero / beginner / advanced / standard |
| 📋 Канбан доска | Отслеживание задач агентов |
| ⚙️ Настройки | Тестирование моделей, авто-выбор, рекомендации |

---

## 🆕 Phase 19A-19D — Developer Mode Foundation

### Developer Mode UI (Phase 19A)
- 🛠 Новая вкладка **Developer** с sidebar layout (ChatGPT/Claude-style)
- Sidebar: Conversations, Projects, Tasks, Knowledge, Runtime, Agents, Memory
- Status bar: project, mode, branch, runtime status
- Conversation panel с message bubbles
- Responsive dark UI

### Project Brain & Understanding (Phase 19B)
- **Project Brain** — единый источник правды (goals, tasks, decisions, constraints, risks)
- **Understanding Engine** — understand-before-execution philosophy
- **Task Contracts** — scoped execution contracts для агентов
- **Context Layers** — layered context system (<150k tokens)
- JSON persistence для brain state

### Safe Orchestration (Phase 19C)
- **TeamLead Runtime** — центральный orchestrator
- **Agent Registry** — 7 агентов с capabilities, limits, risk levels
- **Skill Router** — explicit skill-to-agent routing
- **Execution Plan** — structured plan с phases, tasks, dependencies
- **Safe Review** — validation layer (forbidden files, scope, contracts)
- **Runtime Events** — structured event system (EventBus, timeline)
- **NO FREE AGENTS** — все задачи через TeamLead

### Controlled Execution (Phase 19D)
- **PATCHES > DIRECT WRITES** — никаких write_file(), только patches
- **Patch Engine** — generate, validate, apply, rollback
- **Workspace Runtime** — isolated workspaces per task
- **Repo Scanner** — project understanding (frameworks, entrypoints, risky zones)
- **Knowledge Index** — context compression для LLM
- **Execution Sandbox** — governed execution boundary
- **Approval Runtime** — human approval flow (LOW auto-approve, MEDIUM+/needs human)
- **Task Executor** — controlled worker runtime
- **Safe Terminal** — whitelist/blacklist команд

---

## 🏗️ Архитектура

```
User → Developer Mode UI → Orchestrator → TeamLead → Agents → Patches → Review → Apply
                              ↓              ↓          ↓
                         Project Brain   Contracts   Sandbox
                              ↓              ↓          ↓
                         Brain Store   Skill Router  Workspace
```

### Поток выполнения (Execution Flow):
```
1. User: "Добавь кнопку logout"
2. Understanding Engine → анализ запроса
3. Orchestrator → создание execution plan
4. TeamLead → назначение агентов + task contracts
5. TaskExecutor → создание workspace + scoped context
6. PatchEngine → генерация patch
7. SafeReview → validation (forbidden files, scope, dangerous patterns)
8. ApprovalRuntime → human approve/reject
9. PatchEngine → apply patch
10. Tests → validation
11. Timeline update
```

### Принципы:
- **NO direct file writes** — только через patches
- **NO hidden execution** — все patches требуют approval
- **Main branch protected** — workspaces isolated
- **Rollback works** — каждый patch имеет reverse
- **Agents cannot bypass** — contracts enforced

---

## 📦 API Endpoints

### Developer Mode:
```
POST /api/developer/create_project  — создать project brain
POST /api/developer/message         — сообщение (understanding phase)
POST /api/developer/understand      — анализ запроса
GET  /api/developer/project/{id}    — получить brain state
GET  /api/developer/projects        — список проектов
POST /api/developer/snapshot/{id}   — snapshot brain
POST /api/developer/orchestrate     — полный orchestration flow
GET  /api/developer/timeline        — event timeline
GET  /api/developer/agents          — список агентов
GET  /api/developer/status          — статус orchestrator
POST /api/developer/execute         — execute task (patch flow)
GET  /api/developer/approvals       — approval queue
POST /api/developer/approvals/action — approve/reject patch
GET  /api/developer/repo/scan       — scan repository
GET  /api/developer/knowledge       — knowledge index
POST /api/developer/terminal        — safe terminal command
```

### Repo:
```
POST /api/repo/open                 — открыть проект
GET  /api/repo/files                — список файлов
GET  /api/repo/file/{path}          — содержимое файла
```

---

## 👥 Агенты

| Агент | Роль | Risk Level | Can Write | Needs Review |
|-------|------|------------|-----------|--------------|
| 👔 TeamLead | Orchestrator, координация | CRITICAL | ❌ | ❌ |
| 🏛 Architect | Архитектура, дизайн | HIGH | ✅ | ✅ |
| ⚙️ Backend | API, логика, БД | MEDIUM | ✅ | ✅ |
| 🎨 Frontend | UI, CSS, компоненты | MEDIUM | ✅ | ✅ |
| 🚀 DevOps | Docker, CI/CD | HIGH | ✅ | ✅ |
| 🧪 Tester | Тесты, QA | LOW | ✅ (tests) | ❌ |
| 📝 Documentalist | Документация | LOW | ✅ (docs) | ❌ |

---

## 🔧 Настройка

### API ключи (.env)
```env
OPENROUTER_API_KEY=sk-or-v1-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-coder:480b-cloud
AI_MODE=local
```

### Desktop Launcher
```bash
# Запуск
./scripts/launcher.sh

# Остановка
./scripts/stop.sh

# Диагностика
./scripts/doctor.sh

# Установка .desktop entry
./scripts/install_desktop_entry.sh
```

---

## 🧪 Тесты

```bash
# Все тесты
./venv/bin/python3 -m pytest tests/ -v

# Результат: 1140 passed ✅

# По фазам
./venv/bin/python3 -m pytest tests/test_phase19b_developer.py -v  # 63 tests
./venv/bin/python3 -m pytest tests/test_phase19c_orchestration.py -v  # 76 tests
./venv/bin/python3 -m pytest tests/test_phase19d_execution.py -v  # 52 tests
```

---

## 📁 Структура проекта

```
ai-team-system/
├── core/
│   ├── project_manager/
│   │   ├── workspace/           # Phase 8: project_importer, repair, sandbox
│   │   └── runtime/
│   │       ├── developer/       # Phase 19A-19D: Developer Mode
│   │       │   ├── project_brain.py       # Single source of truth
│   │       │   ├── brain_store.py        # JSON persistence
│   │       │   ├── understanding_engine.py # Understand before execute
│   │       │   ├── task_contracts.py     # Scoped agent contracts
│   │       │   ├── context_layers.py     # Layered context (<150k tokens)
│   │       │   ├── orchestrator.py       # Main orchestration runtime
│   │       │   ├── teamlead_runtime.py   # TeamLead orchestrator
│   │       │   ├── agent_registry.py     # 7 agents with capabilities
│   │       │   ├── skill_router.py       # Skill-to-agent routing
│   │       │   ├── execution_plan.py     # Structured execution plan
│   │       │   ├── execution_memory.py   # Execution timeline
│   │       │   ├── safe_review.py        # Validation layer
│   │       │   ├── patch_engine.py       # Patch-based changes
│   │       │   ├── workspace_runtime.py  # Isolated workspaces
│   │       │   ├── repo_scanner.py       # Project understanding
│   │       │   ├── knowledge_index.py    # Context compression
│   │       │   ├── execution_sandbox.py  # Governed execution
│   │       │   ├── approval_runtime.py   # Human approval flow
│   │       │   ├── task_executor.py      # Controlled worker
│   │       │   ├── developer_terminal.py # Safe terminal
│   │       │   └── developer_api.py      # FastAPI endpoints
│   │       ├── coherence/       # Coherence engine
│   │       ├── compression/     # Context compression
│   │       ├── durability/      # Durability patterns
│   │       ├── ecosystem/       # Ecosystem patterns
│   │       ├── ergonomics/      # Ergonomics patterns
│   │       ├── reality/         # Reality checks
│   │       ├── stabilization/   # Stabilization
│   │       ├── stewardship/     # Stewardship
│   │       ├── trust/           # Trust calibration
│   │       └── workflows.py     # Workflow templates
│   ├── model_router.py          # Multi-provider routing
│   ├── agent_manager.py         # Agent management
│   └── main.py                  # AITeamSystem orchestrator
├── web_ui/
│   ├── app.py                   # FastAPI application
│   ├── repo_endpoints.py        # Repo API endpoints
│   ├── static/
│   │   ├── css/welcome.css      # Dark theme styles
│   │   └── js/welcome.js        # Frontend logic
│   └── templates/
│       └── welcome.html         # Main UI
├── tests/                       # 1140 tests
├── config/                      # Configuration
├── scripts/                     # Launcher, doctor, installer
└── docs/                        # Documentation
```

---

## 🚀 Планы (Phase 19E+)

- [ ] Real Tooling Integration (LLM calls, real patch generation)
- [ ] Git integration (branches, commits, PRs)
- [ ] Webhooks для GitHub/GitLab
- [ ] Multi-language support (i18n)
- [ ] Plugin system
- [ ] Advanced analytics

---

## 📄 Лицензия

MIT
