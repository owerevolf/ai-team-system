"""
Understanding Engine — understand before execution.

Core philosophy: the system NEVER starts coding immediately.
First it must understand the request, the context, the risks.

This is NOT an AI agent. It is a structured analysis engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class UnderstandingResult:
    """Result of the understanding phase."""

    # What the system understood
    objective: str = ""
    interpreted_goal: str = ""

    # Analysis
    affected_areas: List[str] = field(default_factory=list)
    required_changes: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    # Risks
    risks: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)

    # Questions for the user
    clarification_questions: List[str] = field(default_factory=list)

    # Execution hypothesis
    execution_hypothesis: str = ""
    estimated_complexity: str = "medium"  # low, medium, high, critical
    suggested_agent: str = ""

    # State
    is_ready: bool = False
    blocking_issues: List[str] = field(default_factory=list)

    def format_for_display(self) -> str:
        """Format the understanding result for UI display."""
        lines = []

        lines.append("Вот что я понял:")
        lines.append("")
        if self.objective:
            lines.append(f"- {self.objective}")
        if self.interpreted_goal:
            lines.append(f"- {self.interpreted_goal}")
        for area in self.affected_areas:
            lines.append(f"- {area}")

        if self.required_changes:
            lines.append("")
            lines.append("Что нужно сделать:")
            for i, change in enumerate(self.required_changes, 1):
                lines.append(f"  {i}. {change}")

        if self.dependencies:
            lines.append("")
            lines.append("Зависимости:")
            for dep in self.dependencies:
                lines.append(f"  • {dep}")

        if self.risks:
            lines.append("")
            lines.append("Риски:")
            for risk in self.risks:
                lines.append(f"  ⚠ {risk}")

        if self.unknowns:
            lines.append("")
            lines.append("Неизвестные:")
            for u in self.unknowns:
                lines.append(f"  ? {u}")

        if self.clarification_questions:
            lines.append("")
            lines.append("Уточнения:")
            for q in self.clarification_questions:
                lines.append(f"  ❓ {q}")

        if self.execution_hypothesis:
            lines.append("")
            lines.append(f"Гипотеза: {self.execution_hypothesis}")
            lines.append(f"Сложность: {self.estimated_complexity}")
            if self.suggested_agent:
                lines.append(f"Агент: {self.suggested_agent}")

        return "\n".join(lines)


class UnderstandingEngine:
    """
    Analyzes user requests before any execution.

    This is a rule-based engine, not an LLM.
    It extracts structure from natural language requests
    and produces a structured understanding.

    The actual AI understanding happens on the backend via ModelRouter.
    This engine provides the structure and validation.
    """

    # Keywords for area detection
    AREA_KEYWORDS = {
        "backend": ["api", "endpoint", "server", "backend", "rest", "graphql",
                     "database", "db", "query", "model", "service", "auth",
                     "websocket", "notification", "middleware", "route"],
        "frontend": ["ui", "ux", "frontend", "react", "vue", "css", "style",
                      "component", "page", "layout", "button", "form", "modal",
                      "responsive", "animation", "theme", "стил", "главн",
                      "интерфейс", "цвет", "шрифт", "анимац"],
        "devops": ["deploy", "docker", "ci", "cd", "pipeline", "kubernetes",
                    "k8s", "nginx", "server", "hosting", "ssl", "domain",
                    "monitoring", "logging"],
        "testing": ["test", "spec", "coverage", "e2e", "integration", "unit",
                     "mock", "assert", "cypress", "playwright", "тест",
                     "покрытие"],
        "documentation": ["doc", "readme", "wiki", "guide", "tutorial",
                           "comment", "changelog", "api doc"],
        "security": ["auth", "security", "encrypt", "hash", "token", "jwt",
                      "oauth", "permission", "role", "vulnerability"],
        "database": ["migration", "schema", "table", "index", "sql",
                      "postgres", "mysql", "sqlite", "redis", "cache"],
        "architecture": ["refactor", "architecture", "pattern", "design",
                          "structure", "module", "layer", "service"],
    }

    COMPLEXITY_INDICATORS = {
        "critical": ["rewrite", "migrate", "rebuild", "replace", "remove",
                      "breaking", "deprecate", "major", "перепиши", "переписать",
                      "с нуля", "полностью изменить"],
        "high": ["add", "implement", "create", "integrate", "refactor",
                  "redesign", "restructure", "new feature", "добавь", "добавить",
                  "создать", "реализовать", "рефакторинг", "новый"],
        "medium": ["update", "improve", "enhance", "optimize", "fix",
                    "modify", "change", "adjust", "обновить", "обнови",
                    "исправить", "исправь", "улучшить", "оптимизировать",
                    "изменить", "настроить", "настрой"],
        "low": ["typo", "comment", "rename", "format", "style", "color",
                 "text", "label", "hint", "tooltip", "опечатк", "комментар",
                 "переименовать", "форматирование", "текст", "подсказка"],
    }

    AGENT_SUGGESTIONS = {
        "backend": "backend",
        "frontend": "frontend",
        "devops": "devops",
        "testing": "tester",
        "documentation": "documentalist",
        "security": "backend",
        "database": "backend",
        "architecture": "architect",
    }

    def analyze(self, message: str,
                project_context: Optional[Dict] = None) -> UnderstandingResult:
        """
        Analyze a user request and produce a structured understanding.

        Args:
            message: the user's request
            project_context: optional project brain data for context

        Returns:
            UnderstandingResult with structured analysis
        """
        result = UnderstandingResult()
        msg_lower = message.lower()

        # 1. Extract objective
        result.objective = self._extract_objective(message)
        result.interpreted_goal = self._interpret_goal(msg_lower)

        # 2. Detect affected areas
        result.affected_areas = self._detect_areas(msg_lower)

        # 3. Estimate complexity
        result.estimated_complexity = self._estimate_complexity(msg_lower)

        # 4. Suggest agent
        if result.affected_areas:
            primary_area = result.affected_areas[0]
            result.suggested_agent = self.AGENT_SUGGESTIONS.get(primary_area, "teamlead")

        # 5. Generate risks
        result.risks = self._generate_risks(msg_lower, result.affected_areas)

        # 6. Generate unknowns
        result.unknowns = self._generate_unknowns(msg_lower, result.affected_areas)

        # 7. Generate clarification questions
        result.clarification_questions = self._generate_questions(
            msg_lower, result.affected_areas, result.unknowns
        )

        # 8. Build execution hypothesis
        result.execution_hypothesis = self._build_hypothesis(
            result.objective, result.affected_areas, result.estimated_complexity
        )

        # 9. Determine if ready
        result.is_ready = (
            len(result.clarification_questions) == 0
            and len(result.blocking_issues) == 0
            and result.objective != ""
        )

        return result

    def _extract_objective(self, message: str) -> str:
        """Extract the core objective from the message."""
        # Remove common prefixes
        prefixes = [
            "добавь", "добавить", "сделай", "сделать", "создай", "создать",
            "исправить", "исправь", "обнови", "обновить", "удали", "удалить",
            "рефакторинг", "рефакторить", "настроить", "настрой",
            "add", "create", "make", "implement", "fix", "update", "remove",
            "refactor", "setup", "configure", "delete", "improve", "optimize",
        ]
        msg = message.strip()
        msg_lower = msg.lower()
        for prefix in prefixes:
            if msg_lower.startswith(prefix):
                msg = msg[len(prefix):].strip()
                break
        # Capitalize first letter
        if msg:
            msg = msg[0].upper() + msg[1:]
        return msg

    def _interpret_goal(self, msg_lower: str) -> str:
        """Interpret the high-level goal."""
        if any(w in msg_lower for w in ["websocket", "realtime", "real-time", "уведомлен"]):
            return "Требуется реализация realtime функциональности"
        if any(w in msg_lower for w in ["api", "endpoint", "rest"]):
            return "Требуется работа с API слоем"
        if any(w in msg_lower for w in ["test", "тест", "coverage"]):
            return "Требуется улучшение тестирования"
        if any(w in msg_lower for w in ["auth", "авторизац", "login", "token"]):
            return "Требуется работа с системой авторизации"
        if any(w in msg_lower for w in ["ui", "интерфейс", "frontend", "css", "стил"]):
            return "Требуется изменение пользовательского интерфейса"
        if any(w in msg_lower for w in ["deploy", "деплой", "docker", "ci"]):
            return "Требуется настройка инфраструктуры деплоя"
        if any(w in msg_lower for w in ["refactor", "рефакторинг", "архитектур"]):
            return "Требуется рефакторинг или изменение архитектуры"
        if any(w in msg_lower for w in ["database", "бд", "migration", "миграц"]):
            return "Требуется работа с базой данных"
        return "Цель требует дополнительного уточнения"

    def _detect_areas(self, msg_lower: str) -> List[str]:
        """Detect which areas of the project are affected."""
        areas = []
        for area, keywords in self.AREA_KEYWORDS.items():
            if any(kw in msg_lower for kw in keywords):
                areas.append(area)
        return areas if areas else ["backend"]  # default

    def _estimate_complexity(self, msg_lower: str) -> str:
        """Estimate the complexity of the task."""
        for level, keywords in self.COMPLEXITY_INDICATORS.items():
            if any(kw in msg_lower for kw in keywords):
                return level
        return "medium"

    def _generate_risks(self, msg_lower: str, areas: List[str]) -> List[str]:
        """Generate potential risks based on the request."""
        risks = []

        if "backend" in areas:
            risks.append("Изменение API может затронуть существующих клиентов")
        if "database" in areas:
            risks.append("Миграции БД требуют backup перед выполнением")
        if "security" in areas:
            risks.append("Изменения в auth требуют тщательного тестирования")
        if "architecture" in areas:
            risks.append("Архитектурные изменения могут потребовать рефакторинга зависимых модулей")
        if "frontend" in areas and "backend" in areas:
            risks.append("Fullstack изменения требуют синхронизации frontend и backend")
        if any(w in msg_lower for w in ["websocket", "realtime"]):
            risks.append("WebSocket требует обработки reconnect и race conditions")
        if any(w in msg_lower for w in ["auth", "token", "jwt"]):
            risks.append("Изменения в аутентификации могут инвалидировать существующие сессии")

        return risks

    def _generate_unknowns(self, msg_lower: str, areas: List[str]) -> List[str]:
        """Generate list of unknowns that need clarification."""
        unknowns = []

        if "backend" in areas:
            unknowns.append("Текущее состояние соответствующего модуля неизвестно")
        if "database" in areas:
            unknowns.append("Текущая схема БД не проанализирована")
        if "frontend" in areas:
            unknowns.append("Текущее состояние UI компонентов неизвестно")
        if "security" in areas:
            unknowns.append("Текущая реализация auth не проанализирована")

        return unknowns

    def _generate_questions(self, msg_lower: str, areas: List[str],
                            unknowns: List[str]) -> List[str]:
        """Generate clarification questions."""
        questions = []

        if any(w in msg_lower for w in ["websocket", "realtime", "notification"]):
            if "notification" in msg_lower or "уведомлен" in msg_lower:
                questions.append("Нужны ли browser push или только in-app уведомления?")
            questions.append("Нужна ли история уведомлений или только realtime delivery?")

        if "auth" in msg_lower or "token" in msg_lower:
            questions.append("Нужна ли поддержка OAuth или достаточно JWT?")

        if "api" in msg_lower:
            questions.append("Нужна ли обратная совместимость с текущим API?")

        if "database" in msg_lower or "migration" in msg_lower:
            questions.append("Есть ли production данные которые нужно сохранить?")

        if "refactor" in msg_lower:
            questions.append("Какой scope рефакторинга — один модуль или вся система?")

        if not questions and not areas:
            questions.append("Можешь уточнить какую часть системы затрагивает задача?")

        return questions

    def _build_hypothesis(self, objective: str, areas: List[str],
                          complexity: str) -> str:
        """Build an execution hypothesis."""
        if not objective:
            return "Недостаточно информации для построения гипотезы"

        area_str = ", ".join(areas[:3]) if areas else "general"
        return (
            f"Реализовать '{objective}' через изменения в {area_str}. "
            f"Оценочная сложность: {complexity}."
        )
