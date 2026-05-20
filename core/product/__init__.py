"""
Phase 25 — Real Productization, UI Cohesion & Production Workflow Reality.

Modules:
- unified_workspace.py: one workspace experience (learning → engineering)
- cohesion_validation.py: checks if system feels like ONE product
- product_readiness.py: final check — is this a real product?

Principle: THE USER EXPERIENCE IS NOW THE ARCHITECTURE
"""

from .unified_workspace import UnifiedWorkspace, WorkspaceState
from .cohesion_validation import CohesionValidation, CohesionReport, CohesionCheck
from .product_readiness import ProductReadiness, ReadinessReport, ReadinessCheck

__all__ = [
    "UnifiedWorkspace", "WorkspaceState",
    "CohesionValidation", "CohesionReport", "CohesionCheck",
    "ProductReadiness", "ReadinessReport", "ReadinessCheck",
]
