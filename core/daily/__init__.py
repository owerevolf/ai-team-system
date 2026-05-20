"""
Phase 24 — Real Developer Experience, Self-Development & Daily Use Maturity.

Modules:
- self_development.py: governed self-development (patches + approvals only)
- self_protection.py: protects runtime from self-destruction
- growth_journey.py: beginner → engineer growth path
- daily_usage_validation.py: final check — can you live here daily?

Principle: SELF-DEVELOPMENT MUST FEEL BORINGLY SAFE
Not "wow AI writes itself" — but governed, reviewable, explainable, recoverable.
"""

from .self_development import SelfDevelopment, SelfDevTask
from .self_protection import SelfProtection, ProtectionDecision
from .growth_journey import GrowthJourney, UserProgress, JourneyStage
from .daily_usage_validation import DailyUsageValidation, DailyReport, DailyCheck

__all__ = [
    "SelfDevelopment", "SelfDevTask",
    "SelfProtection", "ProtectionDecision",
    "GrowthJourney", "UserProgress", "JourneyStage",
    "DailyUsageValidation", "DailyReport", "DailyCheck",
]
