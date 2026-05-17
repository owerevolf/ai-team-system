#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Team System — Doctor
# Диагностика и автоматический ремонт проблем
# ═══════════════════════════════════════════════════════════════

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$INSTALL_DIR/.server.pid"
LOG_FILE="$INSTALL_DIR/.logs/server.log"
DB_FILE="$INSTALL_DIR/data/ai_team.db"
PORT=8000

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

OK=0
WARN=0
FAIL=0

ok()   { echo -e "  ${GREEN}✓${NC} $1"; ((OK++)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; ((WARN++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)); }
info() { echo -e "  ${CYAN}ℹ${NC} $1"; }
fix()  { echo -e "    ${GREEN}→ Исправлено: $1${NC}"; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          🔧 AI Team System — Doctor                     ║${NC}"
echo -e "${BOLD}║          Диагностика и ремонт                           ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Python ──
echo -e "${BOLD}[1/8] Python${NC}"
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &> /dev/null; then
        PY_VERSION=$("$cmd" --version 2>&1 | awk '{print $2}')
        PYTHON_CMD="$cmd"
        ok "Python $PY_VERSION ($cmd)"
        break
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    fail "Python не найден!"
    info "Установи: sudo apt install python3.11 python3.11-venv"
fi

# ── 2. Git ──
echo -e "\n${BOLD}[2/8] Git${NC}"
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | awk '{print $3}')
    ok "Git $GIT_VERSION"
else
    fail "Git не найден"
    info "Установи: sudo apt install git"
fi

# ── 3. Виртуальное окружение ──
echo -e "\n${BOLD}[3/8] Виртуальное окружение${NC}"
if [ -d "$INSTALL_DIR/venv" ]; then
    ok "venv найден"
    if "$INSTALL_DIR/venv/bin/python" -c "import fastapi" 2>/dev/null; then
        ok "FastAPI установлен в venv"
    else
        fail "FastAPI НЕ установлен в venv!"
        info "Переустановка зависимостей..."
        cd "$INSTALL_DIR"
        "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt -q 2>&1
        if "$INSTALL_DIR/venv/bin/python" -c "import fastapi" 2>/dev/null; then
            fix "Зависимости переустановлены"
        else
            fail "Ошибка установки зависимостей"
        fi
    fi
else
    fail "venv не найден!"
    info "Создаю venv..."
    cd "$INSTALL_DIR"
    "$PYTHON_CMD" -m venv venv
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q 2>&1
    if ./venv/bin/python -c "import fastapi" 2>/dev/null; then
        fix "venv создан, зависимости установлены"
    else
        fail "Ошибка создания venv"
    fi
fi

# ── 4. Зависимости (проверяем через venv) ──
echo -e "\n${BOLD}[4/8] Зависимости Python${NC}"
VENV_PY="$INSTALL_DIR/venv/bin/python"

MISSING=0
# Пакеты и их имена для импорта (не всегда совпадают с pip-именем)
declare -A PACKAGES=(
    [fastapi]="fastapi"
    [uvicorn]="uvicorn"
    [httpx]="httpx"
    [sqlalchemy]="sqlalchemy"
    [pydantic]="pydantic"
    [pyyaml]="yaml"
    [rich]="rich"
    [click]="click"
    [loguru]="loguru"
)

for pip_name in "${!PACKAGES[@]}"; do
    import_name="${PACKAGES[$pip_name]}"
    if "$VENV_PY" -c "import $import_name" 2>/dev/null; then
        ok "$pip_name"
    else
        fail "$pip_name отсутствует"
        ((MISSING++))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    info "Установка $MISSING недостающих пакетов..."
    "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt -q 2>&1
    fix "Недостающие пакеты установлены"
fi

# ── 5. .env файл ──
echo -e "\n${BOLD}[5/8] Конфигурация (.env)${NC}"
if [ -f "$INSTALL_DIR/.env" ]; then
    ok ".env файл существует"
    if grep -q "^SECRET_KEY=$" "$INSTALL_DIR/.env" 2>/dev/null; then
        warn "SECRET_KEY не заполнен"
        NEW_KEY=$("$VENV_PY" -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || head -c 64 /dev/urandom | xxd -p | head -c 64)
        sed -i "s/^SECRET_KEY=$/SECRET_KEY=$NEW_KEY/" "$INSTALL_DIR/.env"
        fix "SECRET_KEY сгенерирован автоматически"
    else
        ok "SECRET_KEY заполнен"
    fi
else
    fail ".env не найден!"
    if [ -f "$INSTALL_DIR/.env.example" ]; then
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        fix ".env создан из .env.example"
        warn "Отредактируй .env — заполни API ключи!"
    else
        fail ".env.example тоже не найден"
    fi
fi

# ── 6. База данных ──
echo -e "\n${BOLD}[6/8] База данных${NC}"
mkdir -p "$INSTALL_DIR/data"
if [ -f "$DB_FILE" ]; then
    ok "База данных существует"
    if "$VENV_PY" -c "
import sqlite3
conn = sqlite3.connect('$DB_FILE')
conn.execute('SELECT 1')
conn.close()
" 2>/dev/null; then
        ok "База данных не повреждена"
    else
        fail "База данных повреждена!"
        rm -f "$DB_FILE"
        fix "Повреждённая база удалена (будет создана при запуске)"
    fi
else
    info "База данных не найдена — будет создана при запуске"
    ok "OK (будет создана автоматически)"
fi

# ── 7. Порт ──
echo -e "\n${BOLD}[7/8] Порт $PORT${NC}"
PORT_PID=$(ss -tlnp 2>/dev/null | grep ":$PORT " | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -n "$PORT_PID" ]; then
    PROC_NAME=$(ps -p "$PORT_PID" -o comm= 2>/dev/null || echo "unknown")
    if echo "$PROC_NAME" | grep -qi "python\|uvicorn"; then
        ok "Порт $PORT занят AI Team System (PID: $PORT_PID)"
    else
        warn "Порт $PORT занят другим процессом: $PROC_NAME (PID: $PORT_PID)"
        info "Останови его или смени порт"
    fi
else
    ok "Порт $PORT свободен"
fi

# ── 8. Здоровье сервера ──
echo -e "\n${BOLD}[8/8] Здоровье сервера${NC}"
if curl -sf "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
    ok "Сервер отвечает на /api/health"
else
    info "Сервер не запущен или не отвечает"
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ! kill -0 "$OLD_PID" 2>/dev/null; then
            warn "PID-файл устарел (процесс $OLD_PID мёртв)"
            rm -f "$PID_FILE"
            fix "PID-файл очищен"
        fi
    fi
fi

# ── Итог ──
echo ""
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "  Результат: ${GREEN}$OK OK${NC}, ${YELLOW}$WARN предупреждений${NC}, ${RED}$FAIL ошибок${NC}"
echo -e "${BOLD}══════════════════════════════════════════════════════════${NC}"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Есть проблемы. Попробуй:${NC}"
    echo "  1. Запусти doctor.sh повторно после исправлений"
    echo "  2. Переустанови: ./scripts/install.sh"
    echo "  3. Смотри лог: $LOG_FILE"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Есть предупреждения, но система должна работать.${NC}"
    exit 0
else
    echo ""
    echo -e "${GREEN}Всё в порядке! Можно запускать: ./scripts/launcher.sh${NC}"
    exit 0
fi
