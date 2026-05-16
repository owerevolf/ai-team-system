"""
Repo Repair Mode (P3) — Deterministic repository repair analysis.

This module provides analysis-only repair planning for Python projects.
It does NOT execute repairs — only identifies issues and produces repair plans.

All methods are deterministic and file-based: AST parsing for imports,
regex for pattern matching, and DFS for cycle detection.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Known deprecated patterns: (regex, human-readable pattern name, suggestion)
# ---------------------------------------------------------------------------
_DEPRECATED_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"\bprint\s+[^(]",
        "print statement (Python 2)",
        "Use print() function instead of print statement.",
    ),
    (
        r"\bhas_key\s*\(",
        "dict.has_key()",
        "Use 'key in dict' instead of dict.has_key(key).",
    ),
    (
        r"\basyncio\.coroutine\b",
        "@asyncio.coroutine decorator",
        "Use 'async def' instead of @asyncio.coroutine.",
    ),
    (
        r"\byield\s+from\s+",
        "yield from (in async context)",
        "Ensure 'yield from' is not used inside an async function.",
    ),
    (
        r"\bplatform\.dist\b|\bplatform\.linux_distribution\b",
        "platform.dist() / platform.linux_distribution()",
        "Use the 'distro' package instead.",
    ),
    (
        r"\bimp\.load_module\b|\bimp\.load_source\b|\bimp\.find_module\b",
        "imp module",
        "Use importlib instead of the deprecated imp module.",
    ),
    (
        r"\boptparse\.",
        "optparse module",
        "Use argparse instead of optparse.",
    ),
    (
        r"\basyncio\.get_event_loop\(\)(?!.*running_loop)",
        "asyncio.get_event_loop() without running check",
        "Use asyncio.get_running_loop() inside async contexts.",
    ),
    (
        r"\.iteritems\(\)|\.itervalues\(\)|\.iterkeys\(\)",
        "dict.iteritems/itervalues/iterkeys",
        "Use .items(), .values(), .keys() (Python 3).",
    ),
    (
        r"\bbasestring\b",
        "basestring type",
        "Use str instead of basestring (Python 3).",
    ),
    (
        r"\blong\s*\(",
        "long() builtin",
        "Use int instead of long (Python 3).",
    ),
    (
        r"\bunicode\s*\(",
        "unicode() builtin",
        "Use str instead of unicode (Python 3).",
    ),
    (
        r"\bxrange\s*\(",
        "xrange()",
        "Use range() instead of xrange (Python 3).",
    ),
    (
        r"\bapply\s*\(",
        "apply() builtin",
        "Use direct function calls instead of apply().",
    ),
    (
        r"\breload\s*\(",
        "reload() builtin",
        "Use importlib.reload() instead of reload().",
    ),
    (
        r"\bexecfile\s*\(",
        "execfile()",
        "Use exec(open(...).read()) instead of execfile().",
    ),
]


class RepoRepair:
    """Deterministic repository repair analysis.

    Analyzes a Python project for common issues and produces repair plans.
    No repairs are executed — only analysis and planning.

    Args:
        project_path: Absolute or relative path to the project root.
    """

    def __init__(self, project_path: str) -> None:
        self.project_path = Path(project_path).resolve()
        if not self.project_path.is_dir():
            raise ValueError(
                f"project_path must be a directory: {self.project_path}"
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _python_files(self) -> list[Path]:
        """Return all .py files under the project root, excluding common
        virtual-environment and cache directories."""
        skip = {".venv", "venv", "env", "__pycache__", ".tox", ".eggs", "node_modules"}
        files: list[Path] = []
        for root, dirs, filenames in os.walk(self.project_path):
            # prune skipped directories in-place
            dirs[:] = [d for d in dirs if d not in skip]
            for fn in filenames:
                if fn.endswith(".py"):
                    files.append(Path(root) / fn)
        return files

    def _module_to_file(self, module_name: str) -> Path | None:
        """Convert a dotted module name to an expected file path relative
        to the project root. Returns None if the module cannot be mapped
        to a project-local file."""
        parts = module_name.split(".")
        # Check as a package: pkg/__init__.py
        pkg_path = self.project_path.joinpath(*parts, "__init__.py")
        if pkg_path.is_file():
            return pkg_path
        # Check as a module: pkg/mod.py
        mod_path = self.project_path.joinpath(*parts[:-1], parts[-1] + ".py")
        if mod_path.is_file():
            return mod_path
        return None

    def _is_stdlib_or_third_party(self, module_name: str) -> bool:
        """Heuristic: treat top-level names that don't map to local files
        and appear in sys.stdlib_module_names (Python 3.10+) or sys.modules
        as standard-library / third-party (not broken)."""
        top_level = module_name.split(".")[0]
        # Check stdlib set (Python 3.10+)
        stdlib_names = getattr(sys, "stdlib_module_names", None)
        if stdlib_names and top_level in stdlib_names:
            return True
        # Check if already importable (third-party or stdlib)
        if top_level in sys.modules:
            return True
        return False

    # ------------------------------------------------------------------
    # Public analysis methods
    # ------------------------------------------------------------------

    def find_broken_imports(self) -> list[dict[str, Any]]:
        """Scan every .py file for imports that do not resolve to an
        existing file within the project.

        Returns:
            List of dicts with keys: file, line, import_name, reason.
        """
        results: list[dict[str, Any]] = []
        for py_file in self._python_files():
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError as exc:
                results.append(
                    {
                        "file": str(py_file),
                        "line": exc.lineno or 0,
                        "import_name": "",
                        "reason": f"SyntaxError: {exc.msg}",
                    }
                )
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._check_import(py_file, node.lineno, alias.name, results)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._check_import(py_file, node.lineno, node.module, results)
        return results

    def _check_import(
        self, py_file: Path, lineno: int, module_name: str, results: list[dict]
    ) -> None:
        """Append to *results* if *module_name* looks like a local import
        that cannot be resolved."""
        # Skip absolute / stdlib / third-party
        if self._is_stdlib_or_third_party(module_name):
            return
        # Try to resolve locally
        if self._module_to_file(module_name) is None:
            results.append(
                {
                    "file": str(py_file),
                    "line": lineno,
                    "import_name": module_name,
                    "reason": f"Module '{module_name}' not found in project.",
                }
            )

    def find_missing_dependencies(self) -> list[dict[str, Any]]:
        """Read requirements.txt (and requirements/*.txt) and check whether
        each package can be found in site-packages or as a local module.

        Returns:
            List of dicts with keys: package, source_file, reason.
        """
        results: list[dict[str, Any]] = []
        req_files = self._find_requirements_files()
        if not req_files:
            return results

        # Build a set of top-level import names available in the environment
        available = set(sys.modules.keys())
        # Also scan site-packages directories
        for site_dir in sys.path:
            site = Path(site_dir)
            if site.is_dir():
                for entry in site.iterdir():
                    name = entry.name
                    if name.endswith(".dist-info") or name.endswith(".egg-info"):
                        available.add(name.split("-")[0].split(".")[0].lower())
                    elif entry.is_dir():
                        available.add(name.lower())
                    elif name.endswith((".py", ".so", ".pyd")):
                        available.add(name.rsplit(".", 1)[0].lower())

        for req_file in req_files:
            for raw_line in req_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Extract package name (before any version specifier)
                pkg = re.split(r"[=<>!~\[\s;]", line)[0].strip()
                if not pkg:
                    continue
                pkg_lower = pkg.lower().replace("-", "_")
                if pkg_lower not in available and pkg_lower.replace("_", "-") not in available:
                    # Check if it's a local module
                    if self._module_to_file(pkg_lower) is None:
                        results.append(
                            {
                                "package": pkg,
                                "source_file": str(req_file),
                                "reason": f"Package '{pkg}' not found in environment or project.",
                            }
                        )
        return results

    def _find_requirements_files(self) -> list[Path]:
        """Return a list of requirements.txt files found in the project."""
        candidates: list[Path] = []
        # Top-level requirements.txt
        top = self.project_path / "requirements.txt"
        if top.is_file():
            candidates.append(top)
        # requirements/ directory
        req_dir = self.project_path / "requirements"
        if req_dir.is_dir():
            for f in sorted(req_dir.glob("*.txt")):
                candidates.append(f)
        return candidates

    def find_circular_dependencies(self) -> list[dict[str, Any]]:
        """Build an import graph for all .py files in the project and
        detect circular dependencies via DFS.

        Returns:
            List of dicts with key 'cycle' mapping to a list of file paths
            forming the cycle.
        """
        # Build adjacency: file -> [file, ...]
        graph: dict[str, list[str]] = {}
        for py_file in self._python_files():
            graph.setdefault(str(py_file), [])

        for py_file in self._python_files():
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                modules: list[str] = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for mod_name in modules:
                    target = self._module_to_file(mod_name)
                    if target and str(target) in graph and str(target) != str(py_file):
                        graph[str(py_file)].append(str(target))

        # DFS cycle detection
        cycles: list[dict[str, Any]] = []
        visited: set[str] = set()
        on_stack: set[str] = set()
        stack: list[str] = []

        def _dfs(node: str) -> None:
            visited.add(node)
            on_stack.add(node)
            stack.append(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    _dfs(neighbor)
                elif neighbor in on_stack:
                    # Extract the cycle
                    idx = stack.index(neighbor)
                    cycle_files = stack[idx:]
                    cycles.append({"cycle": list(cycle_files)})
            stack.pop()
            on_stack.discard(node)

        for node in graph:
            if node not in visited:
                _dfs(node)

        return cycles

    def find_deprecated_patterns(self) -> list[dict[str, Any]]:
        """Scan all .py files for known deprecated patterns using regex.

        Returns:
            List of dicts with keys: file, line, pattern, suggestion.
        """
        results: list[dict[str, Any]] = []
        compiled = [
            (re.compile(pattern), name, suggestion)
            for pattern, name, suggestion in _DEPRECATED_PATTERNS
        ]
        for py_file in self._python_files():
            try:
                lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for lineno, line in enumerate(lines, start=1):
                for regex, name, suggestion in compiled:
                    if regex.search(line):
                        results.append(
                            {
                                "file": str(py_file),
                                "line": lineno,
                                "pattern": name,
                                "suggestion": suggestion,
                            }
                        )
        return results

    def analyze_repair_goal(self, goal: str) -> dict[str, Any]:
        """Produce a deterministic repair plan for a human-readable goal.

        The goal is matched against known issue categories. The method
        runs the relevant analysis methods and assembles a step-by-step
        repair plan.

        Args:
            goal: A human-readable repair goal string.

        Returns:
            Dict with keys: goal, steps, estimated_risk, requires_approval.
        """
        goal_lower = goal.lower().strip()
        steps: list[dict[str, Any]] = []
        risk = "low"
        requires_approval = False

        # Determine which analyses to run based on keywords in the goal
        run_imports = any(
            kw in goal_lower
            for kw in ["import", "broken", "unresolved", "module", "import error"]
        )
        run_deps = any(
            kw in goal_lower
            for kw in ["depend", "require", "package", "install", "pip", "missing package"]
        )
        run_cycles = any(
            kw in goal_lower
            for kw in ["circular", "cycle", "loop", "import loop"]
        )
        run_deprecated = any(
            kw in goal_lower
            for kw in ["deprecat", "outdated", "legacy", "old", "pattern", "modernize"]
        )

        # If no specific keyword matched, run all analyses
        if not any([run_imports, run_deps, run_cycles, run_deprecated]):
            run_imports = run_deps = run_cycles = run_deprecated = True

        if run_imports:
            broken = self.find_broken_imports()
            for item in broken:
                steps.append(
                    {
                        "action": "fix_import",
                        "file": item["file"],
                        "description": f"Fix import '{item['import_name']}' at line {item['line']}: {item['reason']}",
                        "risk": "medium",
                    }
                )

        if run_deps:
            missing = self.find_missing_dependencies()
            for item in missing:
                steps.append(
                    {
                        "action": "install_dependency",
                        "file": item["source_file"],
                        "description": f"Install missing package '{item['package']}': {item['reason']}",
                        "risk": "low",
                    }
                )

        if run_cycles:
            cycles = self.find_circular_dependencies()
            for item in cycles:
                cycle_str = " -> ".join(item["cycle"])
                steps.append(
                    {
                        "action": "break_cycle",
                        "file": item["cycle"][0] if item["cycle"] else "",
                        "description": f"Break circular dependency: {cycle_str}",
                        "risk": "high",
                    }
                )

        if run_deprecated:
            deprecated = self.find_deprecated_patterns()
            for item in deprecated:
                steps.append(
                    {
                        "action": "replace_pattern",
                        "file": item["file"],
                        "description": f"Replace '{item['pattern']}' at line {item['line']}: {item['suggestion']}",
                        "risk": "low",
                    }
                )

        # Determine overall risk
        risks = [s["risk"] for s in steps]
        if "high" in risks:
            risk = "high"
            requires_approval = True
        elif "medium" in risks:
            risk = "medium"
            requires_approval = True

        if not steps:
            steps.append(
                {
                    "action": "none",
                    "file": "",
                    "description": "No issues found matching the given goal.",
                    "risk": "none",
                }
            )

        return {
            "goal": goal,
            "steps": steps,
            "estimated_risk": risk,
            "requires_approval": requires_approval,
        }
