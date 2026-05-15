"""
FileWatch — filesystem watcher for incremental indexing.

Uses watchdog library for inotify/fsevents-based file monitoring.
Features:
- Debounce events (batch rapid changes)
- Event deduplication
- Configurable ignore patterns
- Thread-safe event queue
"""

import time
import threading
from pathlib import Path
from typing import Callable, List, Optional, Set
from collections import defaultdict

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirDeletedEvent,
)

from loguru import logger


# Directories to ignore
IGNORE_DIRS: Set[str] = {
    '__pycache__', 'node_modules', '.git', '.venv', 'venv',
    '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
    'coverage', '.pytest_cache', '.mypy_cache', '.tox',
    '.cache', '.logs', '.agents', '.egg-info',
}

# Extensions to ignore
IGNORE_EXTENSIONS: Set[str] = {
    '.pyc', '.pyo', '.so', '.o', '.a', '.dll', '.exe',
    '.swp', '.swo', '.tmp', '.bak', '.orig',
}


class _EventHandler(FileSystemEventHandler):
    """Internal watchdog event handler with debounce."""

    def __init__(self, callback: Callable[[List[str]], None], debounce_seconds: float = 1.0):
        super().__init__()
        self._callback = callback
        self._debounce_seconds = debounce_seconds
        self._pending: Set[str] = set()
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def on_created(self, event):
        if not event.is_directory:
            self._queue(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._queue(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._queue(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._queue(event.src_path)
            self._queue(event.dest_path)

    def _queue(self, path: str):
        """Add path to pending set and reset debounce timer."""
        p = Path(path)

        # Skip ignored
        if any(part in IGNORE_DIRS for part in p.parts):
            return
        if p.suffix.lower() in IGNORE_EXTENSIONS:
            return
        if p.name.startswith('.') and p.name not in ('.env.example', '.env.template'):
            return

        with self._lock:
            self._pending.add(str(p))
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_seconds, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        """Flush pending paths to callback."""
        with self._lock:
            if not self._pending:
                return
            paths = list(self._pending)
            self._pending.clear()
            self._timer = None

        try:
            self._callback(paths)
        except Exception as e:
            logger.error(f"FileWatch callback error: {e}")


class FileWatch:
    """
    Filesystem watcher for ProjectManager.

    Watches for file changes and triggers incremental re-indexing.
    Debounces rapid changes to avoid excessive re-indexing.

    Usage:
        fw = FileWatch(Path("/project"), callback=on_files_changed)
        fw.start()
        # ... later ...
        fw.stop()
    """

    def __init__(
        self,
        project_path: Path,
        callback: Callable[[List[str]], None],
        debounce_seconds: float = 1.0,
    ):
        """
        Args:
            project_path: Path to watch
            callback: Called with list of changed file paths (relative)
            debounce_seconds: Wait this long before processing batch
        """
        self.project_path = Path(project_path).resolve()
        self._callback = callback
        self._debounce_seconds = debounce_seconds
        self._observer: Optional[Observer] = None
        self._handler: Optional[_EventHandler] = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start watching for file changes."""
        with self._lock:
            if self._running:
                return

            self._handler = _EventHandler(
                callback=self._on_change,
                debounce_seconds=self._debounce_seconds,
            )
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(self.project_path),
                recursive=True,
            )
            self._observer.daemon = True
            self._observer.start()
            self._running = True
            logger.info(f"FileWatch started: {self.project_path}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        with self._lock:
            if not self._running:
                return

            if self._observer:
                self._observer.stop()
                self._observer.join(timeout=5)
                self._observer = None

            self._handler = None
            self._running = False
            logger.info("FileWatch stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def _on_change(self, absolute_paths: List[str]) -> None:
        """Convert absolute paths to relative and call user callback."""
        relative_paths = []
        for abs_path in absolute_paths:
            try:
                rel = str(Path(abs_path).relative_to(self.project_path))
                relative_paths.append(rel)
            except ValueError:
                continue

        if relative_paths:
            logger.debug(f"FileWatch: {len(relative_paths)} changed files")
            self._callback(relative_paths)
