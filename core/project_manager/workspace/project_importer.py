"""
Universal Project Import Module (P1) for AI Team System Phase 8.

Handles importing projects from multiple sources:
  - Local folder attach (validate path exists)
  - GitHub clone (full or shallow via subprocess)
  - Zip archive import (extract to target directory)
  - Partial/shallow repo import (--depth 1 --filter=blob:none)

All operations are deterministic — no AI speculation, just file operations.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

__all__ = ["ProjectImporter"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROJECTS_DIR = Path.home() / "projects"

GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)
GITHUB_SHORT_RE = re.compile(
    r"^github:(?P<owner>[^/]+)/(?P<repo>[^/]+)$"
)


# ---------------------------------------------------------------------------
# ProjectImporter
# ---------------------------------------------------------------------------


class ProjectImporter:
    """Import projects from local paths, GitHub repos, or zip archives.

    All methods return a dict with at minimum an ``"errors"`` key (list of
    strings).  On success ``errors`` is empty; on failure it contains
    human-readable descriptions of what went wrong.

    Parameters
    ----------
    projects_dir : Path or str, optional
        Root directory under which imported projects are placed.
        Defaults to ``~/projects/``.
    """

    def __init__(self, projects_dir: Optional[Path | str] = None) -> None:
        self.projects_dir = Path(projects_dir or DEFAULT_PROJECTS_DIR).expanduser()
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def import_project(
        self,
        source: str,
        project_name: Optional[str] = None,
    ) -> dict:
        """Import a project from *source*.

        Parameters
        ----------
        source : str
            - Local filesystem path (e.g. ``/home/user/myapp``)
            - GitHub short form (e.g. ``github:owner/repo``)
            - GitHub URL (e.g. ``https://github.com/owner/repo``)
            - Path to a ``.zip`` archive
        project_name : str, optional
            Override the directory name for the imported project.  If
            ``None`` a name is derived from the source.

        Returns
        -------
        dict
            ``{
                "project_path": str | None,
                "source_type": str,
                "import_time": float,   # seconds elapsed
                "file_count": int,
                "errors": list[str],
            }``
        """
        start = time.monotonic()
        source_type = self.detect_source_type(source)

        result: dict = {
            "project_path": None,
            "source_type": source_type,
            "import_time": 0.0,
            "file_count": 0,
            "errors": [],
        }

        try:
            if source_type == "local":
                result = self._import_local(source, project_name, result)
            elif source_type == "github":
                result = self._import_github(source, project_name, shallow=False, result=result)
            elif source_type == "url":
                # Treat generic URLs as GitHub URLs for now
                result = self._import_github(source, project_name, shallow=False, result=result)
            elif source_type == "zip":
                result = self._import_zip(source, project_name, result)
            else:
                result["errors"].append(
                    f"Cannot import: unrecognised source type for '{source}'"
                )
        except Exception as exc:  # noqa: BLE001 – catch-all for graceful reporting
            result["errors"].append(f"Unexpected error: {exc}")

        result["import_time"] = round(time.monotonic() - start, 3)
        return result

    def detect_source_type(self, source: str) -> str:
        """Detect the type of *source*.

        Returns one of ``"local"``, ``"github"``, ``"zip"``, ``"url"``,
        or ``"unknown"``.
        """
        source = source.strip()

        # Zip file
        if source.lower().endswith(".zip") and len(source) > 4:
            return "zip"

        # GitHub short form  github:owner/repo
        if GITHUB_SHORT_RE.match(source):
            return "github"

        # GitHub URL
        if GITHUB_URL_RE.match(source):
            return "github"

        # Generic HTTP(S) URL
        if source.startswith(("http://", "https://")):
            return "url"

        # Local path – check existence
        if Path(source).expanduser().exists():
            return "local"

        return "unknown"

    def clone_github(
        self,
        repo_url: str,
        target_dir: str,
        shallow: bool = True,
    ) -> dict:
        """Clone a GitHub repository via ``git clone``.

        Parameters
        ----------
        repo_url : str
            Full HTTPS URL of the repository.
        target_dir : str
            Destination directory for the clone.
        shallow : bool
            If ``True`` (default) use ``--depth 1 --filter=blob:none``
            for a partial clone.

        Returns
        -------
        dict
            ``{"project_path": str, "file_count": int, "errors": list[str]}``
        """
        errors: list[str] = []
        file_count = 0
        target = Path(target_dir)

        cmd = ["git", "clone"]
        if shallow:
            cmd += ["--depth", "1", "--filter=blob:none"]
        cmd += [repo_url, str(target)]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode != 0:
                errors.append(
                    f"git clone failed (exit {proc.returncode}): {proc.stderr.strip()}"
                )
            else:
                file_count = self._count_files(target)
        except FileNotFoundError:
            errors.append("git executable not found on PATH")
        except subprocess.TimeoutExpired:
            errors.append("git clone timed out after 300 s")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"git clone error: {exc}")

        return {
            "project_path": str(target) if not errors else None,
            "file_count": file_count,
            "errors": errors,
        }

    def extract_zip(self, zip_path: str, target_dir: str) -> dict:
        """Extract a zip archive into *target_dir*.

        Parameters
        ----------
        zip_path : str
            Path to the ``.zip`` file.
        target_dir : str
            Directory to extract into (created if it does not exist).

        Returns
        -------
        dict
            ``{"project_path": str, "file_count": int, "errors": list[str]}``
        """
        errors: list[str] = []
        file_count = 0
        zp = Path(zip_path).expanduser()
        target = Path(target_dir)

        if not zp.is_file():
            errors.append(f"Zip file not found: {zp}")
            return {"project_path": None, "file_count": 0, "errors": errors}

        try:
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zp, "r") as zf:
                # Safety: reject paths that escape the target directory
                for member in zf.namelist():
                    member_path = (target / member).resolve()
                    if not member_path.is_relative_to(target.resolve()):
                        errors.append(f"Zip slip detected for member: {member}")
                        return {
                            "project_path": None,
                            "file_count": 0,
                            "errors": errors,
                        }
                zf.extractall(str(target))
            file_count = self._count_files(target)
        except zipfile.BadZipFile:
            errors.append(f"Not a valid zip file: {zp}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Zip extraction error: {exc}")

        return {
            "project_path": str(target) if not errors else None,
            "file_count": file_count,
            "errors": errors,
        }

    def validate_imported_project(self, project_path: str) -> dict:
        """Validate the structure of an imported project.

        Checks performed:
          - Path exists and is a directory
          - Directory is not empty
          - No broken symlinks
          - At least one non-hidden file exists

        Parameters
        ----------
        project_path : str
            Path to the imported project root.

        Returns
        -------
        dict
            ``{
                "valid": bool,
                "project_path": str,
                "file_count": int,
                "empty_dirs": list[str],
                "broken_symlinks": list[str],
                "errors": list[str],
            }``
        """
        errors: list[str] = []
        empty_dirs: list[str] = []
        broken_symlinks: list[str] = []
        file_count = 0
        pp = Path(project_path)

        if not pp.exists():
            errors.append(f"Project path does not exist: {pp}")
            return self._validation_result(False, pp, 0, [], [], errors)

        if not pp.is_dir():
            errors.append(f"Project path is not a directory: {pp}")
            return self._validation_result(False, pp, 0, [], [], errors)

        # Walk the tree
        all_files = []
        for root, dirs, files in os.walk(pp, followlinks=False):
            root_path = Path(root)
            for d in dirs:
                dir_path = root_path / d
                if dir_path.is_symlink() and not dir_path.exists():
                    broken_symlinks.append(str(dir_path))
            for f in files:
                fp = root_path / f
                if fp.is_symlink() and not fp.exists():
                    broken_symlinks.append(str(fp))
                else:
                    all_files.append(fp)

        file_count = len(all_files)

        if file_count == 0:
            errors.append("Project directory is empty (no files found)")

        # Check for empty sub-directories
        for root, dirs, files in os.walk(pp):
            root_path = Path(root)
            # Skip if it has files at this level
            if files:
                continue
            # Check if sub-dirs are all empty (leaf empty dirs)
            has_sub_files = any(
                list((root_path / d).rglob("*")) for d in dirs
            )
            if not has_sub_files and dirs:
                continue  # will be caught deeper
            if not files and not dirs:
                empty_dirs.append(str(root_path))

        # Check for at least one non-hidden file
        non_hidden = [f for f in all_files if not f.name.startswith(".")]
        if not non_hidden and file_count > 0:
            errors.append("Project contains only hidden files")

        is_valid = len(errors) == 0
        return self._validation_result(
            is_valid, pp, file_count, empty_dirs, broken_symlinks, errors
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _import_local(
        self,
        source: str,
        project_name: Optional[str],
        result: dict,
    ) -> dict:
        """Handle local folder attach."""
        src = Path(source).expanduser().resolve()
        if not src.exists():
            result["errors"].append(f"Local path does not exist: {src}")
            return result
        if not src.is_dir():
            result["errors"].append(f"Local path is not a directory: {src}")
            return result

        name = project_name or src.name
        dest = self.projects_dir / name

        if dest.exists():
            result["errors"].append(
                f"Destination already exists: {dest}. Choose a different project_name."
            )
            return result

        try:
            shutil.copytree(src, dest)
            result["project_path"] = str(dest)
            result["file_count"] = self._count_files(dest)
        except Exception as exc:  # noqa: BLE001
            result["errors"].append(f"Failed to copy local project: {exc}")

        return result

    def _import_github(
        self,
        source: str,
        project_name: Optional[str],
        shallow: bool,
        result: dict,
    ) -> dict:
        """Handle GitHub clone (short form or URL)."""
        repo_url = self._resolve_github_url(source)
        if repo_url is None:
            result["errors"].append(f"Could not resolve GitHub URL from: {source}")
            return result

        # Derive project name from repo name
        repo_name = repo_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        name = project_name or repo_name
        dest = self.projects_dir / name

        if dest.exists():
            result["errors"].append(
                f"Destination already exists: {dest}. Choose a different project_name."
            )
            return result

        clone_result = self.clone_github(repo_url, str(dest), shallow=shallow)
        result["project_path"] = clone_result["project_path"]
        result["file_count"] = clone_result["file_count"]
        result["errors"] = clone_result["errors"]
        return result

    def _import_zip(
        self,
        source: str,
        project_name: Optional[str],
        result: dict,
    ) -> dict:
        """Handle zip archive import."""
        zp = Path(source).expanduser()
        if not zp.is_file():
            result["errors"].append(f"Zip file not found: {zp}")
            return result

        name = project_name or zp.stem
        dest = self.projects_dir / name

        if dest.exists():
            result["errors"].append(
                f"Destination already exists: {dest}. Choose a different project_name."
            )
            return result

        extract_result = self.extract_zip(str(zp), str(dest))
        result["project_path"] = extract_result["project_path"]
        result["file_count"] = extract_result["file_count"]
        result["errors"] = extract_result["errors"]
        return result

    # ------------------------------------------------------------------
    # Static / class helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_github_url(source: str) -> Optional[str]:
        """Convert a GitHub short form or URL to a full HTTPS clone URL."""
        m = GITHUB_SHORT_RE.match(source.strip())
        if m:
            return f"https://github.com/{m.group('owner')}/{m.group('repo')}.git"
        m = GITHUB_URL_RE.match(source.strip())
        if m:
            return f"https://github.com/{m.group('owner')}/{m.group('repo')}.git"
        return None

    @staticmethod
    def _count_files(path: Path) -> int:
        """Return the number of regular files under *path* (recursive)."""
        if not path.exists():
            return 0
        return sum(1 for _ in path.rglob("*") if _.is_file())

    @staticmethod
    def _validation_result(
        valid: bool,
        project_path: Path,
        file_count: int,
        empty_dirs: list[str],
        broken_symlinks: list[str],
        errors: list[str],
    ) -> dict:
        return {
            "valid": valid,
            "project_path": str(project_path),
            "file_count": file_count,
            "empty_dirs": empty_dirs,
            "broken_symlinks": broken_symlinks,
            "errors": errors,
        }
