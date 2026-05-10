"""
Tests for Prompt Architect Agent.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio


class TestPromptArchitectAgent:
    """Tests for the PromptArchitectAgent class."""

    def test_import(self):
        """Test that the module can be imported."""
        from core.prompt_architect import PromptArchitectAgent, AGENT_NAME
        assert AGENT_NAME == "prompt_architect"

    def test_init_without_router(self):
        """Test initialization without model router."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        assert agent.model_router is None
        assert agent.messages == []
        assert len(agent._system_prompt) > 0

    def test_init_with_mock_router(self):
        """Test initialization with a mock model router."""
        from core.prompt_architect import PromptArchitectAgent
        mock_router = MagicMock()
        agent = PromptArchitectAgent(model_router=mock_router)
        assert agent.model_router is mock_router

    def test_load_skill_from_file(self):
        """Test that skill is loaded from file."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        # Should have loaded the skill file
        assert "PROMPT ARCHITECT" in agent._system_prompt or "Prompt Architect" in agent._system_prompt

    def test_fallback_prompt_exists(self):
        """Test that fallback prompt is defined."""
        from core.prompt_architect import PromptArchitectAgent
        fallback = PromptArchitectAgent._get_fallback_prompt()
        assert len(fallback) > 0
        assert "Prompt Architect" in fallback

    def test_build_messages_empty(self):
        """Test building messages with no history."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        messages = agent._build_messages()
        assert len(messages) == 1  # Only system prompt
        assert messages[0]["role"] == "system"

    def test_build_messages_with_history(self):
        """Test building messages with conversation history."""
        from core.prompt_architect import PromptArchitectAgent, PAMessage
        agent = PromptArchitectAgent(model_router=None)
        agent.messages = [
            PAMessage(role="user", content="Привет"),
            PAMessage(role="assistant", content="Привет! Я Prompt Architect."),
        ]
        messages = agent._build_messages()
        assert len(messages) == 3  # system + 2 messages
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Привет"
        assert messages[2]["role"] == "assistant"

    def test_format_messages_as_prompt(self):
        """Test formatting messages as text prompt."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
        ]
        result = agent._format_messages_as_prompt(messages)
        assert "System prompt" in result
        assert "User message" in result
        assert "Assistant message" in result
        assert result.endswith("Assistant: ")

    def test_get_history_empty(self):
        """Test getting empty history."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        history = agent.get_history()
        assert history == []

    def test_get_history_with_messages(self):
        """Test getting history with messages."""
        from core.prompt_architect import PromptArchitectAgent, PAMessage
        agent = PromptArchitectAgent(model_router=None)
        agent.messages = [
            PAMessage(role="user", content="Test"),
        ]
        history = agent.get_history()
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Test"

    def test_get_stats_empty(self):
        """Test getting stats with no messages."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        stats = agent.get_stats()
        assert stats["total_messages"] == 0
        assert stats["user_messages"] == 0
        assert stats["assistant_messages"] == 0

    def test_get_stats_with_messages(self):
        """Test getting stats with messages."""
        from core.prompt_architect import PromptArchitectAgent, PAMessage
        agent = PromptArchitectAgent(model_router=None)
        agent.messages = [
            PAMessage(role="user", content="Q1"),
            PAMessage(role="assistant", content="A1"),
            PAMessage(role="user", content="Q2"),
        ]
        stats = agent.get_stats()
        assert stats["total_messages"] == 3
        assert stats["user_messages"] == 2
        assert stats["assistant_messages"] == 1

    def test_clear_history(self):
        """Test clearing conversation history."""
        from core.prompt_architect import PromptArchitectAgent, PAMessage
        agent = PromptArchitectAgent(model_router=None)
        agent.messages = [
            PAMessage(role="user", content="Test"),
            PAMessage(role="assistant", content="Response"),
        ]
        agent.clear_history()
        assert agent.messages == []

    @pytest.mark.asyncio
    async def test_process_message_no_router(self):
        """Test processing message without router returns error."""
        from core.prompt_architect import PromptArchitectAgent
        agent = PromptArchitectAgent(model_router=None)
        result = await agent.process_message("Привет")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_message_with_mock_router(self):
        """Test processing message with mock router."""
        from core.prompt_architect import PromptArchitectAgent
        mock_router = MagicMock()
        mock_router.generate.return_value = "Ответ от Prompt Architect"
        agent = PromptArchitectAgent(model_router=mock_router)
        result = await agent.process_message("Привет")
        assert result["success"] is True
        assert result["response"] == "Ответ от Prompt Architect"
        assert "elapsed_seconds" in result
        # Check that messages were stored
        assert len(agent.messages) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_process_message_router_error(self):
        """Test processing message when router raises error."""
        from core.prompt_architect import PromptArchitectAgent
        mock_router = MagicMock()
        mock_router.generate.side_effect = RuntimeError("API error")
        agent = PromptArchitectAgent(model_router=mock_router)
        result = await agent.process_message("Привет")
        assert result["success"] is False
        assert "API error" in result["error"]


class TestPromptArchitectSkill:
    """Tests for the Prompt Architect skill file."""

    def test_skill_file_exists(self):
        """Test that the skill file exists."""
        from pathlib import Path
        skill_file = Path(__file__).resolve().parent.parent / "core" / "skills" / "PROMPT_ARCHITECT_SKILL.md"
        assert skill_file.exists()

    def test_skill_file_has_content(self):
        """Test that the skill file has meaningful content."""
        from pathlib import Path
        skill_file = Path(__file__).resolve().parent.parent / "core" / "skills" / "PROMPT_ARCHITECT_SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        assert len(content) > 500
        # Check for key sections
        assert "РОЛЬ" in content or "ROLE" in content
        assert "КОНТЕКСТ" in content or "CONTEXT" in content
        assert "ЗАДАЧА" in content or "TASK" in content
        assert "ОГРАНИЧЕНИЯ" in content or "CONSTRAINTS" in content
        assert "ФОРМАТ" in content or "FORMAT" in content

    def test_skill_file_has_startup(self):
        """Test that the skill file has startup message."""
        from pathlib import Path
        skill_file = Path(__file__).resolve().parent.parent / "core" / "skills" / "PROMPT_ARCHITECT_SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        assert "Привет" in content or "STARTUP" in content


class TestPromptArchitectAgentSkills:
    """Tests for prompt_architect in agent_skills."""

    def test_prompt_architect_in_agent_skills(self):
        """Test that prompt_architect is registered in AGENT_SKILL_MAP."""
        from core.agent_skills import AGENT_SKILL_MAP
        assert "prompt_architect" in AGENT_SKILL_MAP

    def test_prompt_architect_config(self):
        """Test prompt_architect configuration."""
        from core.agent_skills import get_agent_config
        config = get_agent_config("prompt_architect")
        assert config["name"] == "prompt_architect"
        assert config["preferred_strength"] == "reasoning"
        assert config["temperature"] == 0.7
        assert "skill_addon" in config
        assert len(config["skill_addon"]) > 0

    def test_prompt_architect_skill_file_reference(self):
        """Test that skill file reference is correct."""
        from core.agent_skills import AGENT_SKILL_MAP
        skill = AGENT_SKILL_MAP["prompt_architect"]
        assert skill["skill_file"] == "PROMPT_ARCHITECT_SKILL.md"
