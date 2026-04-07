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
from .code_validator import CodeValidator, ValidationResult
from .response_cache import ResponseCache
from .token_tracker import TokenTracker, TokenUsage
from .plugins import PluginManager, Plugin
from .dry_run import DryRunSimulator
from .zip_export import ZipExporter

__version__ = "4.0.0"
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
    "CodeValidator",
    "ValidationResult",
    "ResponseCache",
    "TokenTracker",
    "TokenUsage",
    "PluginManager",
    "Plugin",
    "DryRunSimulator",
    "ZipExporter",
]
