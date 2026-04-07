#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Team System — One-Click Installer
# Linux/Mac
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🤖 AI Team System — Installer                    ║"
echo "║        Мультиагентная система разработки ПО             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ─── 1. Проверка ОС ───
OS=$(uname -s)
log_info "ОС: $OS"

# ─── 2. Проверка Python ───
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version | awk '{print $2}')
    log_ok "Python найден: $PY_VERSION"
else
    log_warn "Python не найден. Устанавливаю..."
    if [ "$OS" = "Darwin" ]; then
        brew install python3
    else
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
    fi
    log_ok "Python установлен"
fi

# ─── 3. Создание директории ───
INSTALL_DIR="$HOME/ai-team-system"
if [ -d "$INSTALL_DIR" ]; then
    log_warn "Папка уже существует: $INSTALL_DIR"
    read -p "Перезаписать? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        log_info "Использую существующую установку"
        cd "$INSTALL_DIR"
        source venv/bin/activate 2>/dev/null || true
        exec "$@"
        exit 0
    fi
fi

log_info "Создаю папку: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# ─── 4. Клонирование репозитория ───
log_info "Скачиваю проект..."
if command -v git &> /dev/null; then
    git clone https://github.com/owerevolf/ai-team-system.git .
    log_ok "Проект скачан"
else
    log_warn "Git не найден. Устанавливаю..."
    if [ "$OS" = "Darwin" ]; then
        brew install git
    else
        sudo apt install -y git
    fi
    git clone https://github.com/owerevolf/ai-team-system.git .
    log_ok "Git установлен, проект скачан"
fi

# ─── 5. Виртуальное окружение ───
log_info "Создаю виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate
log_ok "Виртуальное окружение создано"

# ─── 6. Установка зависимостей ───
log_info "Устанавливаю зависимости..."
pip install -r requirements.txt -q
log_ok "Зависимости установлены"

# ─── 7. Проверка Ollama ───
if command -v ollama &> /dev/null; then
    log_ok "Ollama найдена"
    
    # Проверка модели
    if ollama list 2>/dev/null | grep -q "qwen2.5-coder"; then
        log_ok "Модель qwen2.5-coder найдена"
    else
        log_warn "Модель не найдена. Скачиваю qwen2.5-coder:7b..."
        log_info "Это может занять несколько минут..."
        ollama pull qwen2.5-coder:7b
        log_ok "Модель скачана"
    fi
else
    log_warn "Ollama не найдена"
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  Ollama — локальный сервер для AI моделей               ║"
    echo "║  Без неё система не сможет работать офлайн              ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    read -p "Установить Ollama? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
        log_ok "Ollama установлена"
        
        log_info "Скачиваю модель..."
        ollama pull qwen2.5-coder:7b
        log_ok "Модель скачана"
    else
        log_warn "Ollama не установлена. Можно использовать облачные API."
    fi
fi

# ─── 8. Конфигурация ───
if [ ! -f ".env" ]; then
    cp .env.example .env
    log_ok "Конфиг .env создан"
fi

# ─── 9. Создание папок ───
mkdir -p ~/.logs/ai_team
mkdir -p ~/projects
log_ok "Папки созданы"

# ─── 10. Финал ───
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    ✅ ГОТОВО!                            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Запуск:"
echo ""
echo "  cd $INSTALL_DIR"
echo "  source venv/bin/activate"
echo ""
echo "  # Web UI (рекомендуется):"
echo "  python web_ui/app.py"
echo ""
echo "  # CLI:"
echo "  python -m core.main --project-name myapp --requirements 'описание'"
echo ""
echo "Открой в браузере: http://localhost:5000"
echo ""
echo "Документация: https://github.com/owerevolf/ai-team-system"
echo ""
