"""
Тесты установщика — проверка логики install.sh
"""

import subprocess
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class TestInstallScript:
    def test_install_sh_exists(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        assert script.exists(), "install.sh не найден"

    def test_install_sh_executable(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        assert script.stat().st_mode & 0o111, "install.sh не исполняемый"

    def test_install_sh_has_shebang(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        first_line = script.read_text().split("\n")[0]
        assert first_line.startswith("#!/bin/bash"), "Нет shebang в install.sh"

    def test_install_ps1_exists(self) -> None:
        script = BASE_DIR / "scripts" / "install.ps1"
        assert script.exists(), "install.ps1 не найден"

    def test_install_sh_has_hardware_detection(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        content = script.read_text()
        assert "nvidia-smi" in content
        assert "VRAM" in content or "vram" in content
        assert "qwen3" in content

    def test_install_sh_has_ollama_setup(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        content = script.read_text()
        assert "ollama" in content
        assert "ollama pull" in content

    def test_install_sh_creates_venv(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        content = script.read_text()
        assert "venv" in content
        assert "pip install" in content

    def test_install_sh_opens_browser(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        content = script.read_text()
        assert "xdg-open" in content or "open" in content

    def test_install_sh_logs(self) -> None:
        script = BASE_DIR / "scripts" / "install.sh"
        content = script.read_text()
        assert "install.log" in content
