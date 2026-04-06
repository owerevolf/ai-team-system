# 🚀 Быстрый старт за 5 минут

## Шаг 1: Установка зависимостей

```bash
cd ai-team-system
pip install -r requirements.txt
```

## Шаг 2: Настройка Ollama

```bash
# Установи Ollama (если ещё нет)
curl -fsSL https://ollama.ai/install.sh | sh

# Скачай модель
ollama pull qwen2.5-coder:7b

# Увеличь контекст (важно!)
ollama run qwen2.5-coder:7b
>>> /set parameter num_ctx 8192
>>> /save qwen2.5-coder-8k
>>> /bye
```

## Шаг 3: Конфигурация

```bash
cp .env.example .env
# Отредактируй .env, добавив свои API ключи (опционально)
```

## Шаг 4: Запуск

**CLI режим:**
```bash
python core/main.py --project-name myapp --requirements "Веб-приложение на Flask"
```

**Web UI:**
```bash
python web_ui/app.py
# Открой http://localhost:5000
```

## Готово! 🎉

Система создаст проект в `~/projects/myapp_YYYYMMDD_HHMMSS/`
