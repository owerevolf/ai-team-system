# CLI Task Manager

## Описание
Консольное приложение для управления задачами.

## Требования
- Python CLI с click или argparse
- SQLite для хранения задач
- Команды: add, list, done, delete, search

## Команды
- `task add "Название" --priority high` — Добавить задачу
- `task list` — Список всех задач
- `task list --filter done` — Только выполненные
- `task done 1` — Отметить задачу выполненной
- `task delete 1` — Удалить задачу
- `task search "ключевое слово"` — Поиск

## Модель Task
- id (int, PK)
- title (string)
- description (text, optional)
- priority (enum: low/medium/high)
- status (enum: pending/done)
- created_at (datetime)
- completed_at (datetime, optional)

## Тесты
- pytest для всех команд
- Тест фильтрации и поиска

## Инфраструктура
- setup.py / pyproject.toml
- requirements.txt
