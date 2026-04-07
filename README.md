# 🤖 AI Team System

**Мультиагентная система разработки ПО** — 7 AI агентов создают проекты по описанию.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Tests](https://img.shields.io/badge/Tests-58%2F58-brightgreen.svg)
![Version](https://img.shields.io/badge/Version-5.0-orange.svg)

[![Try in Docker](https://img.shields.io/badge/Try%20in-Docker-2496ED?logo=docker)](https://github.com/owerevolf/ai-team-system)
[![Stars](https://img.shields.io/github/stars/owerevolf/ai-team-system?style=social)](https://github.com/owerevolf/ai-team-system)

---

## ⚡ Установка в 1 команду

### Linux / Mac
```bash
curl -fsSL https://raw.githubusercontent.com/owerevolf/ai-team-system/main/scripts/install.sh | bash
```

### Windows
Скачай и запусти: [setup.bat](https://raw.githubusercontent.com/owerevolf/ai-team-system/main/scripts/setup.bat)

### Docker
```bash
docker run -p 5000:5000 -v ~/projects:/app/projects ghcr.io/owerevolf/ai-team-system:latest
```

---

## 🌟 Почему AI Team System?

| Фича | AI Team System | CrewAI | AutoGen | OpenDevin |
|------|:---:|:---:|:---:|:---:|
| Полностью локально (Ollama) | ✅ | ❌ | ❌ | ❌ |
| 7 специализированных агентов | ✅ | ❌ | ❌ | ✅ |
| Параллельная разработка | ✅ | ❌ | ✅ | ❌ |
| Web UI Dashboard | ✅ | ❌ | ❌ | ✅ |
| Бесплатные API (5+) | ✅ | ❌ | ❌ | ❌ |
| Auto-fix кода | ✅ | ❌ | ❌ | ✅ |
| Security Scan | ✅ | ❌ | ❌ | ❌ |
| One-click установка | ✅ | ❌ | ❌ | ❌ |
| Long-term memory | ✅ | ✅ | ❌ | ❌ |
| RAG система | ✅ | ❌ | ❌ | ❌ |

---

## ✨ Возможности

### 🤖 Агенты
- **7 AI агентов** — TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist
- **Параллельная разработка** — Backend, Frontend, DevOps работают одновременно
- **Разные модели на агента** — TeamLead на дешёвой, Backend на мощной

### 🧠 Интеллект
- **Long-term memory** — агенты запоминают прошлые проекты
- **RAG система** — поиск по шаблонам и документации
- **Auto-fix** — автоматическое исправление ошибок в коде
- **Fallback моделей** — если одна модель не работает, пробует другую

### 🛡️ Безопасность
- **Sandbox** — проверка кода перед выполнением
- **Security Scan** — bandit + safety + поиск секретов
- **Command whitelist** — только безопасные shell команды

### 🖥️ Интерфейс
- **Pipeline Dashboard** — визуальный прогресс в реальном времени
- **Reasoning Trace** — отслеживание хода мыслей агентов
- **CLI** — управление из терминала
- **SSE** — real-time события

### 🚀 Инфраструктура
- **Docker** — запуск в контейнере
- **One-click установка** — Linux, Mac, Windows
- **CI/CD** — GitHub Actions
- **ZIP Export** — экспорт проекта

---

## 🏗️ Архитектура

```mermaid
graph LR
    A[User] --> B[TeamLead]
    B --> C[Architect]
    C --> D[Backend]
    C --> E[Frontend]
    C --> F[DevOps]
    D --> G[Tester]
    E --> G
    F --> G
    G --> H[Documentalist]
    H --> I[Report]
```

```
User → TeamLead → Architect → [Backend, Frontend, DevOps] → Tester → Documentalist → Report
```

---

## 👥 Агенты

| Агент | Роль | Модель (medium) |
|-------|------|-----------------|
| 👑 TeamLead | Координатор | qwen3:8b |
| 🏗️ Architect | Архитектор | qwen3:8b |
| ⚙️ Backend | Серверный код | qwen3:8b |
| 🎨 Frontend | UI | qwen3:8b |
| 🚀 DevOps | Docker, CI/CD | qwen3:8b |
| 🧪 Tester | Тесты | qwen3:8b |
| 📝 Documentalist | Документация | qwen3:8b |

---

## 🚀 Быстрый старт

```bash
git clone https://github.com/owerevolf/ai-team-system.git
cd ai-team-system
./scripts/install.sh  # или scripts\setup.bat на Windows
```

### Запуск

```bash
# Web UI
python web_ui/app.py
# http://localhost:5000

# CLI
python -m core.main --project-name myapp --requirements "REST API на FastAPI"

# Интерактивный режим
python -m core.main -i --project-name myapp --requirements "описание"

# Dry-run (без LLM)
python -m core.main --dry-run --project-name myapp --requirements "описание"
```

---

## 📦 Поддерживаемые модели

### Локальные (Ollama)
- qwen3:4b / 8b / 14b / 32b
- qwen2.5-coder:3b / 7b / 32b
- codellama:7b / 13b
- llama3.2:3b

### Бесплатные API
- **Groq** — llama-3.3-70b (30 RPM)
- **DeepSeek** — deepseek-chat (5M tokens free)
- **Google AI** — gemini-2.0-flash (бесплатно)
- **OpenRouter** — deepseek-r1:free
- **xAI** — grok-4 ($25 кредитов)

### Платные API
- **Anthropic** — claude-3.5-sonnet
- **OpenAI** — gpt-4o

---

## ⚙️ Профили железа

| Профиль | RAM | VRAM | Агенты | Модели |
|---------|-----|------|--------|--------|
| Light | 8GB | 4GB | 2 | 3B параметры |
| Medium | 16GB | 8GB | 4 | 7B параметры |
| Heavy | 32GB+ | 16GB+ | 8 | API (70B+) |

---

## 📁 Структура проекта

```
ai-team-system/
├── core/                  # Ядро системы
│   ├── main.py           # Оркестратор
│   ├── agent_manager.py  # Управление агентами
│   ├── model_router.py   # Маршрутизация LLM
│   ├── memory.py         # Long-term memory
│   ├── rag.py            # RAG система
│   ├── event_bus.py      # Event-driven bus
│   ├── sandbox.py        # Code sandbox
│   └── reasoning_trace.py # Reasoning trace
├── prompts/roles/        # Промпты 7 агентов
├── web_ui/               # Flask веб-интерфейс
├── tests/                # 58+ тестов
├── scripts/              # Install скрипты
└── templates/            # Шаблоны проектов
```

---

## 🗺️ Roadmap

### v5.1 (сейчас)
- ✅ Авто-детект железа в install.sh
- ✅ Проактивный fallback на облако
- ✅ Режим обучения для новичков
- ✅ Переключатель режимов (simple/learning/advanced)
- ✅ Обновление на qwen3:8b

### v5.2 (планируется)
- [ ] Kanban dashboard
- [ ] MCP server support
- [ ] Self-improving agents
- [ ] Multi-user collaboration

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

**Made with ❤️ by AI Team System — полностью написано AI агентами**
