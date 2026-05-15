"""
RepoExplorer — Scans repository structure and discovers files.

Simple, no external dependencies. Works with regex and os.walk.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger


class RepoExplorer:
    """
    Explores repository file structure.

    Responsibilities:
    1. Discover all relevant files
    2. Build directory tree
    3. Skip irrelevant files (node_modules, __pycache__, etc.)
    """

    # Directories to ALWAYS skip
    SKIP_DIRS = {
        '__pycache__', 'node_modules', '.git', '.venv', 'venv',
        '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
        'coverage', '.pytest_cache', '.mypy_cache', '.tox',
        '.cache', '.logs', '.agents', '.egg-info',
        '__pycache__', '.git', '.hg', '.svn',  # version control
    }

    # File extensions we care about
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.sql', '.graphql',
        '.vue', '.svelte', '.php', '.rb', '.go', '.rs', '.java', '.kt',
        '.swift', '.c', '.cpp', '.h', '.dockerfile', 'Makefile', '.sh',
        '.md', '.txt',  # Include docs for context
    }

    # Important config files (even without extension)
    IMPORTANT_FILES = {
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
        'Makefile', 'makefile', 'requirements.txt', 'package.json',
        'pyproject.toml', 'setup.py', 'setup.cfg', 'Cargo.toml',
        'go.mod', 'go.sum', 'pom.xml', 'build.gradle', 'Gemfile',
        'composer.json', '.env.example', '.env.template',
    }

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        logger.info(f"RepoExplorer initialized: {self.project_path}")

    def discover_files(self) -> List[str]:
        """
        Discover all relevant files in the project.

        Returns:
            List of relative paths (str)
        """
        files = []

        for root, dirs, filenames in os.walk(self.project_path):
            # Filter out skip directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in self.SKIP_DIRS
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

                # Check if file is relevant
                if self._is_relevant_file(filename, rel_path):
                    files.append(rel_path)

        # Sort for consistent ordering
        files.sort()
        logger.info(f"Discovered {len(files)} files")
        return files

    def _is_relevant_file(self, filename: str, rel_path: str) -> bool:
        """Check if file should be indexed."""
        # Always include important config files
        if filename in self.IMPORTANT_FILES:
            return True

        # Check extension
        ext = Path(filename).suffix.lower()
        if ext in self.CODE_EXTENSIONS:
            return True

        # Check if filename itself is in extensions (like Makefile)
        if filename in self.CODE_EXTENSIONS:
            return True

        # Include README files
        if filename.lower().startswith('readme'):
            return True

        return False

    def get_tree_display(self, files_index: Optional[Dict] = None, max_depth: int = 4) -> List[str]:
        """
        Generate tree-like display of project structure.

        Args:
            files_index: Optional FileEntry dict from ProjectManager
            max_depth: Maximum depth to display

        Returns:
            List of strings representing tree
        """
        tree_lines = [f"{self.project_path.name}/"]

        # Build tree structure
        tree = {}

        if files_index:
            paths = list(files_index.keys())
        else:
            paths = self.discover_files()

        for rel_path in paths:
            parts = rel_path.split('/')
            current = tree

            for i, part in enumerate(parts):
                if i >= max_depth:
                    break

                if part not in current:
                    current[part] = {}
                current = current[part]

        # Render tree
        def render(node, prefix="", is_last=True):
            items = sorted(node.items())
            for i, (name, children) in enumerate(items):
                is_last_item = (i == len(items) - 1)
                connector = "└── " if is_last_item else "├── "
                tree_lines.append(f"{prefix}{connector}{name}")

                if children:
                    extension = "    " if is_last_item else "│   "
                    render(children, prefix + extension, is_last_item)

        render(tree)
        return tree_lines

    def get_directory_stats(self) -> Dict[str, int]:
        """Get file count per top-level directory."""
        stats = {}
        files = self.discover_files()

        for rel_path in files:
            parts = rel_path.split('/')
            if len(parts) > 1:
                top_dir = parts[0]
                stats[top_dir] = stats.get(top_dir, 0) + 1
            else:
                stats['[root]'] = stats.get('[root]', 0) + 1

        return stats

    def find_files_by_pattern(self, pattern: str) -> List[str]:
        """Find files matching a pattern (simple substring match)."""
        pattern = pattern.lower()
        files = self.discover_files()
        return [f for f in files if pattern in f.lower()]

    def get_largest_files(self, n: int = 10) -> List[tuple]:
        """Get N largest files."""
        files = []
        for rel_path in self.discover_files():
            full_path = self.project_path / rel_path
            try:
                size = full_path.stat().st_size
                files.append((rel_path, size))
            except Exception:
                continue

        files.sort(key=lambda x: -x[1])
        return files[:n]
