"""
Phase 15, P10: Core Identity Preservation

The most important subsystem of Phase 15.

As the project grows, it will receive pressure:
- enterprise requests
- cloud demands
- autonomous-agent hype
- SaaS expectations
- "AI employee" positioning
- monetization gravity

This module explicitly preserves the project's core identity.

Principle: Know what you are, and what you are not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IdentityAspect(Enum):
    PURPOSE = "purpose"                # What the system is for
    ARCHITECTURE = "architecture"      # How it's built
    GOVERNANCE = "governance"          # How decisions are made
    VALUES = "values"                  # What principles guide it
    BOUNDARIES = "boundaries"          # What it explicitly does NOT do


class PressureType(Enum):
    ENTERPRISE = "enterprise"          # Enterprise feature requests
    CLOUD = "cloud"                    # Cloud/SaaS pressure
    AI_HYPE = "ai_hype"               # Autonomous agent hype
    MONETIZATION = "monetization"      # Revenue pressure
    SCALE = "scale"                    # Scale-at-all-costs pressure
    FEATURE_CREEP = "feature_creep"    # Endless feature requests


@dataclass
class IdentityStatement:
    """A core identity statement."""
    aspect: IdentityAspect
    statement: str
    what_it_is: list[str] = field(default_factory=list)
    what_it_is_not: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)


@dataclass
class PressureAssessment:
    """Assessment of external pressure on project identity."""
    pressure_type: PressureType
    description: str
    risk_level: str  # low, medium, high
    mitigation: str


class CoreIdentityPreservation:
    """
    Preserves the project's core identity under growth pressure.
    Provides explicit statements of what the system is and is not.
    """

    def __init__(self) -> None:
        self._identity: dict[IdentityAspect, IdentityStatement] = {}
        self._register_identity()

    def _register_identity(self) -> None:
        """Register core identity statements."""

        self._identity[IdentityAspect.PURPOSE] = IdentityStatement(
            aspect=IdentityAspect.PURPOSE,
            statement="Human-controlled, local-first, browser-first governed engineering runtime",
            what_it_is=[
                "A runtime that manages execution, visibility, trust, adaptation, cognitive pressure, operational predictability",
                "A tool for human engineers, not a replacement for them",
                "A local-first system that runs on your machine",
                "A browser-first UI for runtime control",
            ],
            what_it_is_not=[
                "An AGI platform",
                "An autonomous company",
                "An enterprise governance monster",
                "An AI replacement system",
                "A SaaS platform",
                "A cloud service",
            ],
            invariants=[
                "User always has final authority over runtime behavior",
                "Runtime never acts without explicit user consent for non-trivial actions",
                "All automation is auditable and reversible",
            ],
        )

        self._identity[IdentityAspect.ARCHITECTURE] = IdentityStatement(
            aspect=IdentityAspect.ARCHITECTURE,
            statement="66 runtime modules across 6 subpackages, ~14,000 lines, deterministic core",
            what_it_is=[
                "durability/ — survivability, recovery, state lifecycle",
                "ergonomics/ — human scaling, attention, calm mode",
                "trust/ — predictability, visibility, drift detection",
                "optimization/ — performance, caching, profiling",
                "compression/ — minimalism, surface audit, do_less",
                "coherence/ — consistency, vocabulary, boundaries",
                "ecosystem/ — contributor scaling, plugin governance",
            ],
            what_it_is_not=[
                "A microservices architecture",
                "A distributed system",
                "A serverless platform",
                "A monolithic application",
            ],
            invariants=[
                "Deterministic core — AI only for augmentation",
                "Safety > autonomy — hard constraint",
                "Coordination > complexity — explicit protocols",
            ],
        )

        self._identity[IdentityAspect.GOVERNANCE] = IdentityStatement(
            aspect=IdentityAspect.GOVERNANCE,
            statement="Risk-based approval with evolution safety rules",
            what_it_is=[
                "SAFE changes auto-approved (dead code removal, tests)",
                "REVIEW changes need 1 approver",
                "HIGH_RISK changes need architect + safety reviewer",
                "All changes traceable via ADR",
            ],
            what_it_is_not=[
                "Centralized contributor authority",
                "Enterprise contribution workflows",
                "AI-driven maintainer automation",
                "Contributor scoring systems",
            ],
            invariants=[
                "No hidden automation — all actions auditable",
                "No shadow runtime — plugins cannot bypass core",
                "No governance bureaucracy — compress ceremony",
            ],
        )

        self._identity[IdentityAspect.VALUES] = IdentityStatement(
            aspect=IdentityAspect.VALUES,
            statement="Sustainable coherent evolution > feature velocity",
            what_it_is=[
                "Deterministic > AI",
                "Safety > autonomy",
                "Coordination > complexity",
                "Signal > noise",
                "User time is expensive",
                "Calm by default, verbose on demand",
                "Restraint as architecture",
                "Deletion is a first-class operation",
            ],
            what_it_is_not=[
                "Scale at all costs",
                "Feature velocity above all",
                "AI hype chasing",
                "Enterprise-first design",
                "Monetization-driven roadmap",
            ],
            invariants=[
                "Every subsystem must justify its existence",
                "Complexity budget must be enforced",
                "Semantic consistency across all modules",
            ],
        )

        self._identity[IdentityAspect.BOUNDARIES] = IdentityStatement(
            aspect=IdentityAspect.BOUNDARIES,
            statement="Explicit boundaries: what the system does NOT do",
            what_it_is=[
                "Local-first runtime for engineering",
                "Browser-based UI",
                "Plugin ecosystem with capability contracts",
                "Open-source with governed evolution",
            ],
            what_it_is_not=[
                "Cloud platform",
                "SaaS product",
                "Enterprise software",
                "AI agent marketplace",
                "Autonomous coding replacement",
                "Distributed computing platform",
            ],
            invariants=[
                "No mandatory cloud services",
                "No vendor lock-in",
                "No hidden data collection",
                "No AI-driven architecture evolution",
            ],
        )

    def get_identity(self, aspect: IdentityAspect) -> Optional[IdentityStatement]:
        """Get identity statement for an aspect."""
        return self._identity.get(aspect)

    def get_all_identity(self) -> dict[IdentityAspect, IdentityStatement]:
        """Get all identity statements."""
        return dict(self._identity)

    def assess_pressure(self, pressure_type: PressureType) -> PressureAssessment:
        """Assess external pressure on project identity."""
        assessments: dict[PressureType, PressureAssessment] = {
            PressureType.ENTERPRISE: PressureAssessment(
                pressure_type=PressureType.ENTERPRISE,
                description="Requests for enterprise features: SSO, audit logs, compliance",
                risk_level="medium",
                mitigation="Provide enterprise features as plugins, not core",
            ),
            PressureType.CLOUD: PressureAssessment(
                pressure_type=PressureType.CLOUD,
                description="Pressure to offer cloud-hosted version",
                risk_level="high",
                mitigation="Local-first is core identity. Cloud can be community plugin, not official.",
            ),
            PressureType.AI_HYPE: PressureAssessment(
                pressure_type=PressureType.AI_HYPE,
                description="Pressure to add autonomous agent features",
                risk_level="high",
                mitigation="Deterministic > AI is core invariant. Autonomy is augmentation, not replacement.",
            ),
            PressureType.MONETIZATION: PressureAssessment(
                pressure_type=PressureType.MONETIZATION,
                description="Pressure to monetize: SaaS, enterprise tiers, premium features",
                risk_level="medium",
                mitigation="Open-source core stays free. Monetization through support/services, not feature gating.",
            ),
            PressureType.SCALE: PressureAssessment(
                pressure_type=PressureType.SCALE,
                description="Pressure to scale: distributed, multi-tenant, high availability",
                risk_level="medium",
                mitigation="Scale is not a goal. Sustainability is. Scale only when it doesn't compromise coherence.",
            ),
            PressureType.FEATURE_CREEP: PressureAssessment(
                pressure_type=PressureType.FEATURE_CREEP,
                description="Endless feature requests from users and contributors",
                risk_level="high",
                mitigation="Every feature must justify its existence against complexity budget and identity.",
            ),
        }
        return assessments.get(pressure_type, PressureAssessment(
            pressure_type=pressure_type,
            description=f"Unknown pressure type: {pressure_type.value}",
            risk_level="low",
            mitigation="Assess impact on core identity",
        ))

    def get_identity_summary(self) -> str:
        """Get a concise identity summary."""
        return (
            "AI Team System is a human-controlled, local-first, browser-first "
            "governed engineering runtime. It is NOT an AGI platform, autonomous "
            "company, enterprise governance monster, or SaaS product. "
            "Core principles: deterministic > AI, safety > autonomy, "
            "coordination > complexity, restraint as architecture."
        )
