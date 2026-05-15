"""
File Indexer — recursive repo scan, metadata collection.

Exports:
- FileIndexer: full + incremental scan
- FileWatch: filesystem watcher for real-time updates
- GitIntelligence: git state reader
"""

from core.project_manager.indexers.indexer import FileIndexer
from core.project_manager.indexers.file_watch import FileWatch
from core.project_manager.indexers.git_intelligence import GitIntelligence

__all__ = ['FileIndexer', 'FileWatch', 'GitIntelligence']
