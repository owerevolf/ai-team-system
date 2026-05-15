"""
P18 — Governed Extensibility.

Controls how new subsystems are added to the platform.
Extension requirements:
- Lifecycle hooks (init, start, stop, health_check)
- Dependency validation (must declare dependencies)
- Policy registration (must register policies)
- Observability registration (must register metrics)
- Health integration (must report health)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum


class ExtensionState(Enum):
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ExtensionContract:
    """Contract that all extensions must fulfill."""
    name: str
    version: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)  # capabilities provided
    policies: List[Dict[str, Any]] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    health_checks: List[str] = field(default_factory=list)


class PlatformExtension(ABC):
    """
    Base class for all platform extensions.
    Every extension must implement this interface.
    """

    @abstractmethod
    def get_contract(self) -> ExtensionContract:
        """Return the extension contract."""
        ...

    @abstractmethod
    def initialize(self, registry: Any) -> bool:
        """Initialize the extension. Called once at startup."""
        ...

    @abstractmethod
    def start(self) -> bool:
        """Start the extension. Called after all extensions are initialized."""
        ...

    @abstractmethod
    def stop(self) -> bool:
        """Stop the extension. Called during shutdown."""
        ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return health status of this extension."""
        ...

    @abstractmethod
    def get_state(self) -> ExtensionState:
        """Return current state of this extension."""
        ...


class GovernedExtensibility:
    """
    Manages platform extensions.
    All extensions must fulfill the extension contract.
    """

    def __init__(self):
        self._extensions: Dict[str, PlatformExtension] = {}
        self._contracts: Dict[str, ExtensionContract] = {}
        self._states: Dict[str, ExtensionState] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

    def register_extension(self, extension: PlatformExtension) -> tuple:
        """
        Register a new extension.
        Returns: (success, error_message)
        """
        contract = extension.get_contract()
        name = contract.name

        # Validate contract
        if not name:
            return False, "Extension must have a name"
        if not contract.version:
            return False, "Extension must have a version"
        if name in self._extensions:
            return False, f"Extension '{name}' already registered"

        # Check dependencies exist
        for dep in contract.dependencies:
            if dep not in self._extensions:
                return False, f"Dependency '{dep}' not registered"

        self._extensions[name] = extension
        self._contracts[name] = contract
        self._states[name] = ExtensionState.REGISTERED
        self._dependency_graph[name] = set(contract.dependencies)

        return True, ""

    def initialize_extension(self, name: str, registry: Any = None) -> bool:
        """Initialize a registered extension."""
        ext = self._extensions.get(name)
        if not ext:
            return False

        self._states[name] = ExtensionState.INITIALIZING
        try:
            success = ext.initialize(registry)
            self._states[name] = ExtensionState.ACTIVE if success else ExtensionState.FAILED
            return success
        except Exception:
            self._states[name] = ExtensionState.FAILED
            return False

    def start_extension(self, name: str) -> bool:
        """Start an initialized extension."""
        ext = self._extensions.get(name)
        if not ext or self._states.get(name) != ExtensionState.ACTIVE:
            return False
        try:
            return ext.start()
        except Exception:
            self._states[name] = ExtensionState.FAILED
            return False

    def stop_extension(self, name: str) -> bool:
        """Stop an extension."""
        ext = self._extensions.get(name)
        if not ext:
            return False

        self._states[name] = ExtensionState.STOPPING
        try:
            success = ext.stop()
            self._states[name] = ExtensionState.STOPPED if success else ExtensionState.FAILED
            return success
        except Exception:
            self._states[name] = ExtensionState.FAILED
            return False

    def get_extension_health(self, name: str) -> Optional[Dict[str, Any]]:
        """Get health status of an extension."""
        ext = self._extensions.get(name)
        if not ext:
            return None
        try:
            return ext.health_check()
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all extensions."""
        result = {}
        for name in self._extensions:
            result[name] = self.get_extension_health(name)
        return result

    def get_extension_state(self, name: str) -> Optional[ExtensionState]:
        """Get state of an extension."""
        return self._states.get(name)

    def get_all_states(self) -> Dict[str, str]:
        """Get states of all extensions."""
        return {name: state.value for name, state in self._states.items()}

    def get_contract(self, name: str) -> Optional[ExtensionContract]:
        """Get contract of an extension."""
        return self._contracts.get(name)

    def get_all_contracts(self) -> Dict[str, ExtensionContract]:
        """Get all extension contracts."""
        return dict(self._contracts)

    def check_circular_dependencies(self) -> List[List[str]]:
        """Check for circular dependencies among extensions."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self._dependency_graph.get(node, set()):
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result
                elif dep in rec_stack:
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]

            path.pop()
            rec_stack.discard(node)
            return None

        for node in self._dependency_graph:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    cycles.append(cycle)

        return cycles
