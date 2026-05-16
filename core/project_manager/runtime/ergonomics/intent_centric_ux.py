"""
P6 — Intent-Centric UX (Phase 10)

Shifts from "manage the runtime" to "what do you want to do?"
Translates user intents into runtime operations without exposing
internal machinery.

Key principle: user thinks in goals, not in runtime operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class UserIntent(Enum):
    CREATE_PROJECT = "create_project"
    MODIFY_CODE = "modify_code"
    FIX_ERRORS = "fix_errors"
    ADD_FEATURE = "add_feature"
    REFACTOR = "refactor"
    REVIEW_CODE = "review_code"
    RUN_TESTS = "run_tests"
    DEPLOY = "deploy"
    EXPLORE = "explore"
    UNDERSTAND = "understand"
    CLEANUP = "cleanup"
    UNKNOWN = "unknown"


class IntentConfidence(Enum):
    HIGH = "high"       # Clear intent, can proceed
    MEDIUM = "medium"   # Likely intent, confirm
    LOW = "low"         # Unclear, ask clarifying questions


@dataclass
class Intent:
    """A detected user intent."""
    intent_type: UserIntent
    confidence: IntentConfidence
    raw_query: str
    parameters: dict[str, Any] = field(default_factory=dict)
    clarifying_questions: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "confidence": self.confidence.value,
            "parameters": self.parameters,
            "clarifying_questions": self.clarifying_questions,
            "suggested_actions": self.suggested_actions,
        }


@dataclass
class IntentAction:
    """A runtime action derived from a user intent."""
    action_id: str
    label: str
    description: str
    intent: UserIntent
    runtime_operation: str  # The actual runtime operation to execute
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    estimated_steps: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "description": self.description,
            "intent": self.intent.value,
            "runtime_operation": self.runtime_operation,
            "parameters": self.parameters,
            "requires_approval": self.requires_approval,
            "estimated_steps": self.estimated_steps,
        }


# Intent detection patterns
INTENT_PATTERNS: dict[UserIntent, list[str]] = {
    UserIntent.CREATE_PROJECT: [
        "create", "new project", "start a", "build a", "make a",
        "создать", "новый проект", "сделать",
    ],
    UserIntent.MODIFY_CODE: [
        "change", "update", "edit", "modify", "replace",
        "изменить", "обновить",
    ],
    UserIntent.FIX_ERRORS: [
        "fix error", "fix the error", "debug", "broken", "not working", "crash",
        "ошибка", "не работает", "сломан",
    ],
    UserIntent.ADD_FEATURE: [
        "add", "implement", "feature", "support for",
        "добавить", "реализовать",
    ],
    UserIntent.REFACTOR: [
        "refactor", "restructure", "clean up", "simplify",
        "рефакторинг", "упростить",
    ],
    UserIntent.REVIEW_CODE: [
        "review", "check", "look at", "analyze",
        "проверить", "посмотреть", "анализ",
    ],
    UserIntent.RUN_TESTS: [
        "test", "run tests", "check tests",
        "тест", "запустить тесты",
    ],
    UserIntent.DEPLOY: [
        "deploy", "publish", "release", "ship",
        "деплой", "опубликовать",
    ],
    UserIntent.EXPLORE: [
        "explore", "browse", "show me", "find",
        "показать", "найти",
    ],
    UserIntent.UNDERSTAND: [
        "explain", "what is", "how does", "understand",
        "объяснить", "что это", "как",
    ],
    UserIntent.CLEANUP: [
        "cleanup", "clean up", "remove unused", "delete",
        "очистить", "удалить",
    ],
}

# Maps intents to runtime operations
INTENT_OPERATIONS: dict[UserIntent, dict[str, Any]] = {
    UserIntent.CREATE_PROJECT: {
        "operation": "create_project",
        "requires_approval": False,
        "estimated_steps": 5,
    },
    UserIntent.MODIFY_CODE: {
        "operation": "modify_files",
        "requires_approval": True,
        "estimated_steps": 3,
    },
    UserIntent.FIX_ERRORS: {
        "operation": "diagnose_and_fix",
        "requires_approval": True,
        "estimated_steps": 4,
    },
    UserIntent.ADD_FEATURE: {
        "operation": "implement_feature",
        "requires_approval": True,
        "estimated_steps": 6,
    },
    UserIntent.REFACTOR: {
        "operation": "refactor_code",
        "requires_approval": True,
        "estimated_steps": 4,
    },
    UserIntent.REVIEW_CODE: {
        "operation": "review_project",
        "requires_approval": False,
        "estimated_steps": 2,
    },
    UserIntent.RUN_TESTS: {
        "operation": "run_test_suite",
        "requires_approval": False,
        "estimated_steps": 2,
    },
    UserIntent.DEPLOY: {
        "operation": "deploy_project",
        "requires_approval": True,
        "estimated_steps": 5,
    },
    UserIntent.EXPLORE: {
        "operation": "explore_project",
        "requires_approval": False,
        "estimated_steps": 1,
    },
    UserIntent.UNDERSTAND: {
        "operation": "explain_project",
        "requires_approval": False,
        "estimated_steps": 1,
    },
    UserIntent.CLEANUP: {
        "operation": "cleanup_project",
        "requires_approval": True,
        "estimated_steps": 2,
    },
}


class IntentCentricUX:
    """
    Translates user queries into intents and runtime actions.

    Usage:
        ux = IntentCentricUX()
        intent = ux.detect_intent("Add Stripe payments to my project")
        if intent.confidence == IntentConfidence.HIGH:
            action = ux.create_action(intent)
    """

    def detect_intent(self, query: str) -> Intent:
        """Detect user intent from a natural language query."""
        query_lower = query.lower().strip()

        # Score each intent by pattern matches
        scores: dict[UserIntent, int] = {}
        for intent_type, patterns in INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in query_lower:
                    score += 1
            if score > 0:
                scores[intent_type] = score

        if not scores:
            return Intent(
                intent_type=UserIntent.UNKNOWN,
                confidence=IntentConfidence.LOW,
                raw_query=query,
                clarifying_questions=[
                    "What would you like to do?",
                    "Create a new project, modify existing code, or explore?",
                ],
            )

        # Pick highest-scoring intent
        best_intent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_intent]

        # Determine confidence
        if best_score >= 3:
            confidence = IntentConfidence.HIGH
        elif best_score >= 2:
            confidence = IntentConfidence.MEDIUM
        else:
            confidence = IntentConfidence.LOW

        # Generate clarifying questions for low confidence
        questions = []
        if confidence == IntentConfidence.LOW:
            questions = self._generate_questions(best_intent, query)

        # Extract parameters
        parameters = self._extract_parameters(best_intent, query)

        # Generate suggested actions
        suggestions = self._generate_suggestions(best_intent)

        return Intent(
            intent_type=best_intent,
            confidence=confidence,
            raw_query=query,
            parameters=parameters,
            clarifying_questions=questions,
            suggested_actions=suggestions,
        )

    def create_action(self, intent: Intent) -> Optional[IntentAction]:
        """Create a runtime action from a detected intent."""
        op_info = INTENT_OPERATIONS.get(intent.intent_type)
        if not op_info:
            return None

        import uuid
        return IntentAction(
            action_id=f"action-{uuid.uuid4().hex[:8]}",
            label=self._intent_label(intent.intent_type),
            description=f"Execute {op_info['operation']} based on user intent",
            intent=intent.intent_type,
            runtime_operation=op_info["operation"],
            parameters=intent.parameters,
            requires_approval=op_info["requires_approval"],
            estimated_steps=op_info["estimated_steps"],
        )

    def get_intent_menu(self) -> list[dict[str, str]]:
        """Get a user-friendly intent menu."""
        return [
            {"intent": "create_project", "label": "Create new project", "icon": "plus"},
            {"intent": "modify_code", "label": "Modify code", "icon": "edit"},
            {"intent": "fix_errors", "label": "Fix errors", "icon": "wrench"},
            {"intent": "add_feature", "label": "Add feature", "icon": "star"},
            {"intent": "refactor", "label": "Refactor", "icon": "refresh"},
            {"intent": "review_code", "label": "Review code", "icon": "eye"},
            {"intent": "run_tests", "label": "Run tests", "icon": "check"},
            {"intent": "explore", "label": "Explore project", "icon": "search"},
            {"intent": "understand", "label": "Understand code", "icon": "question"},
        ]

    def _generate_questions(self, intent: UserIntent, query: str) -> list[str]:
        """Generate clarifying questions for an intent."""
        questions_map = {
            UserIntent.MODIFY_CODE: ["Which file(s) do you want to modify?"],
            UserIntent.ADD_FEATURE: ["What feature do you want to add?"],
            UserIntent.FIX_ERRORS: ["What error are you seeing?"],
            UserIntent.REFACTOR: ["Which part should be refactored?"],
            UserIntent.DEPLOY: ["Where do you want to deploy?"],
        }
        return questions_map.get(intent, ["Can you tell me more about what you want?"])

    def _extract_parameters(self, intent: UserIntent, query: str) -> dict[str, Any]:
        """Extract parameters from the query based on intent."""
        params: dict[str, Any] = {}
        query_lower = query.lower()

        # Extract file references
        import re
        file_matches = re.findall(r'(\w+\.\w{2,4})', query)
        if file_matches:
            params["files"] = file_matches

        # Extract project name hints
        for keyword in ["project", "app", "service"]:
            idx = query_lower.find(keyword)
            if idx >= 0:
                # Take the word after the keyword
                after = query[idx + len(keyword):].strip().split()
                if after:
                    params["target"] = after[0]
                    break

        return params

    def _generate_suggestions(self, intent: UserIntent) -> list[str]:
        """Generate suggested actions for an intent."""
        suggestions_map = {
            UserIntent.CREATE_PROJECT: ["Choose a template", "Start from scratch"],
            UserIntent.MODIFY_CODE: ["Show affected files", "Preview changes"],
            UserIntent.FIX_ERRORS: ["Run diagnostics", "Show error log"],
            UserIntent.ADD_FEATURE: ["Plan implementation", "Find similar code"],
            UserIntent.REFACTOR: ["Analyze dependencies", "Create backup"],
            UserIntent.REVIEW_CODE: ["Show code metrics", "Find issues"],
            UserIntent.RUN_TESTS: ["Run all tests", "Run failed only"],
            UserIntent.DEPLOY: ["Check prerequisites", "Preview deployment"],
        }
        return suggestions_map.get(intent, [])

    def _intent_label(self, intent: UserIntent) -> str:
        """Get a human-readable label for an intent."""
        labels = {
            UserIntent.CREATE_PROJECT: "Create Project",
            UserIntent.MODIFY_CODE: "Modify Code",
            UserIntent.FIX_ERRORS: "Fix Errors",
            UserIntent.ADD_FEATURE: "Add Feature",
            UserIntent.REFACTOR: "Refactor",
            UserIntent.REVIEW_CODE: "Review Code",
            UserIntent.RUN_TESTS: "Run Tests",
            UserIntent.DEPLOY: "Deploy",
            UserIntent.EXPLORE: "Explore",
            UserIntent.UNDERSTAND: "Understand",
            UserIntent.CLEANUP: "Cleanup",
            UserIntent.UNKNOWN: "Unknown",
        }
        return labels.get(intent, "Action")
