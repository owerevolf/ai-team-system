"""
Phase 15, P1: Contributor Onboarding Compression

Progressive subsystem introduction for new contributors.
Goal: contributor understands the system without reading 500 pages of docs.

5 levels of onboarding:
  Level 1: Runtime overview — what is this system?
  Level 2: Core execution model — how does it run?
  Level 3: Governance + durability — how does it stay safe?
  Level 4: Trust + compression + coherence — how does it stay lean?
  Level 5: Evolution control + ecosystem — how does it grow?

Principle: Guided architectural onboarding > giant docs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OnboardingLevel(Enum):
    OVERVIEW = 1           # What is this system?
    EXECUTION = 2          # How does it run?
    GOVERNANCE = 3         # How does it stay safe?
    OPTIMIZATION = 4       # How does it stay lean?
    EVOLUTION = 5          # How does it grow?


@dataclass
class LearningModule:
    """A single onboarding learning module."""
    name: str
    level: OnboardingLevel
    description: str
    subsystems: list[str]         # Which runtime subpackages are covered
    key_concepts: list[str]       # Key concepts to understand
    estimated_minutes: int        # Estimated time to complete
    prerequisites: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


@dataclass
class ContributorPath:
    """Personalized onboarding path for a contributor."""
    name: str
    role: str                     # e.g. "plugin_developer", "core_maintainer", "ui_contributor"
    current_level: OnboardingLevel = OnboardingLevel.OVERVIEW
    completed_modules: list[str] = field(default_factory=list)
    remaining_modules: list[str] = field(default_factory=list)


class ContributorOnboardingCompressor:
    """
    Manages progressive onboarding for new contributors.
    Provides structured paths based on contributor role.
    """

    def __init__(self) -> None:
        self._modules: dict[str, LearningModule] = {}
        self._register_modules()

    def _register_modules(self) -> None:
        """Register all onboarding modules."""

        # Level 1: Overview
        self.register_module(LearningModule(
            name="runtime_overview",
            level=OnboardingLevel.OVERVIEW,
            description="What is AI Team System? High-level architecture, key principles.",
            subsystems=["runtime"],
            key_concepts=[
                "governed cognitive infrastructure",
                "deterministic > AI",
                "safety > autonomy",
                "coordination > complexity",
            ],
            estimated_minutes=15,
            next_steps=["execution_model"],
        ))

        self.register_module(LearningModule(
            name="subsystem_map",
            level=OnboardingLevel.OVERVIEW,
            description="6 runtime subpackages: durability, ergonomics, trust, optimization, compression, coherence",
            subsystems=["runtime"],
            key_concepts=[
                "durability = survivability",
                "ergonomics = human scaling",
                "trust = predictability",
                "optimization = performance",
                "compression = minimalism",
                "coherence = consistency",
            ],
            estimated_minutes=20,
            next_steps=["execution_model"],
        ))

        # Level 2: Execution
        self.register_module(LearningModule(
            name="execution_model",
            level=OnboardingLevel.EXECUTION,
            description="How runtime executes: workflows, approvals, state management",
            subsystems=["runtime", "durability"],
            key_concepts=[
                "workflow execution",
                "approval gates",
                "state lifecycle (EPHEMERAL → STRUCTURAL)",
                "recovery paths",
            ],
            estimated_minutes=30,
            prerequisites=["runtime_overview"],
            next_steps=["governance_model"],
        ))

        self.register_module(LearningModule(
            name="state_management",
            level=OnboardingLevel.EXECUTION,
            description="State tiers, context GC, checkpoints",
            subsystems=["durability"],
            key_concepts=[
                "StateTier: EPHEMERAL, SESSION, OPERATIONAL, STRUCTURAL",
                "Context GC: STALE → EXPIRED → collected",
                "Checkpoints for recovery",
            ],
            estimated_minutes=25,
            prerequisites=["execution_model"],
            next_steps=["governance_model"],
        ))

        # Level 3: Governance
        self.register_module(LearningModule(
            name="governance_model",
            level=OnboardingLevel.GOVERNANCE,
            description="How runtime stays safe: contracts, approvals, boundaries",
            subsystems=["trust", "ergonomics"],
            key_concepts=[
                "transparency contracts",
                "approval risk levels",
                "architectural boundaries",
                "do_less philosophy",
            ],
            estimated_minutes=35,
            prerequisites=["execution_model"],
            next_steps=["trust_model"],
        ))

        self.register_module(LearningModule(
            name="safety_invariants",
            level=OnboardingLevel.GOVERNANCE,
            description="Safety constraints that cannot be bypassed",
            subsystems=["trust", "durability"],
            key_concepts=[
                "safety > autonomy (hard constraint)",
                "mandatory approval for CRITICAL risk",
                "audit trail for all automation",
                "recovery must be deterministic",
            ],
            estimated_minutes=20,
            prerequisites=["governance_model"],
            next_steps=["trust_model"],
        ))

        # Level 4: Optimization
        self.register_module(LearningModule(
            name="trust_model",
            level=OnboardingLevel.OPTIMIZATION,
            description="How runtime stays predictable: visibility, personality, drift detection",
            subsystems=["trust"],
            key_concepts=[
                "visibility guarantees",
                "predictable personality",
                "trust drift detection",
                "user-controlled adaptivity",
            ],
            estimated_minutes=30,
            prerequisites=["governance_model"],
            next_steps=["compression_model"],
        ))

        self.register_module(LearningModule(
            name="compression_model",
            level=OnboardingLevel.OPTIMIZATION,
            description="How runtime stays lean: surface audit, dead system detection, do_less",
            subsystems=["compression"],
            key_concepts=[
                "surface area audit",
                "dead system detection",
                "interaction minimalism",
                "restraint as architecture",
            ],
            estimated_minutes=25,
            prerequisites=["trust_model"],
            next_steps=["coherence_model"],
        ))

        self.register_module(LearningModule(
            name="coherence_model",
            level=OnboardingLevel.OPTIMIZATION,
            description="How runtime stays consistent: canonical vocabulary, ontology drift",
            subsystems=["coherence"],
            key_concepts=[
                "canonical vocabulary",
                "ontology drift detection",
                "boundary enforcement",
                "semantic compression",
            ],
            estimated_minutes=30,
            prerequisites=["compression_model"],
            next_steps=["evolution_model"],
        ))

        # Level 5: Evolution
        self.register_module(LearningModule(
            name="evolution_model",
            level=OnboardingLevel.EVOLUTION,
            description="How runtime grows: evolution safety, decision traceability",
            subsystems=["coherence"],
            key_concepts=[
                "evolution safety rules (SAFE / REVIEW / HIGH_RISK)",
                "architectural decision traceability (ADR)",
                "controlled evolution framework",
                "core identity preservation",
            ],
            estimated_minutes=25,
            prerequisites=["coherence_model"],
            next_steps=["plugin_development", "core_contribution"],
        ))

    def register_module(self, module: LearningModule) -> None:
        """Register a learning module."""
        self._modules[module.name] = module

    def get_module(self, name: str) -> Optional[LearningModule]:
        """Get a learning module by name."""
        return self._modules.get(name)

    def get_modules_for_level(self, level: OnboardingLevel) -> list[LearningModule]:
        """Get all modules for a given onboarding level."""
        return [m for m in self._modules.values() if m.level == level]

    def create_path(self, role: str) -> list[LearningModule]:
        """Create a personalized onboarding path based on role."""
        role_paths: dict[str, list[str]] = {
            "core_maintainer": [
                "runtime_overview", "subsystem_map", "execution_model",
                "state_management", "governance_model", "safety_invariants",
                "trust_model", "compression_model", "coherence_model", "evolution_model",
            ],
            "plugin_developer": [
                "runtime_overview", "execution_model", "governance_model",
                "trust_model", "evolution_model",
            ],
            "ui_contributor": [
                "runtime_overview", "execution_model", "governance_model",
                "compression_model",
            ],
            "documentation": [
                "runtime_overview", "subsystem_map", "execution_model",
                "governance_model", "trust_model", "compression_model",
                "coherence_model", "evolution_model",
            ],
        }

        module_names = role_paths.get(role, role_paths["core_maintainer"])
        return [self._modules[name] for name in module_names if name in self._modules]

    def estimate_total_time(self, role: str) -> int:
        """Estimate total onboarding time in minutes for a role."""
        path = self.create_path(role)
        return sum(m.estimated_minutes for m in path)

    @property
    def total_modules(self) -> int:
        return len(self._modules)

    @property
    def levels(self) -> list[OnboardingLevel]:
        return list(OnboardingLevel)
