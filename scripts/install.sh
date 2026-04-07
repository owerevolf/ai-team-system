#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Team System — One-Click Installer (Linux/macOS)
# Версия: 2.0
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$INSTALL_DIR/scripts/install.log"
CACHE_FILE="$INSTALL_DIR/.hardware_cache"

mkdir -p "$(dirname "$LOG_FILE")"

log_info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1" | tee -a "$LOG_FILE"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        🤖 AI Team System — Installer v2.0              ║${NC}"
echo -e "${CYAN}║        Мультиагентная система разработки ПО             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

log_info "Лог: $LOG_FILE"

OS=$(uname -s)
log_info "ОС: $OS"

PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &> /dev/null; then
        PY_VERSION=$("$cmd" --version 2>&1 | awk '{print $2}')
        PYTHON_CMD="$cmd"
        log_ok "Python найден: $cmd $PY_VERSION"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    log_warn "Python 3.10+ не найден. Устанавливаю..."
    if [ "$OS" = "Darwin" ]; then
        if command -v brew &> /dev/null; then
            brew install python@3.12
        else
            log_err "Homebrew не найден. Установи Python вручную: https://www.python.org/downloads/"
            exit 1
        fi
    else
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y python3.10 python3.10-venv python3-pip
            PYTHON_CMD="python3.10"
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3.10 python3-pip
            PYTHON_CMD="python3.10"
        elif command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm python python-pip
            PYTHON_CMD="python3"
        else
            log_err "Не удалось установить Python. Установи вручную."
            exit 1
        fi
    fi
    log_ok "Python установлен"
fi

if ! command -v git &> /dev/null; then
    log_warn "Git не найден. Устанавливаю..."
    if [ "$OS" = "Darwin" ]; then
        brew install git
    elif command -v apt-get &> /dev/null; then
        sudo apt-get install -y git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y git
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm git
    fi
    log_ok "Git установлен"
fi

cd "$INSTALL_DIR"

log_info "Создаю виртуальное окружение..."
"$PYTHON_CMD" -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
log_ok "Виртуальное окружение создано"

log_info "Устанавливаю зависимости..."
pip install -r requirements.txt -q 2>&1 | tee -a "$LOG_FILE"
log_ok "Зависимости установлены"

detect_hardware() {
    VRAM_GB=0
    RAM_GB=0

    if command -v nvidia-smi &> /dev/null; then
        VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
        if [ -n "$VRAM_MB" ] && [ "$VRAM_MB" -gt 0 ] 2>/dev/null; then
            VRAM_GB=$((VRAM_MB / 1024))
        fi
    elif [ "$OS" = "Darwin" ]; then
        UNIFIED_MEM=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
        RAM_GB=$((UNIFIED_MEM / 1073741824))
        VRAM_GB=$RAM_GB
    fi

    if [ "$OS" = "Darwin" ]; then
        RAM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1073741824)}')
    else
        RAM_GB=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')
    fi
    RAM_GB=${RAM_GB:-8}

    if [ "$VRAM_GB" -gt 12 ] 2>/dev/null; then
        PROFILE="heavy"
        MODEL="qwen3:14b"
    elif [ "$VRAM_GB" -ge 6 ] 2>/dev/null; then
        PROFILE="medium"
        MODEL="qwen3:8b"
    else
        PROFILE="light"
        MODEL="qwen3:4b"
    fi

    echo "profile=$PROFILE" > "$CACHE_FILE"
    echo "model=$MODEL" >> "$CACHE_FILE"
    echo "vram=$VRAM_GB" >> "$CACHE_FILE"
    echo "ram=$RAM_GB" >> "$CACHE_FILE"
    echo "os=$OS" >> "$CACHE_FILE"

    log_info "Железо: ${VRAM_GB}ГБ VRAM, ${RAM_GB}ГБ RAM → профиль '$PROFILE', модель '$MODEL'"
}

if [ -f "$CACHE_FILE" ]; then
    log_info "Использую кэш железа: $CACHE_FILE"
    PROFILE=$(grep "^profile=" "$CACHE_FILE" | cut -d= -f2)
    MODEL=$(grep "^model=" "$CACHE_FILE" | cut -d= -f2)
else
    log_info "Сканирую железо..."
    detect_hardware
    log_ok "Кэш сохранён в .hardware_cache"
fi

install_ollama() {
    if command -v ollama &> /dev/null; then
        log_ok "Ollama найдена"
    else
        log_warn "Ollama не найдена. Устанавливаю..."
        curl -fsSL https://ollama.ai/install.sh | sh 2>&1 | tee -a "$LOG_FILE"
        log_ok "Ollama установлена"
    fi

    if ollama list 2>/dev/null | grep -q "$MODEL"; then
        log_ok "Модель $MODEL уже загружена"
    else
        log_info "Загружаю модель $MODEL (это может занять время)..."
        ollama pull "$MODEL" 2>&1 | tee -a "$LOG_FILE"
        log_ok "Модель $MODEL загружена"
    fi
}

if command -v ollama &> /dev/null || command -v curl &> /dev/null; then
    read -p "Установить/обновить Ollama и модель? (y/n): " -n 1 -r -t 30 || true
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [ -z "$REPLY" ]; then
        install_ollama
    else
        log_warn "Ollama пропущена. Настрой .env для облачных API."
    fi
fi

if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    if command -v sed &> /dev/null; then
        if [ "$OS" = "Darwin" ]; then
            sed -i "" "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$MODEL/" "$INSTALL_DIR/.env" 2>/dev/null || true
            sed -i "" "s/^HARDWARE_PROFILE=.*/HARDWARE_PROFILE=$PROFILE/" "$INSTALL_DIR/.env" 2>/dev/null || true
        else
            sed -i "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=$MODEL/" "$INSTALL_DIR/.env" 2>/dev/null || true
            sed -i "s/^HARDWARE_PROFILE=.*/HARDWARE_PROFILE=$PROFILE/" "$INSTALL_DIR/.env" 2>/dev/null || true
        fi
    fi
    log_ok ".env создан (профиль: $PROFILE, модель: $MODEL)"
fi

mkdir -p "$HOME/.logs/ai_team"
mkdir -p "$HOME/ai-team-lessons"
mkdir -p "$HOME/projects"
log_ok "Рабочие папки созданы"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ ГОТОВО!                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Запускаю веб-интерфейс..."

cd "$INSTALL_DIR"
source venv/bin/activate

nohup python -m uvicorn web_ui.app:app --host 0.0.0.0 --port 8000 > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
log_info "Сервер запущен (PID: $SERVER_PID)"

sleep 2

if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000 &> /dev/null &
elif command -v open &> /dev/null; then
    open http://localhost:8000 &> /dev/null &
elif command -v start &> /dev/null; then
    start http://localhost:8000 &> /dev/null &
fi

echo ""
echo -e "${CYAN}Веб-интерфейс: http://localhost:8000${NC}"
echo -e "${CYAN}Лог установки: $LOG_FILE${NC}"
echo ""
