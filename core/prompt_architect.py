"""
Prompt Architect Agent — обучалка промтов.

Учит пользователя:
- Что такое промт и зачем он нужен
- Как правильно собирать мысли и контекст
- Как писать ТЗ для AI-агентов
- 5 слоёв хорошего промта (Роль, Контекст, Задача, Ограничения, Формат)
- Как избегать типичных ошибок

Работает как диалоговый агент (без файловых операций).
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


AGENT_NAME = "prompt_architect"


@dataclass
class PAMessage:
    """Сообщение в чате Prompt Architect."""
    role: str  # user, assistant, system
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class PromptArchitectAgent:
    """
    Агент-обучалка промтов.

    Использует system prompt из core/skills/PROMPT_ARCHITECT_SKILL.md
    и model_router для генерации ответов.
    """

    def __init__(self, model_router=None):
        self.model_router = model_router
        self.messages: List[PAMessage] = []
        self._system_prompt: str = ""
        self._load_skill()

    def _load_skill(self):
        """Загрузить system prompt из файла скилла."""
        from pathlib import Path
        skill_file = Path(__file__).parent / "skills" / "PROMPT_ARCHITECT_SKILL.md"
        if skill_file.exists():
            self._system_prompt = skill_file.read_text(encoding="utf-8")
            logger.info(f"Prompt Architect skill loaded ({len(self._system_prompt)} chars)")
        else:
            logger.warning("PROMPT_ARCHITECT_SKILL.md not found, using minimal prompt")
            self._system_prompt = self._get_fallback_prompt()

    @staticmethod
    def _get_fallback_prompt() -> str:
        return """You are a Senior Prompt Architect.
Your job is to teach users how to write effective prompts for AI agents.
Explain the 5 layers of a good prompt: Role, Context, Task, Constraints, Output Format.
Be patient, direct, and practical. Always end with a concrete action for the user.
Speak Russian with the user."""

    def _build_messages(self) -> List[Dict[str, str]]:
        """Построить список сообщений для LLM."""
        result = [{"role": "system", "content": self._system_prompt}]
        for msg in self.messages[-30:]:  # last 30 messages for context
            result.append({"role": msg.role, "content": msg.content})
        return result

    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Обработать сообщение пользователя.

        Returns:
            Dict с полями: response, success, error (если есть)
        """
        if not self.model_router:
            return {
                "response": "⚠️ Model router не настроен. Проверьте конфигурацию.",
                "success": False,
                "error": "model_router not configured",
            }

        # Add user message
        self.messages.append(PAMessage(role="user", content=user_message))

        try:
            # Build prompt from messages
            messages = self._build_messages()
            prompt = self._format_messages_as_prompt(messages)

            # Generate response
            start_time = time.time()
            response = await asyncio.to_thread(
                lambda: self.model_router.generate(
                    prompt=prompt,
                    agent=AGENT_NAME,
                )
            )
            elapsed = time.time() - start_time

            # Store assistant response
            self.messages.append(PAMessage(role="assistant", content=response))

            logger.info(f"Prompt Architect response in {elapsed:.1f}s ({len(response)} chars)")

            return {
                "response": response,
                "success": True,
                "elapsed_seconds": round(elapsed, 1),
            }

        except Exception as e:
            logger.error(f"Prompt Architect error: {e}")
            return {
                "response": f"⚠️ Ошибка: {str(e)}",
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _format_messages_as_prompt(messages: List[Dict[str, str]]) -> str:
        """Форматировать сообщения как текстовый промпт."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"System:\n{content}\n")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant: ")
        return "\n\n".join(parts)

    def get_history(self) -> List[Dict[str, str]]:
        """Получить историю сообщений."""
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in self.messages
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику сессии."""
        user_msgs = sum(1 for m in self.messages if m.role == "user")
        asst_msgs = sum(1 for m in self.messages if m.role == "assistant")
        return {
            "total_messages": len(self.messages),
            "user_messages": user_msgs,
            "assistant_messages": asst_msgs,
        }

    def clear_history(self):
        """Очистить историю (начать новый диалог)."""
        self.messages.clear()
