"""
Tests for LVL99 skill prompts integration
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.agent_manager import AgentManager
from core.model_router import ModelRouter


class TestSkillPrompts:
    """Test that LVL99 skill prompts are loaded correctly"""

    def setup_method(self):
        self.router = ModelRouter()
        self.mgr = AgentManager(self.router)

    def test_advanced_level_uses_skill_prompts(self):
        """Advanced level should load LVL99 skill prompts from core/skills/"""
        for agent in ["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"]:
            prompt = self.mgr.get_agent_prompt(agent, "advanced")
            assert "LVL99" in prompt, f"{agent} advanced prompt should contain LVL99 marker"
            assert len(prompt) > 5000, f"{agent} advanced prompt should be substantial"

    def test_zero_level_uses_role_prompts(self):
        """Zero level should load from prompts/roles/"""
        prompt = self.mgr.get_agent_prompt("teamlead", "zero")
        assert "LVL99" not in prompt
        assert len(prompt) > 100

    def test_beginner_level_uses_role_prompts(self):
        """Beginner level should load from prompts/roles/"""
        prompt = self.mgr.get_agent_prompt("backend", "beginner")
        assert "LVL99" not in prompt
        assert len(prompt) > 100

    def test_skill_prompt_contains_identity(self):
        """Skill prompts should contain agent identity"""
        teamlead_prompt = self.mgr.get_agent_prompt("teamlead", "advanced")
        assert "TEAMLEAD" in teamlead_prompt.upper()
        assert "Senior Engineering Manager" in teamlead_prompt

    def test_skill_prompt_contains_protocol(self):
        """Skill prompts should contain protocols/standards"""
        backend_prompt = self.mgr.get_agent_prompt("backend", "advanced")
        assert "API" in backend_prompt
        assert "Repository" in backend_prompt

    def test_skill_prompt_contains_anti_patterns(self):
        """Skill prompts should contain anti-patterns section"""
        for agent in ["teamlead", "architect", "backend", "frontend"]:
            prompt = self.mgr.get_agent_prompt(agent, "advanced")
            assert "ANTI-PATTERNS" in prompt or "anti-pattern" in prompt.lower()

    def test_skill_prompt_contains_checklist(self):
        """Skill prompts should contain checklists"""
        architect_prompt = self.mgr.get_agent_prompt("architect", "advanced")
        assert "CHECKLIST" in architect_prompt or "checklist" in architect_prompt.lower()

    def test_all_agents_have_skill_files(self):
        """All 7 agents should have skill files"""
        skills_dir = Path(__file__).parent.parent / "core" / "skills"
        for agent in ["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"]:
            skill_file = skills_dir / f"{agent.upper()}_SKILL.md"
            assert skill_file.exists(), f"Skill file for {agent} should exist"
            content = skill_file.read_text(encoding="utf-8")
            assert len(content) > 1000, f"Skill file for {agent} should be substantial"

    def test_skill_prompts_have_core_philosophy(self):
        """All skill prompts should have a core philosophy section"""
        for agent in ["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"]:
            prompt = self.mgr.get_agent_prompt(agent, "advanced")
            assert "CORE PHILOSOPHY" in prompt or "Core Philosophy" in prompt

    def test_fallback_to_default_prompt(self):
        """Unknown agent should get default prompt"""
        prompt = self.mgr.get_agent_prompt("unknown_agent", "advanced")
        assert "unknown_agent" in prompt
        assert "AI Team System" in prompt


class TestSkillPromptContent:
    """Test specific content in skill prompts"""

    def setup_method(self):
        self.router = ModelRouter()
        self.mgr = AgentManager(self.router)

    def test_teamlead_has_intake_protocol(self):
        """TeamLead should have mandatory intake protocol"""
        prompt = self.mgr.get_agent_prompt("teamlead", "advanced")
        assert "INTAKE" in prompt or "intake" in prompt.lower()
        assert "SIGNAL EXTRACTION" in prompt or "Signal Extraction" in prompt

    def test_architect_has_domain_modeling(self):
        """Architect should have domain modeling step"""
        prompt = self.mgr.get_agent_prompt("architect", "advanced")
        assert "DOMAIN" in prompt or "domain" in prompt.lower()

    def test_backend_has_repository_pattern(self):
        """Backend should have repository pattern"""
        prompt = self.mgr.get_agent_prompt("backend", "advanced")
        assert "Repository" in prompt or "repository" in prompt.lower()

    def test_frontend_has_accessibility(self):
        """Frontend should have accessibility standards"""
        prompt = self.mgr.get_agent_prompt("frontend", "advanced")
        assert "accessibility" in prompt.lower() or "ARIA" in prompt

    def test_devops_has_docker_standards(self):
        """DevOps should have Docker standards"""
        prompt = self.mgr.get_agent_prompt("devops", "advanced")
        assert "Docker" in prompt or "docker" in prompt.lower()

    def test_tester_has_test_pyramid(self):
        """Tester should have test pyramid concept"""
        prompt = self.mgr.get_agent_prompt("tester", "advanced")
        assert "pyramid" in prompt.lower() or "test levels" in prompt.lower()

    def test_documentalist_has_taxonomy(self):
        """Documentalist should have documentation taxonomy"""
        prompt = self.mgr.get_agent_prompt("documentalist", "advanced")
        assert "taxonomy" in prompt.lower() or "TAXONOMY" in prompt


class TestAgentManagerIntegration:
    """Test AgentManager integration with skills"""

    def test_get_tools_for_prompt(self):
        """Tools should be available for prompt"""
        mgr = AgentManager(ModelRouter())
        tools = mgr.get_tools_for_prompt()
        assert "create_file" in tools
        assert "read_file" in tools

    def test_register_tools(self):
        """All expected tools should be registered"""
        mgr = AgentManager(ModelRouter())
        assert "create_file" in mgr.tools
        assert "read_file" in mgr.tools
        assert "list_directory" in mgr.tools
        assert "run_command" in mgr.tools
        assert "create_directory" in mgr.tools
        assert "write_to_file" in mgr.tools

    def test_command_whitelist(self):
        """Command whitelist should work"""
        mgr = AgentManager(ModelRouter())
        assert mgr._is_command_allowed("python app.py") is True
        assert mgr._is_command_allowed("pip install fastapi") is True
        assert mgr._is_command_allowed("rm -rf /") is False
