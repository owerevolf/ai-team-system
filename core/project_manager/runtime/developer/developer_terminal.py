"""
Developer Terminal — safe terminal abstraction.

NOT raw shell freedom.
A governed tool with whitelist/blacklist.

Allowed:
- ls, cat, grep, find
- git status, git diff, git log
- pytest, npm test
- pip list, pip show

Prohibited:
- rm -rf, sudo, chmod
- curl | bash
- docker, kubectl
- unrestricted shell
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TerminalCommand:
    """A terminal command with metadata."""
    command: str = ""
    allowed: bool = False
    block_reason: str = ""
    output: str = ""
    exit_code: int = 0


class DeveloperTerminal:
    """
    Safe terminal abstraction for Developer Mode.

    All commands go through whitelist/blacklist validation.
    """

    ALLOWED_COMMANDS = {
        "ls", "cat", "grep", "find", "head", "tail", "wc", "sort", "uniq",
        "git status", "git diff", "git log", "git branch", "git show",
        "pytest", "python -m pytest", "npm test", "yarn test",
        "pip list", "pip show", "pip freeze",
        "echo", "pwd", "which", "whoami", "date",
        "python --version", "node --version", "npm --version",
        "tree", "du -sh", "df -h",
    }

    DANGEROUS_PATTERNS = [
        "rm -rf", "rm -f", "sudo", "chmod", "chown", "chgrp",
        "curl | bash", "curl | sh", "wget | bash", "wget | sh",
        "mkfs", "fdisk", "dd if=", "dd of=",
        "iptables", "ufw", "firewall-cmd",
        "/dev/", "/proc/", "/sys/",
        "docker", "docker-compose", "kubectl", "helm",
        "apt-get", "yum", "dnf", "pacman",
        "systemctl", "service",
        "crontab", "at ",
        "nc ", "ncat", "netcat",
        "python -c 'import os; os.system",
        "eval(", "exec(",
    ]

    def __init__(self, working_dir: str = ".", timeout: int = 30):
        self._working_dir = working_dir
        self._timeout = timeout
        self._history: List[TerminalCommand] = []

    def validate_command(self, command: str) -> TerminalCommand:
        """Validate a command against whitelist/blacklist."""
        cmd = TerminalCommand(command=command)

        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in command.lower():
                cmd.block_reason = f"Dangerous pattern: '{pattern}'"
                self._history.append(cmd)
                return cmd

        # Check whitelist
        cmd_base = command.strip().split()[0] if command.strip() else ""
        whitelisted_bases = {"ls", "cat", "grep", "find", "head", "tail",
                            "wc", "sort", "uniq", "git", "pytest", "python",
                            "npm", "yarn", "pip", "echo", "pwd", "which",
                            "whoami", "date", "node", "tree", "du", "df"}

        if cmd_base not in whitelisted_bases:
            cmd.block_reason = f"Command '{cmd_base}' not in whitelist"
            self._history.append(cmd)
            return cmd

        cmd.allowed = True
        self._history.append(cmd)
        return cmd

    def execute(self, command: str) -> TerminalCommand:
        """Execute a validated command."""
        cmd = self.validate_command(command)

        if not cmd.allowed:
            return cmd

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self._working_dir,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            cmd.output = result.stdout
            cmd.exit_code = result.returncode
        except subprocess.TimeoutExpired:
            cmd.output = ""
            cmd.exit_code = -1
            cmd.block_reason = f"Command timed out ({self._timeout}s)"
        except Exception as e:
            cmd.output = ""
            cmd.exit_code = -1
            cmd.block_reason = str(e)

        return cmd

    def get_history(self, limit: int = 20) -> List[TerminalCommand]:
        return self._history[-limit:]

    def get_safe_commands(self) -> List[str]:
        """Get list of safe example commands."""
        return [
            "ls -la",
            "cat README.md",
            "grep -r 'TODO' .",
            "git status",
            "git diff",
            "pytest -v",
            "pip list",
        ]
