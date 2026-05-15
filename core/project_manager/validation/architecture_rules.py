"""
Architecture Rules Engine — declarative layer boundary enforcement.

Rules are:
- Declarative (defined in config, not code)
- Configurable (per-project)
- Deterministic (no AI interpretation)

Rule types:
- Layer boundaries: frontend cannot import backend
- Path patterns: files matching pattern X cannot import files matching pattern Y
- Symbol visibility: private symbols cannot be imported outside module
- File protection: certain files cannot be modified by agents
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core.project_manager.models import FileEntry
from loguru import logger


class RuleAction(Enum):
    DENY = "deny"       # Block the import/modification
    WARN = "warn"       # Allow but warn
    LOG = "log"         # Just log


@dataclass
class ArchitectureRule:
    """A single architecture rule."""
    name: str
    description: str
    source_pattern: str   # regex for source file path
    target_pattern: str   # regex for target file path (import)
    action: RuleAction
    enabled: bool = True

    def matches(self, source_file: str, target_file: str) -> bool:
        """Check if this rule matches a source→target import."""
        try:
            source_match = re.search(self.source_pattern, source_file) is not None
            target_match = re.search(self.target_pattern, target_file) is not None
            return source_match and target_match
        except re.error:
            return False


@dataclass
class RuleViolation:
    """A single architecture rule violation."""
    rule_name: str
    source_file: str
    target_file: str
    action: RuleAction
    message: str


@dataclass
class ArchitectureRulesConfig:
    """Configuration for architecture rules."""
    rules: List[ArchitectureRule] = field(default_factory=list)
    protected_files: List[str] = field(default_factory=list)  # glob patterns
    protected_symbols: List[str] = field(default_factory=list)  # regex patterns

    @classmethod
    def default_rules(cls) -> 'ArchitectureRulesConfig':
        """Create default architecture rules."""
        config = cls()

        # Layer boundary rules
        config.rules.append(ArchitectureRule(
            name="no_frontend_to_backend",
            description="Frontend cannot import backend internals",
            source_pattern=r"^web_ui/",
            target_pattern=r"^core/(project_manager|storage|events)/",
            action=RuleAction.DENY,
        ))

        config.rules.append(ArchitectureRule(
            name="no_ui_to_database",
            description="UI layer cannot access database layer directly",
            source_pattern=r"^web_ui/",
            target_pattern=r"^core/database",
            action=RuleAction.DENY,
        ))

        config.rules.append(ArchitectureRule(
            name="no_tests_to_tests",
            description="Tests should not import other test utilities (use conftest)",
            source_pattern=r"^tests/",
            target_pattern=r"^tests/",
            action=RuleAction.WARN,
        ))

        # Protected files (cannot be modified by agents)
        config.protected_files = [
            "core/project_manager/__init__.py",
            "core/project_manager/validation/__init__.py",
            "core/project_manager/storage/__init__.py",
            "core/project_manager/events/__init__.py",
            "core/project_manager/models/__init__.py",
            "core/project_manager/query/__init__.py",
            "core/agent_manager.py",
            "web_ui/app.py",
        ]

        # Protected symbols (cannot be removed/renamed)
        config.protected_symbols = [
            r"ProjectManager",
            r"FileEntry",
            r"SymbolEntry",
            r"DependencyEdge",
            r"Snapshot",
            r"QueryEngine",
            r"Storage",
            r"EventBus",
            r"FileIndexer",
            r"DependencyGraph",
            r"SymbolExtractor",
            r"GitIntelligence",
            r"ValidationPipeline",
        ]

        return config

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchitectureRulesConfig':
        """Load config from dict (e.g., from YAML)."""
        config = cls()

        for rule_data in data.get('rules', []):
            config.rules.append(ArchitectureRule(
                name=rule_data['name'],
                description=rule_data.get('description', ''),
                source_pattern=rule_data['source_pattern'],
                target_pattern=rule_data['target_pattern'],
                action=RuleAction(rule_data.get('action', 'warn')),
                enabled=rule_data.get('enabled', True),
            ))

        config.protected_files = data.get('protected_files', [])
        config.protected_symbols = data.get('protected_symbols', [])

        return config


class ArchitectureRulesEngine:
    """
    Enforces architecture rules on the project.

    Checks:
    - Layer boundary violations
    - Protected file modifications
    - Protected symbol changes
    """

    def __init__(
        self,
        files: Dict[str, FileEntry],
        dependencies: Dict[str, List[str]],
        config: Optional[ArchitectureRulesConfig] = None,
    ):
        self.files = files
        self.dependencies = dependencies
        self.config = config or ArchitectureRulesConfig.default_rules()

    def check_import(self, source_file: str, target_file: str) -> Optional[RuleViolation]:
        """Check if an import violates any architecture rule."""
        for rule in self.config.rules:
            if not rule.enabled:
                continue
            if rule.matches(source_file, target_file):
                return RuleViolation(
                    rule_name=rule.name,
                    source_file=source_file,
                    target_file=target_file,
                    action=rule.action,
                    message=f"Architecture violation: {rule.description} ({rule.name})",
                )
        return None

    def check_all_imports(self) -> List[RuleViolation]:
        """Check all imports in the project for rule violations."""
        violations = []

        for source_file, deps in self.dependencies.items():
            for target_file in deps:
                violation = self.check_import(source_file, target_file)
                if violation:
                    violations.append(violation)

        return violations

    def is_file_protected(self, file_path: str) -> bool:
        """Check if a file is protected from agent modifications."""
        for pattern in self.config.protected_files:
            if self._glob_match(pattern, file_path):
                return True
        return False

    def get_protected_files(self) -> List[str]:
        """Get list of protected file paths."""
        protected = []
        for rel_path in self.files:
            if self.is_file_protected(rel_path):
                protected.append(rel_path)
        return protected

    def is_symbol_protected(self, symbol_name: str) -> bool:
        """Check if a symbol is protected from removal/renaming."""
        for pattern in self.config.protected_symbols:
            try:
                if re.search(pattern, symbol_name):
                    return True
            except re.error:
                continue
        return False

    def check_symbol_removal(
        self, old_symbols: List[Dict], new_symbols: List[Dict]
    ) -> List[str]:
        """
        Check if any protected symbols were removed.
        Returns list of removed protected symbol names.
        """
        old_names = {s.get('name', '') for s in old_symbols}
        new_names = {s.get('name', '') for s in new_symbols}
        removed = old_names - new_names

        protected_removed = []
        for name in removed:
            if self.is_symbol_protected(name):
                protected_removed.append(name)

        return protected_removed

    def _glob_match(self, pattern: str, path: str) -> bool:
        """Simple glob-style matching."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
