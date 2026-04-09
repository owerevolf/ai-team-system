# PROJECT_STATE.md
# Вставляй этот файл в начало каждого разговора со мной — экономит токены

---

## Проект
**AI Team System** — мультиагентная система (7 агентов) для создания проектов локально.
GitHub: https://github.com/owerevolf/ai-team-system

## Железо пользователя
VRAM: 8 ГБ | RAM: 15.54 ГБ | Профиль: medium

## Стек
- Backend: FastAPI (Python)
- Frontend: HTML + vanilla JS + CSS (тёмная тема)
- LLM: Ollama (локально)
- Порт: 8000

## Структура (ключевые файлы)
```
web_ui/
  app.py              ← FastAPI сервер, эндпоинты
  templates/
    welcome.html      ← ГЛАВНЫЙ UI (сейчас меняем)
  static/
    app.js            ← клиентская логика
    style.css         ← стили
core/
  main.py             ← AITeamSystem, точка входа
  agent_manager.py    ← управление агентами, метод run_agent(agent_name, task, context)
  learning_mode.py    ← режим обучения (не трогаем)
  model_router.py     ← маршрутизация LLM
  export_lesson.py    ← экспорт markdown
```

## Агенты (AgentManager)
- teamlead, architect, backend, frontend, devops, tester, documentalist
- Метод: `manager.run_agent(agent_name, task, context=None)` → Dict с полями status, files_created, summary

## Что сделано (хронология)

### Сессия 1-10
- FastAPI сервер с SSE-стримингом
- Тёмная тема, тур для новичков
- hardware_detector, learning_mode, export_lesson
- ModelRouter v4 с кэшем и rate limiter

### Сессия 11 (сейчас)
- Замена формы на чат-интерфейс
- 3 файла: welcome.html, app.js, style.css
- Эндпоинты: /api/hardware, /api/create_project_stream, /api/download/{filename}

## Что НЕ трогаем
- core/learning_mode.py (обучающий режим — отдельная задача)
- Промты агентов (отдельная задача)

## Следующие задачи (приоритет)

### СРОЧНО — нужно сделать в backend (web_ui/app.py):
1. Эндпоинт `POST /api/create_project_stream` → SSE стриминг работы агентов
2. Эндпоинт `GET /api/hardware` → возвращает {profile, vram_gb, ram_gb}
3. Эндпоинт `GET /api/download/{filename}` → скачать markdown результат

### ПОТОМ:
4. Уточняющие вопросы генерировать через LLM (не хардкод)
5. Показывать реальный код от агентов, не только summary
6. Режим "Тур" для новичков (объяснения агентов)

## Решения принятые (не обсуждаем снова)
- UI: чат, не форма
- Тема: тёмная (#0d0d0f фон)
- Шрифты: JetBrains Mono + Unbounded
- Уровни: 3 (zero / beginner / advanced)
- Обучение: отдельный слой, не мешать с созданием проектов

## Как использовать этот файл
Скопируй всё содержимое и вставь в начало нового чата со словами:
"Вот контекст проекта, продолжаем:"


## Последнее что сделали (сессия сегодня)
- Исправлен app.py: теперь level передаётся в run_agent()
- Промты _zero и _beginner созданы для всех агентов
- НЕ проверено: работает ли teamlead_zero.md после фикса
- Следующий шаг: проверить что teamlead_zero начинает с представления,
  потом добавить "игровое предложение" в teamlead_zero.md
