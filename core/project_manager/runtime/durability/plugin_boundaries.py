"""
P9 — Plugin & Extension Boundaries (Phase 9)

Hard boundaries for external extensions.
Plugins must NOT destroy determinism, security, or explainability.

Enforces:
  - Plugin sandboxing
  - Capability permissions
  - Resource isolation
  - Execution limits
  - Governance enforcement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class PluginCapability(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_COMMANDS = "execute_commands"
    MODIFY_GOVERNANCE = "modify_governance"
    ACCESS_NETWORK = "access_network"
    MODIFY_PM_CORE = "modify_pm_core"
    READ_CONTEXT = "read_context"
    WRITE_CONTEXT = "write_context"
    TRIGGER_WORKFLOWS = "trigger_workflows"
    BYPASS_APPROVALS = "bypass_approvals"


class PluginTrustLevel(Enum):
    UNTRUSTED = "untrusted"      # Sandboxed, no sensitive access
    BASIC = "basic"              # Read-only, limited write
    TRUSTED = "trusted"          # Full read/write, no governance
    SYSTEM = "system"            # Full access (core modules only)


# Capabilities allowed per trust level
TRUST_CAPABILITIES: dict[PluginTrustLevel, set[PluginCapability]] = {
    PluginTrustLevel.UNTRUSTED: {
        PluginCapability.READ_FILES, PluginCapability.READ_CONTEXT,
    },
    PluginTrustLevel.BASIC: {
        PluginCapability.READ_FILES, PluginCapability.READ_CONTEXT,
        PluginCapability.WRITE_FILES, PluginCapability.WRITE_CONTEXT,
    },
    PluginTrustLevel.TRUSTED: {
        PluginCapability.READ_FILES, PluginCapability.READ_CONTEXT,
        PluginCapability.WRITE_FILES, PluginCapability.WRITE_CONTEXT,
        PluginCapability.EXECUTE_COMMANDS, PluginCapability.ACCESS_NETWORK,
        PluginCapability.TRIGGER_WORKFLOWS,
    },
    PluginTrustLevel.SYSTEM: {
        PluginCapability.READ_FILES, PluginCapability.READ_CONTEXT,
        PluginCapability.WRITE_FILES, PluginCapability.WRITE_CONTEXT,
        PluginCapability.EXECUTE_COMMANDS, PluginCapability.ACCESS_NETWORK,
        PluginCapability.TRIGGER_WORKFLOWS, PluginCapability.MODIFY_GOVERNANCE,
        PluginCapability.MODIFY_PM_CORE, PluginCapability.BYPASS_APPROVALS,
    },
}


@dataclass
class PluginManifest:
    """Manifest for a plugin."""
    plugin_id: str
    name: str
    version: str
    trust_level: PluginTrustLevel = PluginTrustLevel.UNTRUSTED
    requested_capabilities: list[PluginCapability] = field(default_factory=list)
    description: str = ""
    author: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "trust_level": self.trust_level.value,
            "requested_capabilities": [c.value for c in self.requested_capabilities],
            "description": self.description,
            "author": self.author,
        }


@dataclass
class PluginSandbox:
    """Sandbox configuration for a plugin."""
    plugin_id: str
    allowed_paths: list[str] = field(default_factory=list)
    blocked_paths: list[str] = field(default_factory=lambda: [".git", ".env", "venv"])
    max_memory_mb: int = 128
    max_cpu_seconds: float = 30.0
    max_files_per_call: int = 100
    network_allowed: bool = False
    shell_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "allowed_paths": self.allowed_paths,
            "blocked_paths": self.blocked_paths,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_seconds": self.max_cpu_seconds,
            "max_files_per_call": self.max_files_per_call,
            "network_allowed": self.network_allowed,
            "shell_allowed": self.shell_allowed,
        }


class PluginBoundaryEnforcer:
    """
    Enforces boundaries for plugins and extensions.

    Usage:
        enforcer = PluginBoundaryEnforcer()

        # Register a plugin
        manifest = PluginManifest("my-plugin", "My Plugin", "1.0", trust_level=PluginTrustLevel.BASIC)
        sandbox = enforcer.register_plugin(manifest)

        # Check capabilities
        allowed = enforcer.check_capability("my-plugin", PluginCapability.WRITE_FILES)
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}
        self._sandboxes: dict[str, PluginSandbox] = {}

    def register_plugin(self, manifest: PluginManifest) -> PluginSandbox:
        """Register a plugin and create its sandbox."""
        # Validate requested capabilities against trust level
        allowed = TRUST_CAPABILITIES.get(manifest.trust_level, set())
        for cap in manifest.requested_capabilities:
            if cap not in allowed:
                raise ValueError(
                    f"Plugin '{manifest.plugin_id}' requested '{cap.value}' "
                    f"but trust level '{manifest.trust_level.value}' doesn't allow it. "
                    f"Allowed: {[c.value for c in allowed]}"
                )

        self._plugins[manifest.plugin_id] = manifest

        # Create sandbox based on trust level
        sandbox = PluginSandbox(
            plugin_id=manifest.plugin_id,
            network_allowed=PluginCapability.ACCESS_NETWORK in allowed,
            shell_allowed=PluginCapability.EXECUTE_COMMANDS in allowed,
            max_memory_mb=256 if manifest.trust_level in (PluginTrustLevel.TRUSTED, PluginTrustLevel.SYSTEM) else 64,
            max_cpu_seconds=60.0 if manifest.trust_level == PluginTrustLevel.TRUSTED else 10.0,
        )
        self._sandboxes[manifest.plugin_id] = sandbox
        return sandbox

    def check_capability(self, plugin_id: str, capability: PluginCapability) -> bool:
        """Check if a plugin has a specific capability."""
        manifest = self._plugins.get(plugin_id)
        if not manifest:
            return False
        allowed = TRUST_CAPABILITIES.get(manifest.trust_level, set())
        return capability in allowed

    def get_allowed_capabilities(self, plugin_id: str) -> list[str]:
        """Get all capabilities allowed for a plugin."""
        manifest = self._plugins.get(plugin_id)
        if not manifest:
            return []
        allowed = TRUST_CAPABILITIES.get(manifest.trust_level, set())
        return [c.value for c in allowed]

    def get_sandbox(self, plugin_id: str) -> Optional[PluginSandbox]:
        """Get a plugin's sandbox configuration."""
        return self._sandboxes.get(plugin_id)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins."""
        return [m.to_dict() for m in self._plugins.values()]

    def unregister_plugin(self, plugin_id: str) -> bool:
        """Unregister a plugin."""
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            self._sandboxes.pop(plugin_id, None)
            return True
        return False
