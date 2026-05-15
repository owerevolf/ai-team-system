"""
File Indexer — recursive repo scan, metadata collection.

No AI analysis. Just facts: path, size, hash, language.
"""

import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set

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
    """Scans repository and collects file metadata."""

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()

    def scan(self) -> Dict[str, FileEntry]:
        """
        Full recursive scan of the project.

        Returns:
            Dict mapping relative path -> FileEntry
        """
        entries: Dict[str, FileEntry] = {}

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
                    )
                    entries[rel_path] = entry

                except (OSError, PermissionError):
                    continue

        return entries

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
