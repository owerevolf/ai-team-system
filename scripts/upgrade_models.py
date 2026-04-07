#!/usr/bin/env python3
"""
Upgrade Models - Миграция со старых моделей на qwen3
Проверяет .env и предлагает обновить модель
"""

import os
import sys
import subprocess
from pathlib import Path


OLD_MODELS = ["qwen2.5-coder:7b", "qwen2.5-coder:3b", "codellama:7b"]
NEW_MODEL = "qwen3:8b"


def check_env(env_path: Path) -> bool:
    """Проверка: используется ли старая модель"""
    if not env_path.exists():
        return False
    
    content = env_path.read_text()
    for old_model in OLD_MODELS:
        if old_model in content:
            return True
    return False


def update_env(env_path: Path) -> bool:
    """Обновить модель в .env"""
    if not env_path.exists():
        return False
    
    content = env_path.read_text()
    updated = content
    
    for old_model in OLD_MODELS:
        updated = updated.replace(old_model, NEW_MODEL)
    
    if updated != content:
        env_path.write_text(updated)
        return True
    
    return False


def pull_new_model():
    """Скачать новую модель через Ollama"""
    print(f"📥 Скачиваю {NEW_MODEL}...")
    try:
        result = subprocess.run(
            ["ollama", "pull", NEW_MODEL],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            print(f"✅ {NEW_MODEL} скачана")
        else:
            print(f"⚠️ Ошибка: {result.stderr}")
    except FileNotFoundError:
        print("⚠️ Ollama не найдена. Скачайте модель вручную: ollama pull qwen3:8b")
    except subprocess.TimeoutExpired:
        print("⚠️ Таймаут. Модель большая, попробуйте позже: ollama pull qwen3:8b")


def main():
    env_path = Path(__file__).parent.parent / ".env"
    
    if not check_env(env_path):
        print("✅ Вы уже используете актуальную модель")
        return
    
    print(f"⚠️ Вы используете старую модель.")
    print(f"   Рекомендуем {NEW_MODEL} для лучшего качества.")
    print()
    
    response = input("Обновить? [Y/n]: ").strip().lower()
    if response in ["", "y", "yes"]:
        update_env(env_path)
        print(f"✅ .env обновлён → {NEW_MODEL}")
        pull_new_model()
    else:
        print("Пропущено. Вы можете обновить вручную позже.")


if __name__ == "__main__":
    main()
