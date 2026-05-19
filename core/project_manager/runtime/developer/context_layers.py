"""
Context Layers — layered context system to stay under 150k tokens.

Instead of dumping the entire project into the prompt,
we organize context into layers and only include what's needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContextLayer:
    """A single layer of context."""
    name: str = ""
    content: str = ""
    priority: int = 0  # higher = more important
    max_tokens: int = 0  # 0 = unlimited
    required: bool = False
    token_count: int = 0

    def estimate_tokens(self) -> int:
        """Rough token estimation: ~4 chars per token."""
        if self.token_count > 0:
            return self.token_count
        return max(1, len(self.content) // 4)


@dataclass
class ContextLayers:
    """
    Layered context system.

    Layers:
        Layer 1: System Identity (always included)
        Layer 2: Project Brain (always included)
        Layer 3: Current Sprint (included when executing)
        Layer 4: Agent Task Context (included per-task)

    Goal: keep total context under ~150k tokens.
    """

    # Layer 1: System Identity
    system_identity: ContextLayer = field(default_factory=lambda: ContextLayer(
        name="System Identity",
        content="",
        priority=100,
        required=True,
    ))

    # Layer 2: Project Brain
    project_brain: ContextLayer = field(default_factory=lambda: ContextLayer(
        name="Project Brain",
        content="",
        priority=90,
        required=True,
    ))

    # Layer 3: Current Sprint
    current_sprint: ContextLayer = field(default_factory=lambda: ContextLayer(
        name="Current Sprint",
        content="",
        priority=70,
        required=False,
    ))

    # Layer 4: Agent Task Context
    agent_task: ContextLayer = field(default_factory=lambda: ContextLayer(
        name="Agent Task Context",
        content="",
        priority=80,
        required=False,
    ))

    # Additional custom layers
    custom_layers: List[ContextLayer] = field(default_factory=list)

    # Budget
    max_total_tokens: int = 150000

    def set_system_identity(self, content: str) -> None:
        self.system_identity = ContextLayer(
            name="System Identity",
            content=content,
            priority=100,
            required=True,
        )

    def set_project_brain(self, brain_dict: Dict[str, Any]) -> None:
        """Set project brain content from a ProjectBrain dict."""
        # Compress: only include essential fields
        essential = {
            "project_name": brain_dict.get("project_name", ""),
            "project_summary": brain_dict.get("project_summary", ""),
            "current_phase": brain_dict.get("current_phase", ""),
            "current_focus": brain_dict.get("current_focus", ""),
            "runtime_state": brain_dict.get("runtime_state", ""),
            "tech_stack": brain_dict.get("tech_stack", {}),
            "architecture": brain_dict.get("architecture", {}),
            "active_goals": brain_dict.get("active_goals", []),
            "active_tasks": brain_dict.get("active_tasks", []),
            "constraints": brain_dict.get("constraints", []),
            "known_risks": brain_dict.get("known_risks", []),
        }
        content = json.dumps(essential, indent=2, ensure_ascii=False)
        self.project_brain = ContextLayer(
            name="Project Brain",
            content=content,
            priority=90,
            required=True,
        )

    def set_current_sprint(self, goals: List[Dict], tasks: List[Dict]) -> None:
        """Set current sprint content."""
        content = json.dumps({
            "goals": goals,
            "tasks": tasks,
        }, indent=2, ensure_ascii=False)
        self.current_sprint = ContextLayer(
            name="Current Sprint",
            content=content,
            priority=70,
            required=False,
        )

    def set_agent_task(self, contract_context: str) -> None:
        """Set agent task context from a task contract."""
        self.agent_task = ContextLayer(
            name="Agent Task Context",
            content=contract_context,
            priority=80,
            required=False,
        )

    def add_custom_layer(self, name: str, content: str,
                         priority: int = 50, required: bool = False) -> None:
        """Add a custom context layer."""
        self.custom_layers.append(ContextLayer(
            name=name,
            content=content,
            priority=priority,
            required=required,
        ))

    def get_active_layers(self) -> List[ContextLayer]:
        """Get all active layers sorted by priority (highest first)."""
        layers = []
        if self.system_identity.content:
            layers.append(self.system_identity)
        if self.project_brain.content:
            layers.append(self.project_brain)
        if self.current_sprint.content:
            layers.append(self.current_sprint)
        if self.agent_task.content:
            layers.append(self.agent_task)
        layers.extend(self.custom_layers)
        layers.sort(key=lambda l: l.priority, reverse=True)
        return layers

    def build_context(self, max_tokens: int = 0) -> str:
        """
        Build the full context string within token budget.

        Strategy:
        1. Always include required layers
        2. Add optional layers by priority until budget is reached
        3. If budget is exceeded, truncate lowest priority layers
        """
        if max_tokens <= 0:
            max_tokens = self.max_total_tokens

        layers = self.get_active_layers()
        parts = []
        total_tokens = 0

        # First pass: required layers
        for layer in layers:
            if not layer.required:
                continue
            tokens = layer.estimate_tokens()
            if total_tokens + tokens > max_tokens:
                # Truncate required layer to fit
                remaining = max_tokens - total_tokens
                if remaining > 100:
                    truncated = layer.content[:remaining * 4]
                    parts.append(f"## {layer.name}\n{truncated}\n...")
                    total_tokens += remaining
                break
            parts.append(f"## {layer.name}\n{layer.content}")
            total_tokens += tokens

        # Second pass: optional layers by priority
        for layer in layers:
            if layer.required:
                continue
            tokens = layer.estimate_tokens()
            if total_tokens + tokens > max_tokens:
                remaining = max_tokens - total_tokens
                if remaining > 200:
                    truncated = layer.content[:remaining * 4]
                    parts.append(f"## {layer.name}\n{truncated}\n...")
                    total_tokens += remaining
                break
            parts.append(f"## {layer.name}\n{layer.content}")
            total_tokens += tokens

        return "\n\n".join(parts)

    def get_token_usage(self) -> Dict[str, int]:
        """Get token usage per layer."""
        usage = {}
        for layer in self.get_active_layers():
            usage[layer.name] = layer.estimate_tokens()
        usage["total"] = sum(usage.values())
        usage["budget"] = self.max_total_tokens
        usage["remaining"] = max(0, self.max_total_tokens - usage["total"])
        return usage

    def is_within_budget(self) -> bool:
        return self.get_token_usage()["total"] <= self.max_total_tokens
