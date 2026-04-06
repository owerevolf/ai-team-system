# 🤖 AI Team System

Мультиагентная система разработки ПО с AI агентами.

## 🎯 Возможности

- **7 AI агентов** — TeamLead, Architect, Backend, Frontend, DevOps, Tester, Documentalist
- **Автоматическое планирование** — анализ требований и создание плана работ
- **Параллельная разработка** — агенты работают одновременно
- **Web UI** — красивый интерфейс для управления проектами
- **Локальные модели** — работает с Ollama (без отправки кода в облако)
- **Git интеграция** — автоматические коммиты

## 📋 Быстрый старт

### 1. Установка

```bash
git clone https://github.com/yourname/ai-team-system
cd ai-team-system
pip install -r requirements.txt
```

### 2. Настройка Ollama

```bash
# Установите Ollama: https://ollama.ai
ollama pull qwen2.5-coder:7b
ollama run qwen2.5-coder:7b
>>> /set parameter num_ctx 8192
>>> /save qwen2.5-coder-8k
>>> /bye
```

### 3. Запуск

**CLI:**
```bash
python core/main.py --project-name myapp --requirements "REST API на Flask"
```

**Web UI:**
```bash
python web_ui/app.py
# Откройте http://localhost:5000
```

## 🏗️ Структура проекта

```
ai-team-system/
├── core/           # Ядро системы (оркестратор)
├── prompts/        # Промпты для агентов
├── config/         # Конфигурация профилей
├── web_ui/         # Flask веб-интерфейс
├── docs/           # Документация
├── scripts/        # Установочные скрипты
└── templates/      # Шаблоны проектов
```

## 👥 Агенты

| Агент | Описание |
|-------|----------|
| 👑 TeamLead | Координация, планирование |
| 🏗️ Architect | Архитектура системы |
| ⚙️ Backend | Серверный код |
| 🎨 Frontend | Интерфейс |
| 🚀 DevOps | Docker, CI/CD |
| 🧪 Tester | Тесты |
| 📝 Documentalist | Документация |

## ⚙️ Профили железа

- **Light** — 8GB RAM, 4K context, 2 агента
- **Medium** — 16GB RAM, 8K context, 4 агента (рекомендуется)
- **Heavy** — 32GB+ RAM, 16K context, 8 агентов

## 📦 Требования

- Python 3.10+
- Ollama (для локальных моделей)
- Опционально: API ключи Anthropic/OpenAI

## 📚 Документация

- [Быстрый старт](docs/QUICKSTART.md)
- [Подробная установка](docs/INSTALLATION.md)
- [Архитектура](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Решение проблем](docs/TROUBLESHOOTING.md)

## 🤝 Контрибьют

См. [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## 📄 Лицензия

MIT
