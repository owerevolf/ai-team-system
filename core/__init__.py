"""
AI Team System - Core Module
"""

from .main import AITeamSystem
from .agent_manager import AgentManager
from .model_router import ModelRouter
from .database import Database
from .logger import setup_logger, ProjectLogger
from .system_scanner import SystemScanner
from .git_manager import GitManager
from .project_context import ProjectContext, AgentResult

__version__ = "2.0.0"
__all__ = [
    "AITeamSystem",
    "AgentManager", 
    "ModelRouter",
    "Database",
    "setup_logger",
    "ProjectLogger",
    "SystemScanner",
    "GitManager",
    "ProjectContext",
    "AgentResult",
]
