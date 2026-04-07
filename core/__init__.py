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
from .agent_model_config import get_agent_model_config, list_agent_models, MODEL_PROFILES
from .memory import AgentMemory, MemoryEntry
from .rag import RAGSystem, Document, SimpleVectorStore
from .event_bus import EventBus, Event
from .sandbox import CodeSandbox, SandboxResult
from .reasoning_trace import TraceManager, ReasoningTrace, ReasoningStep
from .fallback_manager import FallbackManager, FallbackConfig, FallbackEvent
from .learning_mode import LearningMode, TutorialStep, GlossaryEntry, LearningProgress
from .mode_switcher import ModeSwitcher, ModeConfig, MODES

__version__ = "5.1.0"
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
    "get_agent_model_config",
    "list_agent_models",
    "MODEL_PROFILES",
    "AgentMemory",
    "MemoryEntry",
    "RAGSystem",
    "Document",
    "SimpleVectorStore",
    "EventBus",
    "Event",
    "CodeSandbox",
    "SandboxResult",
    "TraceManager",
    "ReasoningTrace",
    "ReasoningStep",
    "FallbackManager",
    "FallbackConfig",
    "FallbackEvent",
    "LearningMode",
    "TutorialStep",
    "GlossaryEntry",
    "LearningProgress",
    "ModeSwitcher",
    "ModeConfig",
    "MODES",
]
