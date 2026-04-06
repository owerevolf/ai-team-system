# 🤖 AI Team System

**Мультиагентная система разработки ПО** — 7 AI агентов создают проекты по описанию.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Возможности

- **7 AI агентов** — TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist
- **Параллельная разработка** — агенты работают одновременно
- **Бесплатные API** — Groq, DeepSeek, Google AI, OpenRouter, xAI
- **Локальные модели** — Ollama (qwen2.5-coder, codellama)
- **Web UI** — красивый интерфейс в браузере
- **CLI** — управление из терминала
- **Real-time события** — SSE для отслеживания прогресса

## 🚀 Быстрый старт

### 1. Установка

```bash
git clone https://github.com/owerevolf/ai-team-system.git
cd ai-team-system
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Запуск

**Web UI:**
```bash
python web_ui/app.py
# Открой http://localhost:5000
```

**CLI:**
```bash
python -m core.main --project-name myapp --requirements "REST API на FastAPI"
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
