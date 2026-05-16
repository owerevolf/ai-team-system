"""
Workspace sub-package for the Project Manager (Phase 8).

Provides practical daily-usage modules:
  - project_importer (P1): Universal project import
  - project_health (P2): Health dashboard
  - repo_repair (P3): Repo repair analysis
  - feature_dev (P4): Feature development mode
  - educational_mode (P5): Educational mode preservation
  - workspace_ux (P6): Simple workspace UX
  - autonomy_guard (P7): Safe autonomy limits
  - project_understanding (P8): Project understanding layer
  - task_traceability (P9): Task-to-code traceability
  - patch_review (P10): Patch review UX
  - session_memory (P11): Lightweight session memory
  - project_templates (P12): Real project templates
  - user_modes (P13/P17/P18): Human-first execution modes
  - local_first (P14): Local-first operation
  - failure_visibility (P15): Failure visibility
  - project_sandbox (P16): Project sandboxing
  - real_world_testing (P19): Real-world repository testing
  - fun_mode (P20): Keep it fun
"""

from core.project_manager.workspace.autonomy_guard import AutonomyGuard
from core.project_manager.workspace.educational_mode import EducationalMode
from core.project_manager.workspace.failure_visibility import FailureVisibility
from core.project_manager.workspace.feature_dev import FeatureDeveloper
from core.project_manager.workspace.fun_mode import FunMode
from core.project_manager.workspace.local_first import LocalFirstChecker
from core.project_manager.workspace.patch_review import PatchReview
from core.project_manager.workspace.project_health import ProjectHealthBuilder
from core.project_manager.workspace.project_importer import ProjectImporter
from core.project_manager.workspace.project_sandbox import ProjectSandbox
from core.project_manager.workspace.project_templates import TemplateManager, ProjectTemplate
from core.project_manager.workspace.project_understanding import ProjectUnderstanding
from core.project_manager.workspace.real_world_testing import RealWorldTestRunner
from core.project_manager.workspace.repo_repair import RepoRepair
from core.project_manager.workspace.session_memory import SessionMemory
from core.project_manager.workspace.task_traceability import TaskTraceability
from core.project_manager.workspace.user_modes import UserModeManager
from core.project_manager.workspace.workspace_ux import WorkspaceUX

__all__ = [
    "AutonomyGuard",
    "EducationalMode",
    "FailureVisibility",
    "FeatureDeveloper",
    "FunMode",
    "LocalFirstChecker",
    "PatchReview",
    "ProjectHealthBuilder",
    "ProjectImporter",
    "ProjectSandbox",
    "ProjectUnderstanding",
    "ProjectTemplate",
    "TemplateManager",
    "RealWorldTestRunner",
    "RepoRepair",
    "SessionMemory",
    "TaskTraceability",
    "UserModeManager",
    "WorkspaceUX",
]
