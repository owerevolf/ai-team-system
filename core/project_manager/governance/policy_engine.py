"""
P8 — Governance Policy Engine.

Manages platform-wide policies.
All policies are EXPLICIT — never AI-generated.

Policy types:
- Execution policies (how tasks execute)
- Modification policies (what can be modified)
- Protected area policies (read-only zones)
- Workflow permissions (who can run what)
- Concurrency limits (max parallel operations)
- Runtime safety rules (hard limits)
"""

import time
import threading
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class PolicyType(Enum):
    EXECUTION = "execution"
    MODIFICATION = "modification"
    PROTECTED_AREA = "protected_area"
    WORKFLOW_PERMISSION = "workflow_permission"
    CONCURRENCY = "concurrency"
    SAFETY = "safety"


class PolicyAction(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    LOG = "log"  # allow but log


@dataclass
class PolicyRule:
    """A single policy rule."""
    id: str
    name: str
    policy_type: PolicyType
    action: PolicyAction
    condition: str  # human-readable condition description
    enabled: bool = True
    priority: int = 0  # higher = evaluated first
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    """Result of a policy check."""
    allowed: bool
    rule_id: str
    rule_name: str
    action: PolicyAction
    reason: str
    requires_approval: bool = False


@dataclass
class PolicyViolation:
    """A recorded policy violation."""
    timestamp: float
    rule_id: str
    rule_name: str
    context: Dict[str, Any]
    action_taken: str


class GovernancePolicyEngine:
    """
    Platform policy engine.
    All rules are explicit, deterministic, and auditable.
    """

    def __init__(self):
        self._rules: Dict[str, PolicyRule] = {}
        self._violations: List[PolicyViolation] = []
        self._lock = threading.Lock()
        self._max_violations = 10000
        self._build_default_policies()

    def _build_default_policies(self) -> None:
        """Build default platform policies."""
        defaults = [
            # Execution policies
            PolicyRule(
                id="exec-001", name="max_concurrent_tasks",
                policy_type=PolicyType.CONCURRENCY,
                action=PolicyAction.DENY,
                condition="max 10 concurrent tasks per agent",
                priority=100,
                metadata={'max_concurrent': 10}
            ),
            PolicyRule(
                id="exec-002", name="max_task_duration",
                policy_type=PolicyType.EXECUTION,
                action=PolicyAction.REQUIRE_APPROVAL,
                condition="tasks running >5 minutes require approval to continue",
                priority=90,
                metadata={'max_duration_seconds': 300}
            ),
            PolicyRule(
                id="exec-003", name="max_retries",
                policy_type=PolicyType.EXECUTION,
                action=PolicyAction.DENY,
                condition="max 3 retries per task",
                priority=95,
                metadata={'max_retries': 3}
            ),
            # Modification policies
            PolicyRule(
                id="mod-001", name="protected_config_files",
                policy_type=PolicyType.PROTECTED_AREA,
                action=PolicyAction.REQUIRE_APPROVAL,
                condition="config files require approval to modify",
                priority=100,
                metadata={'patterns': ['*.yaml', '*.yml', '*.toml', '*.ini', '*.cfg', '.env']}
            ),
            PolicyRule(
                id="mod-002", name="protected_core_modules",
                policy_type=PolicyType.PROTECTED_AREA,
                action=PolicyAction.REQUIRE_APPROVAL,
                condition="core/ directory requires approval to modify",
                priority=100,
                metadata={'patterns': ['core/main.py', 'core/project_manager/__init__.py']}
            ),
            PolicyRule(
                id="mod-003", name="no_direct_db_modification",
                policy_type=PolicyType.MODIFICATION,
                action=PolicyAction.DENY,
                condition="direct database modification is forbidden — use storage layer",
                priority=100,
            ),
            # Workflow permissions
            PolicyRule(
                id="wf-001", name="destructive_workflow_approval",
                policy_type=PolicyType.WORKFLOW_PERMISSION,
                action=PolicyAction.REQUIRE_APPROVAL,
                condition="destructive workflows (delete, reset) require approval",
                priority=100,
                metadata={'workflows': ['delete', 'reset', 'rollback_all']}
            ),
            # Safety rules
            PolicyRule(
                id="safe-001", name="no_recursive_file_operations",
                policy_type=PolicyType.SAFETY,
                action=PolicyAction.DENY,
                condition="recursive file operations on project root are forbidden",
                priority=200,
            ),
            PolicyRule(
                id="safe-002", name="max_file_size_modification",
                policy_type=PolicyType.SAFETY,
                action=PolicyAction.DENY,
                condition="cannot modify files >10MB",
                priority=100,
                metadata={'max_file_bytes': 10 * 1024 * 1024}
            ),
            PolicyRule(
                id="safe-003", name="no_network_in_validation",
                policy_type=PolicyType.SAFETY,
                action=PolicyAction.DENY,
                condition="validation must not make network requests",
                priority=100,
            ),
        ]
        for rule in defaults:
            self._rules[rule.id] = rule

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a policy rule."""
        with self._lock:
            self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a policy rule."""
        with self._lock:
            return self._rules.pop(rule_id, None) is not None

    def enable_rule(self, rule_id: str, enabled: bool = True) -> bool:
        """Enable or disable a rule."""
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule:
                rule.enabled = enabled
                return True
            return False

    def check_policy(self, policy_type: PolicyType, context: Dict[str, Any]) -> PolicyDecision:
        """
        Check all policies of a given type against a context.
        Returns the highest-priority matching decision.
        """
        matching_rules = []
        with self._lock:
            for rule in self._rules.values():
                if rule.policy_type == policy_type and rule.enabled:
                    if self._evaluate_condition(rule, context):
                        matching_rules.append(rule)

        if not matching_rules:
            return PolicyDecision(
                allowed=True,
                rule_id="",
                rule_name="default",
                action=PolicyAction.ALLOW,
                reason="No matching policy — allowed by default"
            )

        # Sort by priority (highest first)
        matching_rules.sort(key=lambda r: r.priority, reverse=True)
        top_rule = matching_rules[0]

        # Record violation if denied or requires approval
        if top_rule.action in (PolicyAction.DENY, PolicyAction.REQUIRE_APPROVAL):
            self._record_violation(top_rule, context)

        return PolicyDecision(
            allowed=top_rule.action != PolicyAction.DENY,
            rule_id=top_rule.id,
            rule_name=top_rule.name,
            action=top_rule.action,
            reason=top_rule.condition,
            requires_approval=top_rule.action == PolicyAction.REQUIRE_APPROVAL,
        )

    def _evaluate_condition(self, rule: PolicyRule, context: Dict[str, Any]) -> bool:
        """Evaluate if a rule's condition matches the context."""
        # Simple pattern matching based on rule type and metadata
        if rule.id == "exec-001":
            context.get('agent', '')
            current = context.get('current_concurrent', 0)
            return current >= rule.metadata.get('max_concurrent', 10)

        elif rule.id == "exec-002":
            duration = context.get('duration_seconds', 0)
            return duration > rule.metadata.get('max_duration_seconds', 300)

        elif rule.id == "exec-003":
            retries = context.get('retry_count', 0)
            return retries >= rule.metadata.get('max_retries', 3)

        elif rule.id == "mod-001":
            file_path = context.get('file_path', '')
            patterns = rule.metadata.get('patterns', [])
            return any(file_path.endswith(p.lstrip('*')) for p in patterns)

        elif rule.id == "mod-002":
            file_path = context.get('file_path', '')
            patterns = rule.metadata.get('patterns', [])
            return any(file_path.endswith(p.split('/')[-1]) for p in patterns)

        elif rule.id == "mod-003":
            return context.get('operation') == 'direct_db_write'

        elif rule.id == "wf-001":
            workflow = context.get('workflow', '')
            return workflow in rule.metadata.get('workflows', [])

        elif rule.id == "safe-001":
            return context.get('operation') == 'recursive_file_op' and context.get('target') == 'project_root'

        elif rule.id == "safe-002":
            file_size = context.get('file_size_bytes', 0)
            return file_size > rule.metadata.get('max_file_bytes', 10 * 1024 * 1024)

        elif rule.id == "safe-003":
            return context.get('operation') == 'network_request' and context.get('phase') == 'validation'

        # Default: no match
        return False

    def _record_violation(self, rule: PolicyRule, context: Dict[str, Any]) -> None:
        """Record a policy violation."""
        violation = PolicyViolation(
            timestamp=time.time(),
            rule_id=rule.id,
            rule_name=rule.name,
            context=context.copy(),
            action_taken=rule.action.value,
        )
        self._violations.append(violation)
        if len(self._violations) > self._max_violations:
            self._violations = self._violations[-self._max_violations:]

    def get_violations(self, limit: int = 100,
                       rule_id: Optional[str] = None) -> List[PolicyViolation]:
        """Get recorded policy violations."""
        violations = self._violations
        if rule_id:
            violations = [v for v in violations if v.rule_id == rule_id]
        return violations[-limit:]

    def get_all_rules(self) -> List[PolicyRule]:
        """Get all policy rules."""
        return sorted(self._rules.values(), key=lambda r: r.priority, reverse=True)

    def get_rules_by_type(self, policy_type: PolicyType) -> List[PolicyRule]:
        """Get rules by type."""
        return [r for r in self._rules.values() if r.policy_type == policy_type]

    def get_stats(self) -> Dict[str, Any]:
        """Get policy engine statistics."""
        by_type = defaultdict(int)
        for rule in self._rules.values():
            by_type[rule.policy_type.value] += 1

        return {
            'total_rules': len(self._rules),
            'enabled_rules': sum(1 for r in self._rules.values() if r.enabled),
            'total_violations': len(self._violations),
            'by_type': dict(by_type),
        }
