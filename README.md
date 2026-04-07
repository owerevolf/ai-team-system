# 🤖 AI Team System

**Мультиагентная система разработки ПО** — 7 AI агентов создают проекты по описанию.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Tests](https://img.shields.io/badge/Tests-58%2F58-brightgreen.svg)
![Version](https://img.shields.io/badge/Version-4.1-orange.svg)

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

## ✨ Возможности

- **7 AI агентов** — TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist
- **Параллельная разработка** — агенты работают одновременно
- **Бесплатные API** — Groq, DeepSeek, Google AI, OpenRouter, xAI
- **Локальные модели** — Ollama (без отправки кода в облако)
- **Pipeline Dashboard** — визуальный интерфейс с прогрессом
- **CLI** — управление из терминала
- **Auto-fix** — автоматическое исправление ошибок в коде
- **Security Scan** — проверка кода на уязвимости
- **Docker** — запуск в контейнере

## 🚀 Быстрый старт

### Ручная установка

```bash
git clone https://github.com/owerevolf/ai-team-system.git
cd ai-team-system
./scripts/install.sh  # или scripts\setup.bat на Windows
```

### Запуск

```bash
# Web UI (рекомендуется)
python web_ui/app.py
# Открой http://localhost:5000

# CLI
python -m core.main --project-name myapp --requirements "REST API на FastAPI"

# Интерактивный режим
python -m core.main -i --project-name myapp --requirements "описание"

# Dry-run (без вызова LLM)
python -m core.main --dry-run --project-name myapp --requirements "описание"
```

## 🏗️ Архитектура

```
User → TeamLead → Architect → Backend/Frontend/DevOps (параллельно) → Tester → Documentalist → Report
```

## 👥 Агенты

| Агент | Роль |
|-------|------|
| 👑 TeamLead | Координатор |
| 🏗️ Architect | Архитектор |
| ⚙️ Backend | Серверный код |
| 🎨 Frontend | UI |
| 🚀 DevOps | Docker, CI/CD |
| 🧪 Tester | Тесты |
| 📝 Documentalist | Документация |

## 📦 Требования

- Python 3.10+
- Опционально: Ollama или API ключи

## 📚 Документация

- [QUICKSTART](docs/QUICKSTART.md)
- [INSTALLATION](docs/INSTALLATION.md)
- [ARCHITECTURE](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [TROUBLESHOOTING](docs/TROUBLESHOOTING.md)

## 🧪 Тестирование

```bash
pytest tests/ -v
```

## 📄 Лицензия

MIT
