#!/bin/bash
# Setup для Linux/Mac

set -e

echo "🚀 Установка AI Team System"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.10+"
    exit 1
fi

# Проверка pip
if ! command -v pip &> /dev/null; then
    echo "❌ pip не найден"
    exit 1
fi

# Создание виртуального окружения (опционально)
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Проверка Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️ Ollama не найдена. Рекомендуется установить:"
    echo "   curl -fsSL https://ollama.ai/install.sh | sh"
else
    echo "✅ Ollama найдена: $(ollama --version)"
fi

# Создание .env
if [ ! -f ".env" ]; then
    echo "📝 Создание .env из .env.example..."
    cp .env.example .env
    echo "⚠️ Отредактируйте .env и добавьте API ключи (опционально)"
fi

# Создание папок
echo "📁 Создание папок..."
mkdir -p ~/.logs/ai_team
mkdir -p ~/projects

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Запуск:"
echo "  CLI:  python core/main.py --project-name myapp --requirements 'описание'"
echo "  Web:  python web_ui/app.py"
echo ""
echo "Документация: docs/QUICKSTART.md"
