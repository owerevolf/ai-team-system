#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Team System — Desktop Launcher
# Запуск сервера + открытие браузера
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$INSTALL_DIR/.server.pid"
LOG_FILE="$INSTALL_DIR/.logs/server.log"
PORT=8000

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

mkdir -p "$INSTALL_DIR/.logs"

log_info() { echo -e "${CYAN}[AI Team]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[AI Team]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[AI Team]${NC} $1"; }
log_err()  { echo -e "${RED}[AI Team]${NC} $1"; }

# ── Проверка: уже запущен? ──
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log_warn "Сервер уже запущен (PID: $OLD_PID)"
        log_info "Открываю браузер..."
        open_browser
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# ── Проверка порта ──
if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
    log_err "Порт $PORT уже занят другим процессом!"
    log_info "Останови его: ./scripts/stop.sh"
    exit 1
fi

# ── Проверка venv ──
if [ ! -d "$INSTALL_DIR/venv" ]; then
    log_err "Виртуальное окружение не найдено!"
    log_info "Запусти установщик: ./scripts/install.sh"
    exit 1
fi

# ── Проверка .env ──
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log_warn ".env не найден, создаю из .env.example..."
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    log_info "Отредактируй .env и запусти снова"
fi

# ── Запуск сервера ──
log_info "Запускаю AI Team System..."
cd "$INSTALL_DIR"
source venv/bin/activate

nohup "$INSTALL_DIR/venv/bin/python3" -m uvicorn web_ui.app:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
log_info "Сервер запущен (PID: $SERVER_PID, порт: $PORT)"

# ── Ожидание готовности ──
log_info "Жду готовности сервера..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
        log_ok "Сервер готов!"
        break
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        log_err "Сервер упал при запуске!"
        log_info "Лог: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
    sleep 1
done

# ── Открытие браузера ──
open_browser() {
    local URL="http://localhost:$PORT"
    if command -v xdg-open &> /dev/null; then
        xdg-open "$URL" &> /dev/null &
    elif command -v open &> /dev/null; then
        open "$URL" &> /dev/null &
    elif command -v gtk-launch &> /dev/null; then
        gtk-launch "$(xdg-settings get default-web-browser)" "$URL" &> /dev/null &
    else
        log_warn "Не могу открыть браузер автоматически"
        log_info "Открой вручную: $URL"
    fi
}

open_browser

echo ""
log_ok "═══════════════════════════════════════════"
log_ok "  AI Team System запущен!"
log_ok "  Открой: http://localhost:$PORT"
log_ok "  Остановка: ./scripts/stop.sh"
log_ok "  Лог: $LOG_FILE"
log_ok "═══════════════════════════════════════════"
echo ""
