"""
Phase 12, P7: Progressive Disclosure Engine

Reveals complexity only when needed.
Default: minimal operational guidance.
Expand: only on explicit demand.

Principle: Anti-overengineering strategy.
Users should not pay cognitive cost for features they don't use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DisclosureLevel(Enum):
    """Levels of information disclosure."""
    MINIMAL = 0       # Absolute minimum — what happened
    SUMMARY = 1       # Brief summary — what and why
    DETAILED = 2      # Detailed — what, why, how
    FULL = 3          # Complete — everything including internals
    DEBUG = 4         # Debug-level — raw data, traces, state dumps


class ExpandTrigger(Enum):
    """What triggers expansion to the next disclosure level."""
    EXPLICIT_REQUEST = "explicit_request"    # User explicitly asks
    ERROR_CONTEXT = "error_context"          # Error occurred — show more
    REPEATED_ACTION = "repeated_action"      # User does same thing repeatedly
    VERBOSE_MODE = "verbose_mode"           # User enabled verbose mode


@dataclass
class DisclosureItem:
    """An item that can be disclosed at different levels."""
    name: str
    current_level: DisclosureLevel = DisclosureLevel.MINIMAL
    minimal: str = ""
    summary: str = ""
    detailed: str = ""
    full: str = ""
    debug: str = ""
    auto_expand_on_error: bool = True
    expand_count: int = 0  # Track how often user expands this

    def get_content(self, level: Optional[DisclosureLevel] = None) -> str:
        """Get content at the specified or current level."""
        level = level or self.current_level
        content_map = {
            DisclosureLevel.MINIMAL: self.minimal,
            DisclosureLevel.SUMMARY: self.summary or self.minimal,
            DisclosureLevel.DETAILED: self.detailed or self.summary or self.minimal,
            DisclosureLevel.FULL: self.full or self.detailed or self.summary or self.minimal,
            DisclosureLevel.DEBUG: self.debug or self.full or self.detailed or self.summary or self.minimal,
        }
        return content_map.get(level, self.minimal)

    def expand(self) -> bool:
        """Expand to the next level. Returns True if expanded."""
        levels = list(DisclosureLevel)
        current_idx = levels.index(self.current_level)
        if current_idx < len(levels) - 1:
            self.current_level = levels[current_idx + 1]
            self.expand_count += 1
            return True
        return False

    def collapse(self) -> bool:
        """Collapse to the previous level. Returns True if collapsed."""
        levels = list(DisclosureLevel)
        current_idx = levels.index(self.current_level)
        if current_idx > 0:
            self.current_level = levels[current_idx - 1]
            return True
        return False

    def reset(self) -> None:
        """Reset to minimal level."""
        self.current_level = DisclosureLevel.MINIMAL


@dataclass
class DisclosureProfile:
    """User's disclosure preferences."""
    default_level: DisclosureLevel = DisclosureLevel.MINIMAL
    max_level: DisclosureLevel = DisclosureLevel.FULL
    auto_expand_errors: bool = True
    remember_expansions: bool = True  # Remember what user expanded
    verbose_mode: bool = False


class ProgressiveDisclosureEngine:
    """
    Manages progressive disclosure of runtime information.
    Default is minimal; complexity is revealed only on demand.
    """

    def __init__(self, profile: Optional[DisclosureProfile] = None) -> None:
        self.profile = profile or DisclosureProfile()
        self._items: dict[str, DisclosureItem] = {}
        self._expansion_history: list[tuple[str, DisclosureLevel, float]] = []

    def register(self, item: DisclosureItem) -> None:
        """Register a disclosure-managed item."""
        # Apply profile default
        if self.profile.verbose_mode:
            item.current_level = min(
                DisclosureLevel.SUMMARY,
                self.profile.max_level,
                key=lambda l: l.value,
            )
        self._items[item.name] = item

    def get(self, name: str, level: Optional[DisclosureLevel] = None) -> str:
        """Get content for an item at the specified level."""
        item = self._items.get(name)
        if not item:
            return ""
        return item.get_content(level)

    def expand(self, name: str, trigger: ExpandTrigger = ExpandTrigger.EXPLICIT_REQUEST) -> str:
        """Expand an item to the next disclosure level."""
        item = self._items.get(name)
        if not item:
            return ""

        old_level = item.current_level
        if item.expand():
            # Enforce profile max_level
            if item.current_level.value > self.profile.max_level.value:
                item.current_level = old_level  # Revert
                return item.get_content()
            import time
            self._expansion_history.append((name, item.current_level, time.time()))
            return item.get_content()
        return item.get_content()

    def collapse(self, name: str) -> str:
        """Collapse an item to the previous disclosure level."""
        item = self._items.get(name)
        if not item:
            return ""
        item.collapse()
        return item.get_content()

    def handle_error(self, name: str, error_context: str = "") -> str:
        """
        Auto-expand on error if configured.
        Returns the expanded content.
        """
        item = self._items.get(name)
        if not item:
            return error_context

        if item.auto_expand_on_error and self.profile.auto_expand_errors:
            # Jump to at least DETAILED on error
            target = DisclosureLevel.DETAILED
            if item.current_level.value < target.value:
                item.current_level = target
                return item.get_content()

        return item.get_content()

    def get_frequently_expanded(self, min_expands: int = 3) -> list[DisclosureItem]:
        """Get items that user expands frequently — candidate for higher default."""
        return [
            item for item in self._items.values()
            if item.expand_count >= min_expands
        ]

    def get_never_expanded(self) -> list[DisclosureItem]:
        """Get items that user never expands — candidate for removal or further hiding."""
        return [
            item for item in self._items.values()
            if item.expand_count == 0 and item.name in self._items
        ]

    def set_verbose(self, enabled: bool) -> None:
        """Enable or disable verbose mode."""
        self.profile.verbose_mode = enabled
        if enabled:
            for item in self._items.values():
                item.current_level = DisclosureLevel.SUMMARY
        else:
            for item in self._items.values():
                item.current_level = DisclosureLevel.MINIMAL

    @property
    def registered_count(self) -> int:
        return len(self._items)

    @property
    def current_max_level(self) -> DisclosureLevel:
        if not self._items:
            return DisclosureLevel.MINIMAL
        return max((item.current_level for item in self._items.values()), key=lambda l: l.value)
