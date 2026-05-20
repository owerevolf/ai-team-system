"""
growth_journey.py — Beginner → Engineer Journey.

Purpose: Real growth path from beginner to independent engineer.
This is the MAIN uniqueness of the project.

Path:
BEGINNER → GUIDED LEARNER → JUNIOR BUILDER → TEAM COLLABORATOR → INDEPENDENT ENGINEER

System must:
- remember progress
- adapt explanations
- reduce handholding
- increase engineering depth
- teach reasoning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


class JourneyStage:
    BEGINNER = "beginner"
    GUIDED_LEARNER = "guided_learner"
    JUNIOR_BUILDER = "junior_builder"
    TEAM_COLLABORATOR = "team_collaborator"
    INDEPENDENT_ENGINEER = "independent_engineer"


STAGES = [
    JourneyStage.BEGINNER,
    JourneyStage.GUIDED_LEARNER,
    JourneyStage.JUNIOR_BUILDER,
    JourneyStage.TEAM_COLLABORATOR,
    JourneyStage.INDEPENDENT_ENGINEER,
]


@dataclass
class UserProgress:
    """User's progress on the journey."""
    user_id: str = ""
    current_stage: str = JourneyStage.BEGINNER
    completed_milestones: List[str] = field(default_factory=list)
    skills_demonstrated: Dict[str, int] = field(default_factory=dict)
    total_tasks_completed: int = 0
    total_patches_reviewed: int = 0
    total_rollbacks: int = 0
    preferred_mode: str = "learning"
    explanation_preference: str = "detailed"  # detailed, summary, minimal


class GrowthJourney:
    """
    Manages the user's growth journey from beginner to engineer.
    This is the MAIN uniqueness of the project.
    """

    # Milestones per stage
    MILESTONES = {
        JourneyStage.BEGINNER: [
            "first_conversation",
            "first_project_opened",
            "first_explanation_understood",
            "first_simple_task",
        ],
        JourneyStage.GUIDED_LEARNER: [
            "first_patch_reviewed",
            "first_architecture_explained",
            "first_test_understood",
            "first_guided_build",
        ],
        JourneyStage.JUNIOR_BUILDER: [
            "first_independent_patch",
            "first_bug_fixed",
            "first_feature_added",
            "first_refactor",
        ],
        JourneyStage.TEAM_COLLABORATOR: [
            "first_team_task",
            "first_code_review",
            "first_architecture_decision",
            "first_mentoring",
        ],
        JourneyStage.INDEPENDENT_ENGINEER: [
            "first_complex_project",
            "first_production_fix",
            "first_architecture_design",
            "first_system_optimization",
        ],
    }

    # Skills tracked
    SKILLS = [
        "code_reading", "code_writing", "debugging", "testing",
        "architecture", "git", "review", "refactoring",
        "documentation", "collaboration",
    ]

    def __init__(self):
        self._progress: Dict[str, UserProgress] = {}

    def get_or_create_progress(self, user_id: str) -> UserProgress:
        """Get or create user progress."""
        if user_id not in self._progress:
            self._progress[user_id] = UserProgress(user_id=user_id)
        return self._progress[user_id]

    def record_milestone(self, user_id: str, milestone: str) -> bool:
        """Record a completed milestone."""
        progress = self.get_or_create_progress(user_id)
        if milestone not in progress.completed_milestones:
            progress.completed_milestones.append(milestone)
            logger.info(f"Milestone completed: {milestone}")

            # Check for stage advancement
            self._check_stage_advancement(progress)
            return True
        return False

    def record_skill(self, user_id: str, skill: str, level: int = 1) -> None:
        """Record skill demonstration."""
        progress = self.get_or_create_progress(user_id)
        if skill in self.SKILLS:
            progress.skills_demonstrated[skill] = progress.skills_demonstrated.get(skill, 0) + level

    def record_task_completion(self, user_id: str, success: bool) -> None:
        """Record a task completion."""
        progress = self.get_or_create_progress(user_id)
        progress.total_tasks_completed += 1
        if not success:
            progress.total_rollbacks += 1

    def _check_stage_advancement(self, progress: UserProgress) -> None:
        """Check if the user should advance to the next stage."""
        current_idx = STAGES.index(progress.current_stage) if progress.current_stage in STAGES else 0

        if current_idx >= len(STAGES) - 1:
            return  # Already at max

        current_milestones = self.MILESTONES.get(progress.current_stage, [])
        completed_in_stage = [m for m in current_milestones if m in progress.completed_milestones]

        # Advance if 75% of milestones completed
        if len(current_milestones) > 0 and len(completed_in_stage) / len(current_milestones) >= 0.75:
            next_stage = STAGES[current_idx + 1]
            old_stage = progress.current_stage
            progress.current_stage = next_stage

            # Adapt mode and explanation preference
            self._adapt_to_stage(progress)

            logger.info(f"Stage advanced: {old_stage} -> {next_stage}")

    def _adapt_to_stage(self, progress: UserProgress) -> None:
        """Adapt system behavior to the user's stage."""
        stage = progress.current_stage

        if stage == JourneyStage.BEGINNER:
            progress.preferred_mode = "learning"
            progress.explanation_preference = "detailed"
        elif stage == JourneyStage.GUIDED_LEARNER:
            progress.preferred_mode = "guided"
            progress.explanation_preference = "detailed"
        elif stage == JourneyStage.JUNIOR_BUILDER:
            progress.preferred_mode = "guided"
            progress.explanation_preference = "summary"
        elif stage == JourneyStage.TEAM_COLLABORATOR:
            progress.preferred_mode = "engineering"
            progress.explanation_preference = "summary"
        elif stage == JourneyStage.INDEPENDENT_ENGINEER:
            progress.preferred_mode = "engineering"
            progress.explanation_preference = "minimal"

    def get_stage_guidance(self, stage: str = "") -> str:
        """Get guidance for the current stage."""
        if not stage:
            stage = JourneyStage.BEGINNER

        guidance = {
            JourneyStage.BEGINNER: (
                "You're just getting started! 🌱\n\n"
                "I'll explain everything in simple terms.\n"
                "Ask me anything — no question is too basic.\n"
                "We'll learn together."
            ),
            JourneyStage.GUIDED_LEARNER: (
                "You're making great progress! 📚\n\n"
                "I'll start showing you more of the 'why' behind things.\n"
                "We'll work on small projects together.\n"
                "You're ready to review simple patches."
            ),
            JourneyStage.JUNIOR_BUILDER: (
                "You're building real things! 🔨\n\n"
                "I'll give you more independence.\n"
                "You can start making your own decisions.\n"
                "I'll be here when you need guidance."
            ),
            JourneyStage.TEAM_COLLABORATOR: (
                "You're working like a pro! 🤝\n\n"
                "I'll treat you as a peer.\n"
                "We can discuss architecture and tradeoffs.\n"
                "You can help review others' work."
            ),
            JourneyStage.INDEPENDENT_ENGINEER: (
                "You're an independent engineer! 🚀\n\n"
                "I'll be your calm engineering assistant.\n"
                "Minimal explanations unless you ask.\n"
                "Full trust in your judgment."
            ),
        }

        return guidance.get(stage, guidance[JourneyStage.BEGINNER])

    def get_progress_summary(self, user_id: str) -> str:
        """Get a progress summary for the user."""
        progress = self.get_or_create_progress(user_id)

        current_idx = STAGES.index(progress.current_stage) if progress.current_stage in STAGES else 0
        total_stages = len(STAGES)

        current_milestones = self.MILESTONES.get(progress.current_stage, [])
        completed = [m for m in current_milestones if m in progress.completed_milestones]

        lines = [
            f"# Your Journey: {progress.current_stage.replace('_', ' ').title()}",
            "",
            f"Stage {current_idx + 1} of {total_stages}",
            f"Tasks completed: {progress.total_tasks_completed}",
            f"Patches reviewed: {progress.total_patches_reviewed}",
            "",
        ]

        if current_milestones:
            lines.append(f"## Current Stage Progress")
            lines.append(f"{len(completed)}/{len(current_milestones)} milestones")
            for m in current_milestones:
                status = "✓" if m in completed else "○"
                lines.append(f"  {status} {m.replace('_', ' ').title()}")
            lines.append("")

        if progress.skills_demonstrated:
            lines.append("## Skills")
            for skill, level in sorted(progress.skills_demonstrated.items()):
                bar = "█" * min(level, 10) + "░" * (10 - min(level, 10))
                lines.append(f"  {skill.replace('_', ' ').title()}: {bar} {level}")
            lines.append("")

        lines.append(self.get_stage_guidance(progress.current_stage))

        return "\n".join(lines)
