"""
P9 — Operational Modes.

Defines runtime execution modes:
- SAFE MODE: minimal concurrency, strict approvals, limited execution
- NORMAL MODE: balanced execution
- PERFORMANCE MODE: aggressive caching, parallel validation, relaxed low-risk
- DIAGNOSTIC MODE: maximum tracing, verbose telemetry
"""

import threading
from typing import Dict, Any, Optional
from enum import Enum


class OperationalMode(Enum):
    SAFE = "safe"
    NORMAL = "normal"
    PERFORMANCE = "performance"
    DIAGNOSTIC = "diagnostic"


class ModeConfig:
    """Configuration for a single operational mode."""

    def __init__(
        self,
        max_concurrent_tasks: int,
        require_approval_for_all: bool,
        enable_aggressive_caching: bool,
        enable_parallel_validation: bool,
        enable_maximum_tracing: bool,
        enable_verbose_telemetry: bool,
        relaxed_low_risk_workflows: bool,
        max_retries: int,
        lock_timeout_seconds: float,
        description: str,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.require_approval_for_all = require_approval_for_all
        self.enable_aggressive_caching = enable_aggressive_caching
        self.enable_parallel_validation = enable_parallel_validation
        self.enable_maximum_tracing = enable_maximum_tracing
        self.enable_verbose_telemetry = enable_verbose_telemetry
        self.relaxed_low_risk_workflows = relaxed_low_risk_workflows
        self.max_retries = max_retries
        self.lock_timeout_seconds = lock_timeout_seconds
        self.description = description


class OperationalModes:
    """
    Manages platform operational modes.
    Mode changes affect all subsystems.
    """

    CONFIGS = {
        OperationalMode.SAFE: ModeConfig(
            max_concurrent_tasks=1,
            require_approval_for_all=True,
            enable_aggressive_caching=False,
            enable_parallel_validation=False,
            enable_maximum_tracing=True,
            enable_verbose_telemetry=True,
            relaxed_low_risk_workflows=False,
            max_retries=1,
            lock_timeout_seconds=60.0,
            description="Minimal concurrency, strict approvals, limited execution"
        ),
        OperationalMode.NORMAL: ModeConfig(
            max_concurrent_tasks=5,
            require_approval_for_all=False,
            enable_aggressive_caching=True,
            enable_parallel_validation=True,
            enable_maximum_tracing=False,
            enable_verbose_telemetry=False,
            relaxed_low_risk_workflows=False,
            max_retries=3,
            lock_timeout_seconds=30.0,
            description="Balanced execution"
        ),
        OperationalMode.PERFORMANCE: ModeConfig(
            max_concurrent_tasks=10,
            require_approval_for_all=False,
            enable_aggressive_caching=True,
            enable_parallel_validation=True,
            enable_maximum_tracing=False,
            enable_verbose_telemetry=False,
            relaxed_low_risk_workflows=True,
            max_retries=2,
            lock_timeout_seconds=15.0,
            description="Aggressive caching, parallel validation, relaxed low-risk"
        ),
        OperationalMode.DIAGNOSTIC: ModeConfig(
            max_concurrent_tasks=3,
            require_approval_for_all=False,
            enable_aggressive_caching=False,
            enable_parallel_validation=False,
            enable_maximum_tracing=True,
            enable_verbose_telemetry=True,
            relaxed_low_risk_workflows=False,
            max_retries=3,
            lock_timeout_seconds=30.0,
            description="Maximum tracing, verbose telemetry"
        ),
    }

    def __init__(self, default_mode: OperationalMode = OperationalMode.NORMAL):
        self._current_mode = default_mode
        self._config = self.CONFIGS[default_mode]
        self._lock = threading.Lock()
        self._mode_history: list = []

    @property
    def current_mode(self) -> OperationalMode:
        return self._current_mode

    @property
    def config(self) -> ModeConfig:
        return self._config

    def set_mode(self, mode: OperationalMode) -> Dict[str, Any]:
        """
        Switch to a new operational mode.
        Returns a summary of the change.
        """
        with self._lock:
            old_mode = self._current_mode
            self._current_mode = mode
            self._config = self.CONFIGS[mode]
            change = {
                'from': old_mode.value,
                'to': mode.value,
                'config': self.get_config_summary(),
            }
            self._mode_history.append(change)
            return change

    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current mode configuration."""
        return {
            'mode': self._current_mode.value,
            'max_concurrent_tasks': self._config.max_concurrent_tasks,
            'require_approval_for_all': self._config.require_approval_for_all,
            'enable_aggressive_caching': self._config.enable_aggressive_caching,
            'enable_parallel_validation': self._config.enable_parallel_validation,
            'enable_maximum_tracing': self._config.enable_maximum_tracing,
            'enable_verbose_telemetry': self._config.enable_verbose_telemetry,
            'relaxed_low_risk_workflows': self._config.relaxed_low_risk_workflows,
            'max_retries': self._config.max_retries,
            'lock_timeout_seconds': self._config.lock_timeout_seconds,
            'description': self._config.description,
        }

    def is_safe_mode(self) -> bool:
        return self._current_mode == OperationalMode.SAFE

    def is_diagnostic_mode(self) -> bool:
        return self._current_mode == OperationalMode.DIAGNOSTIC

    def get_mode_history(self) -> list:
        """Get mode change history."""
        return list(self._mode_history)
