# 🤖 AI Team System v2.0

**Обучающая платформа для новичков** — 7 AI-агентов создают проекты с нуля, объясняя каждый шаг.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)

---

## ⚡ Быстрый старт (2 минуты)

### Linux / macOS
```bash
git clone https://github.com/owerevolf/ai-team-system.git
cd ai-team-system
chmod +x scripts/install.sh
./scripts/install.sh
```

### Windows
```powershell
# Скачай репозиторий и запусти:
scripts\install.ps1
```

После установки браузер откроется автоматически на **http://localhost:8000**

---

## 🌟 Что умеет AI Team System?

| Фича | Описание |
|------|----------|
| 🎓 Режим обучения | 5-шаговый тур с аналогиями из жизни |
| 🤖 7 AI-агентов | TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist |
| 🧠 Авто-детект железа | Выбор модели по VRAM/RAM (4b/8b/14b) |
| 💬 Оффлайн-первый | Работает через Ollama без интернета |
| ☁️ Fallback на облако | 5+ бесплатных API (Groq, DeepSeek, Google, OpenRouter, xAI) |
| 📥 Экспорт уроков | Markdown-гайды с примерами |
| 🛡️ Безопасность | Песочница, whitelist команд, логирование |
| ⚡ SSE-стриминг | Ответы в реальном времени |
| 💬 Живой диалог | TeamLead ведёт диалог, уточняет детали, предлагает идеи |
| 🎭 4 уровня сложности | zero / beginner / advanced / standard для каждого агента |

---

## 📸 Скриншоты

```
┌─────────────────────────────────────────┐
│  🤖 AI Team System                     │
│                                         │
│  ✨ Тебя приветствует                   │
│  новый мир интересных идей              │
│                                         │
│  [🎓 Начать тур]  [💡 Пропустить]       │
└─────────────────────────────────────────┘
```

Скриншоты UI: папка `screenshots/` (24 PNG)

---

## 📦 Таблица моделей по железу

| Профиль | VRAM | RAM | Модель | Агенты |
|---------|------|-----|--------|--------|
| Light | <6 ГБ | <16 ГБ | qwen3:4b | 2 |
| Medium | 6-12 ГБ | 16-32 ГБ | qwen3:8b | 4 |
| Heavy | >12 ГБ | >32 ГБ | qwen3:14b | 8 |

---

## 🏗️ Архитектура

```
User → Welcome UI (чат) → TeamLead диалог → Подтверждение → 7 Агентов → Проект + Markdown Lesson
                              ↓
                       Hardware Detect → Model Selection
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
         Local (Ollama)              Cloud (через API)
         - qwen3:4b/8b/14b           - OmniRoute (если настроен)
         - Работает оффлайн          - Mistral, DeepSeek, OpenRouter
```

### Поток данных:
```
welcome.html (JS) → POST /api/teamlead_query (SSE) → agent_manager.py
→ model_router.py → Ollama (qwen3:8b, GPU) → SSE stream → welcome.html
```

---

## 👥 Агенты

| Агент | Роль | Температура |
|-------|------|-------------|
| 👑 TeamLead | Координатор, анализ требований, диалог с пользователем | 0.7 |
| 🏗️ Architect | Архитектура, выбор технологий, структура файлов | 0.7 |
| ⚙️ Backend | Серверный код, API, базы данных | 0.3 |
| 🎨 Frontend | Пользовательский интерфейс, HTML/CSS/JS | 0.7 |
| 🚀 DevOps | Docker, CI/CD, инфраструктура | 0.3 |
| 🧪 Tester | Тесты, проверка качества | 0.3 |
| 📝 Documentalist | Документация, README | 0.7 |

### Уровни сложности:
- **zero** — для полных новичков, с аналогиями из реальной жизни
- **beginner** — знает основы, нужны объяснения "почему"
- **advanced** — опытный, только суть
- **standard** — базовый промпт

---

## 🚀 Запуск

```bash
# Web UI (рекомендуется)
python -m uvicorn web_ui.app:app --host 0.0.0.0 --port 8000

# CLI
python -m core.cli --project myapp --desc "REST API на FastAPI"

# Docker
docker compose up --build
```

---

## 📁 Структура проекта

```
ai-team-system/
├── core/                    # ЯДРО (29 Python файлов)
│   ├── main.py              # AITeamSystem — оркестратор
│   ├── agent_manager.py     # AgentManager — запуск агентов
│   ├── model_router.py      # ModelRouter — LLM + кэш
│   ├── learning_mode.py     # Обучение (5 шагов)
│   ├── hardware_detector.py # Авто-детект VRAM/RAM
│   └── ...                  # +24 модуля
├── web_ui/                  # WEB ИНТЕРФЕЙС (FastAPI)
│   ├── app.py               # Эндпоинты, SSE
│   └── templates/welcome.html  # Чат-UI
├── prompts/                 # ПРОМПТЫ (36 файлов)
│   └── roles/               # По ролям × 4 уровня
├── docs/                    # ДОКУМЕНТАЦИЯ (7 файлов)
├── tests/                   # ТЕСТЫ (12 файлов)
├── scripts/                 # УСТАНОВКА
├── templates/               # ШАБЛОНЫ
├── config/                  # КОНФИГИ
├── screenshots/             # СКРИНШОТЫ (24 PNG)
├── .ai-context/             # КОНТЕКСТ ДЛЯ AI
│   ├── PROJECT_STATE.md     # Текущее состояние
│   └── PROJECT_OVERVIEW.md  # Полное описание
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md                # ЭТОТ ФАЙЛ
```

---

## 🔌 Web API (FastAPI, порт 8000)

### GET эндпоинты:
| Путь | Назначение |
|------|------------|
| `/` | Главная страница |
| `/api/health` | Проверка статуса |
| `/api/hardware` | Информация о железе |
| `/api/start` | Создание сессии |
| `/api/stream` | SSE-стриминг |
| `/api/progress` | Прогресс обучения |
| `/api/download/{filename}` | Скачать Markdown |

### POST эндпоинты:
| Путь | Назначение |
|------|------------|
| `/api/teamlead_query` | SSE: диалог с TeamLead |
| `/api/create_project_stream` | SSE: запуск 7 агентов |
| `/api/agent/query` | Запрос к агенту |
| `/api/generate_clarify_questions` | Уточняющие вопросы |
| `/api/export` | Экспорт урока |
| `/api/lesson/step` | Шаг обучения |
| `/api/stop_build` | Остановить сборку |

---

## ❓ FAQ для новичков

**Q: Нужен ли опыт программирования?**  
A: Нет! Режим обучения объясняет всё простыми словами с аналогиями.

**Q: Нужен ли интернет?**  
A: Нет, с Ollama всё работает локально. Интернет нужен только для облачных API.

**Q: Какое железо нужно?**  
A: Минимум 4 ГБ RAM. Для локальных моделей — видеокарта с 6+ ГБ VRAM.

**Q: Это бесплатно?**  
A: Да! Ollama + qwen3 модели полностью бесплатны. Облачные API тоже имеют бесплатные тарифы.

**Q: Где сохраняются уроки?**  
A: В `~/ai-team-lessons/` в формате Markdown.

**Q: Можно ли переключить модель?**  
A: Да, через `.env` → `OLLAMA_MODEL=qwen3:14b` или `AI_MODE=cloud`.

---

## ⚙️ Конфигурация

```bash
# .env файл
OLLAMA_MODEL=qwen3:8b       # Модель для Ollama
HARDWARE_PROFILE=medium     # Профиль железа
AI_MODE=local               # local или cloud
LOG_LEVEL=INFO              # INFO или DEBUG
```

---

## 🧪 Тесты

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## 🗺️ Roadmap

### v2.0 (реализовано ✅)
- ✅ Обучающий режим для новичков
- ✅ Авто-детект железа
- ✅ FastAPI + SSE
- ✅ Экспорт Markdown-уроков
- ✅ Rate limiter + кэш ответов
- ✅ Exponential backoff fallback
- ✅ 7 агентов с 4 уровнями сложности
- ✅ Живой диалог с TeamLead
- ✅ Режим "Тур" для новичков

### v2.1 (планируется)
- [ ] OmniRoute интеграция (облачные модели)
- [ ] LOCAL ↔ CLOUD переключатель в UI
- [ ] Kanban dashboard
- [ ] MCP server support
- [ ] Self-improving agents
- [ ] Fallback цепочки (Ollama → Cloud)

---

## 🤝 Контрибьют

1. Fork репозитория
2. Создай ветку (`git checkout -b feature/amazing`)
3. Коммит (`git commit -m 'feat: add amazing'`)
4. Push (`git push origin feature/amazing`)
5. Pull Request

---

## 📄 Лицензия

MIT

---

**AI Team System v2.0 — Обучающая платформа, где AI объясняет AI**
