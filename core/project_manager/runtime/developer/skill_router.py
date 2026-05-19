"""
Skill Router — maps tasks to agent skills.

Explicit skill assignment. No "agent decides for itself".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


# ── Skill definitions ──

ALL_SKILLS = {
    # Backend skills
    "fastapi": {"domain": "backend", "level": "core"},
    "django": {"domain": "backend", "level": "core"},
    "flask": {"domain": "backend", "level": "core"},
    "websocket": {"domain": "backend", "level": "specialized"},
    "async_python": {"domain": "backend", "level": "core"},
    "api_design": {"domain": "backend", "level": "core"},
    "authentication": {"domain": "backend", "level": "specialized"},
    "database": {"domain": "backend", "level": "core"},
    "database_design": {"domain": "backend", "level": "specialized"},
    "caching": {"domain": "backend", "level": "specialized"},
    "middleware": {"domain": "backend", "level": "specialized"},
    "rest_api": {"domain": "backend", "level": "core"},
    "graphql": {"domain": "backend", "level": "specialized"},

    # Frontend skills
    "react": {"domain": "frontend", "level": "core"},
    "vue": {"domain": "frontend", "level": "core"},
    "css": {"domain": "frontend", "level": "core"},
    "responsive_design": {"domain": "frontend", "level": "core"},
    "component_design": {"domain": "frontend", "level": "core"},
    "accessibility": {"domain": "frontend", "level": "specialized"},
    "state_management": {"domain": "frontend", "level": "specialized"},
    "animation": {"domain": "frontend", "level": "specialized"},

    # DevOps skills
    "docker": {"domain": "devops", "level": "core"},
    "kubernetes": {"domain": "devops", "level": "specialized"},
    "ci_cd": {"domain": "devops", "level": "core"},
    "nginx": {"domain": "devops", "level": "specialized"},
    "monitoring": {"domain": "devops", "level": "specialized"},
    "linux": {"domain": "devops", "level": "core"},
    "github_actions": {"domain": "devops", "level": "specialized"},
    "deployment": {"domain": "devops", "level": "core"},

    # Testing skills
    "pytest": {"domain": "testing", "level": "core"},
    "unit_testing": {"domain": "testing", "level": "core"},
    "integration_testing": {"domain": "testing", "level": "core"},
    "e2e_testing": {"domain": "testing", "level": "specialized"},
    "test_coverage": {"domain": "testing", "level": "core"},
    "debugging": {"domain": "testing", "level": "core"},
    "mocking": {"domain": "testing", "level": "specialized"},

    # Architecture skills
    "architecture": {"domain": "architecture", "level": "core"},
    "design_patterns": {"domain": "architecture", "level": "core"},
    "system_design": {"domain": "architecture", "level": "core"},
    "api_architecture": {"domain": "architecture", "level": "specialized"},
    "microservices": {"domain": "architecture", "level": "specialized"},

    # Documentation skills
    "technical_writing": {"domain": "docs", "level": "core"},
    "api_documentation": {"domain": "docs", "level": "core"},
    "tutorials": {"domain": "docs", "level": "specialized"},
    "changelog": {"domain": "docs", "level": "specialized"},

    # Orchestration skills
    "orchestration": {"domain": "orchestration", "level": "core"},
    "planning": {"domain": "orchestration", "level": "core"},
    "review": {"domain": "orchestration", "level": "core"},
    "coordination": {"domain": "orchestration", "level": "core"},
}

# ── Task type to skills mapping ──

TASK_SKILL_MAP = {
    "create_api": ["fastapi", "api_design", "rest_api", "authentication"],
    "create_endpoint": ["fastapi", "api_design", "rest_api"],
    "create_websocket": ["websocket", "async_python", "fastapi"],
    "create_auth": ["authentication", "fastapi", "database"],
    "create_model": ["database", "database_design", "fastapi"],
    "create_migration": ["database", "database_design"],
    "create_component": ["react", "component_design", "css"],
    "create_page": ["react", "responsive_design", "css"],
    "create_style": ["css", "responsive_design"],
    "create_test": ["pytest", "unit_testing", "test_coverage"],
    "create_integration_test": ["pytest", "integration_testing", "mocking"],
    "create_e2e_test": ["e2e_testing", "debugging"],
    "create_dockerfile": ["docker", "linux"],
    "create_ci_config": ["ci_cd", "github_actions"],
    "create_docs": ["technical_writing", "api_documentation"],
    "create_architecture": ["architecture", "design_patterns", "system_design"],
    "refactor_code": ["design_patterns", "debugging"],
    "fix_bug": ["debugging", "unit_testing"],
    "optimize_performance": ["caching", "database", "async_python"],
    "setup_monitoring": ["monitoring", "linux"],
    "configure_nginx": ["nginx", "linux"],
}


@dataclass
class SkillAssignment:
    """Skills assigned to an agent for a specific task."""
    agent_id: str = ""
    task_id: str = ""
    skills: List[str] = field(default_factory=list)
    primary_skill: str = ""
    confidence: float = 0.0  # 0-1, how well the agent matches

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "skills": self.skills,
            "primary_skill": self.primary_skill,
            "confidence": self.confidence,
        }


class SkillRouter:
    """
    Routes skills to agents based on task requirements.

    Explicit mapping. No agent improvisation.
    """

    def __init__(self, agent_registry=None):
        from .agent_registry import AgentRegistry
        self._registry = agent_registry or AgentRegistry()

    def get_skills_for_task(self, task_type: str) -> List[str]:
        """Get the list of skills required for a task type."""
        return TASK_SKILL_MAP.get(task_type, [])

    def route_task(self, task_type: str,
                   preferred_agent: str = "") -> SkillAssignment:
        """
        Route a task to the best agent with appropriate skills.

        Returns a SkillAssignment with agent, skills, and confidence.
        """
        required_skills = self.get_skills_for_task(task_type)
        if not required_skills:
            return SkillAssignment(
                agent_id="teamlead",
                skills=[],
                primary_skill="",
                confidence=0.0,
            )

        # If preferred agent is specified and can handle it
        if preferred_agent:
            agent = self._registry.get(preferred_agent)
            if agent:
                matching = [s for s in required_skills
                           if s in agent.supported_skills]
                if matching:
                    confidence = len(matching) / len(required_skills)
                    return SkillAssignment(
                        agent_id=preferred_agent,
                        skills=matching,
                        primary_skill=matching[0],
                        confidence=min(1.0, confidence),
                    )

        # Find best agent by skill match
        best_agent = None
        best_match = []
        best_confidence = 0.0

        for agent in self._registry.list_agents():
            matching = [s for s in required_skills
                       if s in agent.supported_skills]
            if matching:
                confidence = len(matching) / len(required_skills)
                if confidence > best_confidence:
                    best_agent = agent
                    best_match = matching
                    best_confidence = confidence

        if best_agent:
            return SkillAssignment(
                agent_id=best_agent.id,
                skills=best_match,
                primary_skill=best_match[0],
                confidence=min(1.0, best_confidence),
            )

        # Fallback to teamlead
        return SkillAssignment(
            agent_id="teamlead",
            skills=[],
            primary_skill="",
            confidence=0.0,
        )

    def get_agent_skills(self, agent_id: str) -> List[str]:
        """Get all skills for an agent."""
        agent = self._registry.get(agent_id)
        if not agent:
            return []
        return agent.supported_skills

    def can_agent_handle(self, agent_id: str, task_type: str) -> bool:
        """Check if an agent has the skills for a task type."""
        required = self.get_skills_for_task(task_type)
        if not required:
            return False
        agent_skills = self.get_agent_skills(agent_id)
        return any(s in agent_skills for s in required)

    def suggest_agents_for_task(self, task_type: str,
                                 limit: int = 3) -> List[Dict]:
        """Suggest agents ranked by skill match for a task."""
        required_skills = self.get_skills_for_task(task_type)
        if not required_skills:
            return []

        results = []
        for agent in self._registry.list_agents():
            matching = [s for s in required_skills
                       if s in agent.supported_skills]
            if matching:
                confidence = len(matching) / len(required_skills)
                results.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "matching_skills": matching,
                    "confidence": round(confidence, 2),
                })

        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results[:limit]
