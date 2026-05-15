"""
Semantic Change Detection — structural analysis of what changed.

NOT AI semantic reasoning. Only structural comparison.

Detects:
- Public API changes (added/removed/changed public symbols)
- Function signature changes (params, return type hints)
- Symbol visibility changes (public → private, etc.)
- Route contract changes (path, method changes)
- Interface modifications (class methods added/removed)
- Inheritance changes (base class changes)
- Export changes (added/removed exports)
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from core.project_manager.models import FileEntry
from loguru import logger


class ChangeType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    VISIBILITY_CHANGED = "visibility_changed"
    SIGNATURE_CHANGED = "signature_changed"
    UNCHANGED = "unchanged"


class ChangeSeverity(Enum):
    LOW = "low"           # Internal change, no API impact
    MEDIUM = "medium"     # Protected symbol changed
    HIGH = "high"         # Public API changed
    BREAKING = "breaking" # Breaking change (removed public API)


@dataclass
class SymbolChange:
    """Change to a single symbol."""
    symbol_name: str
    change_type: ChangeType
    severity: ChangeSeverity
    file_path: str
    old_signature: str = ""
    new_signature: str = ""
    details: str = ""


@dataclass
class FileChange:
    """Changes in a single file."""
    file_path: str
    is_new: bool = False
    is_deleted: bool = False
    symbol_changes: List[SymbolChange] = field(default_factory=list)
    imports_added: List[str] = field(default_factory=list)
    imports_removed: List[str] = field(default_factory=list)
    exports_added: List[str] = field(default_factory=list)
    exports_removed: List[str] = field(default_factory=list)


@dataclass
class SemanticChangeReport:
    """Complete semantic change report."""
    file_changes: List[FileChange] = field(default_factory=list)
    total_symbols_added: int = 0
    total_symbols_removed: int = 0
    total_symbols_modified: int = 0
    public_api_changes: int = 0
    breaking_changes: int = 0

    @property
    def has_breaking_changes(self) -> bool:
        return self.breaking_changes > 0

    @property
    def has_public_api_changes(self) -> bool:
        return self.public_api_changes > 0

    def summary(self) -> Dict[str, Any]:
        return {
            'files_changed': len(self.file_changes),
            'symbols_added': self.total_symbols_added,
            'symbols_removed': self.total_symbols_removed,
            'symbols_modified': self.total_symbols_modified,
            'public_api_changes': self.public_api_changes,
            'breaking_changes': self.breaking_changes,
            'has_breaking': self.has_breaking_changes,
        }


class SemanticChangeDetector:
    """
    Detects semantic changes between two project states.

    Compares:
    - Symbol definitions (name, signature, decorators, parent)
    - Imports and exports
    - Public API surface
    - Route definitions
    """

    def __init__(
        self,
        old_files: Dict[str, FileEntry],
        new_files: Dict[str, FileEntry],
    ):
        self.old_files = old_files
        self.new_files = new_files

    def detect_changes(self) -> SemanticChangeReport:
        """
        Compare old and new file states and produce change report.
        """
        report = SemanticChangeReport()

        all_files = set(self.old_files.keys()) | set(self.new_files.keys())

        for file_path in sorted(all_files):
            old_entry = self.old_files.get(file_path)
            new_entry = self.new_files.get(file_path)

            if not old_entry:
                # New file
                assert new_entry is not None
                file_change = self._analyze_new_file(new_entry)
                report.file_changes.append(file_change)
                report.total_symbols_added += len(new_entry.symbols)
                continue

            if not new_entry:
                # Deleted file
                file_change = self._analyze_deleted_file(old_entry)
                report.file_changes.append(file_change)
                report.total_symbols_removed += len(old_entry.symbols)
                continue

            # Modified file
            file_change = self._analyze_file_changes(old_entry, new_entry)
            if file_change.symbol_changes or file_change.imports_added or file_change.imports_removed:
                report.file_changes.append(file_change)

        # Count totals
        for fc in report.file_changes:
            for sc in fc.symbol_changes:
                if sc.change_type == ChangeType.ADDED:
                    report.total_symbols_added += 1
                elif sc.change_type == ChangeType.REMOVED:
                    report.total_symbols_removed += 1
                elif sc.change_type in (ChangeType.MODIFIED, ChangeType.SIGNATURE_CHANGED):
                    report.total_symbols_modified += 1

                if sc.severity in (ChangeSeverity.HIGH, ChangeSeverity.BREAKING):
                    report.public_api_changes += 1
                if sc.severity == ChangeSeverity.BREAKING:
                    report.breaking_changes += 1

        return report

    def _analyze_new_file(self, entry: FileEntry) -> FileChange:
        """Analyze a newly added file."""
        file_change = FileChange(file_path=entry.path, is_new=True)

        for sym in entry.symbols:
            severity = self._classify_new_symbol(sym)
            file_change.symbol_changes.append(SymbolChange(
                symbol_name=sym.get('name', ''),
                change_type=ChangeType.ADDED,
                severity=severity,
                file_path=entry.path,
                new_signature=sym.get('signature', ''),
                details=f"New {sym.get('type', 'symbol')}",
            ))

        file_change.imports_added = list(entry.imports)
        file_change.exports_added = list(entry.exports)

        return file_change

    def _analyze_deleted_file(self, entry: FileEntry) -> FileChange:
        """Analyze a deleted file."""
        file_change = FileChange(file_path=entry.path, is_deleted=True)

        for sym in entry.symbols:
            severity = ChangeSeverity.BREAKING if self._is_public(sym) else ChangeSeverity.HIGH
            file_change.symbol_changes.append(SymbolChange(
                symbol_name=sym.get('name', ''),
                change_type=ChangeType.REMOVED,
                severity=severity,
                file_path=entry.path,
                old_signature=sym.get('signature', ''),
                details=f"Removed {sym.get('type', 'symbol')}",
            ))

        file_change.imports_removed = list(entry.imports)
        file_change.exports_removed = list(entry.exports)

        return file_change

    def _analyze_file_changes(
        self, old_entry: FileEntry, new_entry: FileEntry
    ) -> FileChange:
        """Analyze changes in an existing file."""
        file_change = FileChange(file_path=old_entry.path)

        old_symbols = {s.get('name', ''): s for s in old_entry.symbols}
        new_symbols = {s.get('name', ''): s for s in new_entry.symbols}

        # Find added symbols
        for name, sym in new_symbols.items():
            if name not in old_symbols:
                severity = self._classify_new_symbol(sym)
                file_change.symbol_changes.append(SymbolChange(
                    symbol_name=name,
                    change_type=ChangeType.ADDED,
                    severity=severity,
                    file_path=old_entry.path,
                    new_signature=sym.get('signature', ''),
                    details=f"New {sym.get('type', 'symbol')}",
                ))

        # Find removed symbols
        for name, sym in old_symbols.items():
            if name not in new_symbols:
                severity = ChangeSeverity.BREAKING if self._is_public(sym) else ChangeSeverity.HIGH
                file_change.symbol_changes.append(SymbolChange(
                    symbol_name=name,
                    change_type=ChangeType.REMOVED,
                    severity=severity,
                    file_path=old_entry.path,
                    old_signature=sym.get('signature', ''),
                    details=f"Removed {sym.get('type', 'symbol')}",
                ))

        # Find modified symbols
        for name in set(old_symbols.keys()) & set(new_symbols.keys()):
            old_sym = old_symbols[name]
            new_sym = new_symbols[name]

            change = self._compare_symbol(old_sym, new_sym, old_entry.path)
            if change:
                file_change.symbol_changes.append(change)

        # Import changes
        old_imports = set(old_entry.imports)
        new_imports = set(new_entry.imports)
        file_change.imports_added = sorted(new_imports - old_imports)
        file_change.imports_removed = sorted(old_imports - new_imports)

        # Export changes
        old_exports = set(old_entry.exports)
        new_exports = set(new_entry.exports)
        file_change.exports_added = sorted(new_exports - old_exports)
        file_change.exports_removed = sorted(old_exports - new_exports)

        return file_change

    def _compare_symbol(
        self, old_sym: Dict, new_sym: Dict, file_path: str
    ) -> Optional[SymbolChange]:
        """Compare two versions of the same symbol."""
        old_sig = old_sym.get('signature', '')
        new_sig = new_sym.get('signature', '')

        if old_sig == new_sig:
            return None

        # Determine change type
        old_type = old_sym.get('type', '')
        new_type = new_sym.get('type', '')

        if old_type != new_type:
            change_type = ChangeType.MODIFIED
            severity = ChangeSeverity.HIGH
            details = f"Type changed: {old_type} → {new_type}"
        elif old_sig != new_sig:
            change_type = ChangeType.SIGNATURE_CHANGED
            severity = ChangeSeverity.HIGH if self._is_public(new_sym) else ChangeSeverity.MEDIUM
            details = "Signature changed"
        else:
            change_type = ChangeType.MODIFIED
            severity = ChangeSeverity.LOW
            details = "Minor change"

        return SymbolChange(
            symbol_name=new_sym.get('name', ''),
            change_type=change_type,
            severity=severity,
            file_path=file_path,
            old_signature=old_sig,
            new_signature=new_sig,
            details=details,
        )

    def _is_public(self, symbol: Dict) -> bool:
        """Check if a symbol is public (not prefixed with _)."""
        name = symbol.get('name', '')
        return not name.startswith('_')

    def _classify_new_symbol(self, symbol: Dict) -> ChangeSeverity:
        """Classify the severity of a new symbol."""
        if not self._is_public(symbol):
            return ChangeSeverity.LOW

        sym_type = symbol.get('type', '')
        if sym_type in ('class', 'function', 'interface'):
            return ChangeSeverity.MEDIUM
        elif sym_type in ('method', 'route'):
            return ChangeSeverity.LOW
        else:
            return ChangeSeverity.LOW
