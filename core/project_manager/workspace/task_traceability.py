"""
Task-to-Code Traceability Module (P9)
======================================

Tracks which tasks changed which files and symbols.
All operations are append-only (audit log style).
Persisted as JSON in the project's .ai-team/ directory.

Usage:
    trace = TaskTraceability("/path/to/project")
    trace.record_task_start("T-001", "Add login feature", "coder-agent")
    trace.record_file_change("T-001", "src/auth.py", "modified", symbols_affected=["login", "validate"])
    trace.record_task_complete("T-001", "completed")
    report = trace.generate_trace_report("T-001")
    print(report)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _load_json(path: str) -> list[dict[str, Any]]:
    """Load a JSON array from disk, returning an empty list if the file doesn't exist."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, OSError):
        return []


def _append_json(path: str, record: dict[str, Any]) -> None:
    """Append a record to a JSON array file, creating it if necessary."""
    records = _load_json(path)
    records.append(record)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TaskTraceability:
    """
    Append-only task-to-code traceability system.

    Every task start, file change, and task completion is recorded as an
    immutable audit entry in a JSON file under .ai-team/trace_log.json.
    """

    def __init__(self, project_path: str) -> None:
        """
        Args:
            project_path: Absolute path to the project root.
        """
        self.project_path = project_path
        self.storage_dir = os.path.join(project_path, ".ai-team")
        self.log_path = os.path.join(self.storage_dir, "trace_log.json")
        os.makedirs(self.storage_dir, exist_ok=True)

    # ---- Recording methods (append-only) ----

    def record_task_start(self, task_id: str, description: str, agent: str) -> dict[str, Any]:
        """
        Record the start of a task.

        Args:
            task_id:   Unique task identifier.
            description: Human-readable task description.
            agent:     Name of the agent executing the task.

        Returns:
            The recorded entry dict.
        """
        entry: dict[str, Any] = {
            "event": "task_start",
            "task_id": task_id,
            "description": description,
            "agent": agent,
            "timestamp": time.time(),
            "status": "in_progress",
        }
        _append_json(self.log_path, entry)
        return entry

    def record_file_change(
        self,
        task_id: str,
        file_path: str,
        change_type: str,
        symbols_affected: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Record a file change associated with a task.

        Args:
            task_id:         Unique task identifier.
            file_path:       Path to the changed file (relative or absolute).
            change_type:     One of "added", "modified", "deleted".
            symbols_affected: Optional list of symbol names (functions, classes, etc.) affected.

        Returns:
            The recorded entry dict.

        Raises:
            ValueError: If change_type is not one of the allowed values.
        """
        allowed = {"added", "modified", "deleted"}
        if change_type not in allowed:
            raise ValueError(f"change_type must be one of {allowed}, got '{change_type}'")

        entry: dict[str, Any] = {
            "event": "file_change",
            "task_id": task_id,
            "file_path": file_path,
            "change_type": change_type,
            "symbols_affected": symbols_affected or [],
            "timestamp": time.time(),
        }
        _append_json(self.log_path, entry)
        return entry

    def record_task_complete(self, task_id: str, status: str) -> dict[str, Any]:
        """
        Record the completion (or failure/cancellation) of a task.

        Args:
            task_id: Unique task identifier.
            status:  Final status, e.g. "completed", "failed", "cancelled".

        Returns:
            The recorded entry dict.
        """
        entry: dict[str, Any] = {
            "event": "task_complete",
            "task_id": task_id,
            "status": status,
            "timestamp": time.time(),
        }
        _append_json(self.log_path, entry)
        return entry

    # ---- Query methods ----

    def _get_log(self) -> list[dict[str, Any]]:
        """Return the full audit log."""
        return _load_json(self.log_path)

    def get_task_trace(self, task_id: str) -> dict[str, Any]:
        """
        Get the full trace for a task: info, file changes, symbols, duration.

        Args:
            task_id: Unique task identifier.

        Returns:
            dict with keys:
                task_id, description, agent, status, start_time, end_time,
                duration_seconds, file_changes, all_symbols
        """
        log = self._get_log()
        task_entries = [e for e in log if e.get("task_id") == task_id]

        if not task_entries:
            return {
                "task_id": task_id,
                "description": None,
                "agent": None,
                "status": "unknown",
                "start_time": None,
                "end_time": None,
                "duration_seconds": None,
                "file_changes": [],
                "all_symbols": [],
            }

        start_entry = next((e for e in task_entries if e["event"] == "task_start"), None)
        complete_entry = next((e for e in task_entries if e["event"] == "task_complete"), None)
        file_changes = [e for e in task_entries if e["event"] == "file_change"]

        # Collect all symbols
        all_symbols: list[str] = []
        seen_symbols: set[str] = set()
        for fc in file_changes:
            for sym in fc.get("symbols_affected", []):
                if sym not in seen_symbols:
                    all_symbols.append(sym)
                    seen_symbols.add(sym)

        start_time = start_entry["timestamp"] if start_entry else None
        end_time = complete_entry["timestamp"] if complete_entry else None
        duration = (end_time - start_time) if (start_time and end_time) else None

        return {
            "task_id": task_id,
            "description": start_entry.get("description") if start_entry else None,
            "agent": start_entry.get("agent") if start_entry else None,
            "status": complete_entry.get("status", "in_progress") if complete_entry else "in_progress",
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": round(duration, 2) if duration is not None else None,
            "file_changes": file_changes,
            "all_symbols": all_symbols,
        }

    def get_file_history(self, file_path: str) -> list[dict[str, Any]]:
        """
        Get all tasks that touched a given file.

        Args:
            file_path: The file path to look up.

        Returns:
            List of dicts with keys: task_id, change_type, agent, timestamp, symbols_affected
        """
        log = self._get_log()
        results: list[dict[str, Any]] = []
        seen_tasks: set[str] = set()

        for entry in log:
            if entry.get("event") == "file_change" and entry.get("file_path") == file_path:
                tid = entry["task_id"]
                # Find the agent from the task_start event
                agent = ""
                for e in log:
                    if e.get("task_id") == tid and e.get("event") == "task_start":
                        agent = e.get("agent", "")
                        break
                results.append({
                    "task_id": tid,
                    "change_type": entry["change_type"],
                    "agent": agent,
                    "timestamp": entry["timestamp"],
                    "symbols_affected": entry.get("symbols_affected", []),
                })
                seen_tasks.add(tid)

        return results

    def get_symbol_history(self, symbol_name: str) -> list[dict[str, Any]]:
        """
        Get all tasks that affected a given symbol.

        Args:
            symbol_name: The symbol name to look up (e.g. "login", "UserController").

        Returns:
            List of dicts with keys: task_id, file_path, change_type, agent, timestamp
        """
        log = self._get_log()
        results: list[dict[str, Any]] = []

        for entry in log:
            if entry.get("event") == "file_change":
                if symbol_name in entry.get("symbols_affected", []):
                    tid = entry["task_id"]
                    agent = ""
                    for e in log:
                        if e.get("task_id") == tid and e.get("event") == "task_start":
                            agent = e.get("agent", "")
                            break
                    results.append({
                        "task_id": tid,
                        "file_path": entry["file_path"],
                        "change_type": entry["change_type"],
                        "agent": agent,
                        "timestamp": entry["timestamp"],
                    })

        return results

    def find_related_tasks(self, task_id: str) -> list[dict[str, Any]]:
        """
        Find tasks that touched the same files as the given task.

        Args:
            task_id: The task to find related tasks for.

        Returns:
            List of dicts with keys: task_id, shared_files, agent, status
        """
        log = self._get_log()

        # Collect files touched by the given task
        my_files: set[str] = set()
        for entry in log:
            if entry.get("task_id") == task_id and entry.get("event") == "file_change":
                my_files.add(entry["file_path"])

        if not my_files:
            return []

        # Find other tasks that touched any of those files
        related: dict[str, set[str]] = {}
        for entry in log:
            if entry.get("task_id") == task_id:
                continue
            if entry.get("event") == "file_change":
                fp = entry["file_path"]
                if fp in my_files:
                    tid = entry["task_id"]
                    related.setdefault(tid, set()).add(fp)

        # Build result with agent and status info
        results: list[dict[str, Any]] = []
        for tid, shared in related.items():
            agent = ""
            status = "in_progress"
            for e in log:
                if e.get("task_id") == tid:
                    if e.get("event") == "task_start":
                        agent = e.get("agent", "")
                    if e.get("event") == "task_complete":
                        status = e.get("status", status)
            results.append({
                "task_id": tid,
                "shared_files": sorted(shared),
                "agent": agent,
                "status": status,
            })

        # Sort by number of shared files descending
        results.sort(key=lambda r: len(r["shared_files"]), reverse=True)
        return results

    def generate_trace_report(self, task_id: str) -> str:
        """
        Generate a human-readable traceability report for a task.

        Args:
            task_id: Unique task identifier.

        Returns:
            A formatted multi-line string.
        """
        trace = self.get_task_trace(task_id)
        lines: list[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("  TASK TRACEABILITY REPORT")
        lines.append(sep)
        lines.append("")

        # Task info
        lines.append(f"  Task ID:     {trace['task_id']}")
        lines.append(f"  Description: {trace['description'] or 'N/A'}")
        lines.append(f"  Agent:       {trace['agent'] or 'N/A'}")
        lines.append(f"  Status:      {trace['status']}")
        lines.append("")

        # Timing
        if trace["start_time"]:
            st = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(trace["start_time"]))
            lines.append(f"  Started:     {st}")
        if trace["end_time"]:
            et = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(trace["end_time"]))
            lines.append(f"  Ended:       {et}")
        if trace["duration_seconds"] is not None:
            lines.append(f"  Duration:    {trace['duration_seconds']}s")
        lines.append("")

        # File changes
        fc = trace["file_changes"]
        lines.append(f"  File Changes ({len(fc)}):")
        if fc:
            for change in fc:
                ct = change["change_type"]
                fp = change["file_path"]
                syms = change.get("symbols_affected", [])
                sym_str = f"  [symbols: {', '.join(syms)}]" if syms else ""
                lines.append(f"    - {ct:10s}  {fp}{sym_str}")
        else:
            lines.append("    (none)")
        lines.append("")

        # Symbols
        if trace["all_symbols"]:
            lines.append(f"  Symbols Affected: {', '.join(trace['all_symbols'])}")
            lines.append("")

        # Related tasks
        related = self.find_related_tasks(task_id)
        lines.append(f"  Related Tasks ({len(related)}):")
        if related:
            for r in related:
                files_str = ", ".join(r["shared_files"])
                lines.append(f"    - {r['task_id']}  (agent: {r['agent']}, status: {r['status']})")
                lines.append(f"      shared files: {files_str}")
        else:
            lines.append("    (none)")
        lines.append("")

        lines.append(sep)
        return "\n".join(lines)
