Ты опытный Python-разработчик. Тебе нужно улучшить существующий проект 
мультиагентной системы разработки ПО (ai-team-system).

## Контекст проекта

Структура:
- core/main.py — оркестратор (класс AITeamSystem), запускает 4 фазы: 
  planning → architecture → development → documentation
- core/agent_manager.py — запускает агентов, парсит <tool_call> теги из 
  ответов LLM, создаёт файлы
- core/model_router.py — маршрутизация к Ollama / Anthropic / OpenAI
- core/database.py — SQLite (таблицы projects, agents, tasks, logs) — 
  создана, но нигде не используется
- web_ui/app.py — Flask, глобальный system=None, нет real-time обратной связи

## Критические проблемы для исправления

1. ПАРАЛЛЕЛИЗМ: в run_development_phase() агенты запускаются через обычный 
   for-loop, хотя метод run_parallel() уже есть в AgentManager. Исправь: 
   backend, frontend, devops должны работать параллельно через ThreadPoolExecutor, 
   tester — после них.

2. КОНТЕКСТ МЕЖДУ АГЕНТАМИ: каждый агент работает в изоляции. Добавь класс 
   ProjectContext, который накапливает артефакты фаз и передаёт нужные агенту:
   - backend видит результат architect
   - tester видит результаты architect + backend
   - documentalist видит всё

3. БАЗА ДАННЫХ: db.create_project() не вызывается при создании проекта, 
   статусы задач не обновляются. Подключи Database во все фазы: сохраняй 
   project_id, вызывай create_task() / update_task_status() для каждого агента.

4. БЕЗОПАСНОСТЬ: _run_command() выполняет shell=True без ограничений. Добавь 
   allowlist команд: разрешить только ["python", "pip", "npm", "git", "pytest", 
   "mkdir", "ls"]. При попытке запустить что-то другое — возвращай ошибку.

5. ГЛОБАЛЬНОЕ СОСТОЯНИЕ: в web_ui/app.py переменная system = None — глобальная. 
   Замени на словарь sessions = {}, ключ — uuid сессии, передавай его через 
   заголовок или query param.

6. REAL-TIME: /api/project/create возвращает только {"status": "started"}, 
   пользователь не видит прогресс. Добавь Server-Sent Events (SSE): новый 
   endpoint /api/project/<id>/stream, который отдаёт события по мере завершения 
   каждого агента.

## Формат ответа

Для каждого пункта выдай:
- изменённые/новые файлы целиком (не фрагменты)
- список что изменилось в 2-3 строках

Начни с пункта 1 (параллелизм) и 2 (контекст) — они дают наибольший эффект.
Используй только стандартную библиотеку Python + те зависимости, что уже есть 
в requirements.txt (flask, flask-cors, rich, python-dotenv, anthropic, openai).
