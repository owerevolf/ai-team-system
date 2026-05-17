#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# AI Team System — Desktop Entry Installer
# Создаёт ярлык на рабочем столе
# Запуск: bash scripts/install_desktop_entry.sh
# ═══════════════════════════════════════════════════════════════

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_FILE="$HOME/Desktop/ai-team-system.desktop"
APPS_FILE="$HOME/.local/share/applications/ai-team-system.desktop"

mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/Desktop" 2>/dev/null || true

# Создаём .desktop файл
cat > "$DESKTOP_FILE" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AI Team System
Name[ru]=AI Team System
Comment=Multi-agent AI software development platform
Comment[ru]=Мультиагентная система разработки ПО
Exec=bash "$INSTALL_DIR/scripts/launcher.sh"
Icon=utilities-terminal
Terminal=true
Categories=Development;ProjectManagement;
Keywords=ai;development;team;project;
StartupNotify=true
Path=$INSTALL_DIR
DESKTOP_EOF

chmod +x "$DESKTOP_FILE"

# Копируем в меню приложений
cp "$DESKTOP_FILE" "$APPS_FILE" 2>/dev/null || true

echo ""
echo "✅ Ярлык создан: $DESKTOP_FILE"
echo "✅ Добавлен в меню: $APPS_FILE"
echo ""
echo "Теперь можно запускать AI Team System двойным кликом на рабочем столе!"
echo ""
echo "Дополнительные команды:"
echo "  ./scripts/launcher.sh  — запуск сервера"
echo "  ./scripts/stop.sh      — остановка сервера"
echo "  ./scripts/doctor.sh    — диагностика и ремонт"
