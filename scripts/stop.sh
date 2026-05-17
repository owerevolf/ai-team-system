#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Team System — Stop Server
# ═══════════════════════════════════════════════════════════════

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$INSTALL_DIR/.server.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null
        sleep 1
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
        echo -e "${GREEN}[AI Team]${NC} Сервер остановлен (PID: $PID)"
    else
        rm -f "$PID_FILE"
        echo -e "${CYAN}[AI Team]${NC} PID-файл устарел, сервер не запущен"
    fi
else
    # Try to find by port
    PID=$(ss -tlnp 2>/dev/null | grep ':8000 ' | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null
        echo -e "${GREEN}[AI Team]${NC} Сервер остановлен (PID: $PID, найден по порту)"
    else
        echo -e "${CYAN}[AI Team]${NC} Сервер не запущен"
    fi
fi
