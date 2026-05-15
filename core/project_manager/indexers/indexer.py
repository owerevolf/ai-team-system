"""
File Indexer — recursive repo scan, metadata collection.

No AI analysis. Just facts: path, size, hash, language.
Supports both full scan and incremental (changed-files-only) scan.
"""

import os
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.project_manager.models import FileEntry


# Directories to skip
SKIP_DIRS: Set[str] = {
    '__pycache__', 'node_modules', '.git', '.venv', 'venv',
    '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
    'coverage', '.pytest_cache', '.mypy_cache', '.tox',
    '.cache', '.logs', '.agents', '.egg-info',
}

# File extensions we care about
CODE_EXTENSIONS: Set[str] = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
    '.json', '.yaml', '.yml', '.toml', '.ini', '.sql', '.graphql',
    '.vue', '.svelte', '.php', '.rb', '.go', '.rs', '.java', '.kt',
    '.swift', '.c', '.cpp', '.h', '.sh', '.md', '.txt',
}

# Important config files by name
IMPORTANT_FILES: Set[str] = {
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    'Makefile', 'makefile', 'requirements.txt', 'package.json',
    'pyproject.toml', 'setup.py', 'setup.cfg', 'Cargo.toml',
    'go.mod', 'go.sum', 'pom.xml', 'build.gradle', 'Gemfile',
    'composer.json', '.env.example', '.env.template',
}

# Extension -> language mapping
EXT_TO_LANG = {
    '.py': 'python', '.js': 'javascript', '.jsx': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript', '.html': 'html',
    '.css': 'css', '.scss': 'scss', '.json': 'json',
    '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
    '.md': 'markdown', '.sql': 'sql', '.sh': 'bash',
    '.go': 'go', '.rs': 'rust', '.java': 'java',
    '.kt': 'kotlin', '.swift': 'swift', '.c': 'c',
    '.cpp': 'cpp', '.h': 'c', '.php': 'php', '.rb': 'ruby',
    '.vue': 'vue', '.svelte': 'svelte',
}


class FileIndexer:
    """Scans repository and collects file metadata. Supports incremental updates."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()

    def scan(self) -> Dict[str, FileEntry]:
        """
        Full recursive scan of the project.

        Returns:
            Dict mapping relative path -> FileEntry
        """
        entries: Dict[str, FileEntry] = {}
        now = time.time()

        for root, dirs, filenames in os.walk(self.project_path):
            # Filter skip directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS
                and not d.startswith('.')
                and not d.startswith('__')
            ]

            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = str(file_path.relative_to(self.project_path))

                # Skip hidden files (except important ones)
                if filename.startswith('.'):
                    if filename not in ('.env.example', '.env.template', '.gitignore', '.dockerignore'):
                        continue

                if not self._is_relevant(filename, rel_path):
                    continue

                try:
                    stat = file_path.stat()
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                    language = self._detect_language(filename)

                    entry = FileEntry(
                        path=rel_path,
                        size=stat.st_size,
                        modified=stat.st_mtime,
                        hash=file_hash,
                        language=language,
                        last_seen=stat.st_mtime,
                        index_time=now,
                    )
                    entries[rel_path] = entry

                except (OSError, PermissionError):
                    continue

        return entries

    def scan_incremental(
        self,
        existing: Dict[str, FileEntry],
    ) -> Tuple[Dict[str, FileEntry], List[str], List[str], List[str]]:
        """
        Incremental scan: only process changed/new/deleted files.

        Args:
            existing: Current file index

        Returns:
            Tuple of (updated_index, changed_files, added_files, removed_files)
        """
        now = time.time()
        current_files: Set[str] = set()
        changed: List[str] = []
        added: List[str] = []
        removed: List[str] = []

        # Walk the filesystem
        for root, dirs, filenames in os.walk(self.project_path):
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS
                and not d.startswith('.')
                and not d.startswith('__')
            ]

            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = str(file_path.relative_to(self.project_path))

                if filename.startswith('.'):
                    if filename not in ('.env.example', '.env.template', '.gitignore', '.dockerignore'):
                        continue

                if not self._is_relevant(filename, rel_path):
                    continue

                current_files.add(rel_path)

                try:
                    stat = file_path.stat()

                    # New file
                    if rel_path not in existing:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                        entry = FileEntry(
                            path=rel_path,
                            size=stat.st_size,
                            modified=stat.st_mtime,
                            hash=file_hash,
                            language=self._detect_language(filename),
                            last_seen=stat.st_mtime,
                            index_time=now,
                        )
                        existing[rel_path] = entry
                        added.append(rel_path)
                        continue

                    # Check if modified (mtime changed or hash differs)
                    entry = existing[rel_path]
                    if stat.st_mtime != entry.last_seen:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

                        if file_hash != entry.hash:
                            entry.size = stat.st_size
                            entry.modified = stat.st_mtime
                            entry.hash = file_hash
                            entry.last_seen = stat.st_mtime
                            entry.index_time = now
                            # Clear stale symbol data — will be re-extracted
                            entry.symbols = []
                            entry.imports = []
                            entry.exports = []
                            changed.append(rel_path)
                        else:
                            # Content same, just update timestamps
                            entry.last_seen = stat.st_mtime

                except (OSError, PermissionError):
                    continue

        # Find deleted files
        for rel_path in list(existing.keys()):
            if rel_path not in current_files:
                del existing[rel_path]
                removed.append(rel_path)

        return existing, changed, added, removed

    def _is_relevant(self, filename: str, rel_path: str) -> bool:
        """Check if file should be indexed."""
        if filename in IMPORTANT_FILES:
            return True
        ext = Path(filename).suffix.lower()
        if ext in CODE_EXTENSIONS:
            return True
        if filename.lower().startswith('readme'):
            return True
        return False

    def _detect_language(self, filename: str) -> str:
        """Detect language from file extension."""
        ext = Path(filename).suffix.lower()
        return EXT_TO_LANG.get(ext, 'unknown')
