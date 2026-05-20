"""
Phase 19F — Long-Context Knowledge Compression & Engineering Memory.

Persistent engineering memory runtime:
- semantic_memory.py: 5-layer project memory
- context_compressor.py: repo knowledge compression
- memory_index.py: engineering knowledge index
- drift_detection.py: memory drift detection
- token_budget.py: token governance runtime
- intent_preservation.py: identity anchor runtime
- architectural_memory.py: persistent architecture understanding
- failure_memory.py: error memory
- memory_governor.py: memory growth control
- knowledge_runtime.py: main coordinator (knowledge operating system)

Principle: RAW CONTEXT DIES. COMPRESSED ENGINEERING MEMORY SURVIVES.
"""

from .semantic_memory import (
    SemanticMemory, ActiveTask, ProjectIdentity,
    SubsystemSummary, ArchitectureMap, FailureRecord, FragileArea,
    FrozenZone, GovernancePolicy,
)
from .context_compressor import (
    ContextCompressor, CompressedModule, CompressedSubsystem, CompressedContext,
)
from .memory_index import MemoryIndex, MemoryEntry
from .drift_detection import DriftDetector, DriftReport
from .token_budget import TokenBudget, ContextItem, BudgetReport
from .intent_preservation import IntentPreservation, IntentStatement
from .architectural_memory import (
    ArchitecturalMemory, ArchitecturalDecision,
    IntegrationContract, DangerousCoupling,
)
from .failure_memory import (
    FailureMemory, FailurePattern, FragileTest, RegressionHotspot,
)
from .memory_governor import MemoryGovernor, GovernorAction
from .knowledge_runtime import KnowledgeRuntime

__all__ = [
    "SemanticMemory", "ActiveTask", "ProjectIdentity",
    "SubsystemSummary", "ArchitectureMap", "FailureRecord", "FragileArea",
    "FrozenZone", "GovernancePolicy",
    "ContextCompressor", "CompressedModule", "CompressedSubsystem", "CompressedContext",
    "MemoryIndex", "MemoryEntry",
    "DriftDetector", "DriftReport",
    "TokenBudget", "ContextItem", "BudgetReport",
    "IntentPreservation", "IntentStatement",
    "ArchitecturalMemory", "ArchitecturalDecision",
    "IntegrationContract", "DangerousCoupling",
    "FailureMemory", "FailurePattern", "FragileTest", "RegressionHotspot",
    "MemoryGovernor", "GovernorAction",
    "KnowledgeRuntime",
]
