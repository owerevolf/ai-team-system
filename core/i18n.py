"""
i18n — internationalization support.

Supported languages: ru, en
Usage: t("key") or t("key", lang="en")
"""

from typing import Dict, Optional
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
I18N_DIR = BASE_DIR / "config" / "i18n"
I18N_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_LANG = "ru"

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # Welcome
        "welcome_title": "AI Team System",
        "welcome_subtitle": "7 AI-агентов. Один разговор. Готовый проект.",
        "welcome_description": "Просто опиши что хочешь — остальное сделает команда.",
        "btn_tour": "🎓 Как это работает (Тур)",
        "btn_skip": "✨ Сразу создать проект",
        
        # Tabs
        "tab_chat": "💬 Чат",
        "tab_settings": "⚙️ Настройки",
        "tab_instruction": "📖 Инструкция",
        "tab_kanban": "📋 Канбан",
        
        # Chat
        "chat_placeholder": "Опиши что хочешь создать...",
        "chat_hint": "Enter — отправить · Shift+Enter — новая строка",
        "btn_send": "Отправить",
        "btn_stop": "Остановить",
        "btn_clear": "🗑 Очистить",
        "btn_export": "📥 Экспорт",
        "btn_new_project": "✨ Новый проект",
        
        # Kanban
        "kanban_title": "📋 Канбан доска",
        "kanban_description": "Отслеживай прогресс агентов в реальном времени.",
        "kanban_todo": "📋 Ожидание",
        "kanban_in_progress": "🔄 В работе",
        "kanban_done": "✅ Готово",
        "kanban_failed": "❌ Ошибка",
        "kanban_all_agents": "Все агенты",
        "kanban_all_priorities": "Все приоритеты",
        "kanban_priority_high": "🔴 Высокий",
        "kanban_priority_medium": "🟡 Средний",
        "kanban_priority_low": "🟢 Низкий",
        "btn_new_task": "➕ Новая задача",
        
        # Settings
        "settings_title": "⚙️ Настройки провайдеров",
        "settings_description": "Выбери провайдера AI моделей и настрой модели для каждого агента.",
        
        # Agents
        "agent_teamlead": "TeamLead",
        "agent_architect": "Architect",
        "agent_backend": "Backend",
        "agent_frontend": "Frontend",
        "agent_devops": "DevOps",
        "agent_tester": "Tester",
        "agent_documentalist": "Documentalist",
        
        # Status
        "status_idle": "Ожидание",
        "status_running": "В работе",
        "status_done": "Готово",
        "status_error": "Ошибка",
        
        # Messages
        "msg_thinking": "Думаю...",
        "msg_error": "Произошла ошибка",
        "msg_success": "Успешно",
    },
    "en": {
        # Welcome
        "welcome_title": "AI Team System",
        "welcome_subtitle": "7 AI agents. One conversation. Ready project.",
        "welcome_description": "Just describe what you want — the team does the rest.",
        "btn_tour": "🎓 How it works (Tour)",
        "btn_skip": "✨ Create project now",
        
        # Tabs
        "tab_chat": "💬 Chat",
        "tab_settings": "⚙️ Settings",
        "tab_instruction": "📖 Guide",
        "tab_kanban": "📋 Kanban",
        
        # Chat
        "chat_placeholder": "Describe what you want to create...",
        "chat_hint": "Enter — send · Shift+Enter — new line",
        "btn_send": "Send",
        "btn_stop": "Stop",
        "btn_clear": "🗑 Clear",
        "btn_export": "📥 Export",
        "btn_new_project": "✨ New project",
        
        # Kanban
        "kanban_title": "📋 Kanban Board",
        "kanban_description": "Track agent progress in real time.",
        "kanban_todo": "📋 To Do",
        "kanban_in_progress": "🔄 In Progress",
        "kanban_done": "✅ Done",
        "kanban_failed": "❌ Failed",
        "kanban_all_agents": "All agents",
        "kanban_all_priorities": "All priorities",
        "kanban_priority_high": "🔴 High",
        "kanban_priority_medium": "🟡 Medium",
        "kanban_priority_low": "🟢 Low",
        "btn_new_task": "➕ New Task",
        
        # Settings
        "settings_title": "⚙️ Provider Settings",
        "settings_description": "Choose AI model provider and configure models for each agent.",
        
        # Agents
        "agent_teamlead": "TeamLead",
        "agent_architect": "Architect",
        "agent_backend": "Backend",
        "agent_frontend": "Frontend",
        "agent_devops": "DevOps",
        "agent_tester": "Tester",
        "agent_documentalist": "Documentalist",
        
        # Status
        "status_idle": "Idle",
        "status_running": "Running",
        "status_done": "Done",
        "status_error": "Error",
        
        # Messages
        "msg_thinking": "Thinking...",
        "msg_error": "An error occurred",
        "msg_success": "Success",
    },
}


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Get translation for key"""
    lang = lang or _DEFAULT_LANG
    translations = _TRANSLATIONS.get(lang, _TRANSLATIONS[_DEFAULT_LANG])
    text = translations.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def set_default_lang(lang: str):
    """Set default language"""
    global _DEFAULT_LANG
    if lang in _TRANSLATIONS:
        _DEFAULT_LANG = lang


def get_available_languages() -> Dict[str, str]:
    """Get available languages"""
    return {
        "ru": "Русский",
        "en": "English",
    }


def add_translations(lang: str, translations: Dict[str, str]):
    """Add or update translations for a language"""
    if lang not in _TRANSLATIONS:
        _TRANSLATIONS[lang] = {}
    _TRANSLATIONS[lang].update(translations)
