# 🤖 AI Team System v2.1

**Мультиагентная платформа разработки ПО** — 7 AI-агентов создают проекты с нуля, объясняя каждый шаг.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![Tests](https://img.shields.io/badge/Tests-143%20passed-brightgreen.svg)

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
| ☁️ Мульти-провайдер | OpenRouter, Ollama, OmniRoute — fallback цепочки |
| 📥 Экспорт уроков | Markdown-гайды с примерами |
| 🛡️ Безопасность | Песочница, whitelist команд, логирование |
| ⚡ SSE-стриминг | Ответы в реальном времени |
| 💬 Живой диалог | TeamLead ведёт диалог, уточняет детали, предлагает идеи |
| 🎭 4 уровня сложности | zero / beginner / advanced / standard |
| 🎨 Цветные агенты | Каждый агент имеет свой цвет в баре |
| 🔀 Hot-swap моделей | Переключение моделей без перезагрузки сервера |
| 📖 Интерактивная инструкция | Вкладка с пошаговым гайдом |

---

## 🆕 v2.1 — Что нового

### Исправлено
- ✅ Удалено дублирование JS кода (welcome.html: 2290→1924 строк)
- ✅ Исправлен тест `test_init_light_profile` (groq больше нет в priority)
- ✅ `fallbackBuild` вызывал несуществующий `/api/agent_response` → `/api/agent/query`
- ✅ Обновлена Ollama модель на `qwen3-coder:480b-cloud`

### Улучшено
- ✅ Цветные индикаторы для каждого агента в баре
- ✅ Читаемые имена моделей в настройках (ID мелким шрифтом)
- ✅ Цветные бейджи типа модели (FREE/REASONING/CODING/STRONG/FAST)
- ✅ Читаемый формат контекста (256K, 1.0M)
- ✅ Разные иконки для кнопок (🔌 Проверить, 🔄 Обновить)
- ✅ Анимация появления табов
- ✅ Переключение моделей в реальном времени без перезагрузки

### Архитектура
- ✅ Приоритет конфигурации из `config/agent_models.json` над model_registry
- ✅ Поддержка `agent_models.json` для пользовательских настроек моделей
- ✅ SSH ключ для GitHub

---

## 📸 Скриншоты

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
         - qwen3:4b/8b/14b           - OpenRouter (29+ бесплатных)
         - Работает оффлайн          - OmniRoute (опционально)
                                     - Google, Anthropic, OpenAI
```

### Поток данных:
```
welcome.html (JS) → POST /api/teamlead_query (SSE) → agent_manager.py
→ model_router.py → Ollama/OpenRouter → SSE stream → welcome.html
```

### API Endpoints:
```
GET  /api/status          — статус сервера и провайдеров
GET  /api/config          — текущая конфигурация
POST /api/config          — сохранение конфигурации (hot-reload)
GET  /api/providers       — список провайдеров
GET  /api/models          — список моделей
GET  /api/agents/config   — конфигурация агентов
GET  /api/hardware        — информация о железе
POST /api/teamlead_query  — запрос к TeamLead (SSE)
POST /api/create_project_stream — сборка проекта (SSE)
POST /api/agent/query     — запрос к агенту
POST /api/stop_build      — остановка сборки
```

---

## 👥 Агенты

| Агент | Роль | Температура | Цвет |
|-------|------|-------------|------|
| 👑 TeamLead | Координатор, анализ требований, диалог с пользователем | 0.7 | 🟣 |
| 🏗️ Architect | Архитектура, структура проекта, выбор технологий | 0.5 | 🔵 |
| ⚙️ Backend | Серверный код, API, базы данных | 0.3 | 🩷 |
| 🎨 Frontend | Интерфейс, HTML/CSS/JS, дизайн | 0.7 | 🟠 |
| 🚀 DevOps | Docker, CI/CD, инфраструктура | 0.3 | 🟢 |
| 🧪 Tester | Тесты, проверка качества, QA | 0.2 | 🟡 |
| 📝 Documentalist | Документация, README, комментарии | 0.7 | 🟪 |

Каждый агент имеет свой цвет в баре и в сообщениях чата.

---

## 🔧 Настройка

### API ключи (.env)
```env
# OpenRouter — агрегатор (29+ бесплатных моделей)
OPENROUTER_API_KEY=sk-or-v1-...

# Ollama — локальные модели
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-coder:480b-cloud

# Режим: local (Ollama-first) или cloud (OpenRouter-first)
AI_MODE=local
```

### Переключение моделей в реальном времени
1. Откройте вкладку **⚙️ Настройки**
2. Выберите провайдера
3. Выберите модель для каждого агента
4. Нажмите **💾 Сохранить** — конфигурация применится без перезагрузки

---

## 🧪 Тесты

```bash
# Запуск всех тестов
OLLAMA_BASE_URL="" AI_MODE=cloud HARDWARE_PROFILE=light PYTHONPATH=. pytest tests/ -v

# Результат: 143 passed ✅
```

---

## 📁 Структура проекта

```
ai-team-system/
├── core/                   # Ядро системы
│   ├── model_router.py     # Мульти-провайдер маршрутизация v5.0
│   ├── agent_manager.py    # Управление агентами
│   ├── model_registry.py   # Реестр моделей
│   ├── agent_skills.py     # Скиллы агентов
│   ├── hardware_detector.py # Детектор железа
│   ├── export_lesson.py    # Экспорт уроков
│   └── skills/             # Промпты скиллов (LVL99)
├── web_ui/                 # Веб-интерфейс
│   ├── app.py              # FastAPI приложение
│   ├── static/             # CSS, JS
│   └── templates/
│       └── welcome.html    # Главная страница
├── tests/                  # Тесты (108 passed)
├── config/                 # Конфигурация
│   ├── agent_models.json   # Пользовательские модели
│   └── profiles.yaml       # Профили железа
├── scripts/                # Скрипты установки
├── docs/                   # Документация
└── screenshots/            # Скриншоты UI
```

---

## 🚀 Планы (v2.2+)

- [ ] Webhooks для интеграции с GitHub/GitLab
- [ ] Расширенная аналитика использования агентов
- [ ] Поддержка пользовательских плагинов через UI
- [ ] Мульти-языковая поддержка (i18n)

---

## 📄 Лицензия

MIT
