#!/bin/bash
# Автоматическая установка моделей Ollama

set -e

echo "🔧 Установка моделей Ollama для AI Team System"

# Определение VRAM
check_vram() {
    if command -v nvidia-smi &> /dev/null; then
        VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        echo "VRAM: $VRAM MB"
    else
        echo "GPU не обнаружен, используем минимальную модель"
        VRAM=4000
    fi
}

# Установка модели
install_model() {
    MODEL=$1
    echo "📥 Установка $MODEL..."
    ollama pull $MODEL
    echo "✅ $MODEL установлен"
}

# Увеличение контекста
setup_context() {
    MODEL=$1
    CTX=$2
    echo "⚙️ Настройка контекста $CTX для $MODEL..."
    ollama run $MODEL
    # Следующие команды нужно ввести вручную в терминале Ollama:
    # /set parameter num_ctx $CTX
    # /save $MODEL-$CTXk
    # /bye
    echo "✅ Для завершения настройки выполните вручную:"
    echo "   ollama run $MODEL"
    echo "   >>> /set parameter num_ctx $CTX"
    echo "   >>> /save $MODEL-$CTXk"
    echo "   >>> /bye"
}

check_vram

if [ $VRAM -ge 16000 ]; then
    echo "🖥️ Мощная видеокарта, устанавливаем большие модели..."
    install_model "huihui_ai/qwen3.5-abliterated:27b-Claude"
    setup_context "huihui_ai/qwen3.5-abliterated:27b-Claude" 16384
elif [ $VRAM -ge 8000 ]; then
    echo "🖥️ Средняя видеокарта, устанавливаем оптимальные модели..."
    install_model "qwen2.5-coder:7b"
    install_model "codellama:7b"
    setup_context "qwen2.5-coder:7b" 8192
else
    echo "🖥️ Слабая видеокарта, устанавливаем легкие модели..."
    install_model "qwen2.5-coder:3b"
    setup_context "qwen2.5-coder:3b" 4096
fi

echo ""
echo "✅ Установка моделей завершена!"
echo "📋 Проверить модели: ollama list"
