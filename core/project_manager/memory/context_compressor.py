"""
context_compressor.py — Repo Knowledge Compression.

Compresses repo knowledge into usable engineering context.
NOT summary for summary's sake — compressed operational truth.

Output example:
  AUTH SUBSYSTEM:
  - JWT based
  - refresh rotation fragile
  - middleware in auth.py
  - frontend uses useAuth()
  - avoid changing token lifecycle
  - previous bug: session invalidation loop
  - critical tests: tests/auth/test_refresh.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class CompressedModule:
    """Compressed module knowledge."""
    name: str = ""
    purpose: str = ""
    key_files: List[str] = field(default_factory=list)
    key_symbols: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    fragile_points: List[str] = field(default_factory=list)
    critical_tests: List[str] = field(default_factory=list)
    avoid_changes_to: List[str] = field(default_factory=list)
    token_cost: int = 0  # estimated tokens for this compression

    def to_compressed_string(self) -> str:
        """Compress to minimal string representation."""
        parts = [f"{self.name}: {self.purpose}"] if self.purpose else [self.name]

        if self.key_files:
            parts.append(f"  files: {', '.join(self.key_files[:3])}")
        if self.key_symbols:
            parts.append(f"  symbols: {', '.join(self.key_symbols[:5])}")
        if self.dependencies:
            parts.append(f"  deps: {', '.join(self.dependencies)}")
        if self.fragile_points:
            parts.append(f"  FRAGILE: {'; '.join(self.fragile_points)}")
        if self.critical_tests:
            parts.append(f"  tests: {', '.join(self.critical_tests[:3])}")
        if self.avoid_changes_to:
            parts.append(f"  AVOID: {'; '.join(self.avoid_changes_to)}")

        return "\n".join(parts)


@dataclass
class CompressedSubsystem:
    """Compressed subsystem knowledge."""
    name: str = ""
    role: str = ""
    modules: List[str] = field(default_factory=list)
    integration_points: List[str] = field(default_factory=list)
    known_risks: List[str] = field(default_factory=list)
    token_cost: int = 0

    def to_compressed_string(self) -> str:
        parts = [f"{self.name}: {self.role}"] if self.role else [self.name]
        if self.modules:
            parts.append(f"  modules: {', '.join(self.modules)}")
        if self.integration_points:
            parts.append(f"  integrates: {', '.join(self.integration_points)}")
        if self.known_risks:
            parts.append(f"  RISKS: {'; '.join(self.known_risks)}")
        return "\n".join(parts)


@dataclass
class CompressedContext:
    """Complete compressed context for LLM consumption."""
    architecture: str = ""
    active_subsystems: List[CompressedSubsystem] = field(default_factory=list)
    active_modules: List[CompressedModule] = field(default_factory=list)
    fragile_areas: List[str] = field(default_factory=list)
    frozen_zones: List[str] = field(default_factory=list)
    recent_failures: List[str] = field(default_factory=list)
    token_cost: int = 0

    def to_string(self) -> str:
        """Convert to compressed string."""
        lines = ["# Compressed Project Context", ""]

        if self.architecture:
            lines.append("## Architecture")
            lines.append(self.architecture)
            lines.append("")

        if self.active_subsystems:
            lines.append("## Active Subsystems")
            for sub in self.active_subsystems:
                lines.append(sub.to_compressed_string())
            lines.append("")

        if self.active_modules:
            lines.append("## Active Modules")
            for mod in self.active_modules:
                lines.append(mod.to_compressed_string())
            lines.append("")

        if self.fragile_areas:
            lines.append("## Fragile Areas")
            for area in self.fragile_areas:
                lines.append(f"- {area}")
            lines.append("")

        if self.frozen_zones:
            lines.append("## Frozen Zones")
            for zone in self.frozen_zones:
                lines.append(f"- {zone}")
            lines.append("")

        if self.recent_failures:
            lines.append("## Recent Failures")
            for failure in self.recent_failures:
                lines.append(f"- {failure}")
            lines.append("")

        return "\n".join(lines)


class ContextCompressor:
    """
    Compresses repo knowledge into usable engineering context.

    Takes raw project data and produces compressed operational truth.
    """

    # Token estimation: ~4 chars per token (rough average)
    CHARS_PER_TOKEN = 4

    def __init__(self, max_tokens: int = 30000):
        self._max_tokens = max_tokens

    def compress_module(self, name: str, purpose: str = "",
                        key_files: Optional[List[str]] = None,
                        key_symbols: Optional[List[str]] = None,
                        dependencies: Optional[List[str]] = None,
                        fragile_points: Optional[List[str]] = None,
                        critical_tests: Optional[List[str]] = None,
                        avoid_changes_to: Optional[List[str]] = None) -> CompressedModule:
        """Compress a module into minimal representation."""
        module = CompressedModule(
            name=name, purpose=purpose,
            key_files=key_files or [],
            key_symbols=key_symbols or [],
            dependencies=dependencies or [],
            fragile_points=fragile_points or [],
            critical_tests=critical_tests or [],
            avoid_changes_to=avoid_changes_to or [],
        )
        module.token_cost = self._estimate_tokens(module.to_compressed_string())
        return module

    def compress_subsystem(self, name: str, role: str = "",
                           modules: Optional[List[str]] = None,
                           integration_points: Optional[List[str]] = None,
                           known_risks: Optional[List[str]] = None) -> CompressedSubsystem:
        """Compress a subsystem."""
        sub = CompressedSubsystem(
            name=name, role=role,
            modules=modules or [],
            integration_points=integration_points or [],
            known_risks=known_risks or [],
        )
        sub.token_cost = self._estimate_tokens(sub.to_compressed_string())
        return sub

    def compress_architecture(self, subsystems: Dict[str, str],
                              module_map: Dict[str, str]) -> str:
        """Compress architecture into minimal string."""
        lines = []
        for name, role in subsystems.items():
            lines.append(f"{name}: {role}")
        return "\n".join(lines)

    def compress_execution_history(self, failures: List[Dict[str, Any]],
                                    limit: int = 5) -> List[str]:
        """Compress execution history to key failures."""
        compressed = []
        for f in failures[:limit]:
            desc = f.get("description", f.get("type", "unknown"))
            count = f.get("recurrence_count", 1)
            if count > 1:
                compressed.append(f"{desc} (x{count})")
            else:
                compressed.append(desc)
        return compressed

    def compress_adrs(self, adrs: List[Dict[str, str]],
                      limit: int = 10) -> List[str]:
        """Compress ADRs to key decisions."""
        compressed = []
        for adr in adrs[:limit]:
            title = adr.get("title", "")
            decision = adr.get("decision", "")
            if title and decision:
                compressed.append(f"{title}: {decision[:100]}")
        return compressed

    def build_context(self, architecture: str = "",
                      subsystems: Optional[List[CompressedSubsystem]] = None,
                      modules: Optional[List[CompressedModule]] = None,
                      fragile_areas: Optional[List[str]] = None,
                      frozen_zones: Optional[List[str]] = None,
                      recent_failures: Optional[List[str]] = None,
                      max_tokens: int = 0) -> CompressedContext:
        """Build complete compressed context within token budget."""
        max_tokens = max_tokens or self._max_tokens
        context = CompressedContext(
            architecture=architecture,
            fragile_areas=fragile_areas or [],
            frozen_zones=frozen_zones or [],
            recent_failures=recent_failures or [],
        )

        # Add subsystems within budget
        current_tokens = self._estimate_tokens(architecture)
        for sub in (subsystems or []):
            if current_tokens + sub.token_cost > max_tokens:
                break
            context.active_subsystems.append(sub)
            current_tokens += sub.token_cost

        # Add modules within remaining budget
        for mod in (modules or []):
            if current_tokens + mod.token_cost > max_tokens:
                break
            context.active_modules.append(mod)
            current_tokens += mod.token_cost

        context.token_cost = current_tokens
        return context

    def compress_for_task(self, task_context: Dict[str, Any],
                          memory_snapshot: Dict[str, Any],
                          max_tokens: int = 15000) -> str:
        """
        Build task-specific compressed context.

        Prioritizes:
        1. Current task info
        2. Relevant architecture
        3. Fragile areas for active files
        4. Recent relevant failures
        """
        lines = []

        # Task info
        task = task_context.get("active_task", {})
        if task:
            lines.append(f"# Task: {task.get('title', 'Unknown')}")
            if task.get("objective"):
                lines.append(f"Objective: {task['objective']}")
            if task.get("constraints"):
                lines.append(f"Constraints: {'; '.join(task['constraints'])}")
            lines.append("")

        # Architecture (only relevant subsystems)
        arch = memory_snapshot.get("architecture", {})
        active_files = task.get("active_files", [])
        if arch:
            lines.append("# Relevant Architecture")
            for name, info in arch.items():
                # Only include if relevant to active files
                key_files = info.get("key_files", [])
                if any(f in af for f in key_files for af in active_files):
                    role = info.get("role", "")
                    lines.append(f"{name}: {role}")
                    fragile = info.get("fragile_areas", [])
                    if fragile:
                        lines.append(f"  FRAGILE: {'; '.join(fragile)}")
            lines.append("")

        # Fragile areas
        fragile = memory_snapshot.get("fragile_areas", [])
        if fragile:
            lines.append("# Fragile Areas")
            for f in fragile[:10]:
                lines.append(f"- {f['area']}: {f['reason']} ({f['incidents']} incidents)")
            lines.append("")

        # Frozen zones
        frozen = memory_snapshot.get("frozen_zones", [])
        if frozen:
            lines.append("# Frozen Zones")
            for z in frozen:
                lines.append(f"- {z['area']}: {z['reason']}")
            lines.append("")

        # Recurring failures
        failures = memory_snapshot.get("recurring_failures", [])
        if failures:
            lines.append("# Recurring Failures")
            for f in failures[:5]:
                lines.append(f"- {f['type']}: {f['desc']} (x{f['count']})")
            lines.append("")

        result = "\n".join(lines)

        # Truncate if over budget
        if self._estimate_tokens(result) > max_tokens:
            result = self._truncate_to_tokens(result, max_tokens)

        return result

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return max(1, len(text) // self.CHARS_PER_TOKEN)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget."""
        max_chars = max_tokens * self.CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        # Truncate at line boundary
        lines = text.split("\n")
        result = []
        current_chars = 0
        for line in lines:
            if current_chars + len(line) + 1 > max_chars:
                result.append("... [truncated]")
                break
            result.append(line)
            current_chars += len(line) + 1
        return "\n".join(result)
