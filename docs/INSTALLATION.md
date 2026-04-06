# 📦 Подробная установка

## Системные требования

### Минимальные
- Python 3.10+
- 8 GB RAM
- 10 GB свободного места

### Рекомендуемые
- 16 GB RAM
- GPU с 8+ GB VRAM (для локальных моделей)
- SSD диск

## Установка Python зависимостей

```bash
pip install -r requirements.txt
```

## Установка Ollama

### Linux/Mac
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Скачайте с https://ollama.ai/download

### Проверка
```bash
ollama --version
```

## Установка моделей

### Для слабого железа (8GB VRAM)
```bash
ollama pull qwen2.5-coder:7b
```

### Для среднего железа (12GB VRAM)
```bash
ollama pull huihui_ai/qwen3.5-abliterated:27b-Claude
```

### Для мощного железа (24GB+ VRAM)
```bash
ollama pull qwen2.5-coder:32b
```

## Настройка контекста

Ollama по умолчанию использует маленький контекст. Увеличьте его:

```bash
ollama run qwen2.5-coder:7b
```

Внутри терминала Ollama:
```
>>> /set parameter num_ctx 8192
>>> /save qwen2.5-coder-8k
>>> /bye
```

## API ключи (опционально)

Для ускорения работы добавьте ключи в `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

## Структура проектов

Проекты создаются в `~/projects/`:

```
~/projects/myapp_20240401_120000/
├── code/
│   ├── backend/
│   ├── frontend/
│   └── shared/
├── tests/
├── docs/
├── .agents/
├── .logs/
└── report.json
```
