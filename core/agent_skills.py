"""
Agent Skills — маппинг агентов на категории моделей с описанием скиллов.

Скиллы загружаются из файлов в core/skills/*.md
Каждый файл содержит полный system prompt addon для агента (DeepSeek LVL99).
"""

from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "core" / "skills"

# Маппинг агентов на категории моделей
AGENT_SKILL_MAP = {
    "teamlead": {
        "preferred_strength": "reasoning",
        "min_context": 65536,
        "fallback_strengths": ["strong", "general"],
        "temperature": 0.7,
        "description": "Координатор, планирование, декомпозиция задач",
        "skill_file": "TEAMLEAD_SKILL.md",
    },
    "architect": {
        "preferred_strength": "strong",
        "min_context": 65536,
        "fallback_strengths": ["reasoning", "general"],
        "temperature": 0.5,
        "description": "Архитектура, структура проекта, выбор технологий",
        "skill_file": "ARCHITECT_SKILL.md",
    },
    "backend": {
        "preferred_strength": "coding",
        "min_context": 32768,
        "fallback_strengths": ["strong", "reasoning", "general"],
        "temperature": 0.3,
        "description": "Серверный код, API, базы данных",
        "skill_file": "BACKEND_SKILL.md",
    },
    "frontend": {
        "preferred_strength": "fast",
        "min_context": 32768,
        "fallback_strengths": ["coding", "general"],
        "temperature": 0.7,
        "description": "Интерфейс, HTML/CSS/JS, дизайн",
        "skill_file": "FRONTEND_SKILL.md",
    },
    "devops": {
        "preferred_strength": "general",
        "min_context": 32768,
        "fallback_strengths": ["coding", "strong"],
        "temperature": 0.3,
        "description": "Docker, CI/CD, инфраструктура",
        "skill_file": "DEVOPS_SKILL.md",
    },
    "tester": {
        "preferred_strength": "coding",
        "min_context": 32768,
        "fallback_strengths": ["reasoning", "general"],
        "temperature": 0.2,
        "description": "Тесты, проверка качества, QA",
        "skill_file": "TESTER_SKILL.md",
    },
    "documentalist": {
        "preferred_strength": "fast",
        "min_context": 32768,
        "fallback_strengths": ["general", "strong"],
        "temperature": 0.7,
        "description": "Документация, README, комментарии",
        "skill_file": "DOCUMENTALIST_SKILL.md",
    },
    "prompt_architect": {
        "preferred_strength": "reasoning",
        "min_context": 65536,
        "fallback_strengths": ["strong", "general"],
        "temperature": 0.7,
        "description": "Обучалка промтов — учит собирать мысли, контекст, ТЗ",
        "skill_file": "PROMPT_ARCHITECT_SKILL.md",
    },
}


def get_agent_skill_addon(agent_name: str) -> str:
    """Загружает скилл агента из файла core/skills/*.md"""
    skill = AGENT_SKILL_MAP.get(agent_name)
    if not skill:
        return ""

    skill_file = SKILLS_DIR / skill["skill_file"]
    if skill_file.exists():
        return skill_file.read_text(encoding="utf-8")

    return ""


def get_agent_config(agent_name: str) -> Dict:
    """Возвращает полный конфиг агента (модель + скиллы)."""
    skill = AGENT_SKILL_MAP.get(agent_name, {})
    return {
        "name": agent_name,
        "preferred_strength": skill.get("preferred_strength", "general"),
        "min_context": skill.get("min_context", 32768),
        "fallback_strengths": skill.get("fallback_strengths", ["general"]),
        "temperature": skill.get("temperature", 0.7),
        "description": skill.get("description", ""),
        "skill_addon": get_agent_skill_addon(agent_name),
    }


def list_agents() -> List[Dict]:
    """Возвращает список всех агентов с их конфигами."""
    return [get_agent_config(name) for name in AGENT_SKILL_MAP]
