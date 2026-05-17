"""
Project Understanding Layer (P8) for AI Team System Phase 8.

Builds a deterministic "understanding snapshot" of any imported project.
NO AI/hallucinations -- only file-based detection.

All detection is based on actual file presence and file content reading.
If a file does not exist or cannot be read, the corresponding field
remains at its default value. No guessing, no inference beyond what
the filesystem explicitly shows.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = ["ProjectUnderstanding", "ProjectUnderstandingSnapshot"]


# ---------------------------------------------------------------------------
# Dataclass: ProjectUnderstandingSnapshot
# ---------------------------------------------------------------------------

@dataclass
class ProjectUnderstandingSnapshot:
    """Deterministic snapshot of a project's structure and tooling.

    Every field is derived from file presence or file content inspection.
    No field is ever populated by guesswork or AI inference.
    """

    # -- Tech stack ----------------------------------------------------------
    # Detected from manifest files (package.json, requirements.txt, etc.)
    language: str = ""              # python, javascript, typescript, rust, go, dart, java, unknown
    language_version: str = ""      # e.g. "3.11", "20.5.0" (from manifest if available)
    frameworks: list[str] = field(default_factory=list)
    # e.g. ["react", "fastapi", "next.js"] -- detected from manifest deps
    #     or from framework-specific config files

    # -- Build system --------------------------------------------------------
    # Detected from build config files in project root
    build_system: str = ""          # webpack, vite, rollup, gradle, maven, make, cmake, cargo, go_modules, npm, yarn, pnpm, unknown
    build_config_files: list[str] = field(default_factory=list)
    # e.g. ["webpack.config.js", "vite.config.ts"]

    # -- Test system ---------------------------------------------------------
    # Detected from test config files and test directories
    test_system: str = ""           # pytest, jest, mocha, unittest, junit, vitest, cargo_test, go_test, unknown
    test_config_files: list[str] = field(default_factory=list)
    # e.g. ["jest.config.ts", "pytest.ini"]
    test_directories: list[str] = field(default_factory=list)
    # e.g. ["tests/", "__tests__/"]

    # -- Entry points --------------------------------------------------------
    # Detected from known entry-point filenames
    entry_points: list[str] = field(default_factory=list)
    # e.g. ["main.py", "src/index.ts"]

    # -- Architecture style --------------------------------------------------
    # Detected from directory structure
    architecture_style: str = ""    # monolith, microservices, monorepo, library, unknown

    # -- Code quality signals -----------------------------------------------
    has_type_hints: bool = False    # pyrightconfig.json, tsconfig.json, mypy.ini
    has_linting: bool = False       # .eslintrc*, .pylintrc, ruff.toml, .flake8
    has_formatting: bool = False    # .prettierrc*, pyproject.toml [tool.black], .editorconfig
    has_ci: bool = False            # .github/workflows/, .gitlab-ci.yml, Jenkinsfile
    ci_systems: list[str] = field(default_factory=list)
    # e.g. ["github_actions", "gitlab_ci"]
    lint_config_files: list[str] = field(default_factory=list)
    format_config_files: list[str] = field(default_factory=list)
    type_config_files: list[str] = field(default_factory=list)

    # -- Project type --------------------------------------------------------
    # Derived from the combination of signals above
    project_type: str = "unknown"   # web_app, cli_tool, library, mobile_app, desktop_app, api_service, monorepo, unknown

    # -- Raw signals ---------------------------------------------------------
    # For debugging / transparency: which files were found
    manifest_files: list[str] = field(default_factory=list)
    # e.g. ["package.json", "requirements.txt"]
    root_files: list[str] = field(default_factory=list)
    # All files in project root (basename only)
    root_directories: list[str] = field(default_factory=list)
    # All directories in project root (basename only)


# ---------------------------------------------------------------------------
# Class: ProjectUnderstanding
# ---------------------------------------------------------------------------

class ProjectUnderstanding:
    """Deterministic project analyzer.

    Reads the filesystem, inspects manifest files, and produces a
    ProjectUnderstandingSnapshot with no AI involvement.

    Parameters
    ----------
    None -- this class is stateless. All state lives in the snapshot.

    Usage
    -----
    >>> pu = ProjectUnderstanding()
    >>> snapshot = pu.analyze("/path/to/project")
    >>> summary = pu.get_summary(snapshot)
    """

    # -- Public API ---------------------------------------------------------

    def analyze(self, project_path: str) -> ProjectUnderstandingSnapshot:
        """Analyze *project_path* and return a deterministic snapshot.

        Parameters
        ----------
        project_path : str
            Absolute or relative path to the project root directory.

        Returns
        -------
        ProjectUnderstandingSnapshot
            All fields populated from file inspection only.
        """
        root = Path(project_path).expanduser().resolve()

        if not root.is_dir():
            # Return empty snapshot for non-existent paths
            return ProjectUnderstandingSnapshot()

        snapshot = ProjectUnderstandingSnapshot()

        # Gather raw signals first (used by all detectors)
        snapshot.root_files = self._list_root_files(root)
        snapshot.root_directories = self._list_root_dirs(root)

        # Run all detectors
        self._detect_manifest_files(root, snapshot)
        self._detect_language(root, snapshot)
        self._detect_frameworks(root, snapshot)
        self._detect_build_system(root, snapshot)
        self._detect_test_system(root, snapshot)
        self._detect_entry_points(root, snapshot)
        self._detect_architecture(root, snapshot)
        self._detect_code_quality(root, snapshot)
        self._classify_project_type(root, snapshot)

        return snapshot

    def get_summary(self, snapshot: ProjectUnderstandingSnapshot) -> dict:
        """Convert *snapshot* to a JSON-serializable dict.

        Parameters
        ----------
        snapshot : ProjectUnderstandingSnapshot
            The snapshot to serialize.

        Returns
        -------
        dict
            Plain dict with all snapshot fields, suitable for json.dumps().
        """
        return {
            "language": snapshot.language,
            "language_version": snapshot.language_version,
            "frameworks": snapshot.frameworks,
            "build_system": snapshot.build_system,
            "build_config_files": snapshot.build_config_files,
            "test_system": snapshot.test_system,
            "test_config_files": snapshot.test_config_files,
            "test_directories": snapshot.test_directories,
            "entry_points": snapshot.entry_points,
            "architecture_style": snapshot.architecture_style,
            "has_type_hints": snapshot.has_type_hints,
            "has_linting": snapshot.has_linting,
            "has_formatting": snapshot.has_formatting,
            "has_ci": snapshot.has_ci,
            "ci_systems": snapshot.ci_systems,
            "lint_config_files": snapshot.lint_config_files,
            "format_config_files": snapshot.format_config_files,
            "type_config_files": snapshot.type_config_files,
            "project_type": snapshot.project_type,
            "manifest_files": snapshot.manifest_files,
            "root_files": snapshot.root_files,
            "root_directories": snapshot.root_directories,
        }

    # -- Internal: raw listing helpers --------------------------------------

    @staticmethod
    def _list_root_files(root: Path) -> list[str]:
        """Return basenames of all files in *root* (non-recursive)."""
        try:
            return sorted(
                p.name for p in root.iterdir() if p.is_file()
            )
        except PermissionError:
            return []

    @staticmethod
    def _list_root_dirs(root: Path) -> list[str]:
        """Return basenames of all directories in *root* (non-recursive)."""
        try:
            return sorted(
                p.name for p in root.iterdir() if p.is_dir()
            )
        except PermissionError:
            return []

    @staticmethod
    def _file_exists(root: Path, name: str) -> bool:
        """Check if *name* exists as a file in *root*."""
        return (root / name).is_file()

    @staticmethod
    def _dir_exists(root: Path, name: str) -> bool:
        """Check if *name* exists as a directory in *root*."""
        return (root / name).is_dir()

    @staticmethod
    def _any_file_exists(root: Path, names: list[str]) -> Optional[str]:
        """Return the first name in *names* that exists as a file, or None."""
        for n in names:
            if (root / n).is_file():
                return n
        return None

    @staticmethod
    def _any_dir_exists(root: Path, names: list[str]) -> list[str]:
        """Return all names in *names* that exist as directories."""
        return [n for n in names if (root / n).is_dir()]

    @staticmethod
    def _read_json_safe(root: Path, filename: str) -> Optional[dict]:
        """Read a JSON file and return its dict, or None on any error."""
        path = root / filename
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            return None

    @staticmethod
    def _read_text_lines_safe(root: Path, filename: str) -> list[str]:
        """Read a text file and return lines, or empty list on any error."""
        path = root / filename
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.readlines()
        except (OSError, UnicodeDecodeError):
            return []

    @staticmethod
    def _file_contains(root: Path, filename: str, text: str) -> bool:
        """Check if *filename* contains the string *text* (case-insensitive)."""
        path = root / filename
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().lower()
                return text.lower() in content
        except OSError:
            return False

    @staticmethod
    def _any_file_contains(root: Path, filenames: list[str], text: str) -> bool:
        """Check if any of *filenames* contains *text*."""
        for fn in filenames:
            if ProjectUnderstanding._file_contains(root, fn, text):
                return True
        return False

    # -- Internal: manifest file detection ----------------------------------

    def _detect_manifest_files(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Record which manifest files exist in the project root."""
        known_manifests = [
            "package.json",
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "go.sum",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "pom.xml",
            "pubspec.yaml",
            "Gemfile",
            "composer.json",
            "CMakeLists.txt",
            "Makefile",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            ".nvmrc",
            ".python-version",
            "rust-toolchain.toml",
            "build.zig",
            "Package.swift",
            "mix.exs",
            "rebar.config",
            "stack.yaml",
        ]
        snap.manifest_files = [n for n in known_manifests if self._file_exists(root, n)]

    # -- Internal: language detection ---------------------------------------

    def _detect_language(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect primary language from manifest files."""

        # Python
        if self._any_file_exists(root, ["requirements.txt", "setup.py", "pyproject.toml"]):
            snap.language = "python"
            self._detect_python_version(root, snap)
            return

        # Node.js / JavaScript / TypeScript
        if self._file_exists(root, "package.json"):
            pkg = self._read_json_safe(root, "package.json")
            if pkg:
                # Check for TypeScript dependency
                deps = pkg.get("dependencies", {})
                dev_deps = pkg.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}
                if "typescript" in all_deps:
                    snap.language = "typescript"
                else:
                    snap.language = "javascript"
            else:
                snap.language = "javascript"
            self._detect_node_version(root, snap)
            return

        # Rust
        if self._file_exists(root, "Cargo.toml"):
            snap.language = "rust"
            return

        # Go
        if self._file_exists(root, "go.mod"):
            snap.language = "go"
            return

        # Dart / Flutter
        if self._file_exists(root, "pubspec.yaml"):
            snap.language = "dart"
            return

        # Java / Kotlin / Groovy (Gradle or Maven)
        if self._any_file_exists(root, ["pom.xml", "build.gradle", "build.gradle.kts"]):
            snap.language = "java"
            return

        # Ruby
        if self._file_exists(root, "Gemfile"):
            snap.language = "ruby"
            return

        # PHP
        if self._file_exists(root, "composer.json"):
            snap.language = "php"
            return

        # C / C++ (CMake or Makefile)
        if self._any_file_exists(root, ["CMakeLists.txt", "Makefile"]):
            snap.language = "c_cpp"
            return

        # Swift
        if self._file_exists(root, "Package.swift"):
            snap.language = "swift"
            return

        # Elixir
        if self._file_exists(root, "mix.exs"):
            snap.language = "elixir"
            return

        # Zig
        if self._file_exists(root, "build.zig"):
            snap.language = "zig"
            return

        # Haskell
        if self._file_exists(root, "stack.yaml"):
            snap.language = "haskell"
            return

        # Erlang
        if self._file_exists(root, "rebar.config"):
            snap.language = "erlang"
            return

        # Fallback: detect by file extensions in root
        snap.language = self._detect_language_by_extension(root)

    def _detect_python_version(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Extract Python version from manifest files."""
        # .python-version
        lines = self._read_text_lines_safe(root, ".python-version")
        if lines:
            ver = lines[0].strip()
            if ver:
                snap.language_version = ver
                return

        # pyproject.toml
        if self._file_contains(root, "pyproject.toml", "requires-python"):
            lines = self._read_text_lines_safe(root, "pyproject.toml")
            for line in lines:
                line = line.strip()
                if "requires-python" in line:
                    # Extract version from: requires-python = ">=3.11"
                    parts = line.split("=")
                    if len(parts) >= 2:
                        ver = parts[1].strip().strip('"').strip("'")
                        # Extract just the version number
                        import re
                        m = re.search(r"(\d+\.\d+)", ver)
                        if m:
                            snap.language_version = m.group(1)
                            return

    def _detect_node_version(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Extract Node.js version from package.json or .nvmrc."""
        # .nvmrc
        lines = self._read_text_lines_safe(root, ".nvmrc")
        if lines:
            ver = lines[0].strip()
            if ver:
                snap.language_version = ver.lstrip("v")
                return

        # package.json engines field
        pkg = self._read_json_safe(root, "package.json")
        if pkg and "engines" in pkg:
            node_ver = pkg["engines"].get("node", "")
            if node_ver:
                snap.language_version = node_ver.strip(">=").strip()

    @staticmethod
    def _detect_language_by_extension(root: Path) -> str:
        """Fallback: detect language by counting file extensions in root."""
        ext_counts: dict[str, int] = {}
        try:
            for p in root.iterdir():
                if p.is_file() and p.suffix:
                    ext_counts[p.suffix] = ext_counts.get(p.suffix, 0) + 1
        except PermissionError:
            return "unknown"

        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".rs": "rust",
            ".go": "go",
            ".dart": "dart",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".c": "c_cpp",
            ".cpp": "c_cpp",
            ".h": "c_cpp",
            ".hpp": "c_cpp",
            ".swift": "swift",
            ".ex": "elixir",
            ".exs": "elixir",
            ".zig": "zig",
            ".hs": "haskell",
        }

        best_lang = "unknown"
        best_count = 0
        for ext, lang in ext_to_lang.items():
            count = ext_counts.get(ext, 0)
            if count > best_count:
                best_count = count
                best_lang = lang

        return best_lang if best_count > 0 else "unknown"

    # -- Internal: framework detection --------------------------------------

    def _detect_frameworks(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect frameworks from config files and manifest dependencies."""

        # -- Framework-specific config files --------------------------------
        config_to_framework = {
            # Node.js / JS / TS
            "next.config.js": "next.js",
            "next.config.mjs": "next.js",
            "next.config.ts": "next.js",
            "nuxt.config.js": "nuxt",
            "nuxt.config.ts": "nuxt",
            "svelte.config.js": "svelte",
            "svelte.config.ts": "svelte",
            "astro.config.mjs": "astro",
            "astro.config.js": "astro",
            "astro.config.ts": "astro",
            "remix.config.js": "remix",
            "remix.config.ts": "remix",
            "gatsby-config.js": "gatsby",
            "gatsby-config.ts": "gatsby",
            "gatsby-config.mjs": "gatsby",
            "angular.json": "angular",
            "vue.config.js": "vue",
            "vue.config.ts": "vue",
            "quasar.config.js": "quasar",
            "quasar.config.ts": "quasar",
            "ionic.config.json": "ionic",
            "capacitor.config.ts": "capacitor",
            "capacitor.config.json": "capacitor",
            "expo.config.js": "expo",
            # Python
            "manage.py": "django",
            "app.py": "flask",
            # Rust
            "Cargo.toml": "cargo",
            # Go
            "go.mod": "go_modules",
            # Flutter
            "pubspec.yaml": "flutter",
            # Ruby
            "config.ru": "rack",
            # Elixir
            "mix.exs": "phoenix",
        }

        for config_file, framework in config_to_framework.items():
            if self._file_exists(root, config_file):
                if framework not in snap.frameworks:
                    snap.frameworks.append(framework)

        # -- Detect from package.json dependencies --------------------------
        if self._file_exists(root, "package.json"):
            self._detect_js_frameworks_from_deps(root, snap)

        # -- Detect from requirements.txt -----------------------------------
        if self._file_exists(root, "requirements.txt"):
            self._detect_python_frameworks_from_requirements(root, snap)

        # -- Detect from pyproject.toml -------------------------------------
        if self._file_exists(root, "pyproject.toml"):
            self._detect_python_frameworks_from_pyproject(root, snap)

        # -- Detect from Cargo.toml -----------------------------------------
        if self._file_exists(root, "Cargo.toml"):
            self._detect_rust_frameworks_from_cargo(root, snap)

        # -- Detect from go.mod ---------------------------------------------
        if self._file_exists(root, "go.mod"):
            self._detect_go_frameworks_from_gomod(root, snap)

        # -- Detect from pubspec.yaml ---------------------------------------
        if self._file_exists(root, "pubspec.yaml"):
            self._detect_dart_frameworks_from_pubspec(root, snap)

        snap.frameworks.sort()

    def _detect_js_frameworks_from_deps(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect JS/TS frameworks from package.json dependencies."""
        pkg = self._read_json_safe(root, "package.json")
        if not pkg:
            return

        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}

        dep_to_framework = {
            "react": "react",
            "react-dom": "react",
            "@angular/core": "angular",
            "@angular/common": "angular",
            "vue": "vue",
            "nuxt": "nuxt",
            "next": "next.js",
            "svelte": "svelte",
            "@sveltejs/kit": "sveltekit",
            "@remix-run/react": "remix",
            "@remix-run/node": "remix",
            "gatsby": "gatsby",
            "express": "express",
            "koa": "koa",
            "fastify": "fastify",
            "hapi": "hapi",
            "@nestjs/core": "nestjs",
            "socket.io": "socket.io",
            "electron": "electron",
            "tauri": "tauri",
            "@tauri-apps/api": "tauri",
            "expo": "expo",
            "react-native": "react-native",
            "@ionic/react": "ionic",
            "@ionic/angular": "ionic",
            "@capacitor/core": "capacitor",
            "three": "three.js",
            "phaser": "phaser",
            "pixi.js": "pixi.js",
        }

        for dep_name, framework in dep_to_framework.items():
            if dep_name in all_deps and framework not in snap.frameworks:
                snap.frameworks.append(framework)

    def _detect_python_frameworks_from_requirements(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect Python frameworks from requirements.txt."""
        lines = self._read_text_lines_safe(root, "requirements.txt")
        req_to_framework = {
            "django": "django",
            "flask": "flask",
            "fastapi": "fastapi",
            "tornado": "tornado",
            "bottle": "bottle",
            "pyramid": "pyramid",
            "sanic": "sanic",
            "litestar": "litestar",
            "starlette": "starlette",
            "celery": "celery",
            "sqlalchemy": "sqlalchemy",
            "pydantic": "pydantic",
            "scrapy": "scrapy",
            "streamlit": "streamlit",
            "gradio": "gradio",
            "panel": "panel",
            "dash": "dash",
            "pytest": "pytest",
            "click": "click",
            "typer": "typer",
            "argparse": "argparse",
            "httpx": "httpx",
            "aiohttp": "aiohttp",
            "requests": "requests",
            "scikit-learn": "scikit-learn",
            "tensorflow": "tensorflow",
            "torch": "pytorch",
            "transformers": "huggingface",
            "opencv-python": "opencv",
            "pillow": "pillow",
            "matplotlib": "matplotlib",
            "seaborn": "seaborn",
            "plotly": "plotly",
            "bokeh": "bokeh",
        }

        for line in lines:
            pkg = line.strip().split("==")[0].split(">=")[0].split("<=")[0].split("!=")[0].split("~=")[0].lower()
            if pkg in req_to_framework:
                fw = req_to_framework[pkg]
                if fw not in snap.frameworks:
                    snap.frameworks.append(fw)

    def _detect_python_frameworks_from_pyproject(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect Python frameworks from pyproject.toml dependencies."""
        lines = self._read_text_lines_safe(root, "pyproject.toml")
        req_to_framework = {
            "django": "django",
            "flask": "flask",
            "fastapi": "fastapi",
            "tornado": "tornado",
            "bottle": "bottle",
            "pyramid": "pyramid",
            "sanic": "sanic",
            "litestar": "litestar",
            "starlette": "starlette",
            "celery": "celery",
            "sqlalchemy": "sqlalchemy",
            "pydantic": "pydantic",
            "scrapy": "scrapy",
            "streamlit": "streamlit",
            "gradio": "gradio",
            "click": "click",
            "typer": "typer",
            "httpx": "httpx",
            "aiohttp": "aiohttp",
            "scikit-learn": "scikit-learn",
            "tensorflow": "tensorflow",
            "torch": "pytorch",
            "transformers": "huggingface",
            "opencv-python": "opencv",
            "matplotlib": "matplotlib",
            "plotly": "plotly",
        }

        in_deps = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and "dependenc" in stripped.lower():
                in_deps = True
                continue
            if stripped.startswith("[") and "dependenc" not in stripped.lower():
                in_deps = False
                continue
            if in_deps:
                # Extract package name from lines like: "fastapi>=0.100.0",
                pkg = stripped.strip('"').strip("'").split(">=")[0].split("==")[0].split("<")[0].split(">")[0].split("!=")[0].split("~=")[0].strip().lower()
                if pkg in req_to_framework:
                    fw = req_to_framework[pkg]
                    if fw not in snap.frameworks:
                        snap.frameworks.append(fw)

    def _detect_rust_frameworks_from_cargo(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect Rust frameworks from Cargo.toml dependencies."""
        lines = self._read_text_lines_safe(root, "Cargo.toml")
        dep_to_framework = {
            "actix-web": "actix-web",
            "axum": "axum",
            "rocket": "rocket",
            "warp": "warp",
            "tokio": "tokio",
            "serde": "serde",
            "tower": "tower",
            "tonic": "tonic",
            "diesel": "diesel",
            "sqlx": "sqlx",
            "sea-orm": "sea-orm",
            "tauri": "tauri",
            "bevy": "bevy",
            "yew": "yew",
            "leptos": "leptos",
            "egui": "egui",
            "iced": "iced",
            "clap": "clap",
        }

        in_deps = False
        for line in lines:
            stripped = line.strip()
            if stripped == "[dependencies]" or stripped.startswith("[dependencies."):
                in_deps = True
                continue
            if stripped.startswith("[") and "dependenc" not in stripped:
                in_deps = False
                continue
            if in_deps:
                pkg = stripped.split("=")[0].strip().strip('"').lower()
                if pkg in dep_to_framework:
                    fw = dep_to_framework[pkg]
                    if fw not in snap.frameworks:
                        snap.frameworks.append(fw)

    def _detect_go_frameworks_from_gomod(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect Go frameworks from go.mod imports."""
        lines = self._read_text_lines_safe(root, "go.mod")
        mod_to_framework = {
            "github.com/gin-gonic/gin": "gin",
            "github.com/labstack/echo": "echo",
            "github.com/gofiber/fiber": "fiber",
            "github.com/gorilla/mux": "gorilla-mux",
            "github.com/go-chi/chi": "chi",
            "github.com/revel/revel": "revel",
            "github.com/beego/beego": "beego",
            "github.com/graphql-go/graphql": "graphql-go",
            "github.com/grpc-ecosystem/grpc-gateway": "grpc-gateway",
            "google.golang.org/grpc": "grpc",
        }

        for line in lines:
            stripped = line.strip()
            for mod_path, framework in mod_to_framework.items():
                if mod_path in stripped and framework not in snap.frameworks:
                    snap.frameworks.append(framework)

    def _detect_dart_frameworks_from_pubspec(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect Dart/Flutter frameworks from pubspec.yaml."""
        lines = self._read_text_lines_safe(root, "pubspec.yaml")
        dep_to_framework = {
            "flutter": "flutter",
            "flutter_web_plugins": "flutter_web",
            "riverpod": "riverpod",
            "bloc": "bloc",
            "provider": "provider",
            "get": "getx",
            "dio": "dio",
            "chopper": "chopper",
            "freezed": "freezed",
            "json_serializable": "json_serializable",
        }

        in_deps = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("dependencies:") or stripped.startswith("dev_dependencies:"):
                in_deps = True
                continue
            if not line.startswith(" ") and not line.startswith("\t") and stripped:
                in_deps = False
                continue
            if in_deps:
                pkg = stripped.split(":")[0].strip()
                if pkg in dep_to_framework:
                    fw = dep_to_framework[pkg]
                    if fw not in snap.frameworks:
                        snap.frameworks.append(fw)

    # -- Internal: build system detection -----------------------------------

    def _detect_build_system(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect build system from config files."""

        # Map of (config_file, build_system_name)
        build_configs: list[tuple[list[str], str]] = [
            # JavaScript / TypeScript
            (["webpack.config.js", "webpack.config.ts", "webpack.config.mjs"], "webpack"),
            (["vite.config.js", "vite.config.ts", "vite.config.mjs"], "vite"),
            (["rollup.config.js", "rollup.config.ts", "rollup.config.mjs"], "rollup"),
            (["esbuild.config.js", "esbuild.config.mjs"], "esbuild"),
            (["tsup.config.ts", "tsup.config.js"], "tsup"),
            (["turbo.json"], "turborepo"),
            (["lerna.json"], "lerna"),
            (["nx.json"], "nx"),
            ([".parcelrc", "parcel.config.json"], "parcel"),
            (["snowpack.config.js", "snowpack.config.mjs", "snowpack.config.ts"], "snowpack"),
            # Python
            (["setup.py"], "setuptools"),
            (["setup.cfg"], "setuptools"),
            (["pyproject.toml"], "poetry_or_flit"),
            (["Pipfile"], "pipenv"),
            (["tox.ini"], "tox"),
            (["noxfile.py"], "nox"),
            (["taskfile.yml", "Taskfile.yml"], "taskfile"),
            # Rust
            (["Cargo.toml"], "cargo"),
            # Go
            (["go.mod"], "go_modules"),
            # Java / JVM
            (["pom.xml"], "maven"),
            (["build.gradle"], "gradle"),
            (["build.gradle.kts"], "gradle"),
            # C / C++
            (["CMakeLists.txt"], "cmake"),
            (["Makefile", "makefile", "GNUmakefile"], "make"),
            (["meson.build"], "meson"),
            (["BUILD", "BUILD.bazel", "WORKSPACE"], "bazel"),
            (["SConstruct"], "scons"),
            # .NET
            (["*.csproj"], "dotnet"),
            (["*.fsproj"], "dotnet"),
            # Ruby
            (["Gemfile"], "bundler"),
            (["Rakefile"], "rake"),
            # PHP
            (["composer.json"], "composer"),
            # Dart
            (["pubspec.yaml"], "pub"),
            # Swift
            (["Package.swift"], "swiftpm"),
            # Elixir
            (["mix.exs"], "mix"),
            # Zig
            (["build.zig"], "zig_build"),
            # Haskell
            (["stack.yaml"], "stack"),
            (["cabal.project"], "cabal"),
            # Docker
            (["Dockerfile"], "docker"),
            (["docker-compose.yml", "docker-compose.yaml"], "docker_compose"),
        ]

        detected_systems: list[str] = []
        detected_configs: list[str] = []

        for config_files, system_name in build_configs:
            for cfg in config_files:
                if cfg.startswith("*."):
                    # Glob-like: check by extension
                    ext = cfg.lstrip("*")
                    for f in snap.root_files:
                        if f.endswith(ext):
                            if system_name not in detected_systems:
                                detected_systems.append(system_name)
                            detected_configs.append(f)
                elif self._file_exists(root, cfg):
                    if system_name not in detected_systems:
                        detected_systems.append(system_name)
                    detected_configs.append(cfg)

        # Also detect from package.json scripts
        if self._file_exists(root, "package.json"):
            pkg = self._read_json_safe(root, "package.json")
            if pkg and "scripts" in pkg:
                scripts = pkg["scripts"]
                # Check for common build script patterns
                build_script = scripts.get("build", "")
                if "webpack" in build_script and "webpack" not in detected_systems:
                    detected_systems.append("webpack")
                if "vite" in build_script and "vite" not in detected_systems:
                    detected_systems.append("vite")
                if "rollup" in build_script and "rollup" not in detected_systems:
                    detected_systems.append("rollup")
                if "esbuild" in build_script and "esbuild" not in detected_systems:
                    detected_systems.append("esbuild")
                if "tsc" in build_script and "typescript" not in detected_systems:
                    detected_systems.append("typescript_compiler")

        # Detect npm/yarn/pnpm from lock files
        if self._file_exists(root, "pnpm-lock.yaml"):
            if "pnpm" not in detected_systems:
                detected_systems.append("pnpm")
                detected_configs.append("pnpm-lock.yaml")
        elif self._file_exists(root, "yarn.lock"):
            if "yarn" not in detected_systems:
                detected_systems.append("yarn")
                detected_configs.append("yarn.lock")
        elif self._file_exists(root, "package-lock.json"):
            if "npm" not in detected_systems:
                detected_systems.append("npm")
                detected_configs.append("package-lock.json")

        # Set primary build system (first detected, or most specific)
        snap.build_config_files = sorted(set(detected_configs))
        if detected_systems:
            # Priority: specific build tools over generic package managers
            priority = [
                "webpack", "vite", "rollup", "esbuild", "tsup", "turborepo",
                "lerna", "nx", "parcel", "snowpack",
                "gradle", "maven", "cmake", "make", "meson", "bazel", "scons",
                "cargo", "go_modules", "swiftpm", "mix", "zig_build",
                "setuptools", "poetry_or_flit", "pipenv",
                "dotnet", "bundler", "rake", "composer", "pub",
                "docker", "docker_compose",
                "typescript_compiler",
                "npm", "yarn", "pnpm",
            ]
            for p in priority:
                if p in detected_systems:
                    snap.build_system = p
                    break
            else:
                snap.build_system = detected_systems[0]

    # -- Internal: test system detection ------------------------------------

    def _detect_test_system(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect test framework from config files and test directories."""

        # -- Test config files ----------------------------------------------
        test_config_map: list[tuple[list[str], str]] = [
            # JavaScript / TypeScript
            (["jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.cjs"], "jest"),
            (["vitest.config.js", "vitest.config.ts", "vitest.config.mjs"], "vitest"),
            (["mocha.opts", ".mocharc.json", ".mocharc.yml", ".mocharc.yaml", ".mocharc.js", ".mocharc.cjs"], "mocha"),
            (["karma.conf.js", "karma.conf.ts"], "karma"),
            (["cypress.config.js", "cypress.config.ts", "cypress.config.mjs", "cypress.json"], "cypress"),
            (["playwright.config.js", "playwright.config.ts"], "playwright"),
            (["ava.config.js", "ava.config.mjs", "ava.config.cjs"], "ava"),
            ([".nycrc", ".nycrc.json", "nyc.config.js"], "nyc"),
            # Python
            (["pytest.ini"], "pytest"),
            (["setup.cfg"], "pytest"),  # [tool:pytest] section
            (["tox.ini"], "tox"),
            ([".pytest.ini"], "pytest"),
            (["conftest.py"], "pytest"),
            (["nose2.cfg"], "nose2"),
            ([".nose2.cfg"], "nose2"),
            # Rust -- no config file needed, cargo test is implicit
            # Go -- no config file needed, go test is implicit
            # Java
            (["surefire-reports"], "junit"),
            # Ruby
            ([".rspec", "spec/spec_helper.rb"], "rspec"),
            # PHP
            (["phpunit.xml", "phpunit.xml.dist"], "phpunit"),
            # Elixir
            (["test/test_helper.exs"], "ex_unit"),
        ]

        detected_systems: list[str] = []
        detected_configs: list[str] = []

        for config_files, system_name in test_config_map:
            for cfg in config_files:
                if self._file_exists(root, cfg):
                    if system_name not in detected_systems:
                        detected_systems.append(system_name)
                    detected_configs.append(cfg)

        # -- Test directories -----------------------------------------------
        test_dir_names = [
            "tests", "test", "__tests__", "spec", "specs",
            "e2e", "integration", "unit", "functional",
            "testing", "test_suite", "test-suite",
            "cypress", "playwright",
        ]
        found_test_dirs = self._any_dir_exists(root, test_dir_names)
        snap.test_directories = found_test_dirs

        # -- Detect from package.json devDependencies -----------------------
        if self._file_exists(root, "package.json"):
            pkg = self._read_json_safe(root, "package.json")
            if pkg:
                dev_deps = pkg.get("devDependencies", {})
                dep_to_test = {
                    "jest": "jest",
                    "vitest": "vitest",
                    "mocha": "mocha",
                    "ava": "ava",
                    "karma": "karma",
                    "cypress": "cypress",
                    "@playwright/test": "playwright",
                    "nyc": "nyc",
                    "ts-jest": "jest",
                    "@testing-library/react": "testing-library",
                    "@testing-library/jest-dom": "jest",
                    "@vue/test-utils": "vitest",
                    "jasmine": "jasmine",
                    "qunit": "qunit",
                    "tape": "tape",
                    "sinon": "sinon",
                }
                for dep, test_sys in dep_to_test.items():
                    if dep in dev_deps and test_sys not in detected_systems:
                        detected_systems.append(test_sys)

        # -- Detect from pyproject.toml / requirements.txt ------------------
        if self._file_exists(root, "pyproject.toml"):
            if self._file_contains(root, "pyproject.toml", "pytest") and "pytest" not in detected_systems:
                detected_systems.append("pytest")
            if self._file_contains(root, "pyproject.toml", "hypothesis") and "hypothesis" not in detected_systems:
                detected_systems.append("hypothesis")

        if self._file_exists(root, "requirements.txt"):
            lines = self._read_text_lines_safe(root, "requirements.txt")
            for line in lines:
                pkg = line.strip().split("==")[0].split(">=")[0].lower()
                if pkg == "pytest" and "pytest" not in detected_systems:
                    detected_systems.append("pytest")
                if pkg == "hypothesis" and "hypothesis" not in detected_systems:
                    detected_systems.append("hypothesis")
                if pkg == "nose2" and "nose2" not in detected_systems:
                    detected_systems.append("nose2")
                if pkg == "coverage" and "coverage" not in detected_systems:
                    detected_systems.append("coverage")

        # -- Implicit test systems ------------------------------------------
        # Rust: Cargo.toml exists => cargo test
        if self._file_exists(root, "Cargo.toml") and "cargo_test" not in detected_systems:
            if found_test_dirs or self._file_contains(root, "Cargo.toml", "[dev-dependencies]"):
                detected_systems.append("cargo_test")

        # Go: go.mod exists => go test
        if self._file_exists(root, "go.mod") and "go_test" not in detected_systems:
            # Go uses *_test.go files -- check for any
            if found_test_dirs:
                detected_systems.append("go_test")

        # Python: unittest is built-in, detect from test files
        if snap.language == "python" and "unittest" not in detected_systems:
            if found_test_dirs:
                # Check if test files use unittest patterns
                for td in found_test_dirs:
                    test_dir = root / td
                    try:
                        for f in test_dir.iterdir():
                            if f.is_file() and self._file_contains(root / td, f.name, "unittest"):
                                detected_systems.append("unittest")
                                break
                    except PermissionError:
                        pass

        snap.test_config_files = sorted(set(detected_configs))
        if detected_systems:
            snap.test_system = detected_systems[0]

    # -- Internal: entry point detection ------------------------------------

    def _detect_entry_points(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect entry point files from known patterns."""

        # Known entry point filenames (checked in root and common subdirs)
        entry_point_names = [
            # Python
            "main.py", "app.py", "server.py", "manage.py", "run.py",
            "wsgi.py", "asgi.py", "cli.py", "__main__.py", "__init__.py",
            # JavaScript / TypeScript
            "index.js", "index.ts", "index.mjs", "index.cjs",
            "main.js", "main.ts", "main.mjs",
            "app.js", "app.ts", "app.mjs",
            "server.js", "server.ts", "server.mjs",
            "cli.js", "cli.ts",
            # Go
            "main.go",
            # Rust
            "main.rs", "lib.rs",
            # Java
            "Main.java", "Application.java",
            # Ruby
            "main.rb", "app.rb", "server.rb",
            # PHP
            "index.php",
            # Swift
            "main.swift",
            # Elixir
            "application.ex",
            # C / C++
            "main.c", "main.cpp",
        ]

        # Check in root
        for ep in entry_point_names:
            if self._file_exists(root, ep):
                snap.entry_points.append(ep)

        # Check in common source directories
        src_dirs = ["src", "app", "lib", "bin", "cmd", "source", "sources"]
        for src_dir in src_dirs:
            if self._dir_exists(root, src_dir):
                src_path = root / src_dir
                for ep in entry_point_names:
                    if (src_path / ep).is_file():
                        snap.entry_points.append(f"{src_dir}/{ep}")

        # For Go: any file with 'package main' in cmd/ directory
        if self._dir_exists(root, "cmd"):
            cmd_path = root / "cmd"
            try:
                for p in cmd_path.rglob("*.go"):
                    if p.is_file() and self._file_contains(cmd_path, str(p.relative_to(cmd_path)), "package main"):
                        rel = str(p.relative_to(root))
                        if rel not in snap.entry_points:
                            snap.entry_points.append(rel)
            except PermissionError:
                pass

        # For Rust: src/main.rs or src/bin/*.rs
        if self._file_exists(root, "src/main.rs"):
            ep = "src/main.rs"
            if ep not in snap.entry_points:
                snap.entry_points.append(ep)

        snap.entry_points.sort()

    # -- Internal: architecture detection -----------------------------------

    def _detect_architecture(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect architecture style from directory structure."""

        dirs = snap.root_directories

        # Monorepo indicators
        monorepo_dirs = ["packages", "apps", "libs", "modules"]
        if any(d in dirs for d in monorepo_dirs):
            # Check if there are multiple sub-projects
            count = 0
            for md in monorepo_dirs:
                md_path = root / md
                if md_path.is_dir():
                    try:
                        subdirs = [d for d in md_path.iterdir() if d.is_dir()]
                        count += len(subdirs)
                    except PermissionError:
                        pass
            if count >= 2:
                snap.architecture_style = "monorepo"
                return

        # Microservices indicators
        service_indicators = ["services", "microservices", "svc", "api", "backend", "frontend"]
        service_count = 0
        for si in service_indicators:
            si_path = root / si
            if si_path.is_dir():
                try:
                    subdirs = [d for d in si_path.iterdir() if d.is_dir()]
                    service_count += len(subdirs)
                except PermissionError:
                    pass

        # Also check for docker-compose with multiple services
        if self._file_exists(root, "docker-compose.yml") or self._file_exists(root, "docker-compose.yaml"):
            compose_file = "docker-compose.yml" if self._file_exists(root, "docker-compose.yml") else "docker-compose.yaml"
            if self._file_contains(root, compose_file, "services:"):
                service_count += 1  # At least one service defined

        if service_count >= 2:
            snap.architecture_style = "microservices"
            return

        # Library indicators
        if self._dir_exists(root, "src") and self._any_file_exists(root, ["setup.py", "pyproject.toml", "package.json"]):
            snap.architecture_style = "library"
            return

        # Single src/ directory without monorepo structure = monolith
        if self._dir_exists(root, "src") or self._dir_exists(root, "app"):
            snap.architecture_style = "monolith"
            return

        # Check for any source directory with code files
        has_source = False
        for d in dirs:
            d_path = root / d
            if d_path.is_dir() and not d.startswith(".") and d not in ("node_modules", "venv", ".git", "__pycache__", ".cache"):
                try:
                    for f in d_path.iterdir():
                        if f.is_file() and f.suffix in (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php", ".swift", ".dart", ".c", ".cpp", ".h", ".hpp"):
                            has_source = True
                            break
                except PermissionError:
                    pass
            if has_source:
                break

        if has_source:
            snap.architecture_style = "monolith"

    # -- Internal: code quality detection -----------------------------------

    def _detect_code_quality(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Detect code quality tooling from config files."""

        # -- Type hints / type checking -------------------------------------
        type_configs = [
            "pyrightconfig.json",
            "tsconfig.json",
            "tsconfig.build.json",
            "mypy.ini",
            ".mypy.ini",
            "mypy.cfg",
        ]
        for tc in type_configs:
            if self._file_exists(root, tc):
                snap.has_type_hints = True
                snap.type_config_files.append(tc)

        # -- Linting --------------------------------------------------------
        lint_configs = [
            # JavaScript / TypeScript
            ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
            ".eslintrc.yaml", ".eslintrc.yml",
            ".eslintignore",
            # Python
            ".pylintrc", "pylintrc", "pylint.cfg",
            "ruff.toml", ".ruff.toml",
            ".flake8", "setup.cfg",  # [flake8] section
            "pyproject.toml",  # [tool.ruff] or [tool.flake8] section
            # Rust (clippy is built-in, but check for config)
            ".clippy.toml", "clippy.toml",
            # Go
            ".golangci.yml", ".golangci.yaml", ".golangci.toml",
            # Ruby
            ".rubocop.yml",
            # PHP
            ".phpcs.xml", "phpcs.xml", "phpunit.xml",
            # General
            ".editorconfig",
        ]
        for lc in lint_configs:
            if self._file_exists(root, lc):
                snap.has_linting = True
                snap.lint_config_files.append(lc)

        # Check pyproject.toml for ruff/flake8 sections
        if self._file_exists(root, "pyproject.toml"):
            if self._file_contains(root, "pyproject.toml", "[tool.ruff]"):
                snap.has_linting = True
                if "pyproject.toml" not in snap.lint_config_files:
                    snap.lint_config_files.append("pyproject.toml")
            if self._file_contains(root, "pyproject.toml", "[tool.flake8]"):
                snap.has_linting = True
                if "pyproject.toml" not in snap.lint_config_files:
                    snap.lint_config_files.append("pyproject.toml")

        # -- Formatting -----------------------------------------------------
        format_configs = [
            ".prettierrc", ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.yml",
            ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.mjs",
            "prettier.config.js", "prettier.config.cjs",
            ".prettierignore",
            ".editorconfig",
            ".black", "pyproject.toml",  # [tool.black]
            "isort.cfg", ".isort.cfg",
            ".stylua.toml", "stylua.toml",
        ]
        for fc in format_configs:
            if self._file_exists(root, fc):
                snap.has_formatting = True
                snap.format_config_files.append(fc)

        # Check pyproject.toml for black/isort sections
        if self._file_exists(root, "pyproject.toml"):
            if self._file_contains(root, "pyproject.toml", "[tool.black]"):
                snap.has_formatting = True
                if "pyproject.toml" not in snap.format_config_files:
                    snap.format_config_files.append("pyproject.toml")
            if self._file_contains(root, "pyproject.toml", "[tool.isort]"):
                snap.has_formatting = True
                if "pyproject.toml" not in snap.format_config_files:
                    snap.format_config_files.append("pyproject.toml")

        # -- CI/CD ----------------------------------------------------------
        ci_paths = [
            (".github/workflows", "github_actions"),
            (".gitlab-ci.yml", "gitlab_ci"),
            ("Jenkinsfile", "jenkins"),
            (".travis.yml", "travis_ci"),
            (".circleci", "circleci"),
            ("azure-pipelines.yml", "azure_pipelines"),
            ("bitbucket-pipelines.yml", "bitbucket_pipelines"),
            (".drone.yml", "drone_ci"),
            ("netlify.toml", "netlify"),
            ("vercel.json", "vercel"),
            ("heroku.yml", "heroku"),
            ("appveyor.yml", "appveyor"),
            (".buildkite", "buildkite"),
            ("taskfile.yml", "taskfile_ci"),
            ("Earthfile", "earthly"),
            ("Dockerfile", "docker"),
        ]
        for ci_path, ci_name in ci_paths:
            if ci_path.startswith("."):
                # Directory or file
                if self._dir_exists(root, ci_path) or self._file_exists(root, ci_path):
                    snap.has_ci = True
                    snap.ci_systems.append(ci_name)
            elif self._file_exists(root, ci_path):
                snap.has_ci = True
                snap.ci_systems.append(ci_name)

        snap.type_config_files.sort()
        snap.lint_config_files.sort()
        snap.format_config_files.sort()
        snap.ci_systems.sort()

    # -- Internal: project type classification ------------------------------

    def _classify_project_type(self, root: Path, snap: ProjectUnderstandingSnapshot) -> None:
        """Classify the project type based on all detected signals.

        This is the final classification step that combines all previously
        detected signals to determine the most specific project type.
        """

        # Monorepo takes precedence
        if snap.architecture_style == "monorepo":
            snap.project_type = "monorepo"
            return

        # Mobile app detection
        mobile_signals = [
            "react-native", "flutter", "expo", "ionic", "capacitor",
            "xamarin", "cordova", "nativescript",
        ]
        if any(fw in snap.frameworks for fw in mobile_signals):
            snap.project_type = "mobile_app"
            return

        # Desktop app detection
        desktop_signals = ["electron", "tauri", "wails", "qt", "gtk", "wxwidgets", "egui", "iced"]
        if any(fw in snap.frameworks for fw in desktop_signals):
            snap.project_type = "desktop_app"
            return

        # Library detection
        if snap.architecture_style == "library":
            snap.project_type = "library"
            return

        # Check for library indicators: setup.py/pyproject.toml with name + src/
        if self._any_file_exists(root, ["setup.py", "pyproject.toml"]) and self._dir_exists(root, "src"):
            snap.project_type = "library"
            return

        # API service detection
        api_frameworks = ["fastapi", "flask", "express", "koa", "fastify", "nestjs",
                          "actix-web", "axum", "rocket", "warp", "gin", "echo", "fiber",
                          "chi", "revel", "beego", "rack", "sinatra", "phoenix"]
        if any(fw in snap.frameworks for fw in api_frameworks):
            # Check if it's primarily an API (no heavy frontend framework)
            frontend_frameworks = ["react", "vue", "angular", "svelte", "sveltekit",
                                   "next.js", "nuxt", "gatsby", "remix", "astro"]
            has_frontend = any(fw in snap.frameworks for fw in frontend_frameworks)
            if not has_frontend:
                snap.project_type = "api_service"
                return

        # Web app detection
        web_frameworks = ["react", "vue", "angular", "svelte", "sveltekit", "next.js",
                          "nuxt", "gatsby", "remix", "astro", "django", "rails",
                          "laravel", "spring", "phoenix", "streamlit", "gradio",
                          "dash", "panel"]
        if any(fw in snap.frameworks for fw in web_frameworks):
            snap.project_type = "web_app"
            return

        # CLI tool detection
        cli_frameworks = ["click", "typer", "argparse", "commander", "yargs", "clap",
                          "cobra", "urfave", "picocli"]
        if any(fw in snap.frameworks for fw in cli_frameworks):
            snap.project_type = "cli_tool"
            return

        # Check for CLI indicators: bin/ or cmd/ directory with executables
        if self._dir_exists(root, "bin") or self._dir_exists(root, "cmd"):
            snap.project_type = "cli_tool"
            return

        # If we have a language but couldn't classify further
        if snap.language and snap.language != "unknown":
            # Default to web_app if there's a web-like structure
            if self._any_dir_exists(root, ["public", "static", "assets", "templates", "views"]):
                snap.project_type = "web_app"
                return
            # Default to api_service if there's an api-like structure
            if self._any_dir_exists(root, ["api", "routes", "controllers", "endpoints", "handlers"]):
                snap.project_type = "api_service"
                return
            # If it has tests and source code, it's likely a library
            if snap.test_system and self._dir_exists(root, "src"):
                snap.project_type = "library"
                return

        # If we have at least some code, default to web_app
        if snap.language and snap.language != "unknown":
            snap.project_type = "web_app"
