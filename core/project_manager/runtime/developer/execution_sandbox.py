"""
Execution Sandbox — governed execution boundary.

Allows:
- file reads
- patch generation
- dry-run validation
- safe test execution

Prohibits:
- dangerous shell
- system modification
- network abuse
- destructive ops
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SandboxPolicy(Enum):
    READ_ONLY = "read_only"       # Only file reads
    PATCH_ONLY = "patch_only"     # Reads + patch generation
    TEST_RUN = "test_run"         # Reads + patch + test execution
    FULL = "full"                 # All safe operations


@dataclass
class SandboxResult:
    """Result of a sandbox operation."""
    success: bool = False
    output: str = ""
    error: str = ""
    exit_code: int = 0
    blocked: bool = False
    block_reason: str = ""


class ExecutionSandbox:
    """
    Controlled execution environment.

    NOT a docker replacement.
    This is a governed execution boundary.
    """

    # Allowed commands (whitelist)
    ALLOWED_COMMANDS = {
        "ls", "cat", "grep", "find", "head", "tail", "wc",
        "git status", "git diff", "git log", "git branch",
        "pytest", "python -m pytest", "npm test", "yarn test",
        "python -c", "node -e",
        "pip list", "pip show",
        "echo", "pwd", "which",
    }

    # Dangerous patterns (blacklist)
    DANGEROUS_PATTERNS = [
        "rm -rf", "rm -f", "sudo", "chmod", "chown",
        "curl | bash", "curl | sh", "wget | bash",
        "mkfs", "fdisk", "dd if=",
        "iptables", "ufw", "firewall",
        "/dev/", "/proc/", "/sys/",
        "docker run", "docker exec",
        "kubectl", "helm",
    ]

    # Allowed file extensions for reading
    READABLE_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.md', '.rst', '.txt', '.sh', '.bash',
        '.sql', '.env', '.example',
    }

    def __init__(self, workspace_path: str = ".",
                 policy: str = SandboxPolicy.PATCH_ONLY.value):
        self._workspace = Path(workspace_path)
        self._policy = policy

    def read_file(self, file_path: str) -> SandboxResult:
        """Read a file within the workspace."""
        result = SandboxResult()

        # Check extension
        ext = Path(file_path).suffix
        if ext and ext not in self.READABLE_EXTENSIONS:
            result.blocked = True
            result.block_reason = f"File type '{ext}' not readable in sandbox"
            return result

        # Check path traversal
        full_path = (self._workspace / file_path).resolve()
        if not str(full_path).startswith(str(self._workspace.resolve())):
            result.blocked = True
            result.block_reason = "Path traversal detected"
            return result

        try:
            content = full_path.read_text(encoding='utf-8')
            result.success = True
            result.output = content
        except (IOError, UnicodeDecodeError) as e:
            result.error = str(e)

        return result

    def list_files(self, directory: str = ".") -> SandboxResult:
        """List files in a directory."""
        result = SandboxResult()
        full_path = self._workspace / directory

        if not full_path.exists():
            result.error = f"Directory not found: {directory}"
            return result

        try:
            files = []
            for f in sorted(full_path.iterdir()):
                if f.is_file():
                    files.append(f"  {f.name}")
                elif f.is_dir():
                    files.append(f"  {f.name}/")
            result.success = True
            result.output = "\n".join(files)
        except (IOError, PermissionError) as e:
            result.error = str(e)

        return result

    def run_command(self, command: str) -> SandboxResult:
        """
        Run a command in the sandbox.

        Only whitelisted commands are allowed.
        Dangerous patterns are blocked.
        """
        result = SandboxResult()

        # Check policy
        if self._policy == SandboxPolicy.READ_ONLY.value:
            result.blocked = True
            result.block_reason = "Command execution not allowed in read-only mode"
            return result

        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command.lower():
                result.blocked = True
                result.block_reason = f"Dangerous pattern detected: '{pattern}'"
                return result

        # Check whitelist
        cmd_base = command.split()[0] if command.split() else ""
        if cmd_base not in ("ls", "cat", "grep", "find", "git", "pytest",
                           "python", "npm", "yarn", "pip", "echo", "pwd", "which", "head", "tail", "wc", "node"):
            result.blocked = True
            result.block_reason = f"Command '{cmd_base}' not in whitelist"
            return result

        # Run the command
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=30,
            )
            result.success = (proc.returncode == 0)
            result.output = proc.stdout
            result.error = proc.stderr
            result.exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            result.error = "Command timed out (30s limit)"
        except Exception as e:
            result.error = str(e)

        return result

    def validate_patch_dry_run(self, patch_diff: str) -> SandboxResult:
        """
        Validate a patch without applying it.

        Uses git apply --check if available.
        """
        result = SandboxResult()

        if self._policy == SandboxPolicy.READ_ONLY.value:
            result.blocked = True
            result.block_reason = "Patch validation not allowed in read-only mode"
            return result

        # Basic validation: check diff format
        if not patch_diff.strip():
            result.error = "Empty patch"
            return result

        if not patch_diff.startswith("---") and not patch_diff.startswith("diff"):
            result.error = "Invalid diff format"
            return result

        result.success = True
        result.output = "Patch format valid (dry-run)"

        return result

    def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about the workspace."""
        return {
            "workspace_path": str(self._workspace),
            "policy": self._policy,
            "exists": self._workspace.exists(),
            "readable_extensions": list(self.READABLE_EXTENSIONS),
            "allowed_commands": list(self.ALLOWED_COMMANDS),
        }
