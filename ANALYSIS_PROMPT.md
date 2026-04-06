# ПРОМПТ ДЛЯ GPT/CLAUDE/DEEPSEEK — Анализ AI Team System

## КОНТЕКСТ

Это мультиагентная система разработки ПО. Репозиторий: https://github.com/owerevolf/ai-team-system

Структура:
- `core/` — Python оркестратор (main.py, agent_manager.py, model_router.py, database.py, etc.)
- `prompts/roles/` — Промпты для 7 агентов (teamlead, architect, backend, frontend, devops, tester, documentalist)
- `web_ui/` — Flask веб-интерфейс
- `config/` — YAML конфиги профилей

## ЗАДАЧА

Проанализируй код и дай рекомендации по:

### 1. Архитектура
- Правильная ли архитектура для multi-agent системы?
- Нужны ли изменения?

### 2. Промпты агентов
- Достаточно ли детализированы промпты?
- Что добавить для лучшей работы?

### 3. Orchestrator (main.py)
- Логика управления потоком?
- Обработка ошибок?
- Параллелизация агентов?

### 4. Model Router
- Поддержка разных провайдеров (Ollama, OpenAI, Anthropic)?
- Что улучшить?

### 5. Практические улучшения
- Конкретные примеры кода для улучшений
- Какие фичи добавить?

## ВЫХОДНОЙ ФОРМАТ

```json
{
  "overall_score": "8/10",
  "critical_issues": ["список"],
  "architecture": {
    "score": "X/10",
    "issues": ["..."],
    "suggestions": ["..."]
  },
  "prompts": {
    "score": "X/10",
    "issues": ["..."],
    "suggestions": ["具体的改进建议 with examples"]
  },
  "orchestrator": {
    "score": "X/10",
    "issues": ["..."],
    "code_suggestions": ["..."]
  },
  "new_features": ["список с приоритетами"],
  "priority_fixes": ["что исправить в первую очередь"]
}
```

## ВАЖНО

1. Будь конкретным — давай примеры кода
2. Оцени реалистично — не хвали без причины
3. Фокус на PRACTICAL улучшениях
4. Учитывай что модели работают локально через Ollama
