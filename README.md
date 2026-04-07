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
| 🧠 Авто-детект железа | Выбор модели по VRAM/RAM |
| 💬 Оффлайн-первый | Работает через Ollama без интернета |
| ☁️ Fallback на облако | 5+ бесплатных API (Groq, DeepSeek, Google, OpenRouter, xAI) |
| 📥 Экспорт уроков | Markdown-гайды с примерами |
| 🛡️ Безопасность | Песочница, whitelist команд, логирование |
| ⚡ SSE-стриминг | Ответы в реальном времени |

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
User → Welcome UI → Tour (5 шагов) → Project → 7 Agents → Markdown Lesson
                           ↓
                    Hardware Detect → Model Selection
                           ↓
                    Local (Ollama) or Cloud (API)
```

---

## 👥 Агенты

| Агент | Роль |
|-------|------|
| 👑 TeamLead | Координатор, анализ требований |
| 🏗️ Architect | Архитектура, выбор технологий |
| ⚙️ Backend | Серверный код, API |
| 🎨 Frontend | Пользовательский интерфейс |
| 🚀 DevOps | Docker, CI/CD, инфраструктура |
| 🧪 Tester | Тесты, проверка качества |
| 📝 Documentalist | Документация, README |

---

## 🚀 Запуск

```bash
# Web UI (рекомендуется)
python -m uvicorn web_ui.app:app --host 0.0.0.0 --port 8000

# CLI
python -m core.cli --project myapp --desc "REST API на FastAPI"
```

---

## 📁 Структура проекта

```
ai-team-system/
├── core/                    # Ядро системы
│   ├── hardware_detector.py  # Детект железа
│   ├── learning_mode.py      # Режим обучения (5 шагов)
│   ├── model_router.py       # Маршрутизация LLM + кэш
│   ├── export_lesson.py      # Экспорт Markdown
│   └── ...
├── web_ui/                   # FastAPI сервер
│   ├── app.py               # Маршруты, SSE
│   ├── templates/welcome.html
│   └── static/
│       ├── style.css
│       └── app.js
├── scripts/                  # Установщики
│   ├── install.sh           # Linux/macOS
│   └── install.ps1          # Windows
├── config/                   # Конфиги
│   └── config.yaml
├── tests/                    # pytest
├── templates/                # Шаблоны проектов
├── requirements.txt
├── .env.example
└── README.md
```

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

### v2.0 (сейчас)
- ✅ Обучающий режим для новичков
- ✅ Авто-детект железа
- ✅ FastAPI + SSE
- ✅ Экспорт Markdown-уроков
- ✅ Rate limiter + кэш ответов
- ✅ Exponential backoff fallback

### v2.1 (планируется)
- [ ] Kanban dashboard
- [ ] MCP server support
- [ ] Self-improving agents

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
