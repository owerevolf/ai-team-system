"""
Phase 15, P5: Plugin Ecosystem Governance

Extension capability contracts for plugins.
Plugins must not become shadow runtime.

Principle: Extensions enhance, they don't replace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CapabilityType(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_COMMANDS = "execute_commands"
    MODIFY_CONTEXT = "modify_context"
    TRIGGER_WORKFLOWS = "trigger_workflows"
    READ_GOVERNANCE = "read_governance"
    WRITE_GOVERNANCE = "write_governance"           # Restricted
    BYPASS_APPROVALS = "bypass_approvals"           # Forbidden
    ACCESS_NETWORK = "access_network"              # Restricted
    MODIFY_PM_CORE = "modify_pm_core"              # Forbidden
    READ_TRUST = "read_trust"
    WRITE_TRUST = "write_trust"                    # Restricted
    READ_COMPRESSION = "read_compression"
    WRITE_COMPRESSION = "write_compression"        # Restricted


class CapabilityRisk(Enum):
    LOW = "low"            # Read-only, no side effects
    MEDIUM = "medium"      # Write within bounds
    HIGH = "high"          # Can modify governance/trust
    FORBIDDEN = "forbidden"  # Never allowed for plugins


# Map capabilities to risk levels
CAPABILITY_RISK: dict[CapabilityType, CapabilityRisk] = {
    CapabilityType.READ_FILES: CapabilityRisk.LOW,
    CapabilityType.WRITE_FILES: CapabilityRisk.MEDIUM,
    CapabilityType.EXECUTE_COMMANDS: CapabilityRisk.MEDIUM,
    CapabilityType.MODIFY_CONTEXT: CapabilityRisk.MEDIUM,
    CapabilityType.TRIGGER_WORKFLOWS: CapabilityRisk.MEDIUM,
    CapabilityType.READ_GOVERNANCE: CapabilityRisk.LOW,
    CapabilityType.WRITE_GOVERNANCE: CapabilityRisk.HIGH,
    CapabilityType.BYPASS_APPROVALS: CapabilityRisk.FORBIDDEN,
    CapabilityType.ACCESS_NETWORK: CapabilityRisk.HIGH,
    CapabilityType.MODIFY_PM_CORE: CapabilityRisk.FORBIDDEN,
    CapabilityType.READ_TRUST: CapabilityRisk.LOW,
    CapabilityType.WRITE_TRUST: CapabilityRisk.HIGH,
    CapabilityType.READ_COMPRESSION: CapabilityRisk.LOW,
    CapabilityType.WRITE_COMPRESSION: CapabilityRisk.HIGH,
}


@dataclass
class ExtensionContract:
    """Capability contract for a plugin."""
    plugin_name: str
    allowed_capabilities: list[CapabilityType]
    forbidden_capabilities: list[CapabilityType] = field(default_factory=list)
    max_workflow_depth: int = 5
    max_approval_bypass: int = 0  # Plugins cannot bypass approvals
    audit_all_actions: bool = True
    sandbox_enabled: bool = True

    def is_capability_allowed(self, capability: CapabilityType) -> bool:
        """Check if a capability is allowed for this plugin."""
        if capability in self.forbidden_capabilities:
            return False
        if capability in self.allowed_capabilities:
            return True
        # Default: check risk level
        risk = CAPABILITY_RISK.get(capability, CapabilityRisk.HIGH)
        return risk != CapabilityRisk.FORBIDDEN


@dataclass
class PluginGovernanceReport:
    """Report of plugin governance status."""
    total_plugins: int = 0
    compliant_plugins: int = 0
    non_compliant_plugins: list[str] = field(default_factory=list)
    forbidden_capability_violations: list[tuple[str, CapabilityType]] = field(default_factory=list)


class PluginEcosystemGovernance:
    """
    Manages plugin ecosystem governance.
    Ensures plugins respect runtime boundaries and don't become shadow runtime.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, ExtensionContract] = {}

    def register_plugin(self, contract: ExtensionContract) -> None:
        """Register a plugin with its capability contract."""
        self._contracts[contract.plugin_name] = contract

    def get_contract(self, plugin_name: str) -> Optional[ExtensionContract]:
        """Get a plugin's capability contract."""
        return self._contracts.get(plugin_name)

    def validate_plugin(self, plugin_name: str) -> tuple[bool, list[str]]:
        """Validate that a plugin respects its contract."""
        contract = self._contracts.get(plugin_name)
        if not contract:
            return False, [f"Plugin '{plugin_name}' is not registered"]

        issues: list[str] = []

        # Check for forbidden capabilities
        for cap in contract.allowed_capabilities:
            risk = CAPABILITY_RISK.get(cap, CapabilityRisk.HIGH)
            if risk == CapabilityRisk.FORBIDDEN:
                issues.append(f"Plugin requests forbidden capability: {cap.value}")

        # Check approval bypass
        if contract.max_approval_bypass > 0:
            issues.append("Plugins cannot bypass approvals")

        # Check audit requirement
        if not contract.audit_all_actions:
            issues.append("Plugins must audit all actions")

        return len(issues) == 0, issues

    def check_capability(self, plugin_name: str, capability: CapabilityType) -> bool:
        """Check if a plugin is allowed to use a capability."""
        contract = self._contracts.get(plugin_name)
        if not contract:
            return False
        return contract.is_capability_allowed(capability)

    def get_governance_report(self) -> PluginGovernanceReport:
        """Generate governance report for all plugins."""
        report = PluginGovernanceReport()
        report.total_plugins = len(self._contracts)

        for name, contract in self._contracts.items():
            valid, issues = self.validate_plugin(name)
            if valid:
                report.compliant_plugins += 1
            else:
                report.non_compliant_plugins.append(name)
                for issue in issues:
                    if "forbidden capability" in issue:
                        # Extract capability name
                        for cap in CapabilityType:
                            if cap.value in issue:
                                report.forbidden_capability_violations.append((name, cap))
                                break

        return report

    def create_safe_contract(self, plugin_name: str, requested_capabilities: list[CapabilityType]) -> ExtensionContract:
        """Create a safe contract, filtering out forbidden capabilities."""
        allowed = []
        forbidden = []

        for cap in requested_capabilities:
            risk = CAPABILITY_RISK.get(cap, CapabilityRisk.HIGH)
            if risk == CapabilityRisk.FORBIDDEN:
                forbidden.append(cap)
            else:
                allowed.append(cap)

        return ExtensionContract(
            plugin_name=plugin_name,
            allowed_capabilities=allowed,
            forbidden_capabilities=forbidden,
        )

    @property
    def total_plugins(self) -> int:
        return len(self._contracts)
