#!/usr/bin/env python3
"""
GITHUB VISION — Анализ скриншотов через GitHub Models (GPT-4o)
Использует OpenAI SDK с кастомным base_url
"""
import base64
import os
import sys
import logging
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()

logger = logging.getLogger(__name__)

# GitHub Models API
GITHUB_API_URL = "https://models.github.ai/inference"
GITHUB_MODEL = "openai/gpt-4o"


def get_client():
    """Создаёт OpenAI клиент для GitHub Models"""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN не найден в .env!\n"
            "Получи токен: github.com/settings/tokens → Generate new token (classic) → без прав → скопируй → вставь в .env"
        )
    return OpenAI(base_url=GITHUB_API_URL, api_key=token)


def validate_token():
    """Проверяет что токен работает"""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=GITHUB_MODEL,
            messages=[{"role": "user", "content": "say hello"}],
            max_tokens=10
        )
        text = response.choices[0].message.content
        logger.info(f"✅ GitHub Models токен валиден: {text[:50]}")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            logger.error("❌ Токен неверный. Получи на github.com/settings/tokens")
        elif "429" in error_str or "rate" in error_str:
            logger.error("❌ Лимит исчерпан (50 запросов/день). Подожди до завтра.")
        else:
            logger.error(f"❌ Ошибка валидации токена: {e}")
        return False


def image_to_base64(image_path):
    """Конвертирует изображение в base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_screenshot(image_path, question="Опиши что видишь на этом изображении"):
    """
    Отправляет скриншот в GitHub Models GPT-4o для анализа.
    
    Args:
        image_path: Путь к файлу скриншота
        question: Вопрос для модели
    
    Returns:
        str: Ответ модели или None при ошибке
    """
    path = Path(image_path)
    if not path.exists():
        logger.error(f"❌ Скриншот не найден: {image_path}")
        return None

    try:
        client = get_client()
        base64_image = image_to_base64(path)
        
        response = client.chat.completions.create(
            model=GITHUB_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": question
                    }
                ]
            }],
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        return answer
        
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "rate" in error_str:
            logger.error("❌ Лимит GitHub Models исчерпан (50 запросов/день)")
        elif "401" in error_str:
            logger.error("❌ Неверный токен")
        else:
            logger.error(f"❌ Ошибка vision анализа: {e}")
        return None


def check_agent_hearing(image_path):
    """
    Проверяет: агент СЛЫШИТ пользователя или отвечает общим скриптом.
    
    Returns:
        str: "СЛЫШИТ" или "НЕ СЛЫШИТ"
    """
    question = (
        "Это интерфейс AI Team System. Пользователь отправил сообщение агенту. "
        "Посмотри на ответ агента: он реагирует НА СОДЕРЖАНИЕ сообщения пользователя "
        "или это общий шаблонный скрипт приветствия? "
        "Ответь ОДНИМ СЛОВОМ: СЛЫШИТ или НЕ СЛЫШИТ. "
        "Объясни коротко (1-2 предложения) ПОЧЕМУ."
    )
    
    result = analyze_screenshot(image_path, question)
    if not result:
        return "ОШИБКА"
    
    # Извлекаем ключевое слово
    upper = result.upper()
    if "НЕ СЛЫШИТ" in upper:
        return "НЕ СЛЫШИТ"
    elif "СЛЫШИТ" in upper:
        return "СЛЫШИТ"
    else:
        # Если модель не ответила одним словом, анализируем
        if any(w in upper for w in ["ОБЩ", "ШАБЛОН", "СКРИПТ", "ПРИВЕТСТВИЕ", "БОТОВИНА"]):
            return "НЕ СЛЫШИТ"
        return "СЛЫШИТ"


def check_ui_errors(image_path):
    """
    Проверяет скриншот на ошибки UI.
    
    Returns:
        dict: {"has_errors": bool, "description": str}
    """
    question = (
        "Это веб-интерфейс приложения. Есть ли на странице: "
        "1. Ошибки JavaScript (в консоли или видимые)? "
        "2. Сломанные элементы (пустые блоки, перекрывающийся текст)? "
        "3. Незаполненные placeholder'ы? "
        "4. Кривая вёрстка? "
        "Опиши проблемы списком. Если всё ок — напиши 'Всё чисто'."
    )
    
    result = analyze_screenshot(image_path, question)
    if not result:
        return {"has_errors": None, "description": "Ошибка анализа"}
    
    has_errors = "всё чисто" not in result.lower() and "нет ошибок" not in result.lower()
    return {"has_errors": has_errors, "description": result}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    print("🔍 GitHub Vision — тестирование")
    print("=" * 40)
    
    if validate_token():
        print("✅ Токен валиден!")
        if len(sys.argv) > 1:
            screenshot = sys.argv[1]
            result = check_ui_errors(screenshot)
            print(f"\nРезультат анализа {screenshot}:")
            print(result["description"])
        else:
            print("Использование: python github_vision.py <screenshot.png>")
    else:
        print("❌ Токен не валиден. Добавь GITHUB_TOKEN в .env")
        sys.exit(1)
