# ALL TEAM ROLES

## QUICK REFERENCE

| Agent | Role | Main Tasks |
|-------|------|------------|
| teamlead | Координатор | Планирование, контроль |
| architect | Архитектор | Архитектура, технологии |
| backend | Backend Dev | API, логика, базы данных |
| frontend | Frontend Dev | UI, интерфейсы |
| devops | DevOps | Docker, CI/CD, деплой |
| tester | QA | Тесты, качество |
| documentalist | Writer | Документация |

## WORKFLOW

```
teamlead → architect → backend/frontend/devops/tester → documentalist → teamlead (final report)
```

## AGENT COMMUNICATION

Все агенты общаются через JSON:

```json
{
  "from": "backend",
  "to": "teamlead",
  "type": "task_complete",
  "data": {
    "task_id": 3,
    "files_created": ["api/users.py", "models/user.py"]
  }
}
```

## ERROR HANDLING

Если агент не справляется:
1. Повторить с уточнениями
2. Упростить задачу
3. Переназначить другому агенту
4. Задокументировать проблему
