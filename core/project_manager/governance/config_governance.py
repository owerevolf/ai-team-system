"""
P13 — Configuration Governance.

Manages platform configuration with:
- Centralized config registry
- Config validation
- Schema enforcement
- Environment isolation
- Config versioning
"""

import time
import threading
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ConfigEnvironment(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ConfigEntry:
    """A single configuration entry."""
    key: str
    value: Any
    env: ConfigEnvironment
    version: int = 1
    created_at: float = 0.0
    updated_at: float = 0.0
    description: str = ""
    is_sensitive: bool = False  # if True, value is masked in logs
    schema_type: str = "str"  # str, int, float, bool, list, dict


@dataclass
class ConfigChange:
    """A configuration change record."""
    key: str
    old_value: Any
    new_value: Any
    env: ConfigEnvironment
    version: int
    timestamp: float
    changed_by: str = ""


class ConfigurationGovernance:
    """
    Centralized configuration registry with validation and versioning.
    """

    # Schema: key -> expected type
    SCHEMA: Dict[str, str] = {
        'max_concurrent_tasks': 'int',
        'max_task_duration_seconds': 'int',
        'max_retries': 'int',
        'lock_timeout_seconds': 'float',
        'cache_ttl_seconds': 'int',
        'cache_max_size': 'int',
        'enable_watch': 'bool',
        'storage_backend': 'str',
        'max_context_chars': 'int',
        'log_level': 'str',
        'operational_mode': 'str',
        'enable_tracing': 'bool',
        'enable_telemetry': 'bool',
    }

    # Valid values for enum-like configs
    VALID_VALUES: Dict[str, Set[str]] = {
        'storage_backend': {'json', 'sqlite'},
        'log_level': {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'},
        'operational_mode': {'safe', 'normal', 'performance', 'diagnostic'},
    }

    def __init__(self, env: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT):
        self._configs: Dict[str, ConfigEntry] = {}
        self._history: List[ConfigChange] = []
        self._env = env
        self._lock = threading.Lock()
        self._max_history = 1000

    def set(self, key: str, value: Any, description: str = "",
            is_sensitive: bool = False, changed_by: str = "") -> tuple:
        """
        Set a configuration value.
        Returns: (success, error_message)
        """
        # Validate against schema
        error = self._validate(key, value)
        if error:
            return False, error

        with self._lock:
            old_entry = self._configs.get(key)
            old_value = old_entry.value if old_entry else None
            version = (old_entry.version + 1) if old_entry else 1

            entry = ConfigEntry(
                key=key,
                value=value,
                env=self._env,
                version=version,
                created_at=old_entry.created_at if old_entry else time.time(),
                updated_at=time.time(),
                description=description,
                is_sensitive=is_sensitive,
                schema_type=self.SCHEMA.get(key, 'str'),
            )
            self._configs[key] = entry

            # Record change
            change = ConfigChange(
                key=key,
                old_value=old_value,
                new_value=value,
                env=self._env,
                version=version,
                timestamp=time.time(),
                changed_by=changed_by,
            )
            self._history.append(change)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        return True, ""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        entry = self._configs.get(key)
        return entry.value if entry else default

    def get_entry(self, key: str) -> Optional[ConfigEntry]:
        """Get full config entry."""
        return self._configs.get(key)

    def get_all(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Get all configuration values."""
        result = {}
        for key, entry in self._configs.items():
            if mask_sensitive and entry.is_sensitive:
                result[key] = "***"
            else:
                result[key] = entry.value
        return result

    def get_history(self, key: Optional[str] = None, limit: int = 50) -> List[ConfigChange]:
        """Get configuration change history."""
        history = self._history
        if key:
            history = [c for c in history if c.key == key]
        return history[-limit:]

    def _validate(self, key: str, value: Any) -> Optional[str]:
        """Validate a config value. Returns error message or None."""
        expected_type = self.SCHEMA.get(key)
        if expected_type:
            type_map = {
                'str': str, 'int': int, 'float': (int, float),
                'bool': bool, 'list': list, 'dict': dict,
            }
            expected = type_map.get(expected_type)
            if expected and not isinstance(value, expected):
                return f"Config '{key}' expects {expected_type}, got {type(value).__name__}"

        valid_values = self.VALID_VALUES.get(key)
        if valid_values and value not in valid_values:
            return f"Config '{key}' must be one of {valid_values}, got '{value}'"

        return None

    def validate_all(self) -> List[str]:
        """Validate all current config values."""
        errors = []
        for key, entry in self._configs.items():
            error = self._validate(key, entry.value)
            if error:
                errors.append(error)
        return errors

    def get_stats(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        return {
            'total_configs': len(self._configs),
            'environment': self._env.value,
            'total_changes': len(self._history),
            'schema_defined': len(self.SCHEMA),
            'sensitive_keys': sum(1 for e in self._configs.values() if e.is_sensitive),
        }
