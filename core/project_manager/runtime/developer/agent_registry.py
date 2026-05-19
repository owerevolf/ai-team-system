"""
Agent Registry — unified registry of all agents.

Single map of capabilities. No hardcoded chaos.
Every agent's capabilities, limits, and constraints are defined here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class AgentRole(Enum):
    TEAMLEAD = "teamlead"
    ARCHITECT = "architect"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    TESTER = "tester"
    DOCUMENTALIST = "documentalist"


class RiskLevel(Enum):
    LOW = "low"          # Safe, read-only or low-impact
    MEDIUM = "medium"    # Standard development
    HIGH = "high"        # Can modify critical systems
    CRITICAL = "critical"  # Can modify anything (teamlead only)


@dataclass
class AgentCapabilities:
    """Defines what an agent can do."""
    can_create_files: bool = True
    can_modify_files: bool = True
    can_delete_files: bool = False
    can_create_dirs: bool = False
    can_run_tests: bool = False
    can_run_commands: bool = False
    can_modify_config: bool = False
    can_modify_architecture: bool = False
    can_approve_tasks: bool = False
    can_assign_tasks: bool = False
    can_review_others: bool = False


@dataclass
class AgentProfile:
    """Complete profile of an agent."""
    id: str = ""
    role: str = ""
    name: str = ""
    description: str = ""

    # Capabilities
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    allowed_operations: List[str] = field(default_factory=list)
    forbidden_operations: List[str] = field(default_factory=list)

    # Skills & languages
    preferred_languages: List[str] = field(default_factory=list)
    supported_skills: List[str] = field(default_factory=list)

    # Limits
    context_limit: int = 32000  # tokens
    max_files_per_task: int = 10
    max_lines_per_task: int = 500
    risk_level: str = RiskLevel.MEDIUM.value

    # Constraints
    requires_review: bool = True
    can_work_independently: bool = False
    requires_teamlead_approval: bool = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "role": self.role,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities.__dict__,
            "allowed_operations": self.allowed_operations,
            "forbidden_operations": self.forbidden_operations,
            "preferred_languages": self.preferred_languages,
            "supported_skills": self.supported_skills,
            "context_limit": self.context_limit,
            "max_files_per_task": self.max_files_per_task,
            "max_lines_per_task": self.max_lines_per_task,
            "risk_level": self.risk_level,
            "requires_review": self.requires_review,
            "can_work_independently": self.can_work_independently,
            "requires_teamlead_approval": self.requires_teamlead_approval,
        }


class AgentRegistry:
    """
    Unified registry of all agents in the system.

    This is the single source of truth for:
    - what each agent can do
    - what each agent cannot do
    - agent limits and constraints
    """

    def __init__(self):
        self._agents: Dict[str, AgentProfile] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the default 7 agents."""
        self.register(self._create_teamlead())
        self.register(self._create_architect())
        self.register(self._create_backend())
        self.register(self._create_frontend())
        self.register(self._create_devops())
        self.register(self._create_tester())
        self.register(self._create_documentalist())

    def _create_teamlead(self) -> AgentProfile:
        return AgentProfile(
            id="teamlead",
            role="teamlead",
            name="TeamLead",
            description="Orchestrator. Coordinates all agents. Does not write code directly.",
            capabilities=AgentCapabilities(
                can_create_files=False,
                can_modify_files=False,
                can_delete_files=False,
                can_create_dirs=False,
                can_run_tests=False,
                can_run_commands=False,
                can_modify_config=False,
                can_modify_architecture=False,
                can_approve_tasks=True,
                can_assign_tasks=True,
                can_review_others=True,
            ),
            allowed_operations=[
                "plan", "assign", "review", "coordinate", "validate",
                "block", "approve", "prioritize",
            ],
            forbidden_operations=[
                "write_code", "modify_files", "run_commands",
                "direct_execution",
            ],
            preferred_languages=[],
            supported_skills=["orchestration", "planning", "review", "coordination"],
            context_limit=64000,
            max_files_per_task=0,
            max_lines_per_task=0,
            risk_level=RiskLevel.CRITICAL.value,
            requires_review=False,
            can_work_independently=True,
            requires_teamlead_approval=False,
        )

    def _create_architect(self) -> AgentProfile:
        return AgentProfile(
            id="architect",
            role="architect",
            name="Architect",
            description="System design. Architecture decisions. High-level structure.",
            capabilities=AgentCapabilities(
                can_create_files=True,
                can_modify_files=True,
                can_delete_files=False,
                can_create_dirs=True,
                can_run_tests=False,
                can_run_commands=False,
                can_modify_config=True,
                can_modify_architecture=True,
                can_approve_tasks=False,
                can_assign_tasks=False,
                can_review_others=True,
            ),
            allowed_operations=[
                "design", "structure", "pattern", "review_architecture",
                "create_module", "define_interface",
            ],
            forbidden_operations=[
                "write_business_logic", "modify_tests", "deploy",
            ],
            preferred_languages=["python", "typescript"],
            supported_skills=["architecture", "design_patterns", "system_diagram",
                              "api_design", "database_design"],
            context_limit=48000,
            max_files_per_task=5,
            max_lines_per_task=200,
            risk_level=RiskLevel.HIGH.value,
            requires_review=True,
            can_work_independently=False,
            requires_teamlead_approval=True,
        )

    def _create_backend(self) -> AgentProfile:
        return AgentProfile(
            id="backend",
            role="backend",
            name="Backend",
            description="API, business logic, database, server-side.",
            capabilities=AgentCapabilities(
                can_create_files=True,
                can_modify_files=True,
                can_delete_files=False,
                can_create_dirs=False,
                can_run_tests=True,
                can_run_commands=False,
                can_modify_config=False,
                can_modify_architecture=False,
                can_approve_tasks=False,
                can_assign_tasks=False,
                can_review_others=False,
            ),
            allowed_operations=[
                "write_api", "write_logic", "write_model", "write_test",
                "create_endpoint", "implement_auth", "database_query",
            ],
            forbidden_operations=[
                "modify_architecture", "deploy", "modify_frontend",
                "approve_tasks",
            ],
            preferred_languages=["python", "typescript", "sql"],
            supported_skills=["fastapi", "django", "flask", "database",
                              "api_design", "authentication", "websocket",
                              "async_python", "testing"],
            context_limit=32000,
            max_files_per_task=8,
            max_lines_per_task=400,
            risk_level=RiskLevel.MEDIUM.value,
            requires_review=True,
            can_work_independently=False,
            requires_teamlead_approval=True,
        )

    def _create_frontend(self) -> AgentProfile:
        return AgentProfile(
            id="frontend",
            role="frontend",
            name="Frontend",
            description="UI, UX, client-side, components, styles.",
            capabilities=AgentCapabilities(
                can_create_files=True,
                can_modify_files=True,
                can_delete_files=False,
                can_create_dirs=False,
                can_run_tests=True,
                can_run_commands=False,
                can_modify_config=False,
                can_modify_architecture=False,
                can_approve_tasks=False,
                can_assign_tasks=False,
                can_review_others=False,
            ),
            allowed_operations=[
                "write_component", "write_style", "write_page",
                "create_ui", "implement_ux", "write_test",
            ],
            forbidden_operations=[
                "modify_backend", "modify_api", "deploy", "modify_database",
                "approve_tasks",
            ],
            preferred_languages=["typescript", "javascript", "css", "html"],
            supported_skills=["react", "vue", "css", "responsive_design",
                              "component_design", "accessibility", "testing"],
            context_limit=32000,
            max_files_per_task=8,
            max_lines_per_task=400,
            risk_level=RiskLevel.MEDIUM.value,
            requires_review=True,
            can_work_independently=False,
            requires_teamlead_approval=True,
        )

    def _create_devops(self) -> AgentProfile:
        return AgentProfile(
            id="devops",
            role="devops",
            name="DevOps",
            description="Deployment, CI/CD, infrastructure, monitoring.",
            capabilities=AgentCapabilities(
                can_create_files=True,
                can_modify_files=True,
                can_delete_files=False,
                can_create_dirs=False,
                can_run_tests=False,
                can_run_commands=False,
                can_modify_config=True,
                can_modify_architecture=False,
                can_approve_tasks=False,
                can_assign_tasks=False,
                can_review_others=False,
            ),
            allowed_operations=[
                "write_dockerfile", "write_ci_config", "configure_deploy",
                "setup_monitoring", "write_nginx_config",
            ],
            forbidden_operations=[
                "modify_business_logic", "modify_frontend", "approve_tasks",
            ],
            preferred_languages=["yaml", "bash", "python"],
            supported_skills=["docker", "kubernetes", "ci_cd", "nginx",
                              "monitoring", "linux", "github_actions"],
            context_limit=24000,
            max_files_per_task=5,
            max_lines_per_task=200,
            risk_level=RiskLevel.HIGH.value,
            requires_review=True,
            can_work_independently=False,
            requires_teamlead_approval=True,
        )

    def _create_tester(self) -> AgentProfile:
        return AgentProfile(
            id="tester",
            role="tester",
            name="Tester",
            description="QA, testing, test coverage, bug finding.",
            capabilities=AgentCapabilities(
                can_create_files=True,
                can_modify_files=False,
                can_delete_files=False,
                can_create_dirs=False,
                can_run_tests=True,
                can_run_commands=False,
                can_modify_config=False,
                can_modify_architecture=False,
                can_approve_tasks=False,
                can_assign_tasks=False,
                can_review_others=False,
            ),
            allowed_operations=[
                "write_test", "run_test", "report_bug", "verify_fix",
                "check_coverage",
            ],
            forbidden_operations=[
                "modify_production_code", "deploy", "approve_tasks",
            ],
            preferred_languages=["python", "typescript", "javascript"],
            supported_skills=["pytest", "unit_testing", "integration_testing",
                              "e2e_testing", "test_coverage", "debugging"],
            context_limit=24000,
            max_files_per_task=5,
            max_lines_per_task=300,
            risk_level=RiskLevel.LOW.value,
            requires_review=False,
            can_work_independently=True,
            requires_teamlead_approval=False,
        )

    def _create_documentalist(self) -> AgentProfile:
        return AgentProfile(
            id="documentalist",
            role="documentalist",
            name="Documentalist",
            description="Documentation, README, API docs, guides.",
            capabilities=AgentCapabilities(
                can_create_files=True,
                can_modify_files=True,
                can_delete_files=False,
                can_create_dirs=False,
                can_run_tests=False,
                can_run_commands=False,
                can_modify_config=False,
                can_modify_architecture=False,
                can_approve_tasks=False,
                can_assign_tasks=False,
                can_review_others=False,
            ),
            allowed_operations=[
                "write_docs", "update_readme", "write_guide",
                "document_api", "write_changelog",
            ],
            forbidden_operations=[
                "modify_code", "deploy", "approve_tasks",
            ],
            preferred_languages=["markdown"],
            supported_skills=["technical_writing", "api_documentation",
                              "tutorials", "changelog"],
            context_limit=16000,
            max_files_per_task=5,
            max_lines_per_task=500,
            risk_level=RiskLevel.LOW.value,
            requires_review=False,
            can_work_independently=True,
            requires_teamlead_approval=False,
        )

    def register(self, agent: AgentProfile) -> None:
        """Register an agent profile."""
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[AgentProfile]:
        """Get agent profile by ID."""
        return self._agents.get(agent_id)

    def get_by_role(self, role: str) -> Optional[AgentProfile]:
        """Get agent profile by role."""
        for agent in self._agents.values():
            if agent.role == role:
                return agent
        return None

    def list_agents(self) -> List[AgentProfile]:
        """List all registered agents."""
        return list(self._agents.values())

    def get_capable_agents(self, skill: str) -> List[AgentProfile]:
        """Find agents that support a given skill."""
        return [a for a in self._agents.values()
                if skill in a.supported_skills]

    def get_agents_by_risk(self, max_risk: str) -> List[AgentProfile]:
        """Get agents with risk level <= max_risk."""
        levels = ["low", "medium", "high", "critical"]
        if max_risk not in levels:
            return []
        max_idx = levels.index(max_risk)
        return [a for a in self._agents.values()
                if levels.index(a.risk_level) <= max_idx]

    def can_agent(self, agent_id: str, operation: str) -> bool:
        """Check if an agent can perform an operation."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        if operation in agent.forbidden_operations:
            return False
        return operation in agent.allowed_operations

    def validate_agent_task(self, agent_id: str,
                            task_type: str) -> tuple[bool, str]:
        """Validate if an agent can handle a task type."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False, f"Unknown agent: {agent_id}"
        if task_type in agent.forbidden_operations:
            return False, f"Agent '{agent_id}' cannot perform '{task_type}'"
        if task_type not in agent.allowed_operations:
            return False, f"Agent '{agent_id}' not qualified for '{task_type}'"
        return True, "OK"
