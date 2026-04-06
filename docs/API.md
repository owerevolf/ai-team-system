# API для разработчиков

## Эндпоинты Web UI

### Система

#### GET /api/system/info
Информация о железе

```json
{
  "cpu": { "cores": 8, "threads": 16, "usage_percent": 45 },
  "ram": { "total_gb": 32, "available_gb": 16 },
  "gpu": { "name": "NVIDIA RTX 3060", "vram_gb": 8 },
  "ollama": { "available": true, "models": ["qwen2.5-coder:7b"] }
}
```

#### GET /api/models
Список доступных моделей

```json
{
  "ollama": ["qwen2.5-coder:7b", "codellama:7b"],
  "anthropic": ["claude-3-5-sonnet"]
}
```

### Проекты

#### GET /api/projects
Список всех проектов

```json
[
  { "name": "myapp_20240401_120000", "path": "/home/user/projects/myapp_20240401_120000" }
]
```

#### POST /api/project/create
Создание нового проекта

**Request:**
```json
{
  "name": "myapp",
  "requirements": "REST API на Flask",
  "profile": "medium"
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Проект myapp запущен"
}
```

#### GET /api/project/{name}/logs
Логи проекта

```json
[
  { "name": "agents.log", "content": "2024-04-01 | teamlead | ..." }
]
```

#### GET /api/project/{name}/files
Список файлов проекта

```json
["code/backend/main.py", "code/frontend/index.html", ...]
```

## Python API

```python
from core.main import AITeamSystem

# Инициализация
system = AITeamSystem(profile="medium")

# Информация о системе
info = system.scan_hardware()

# Создание проекта
project = system.create_project("myapp", "requirements.md")

# Полный цикл
report = system.run_full_pipeline("myapp", "requirements.md")
```
