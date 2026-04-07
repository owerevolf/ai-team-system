"""
Тесты HardwareDetector
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.hardware_detector import HardwareDetector


class TestHardwareDetector:
    def test_detect_returns_required_keys(self, tmp_path: Path) -> None:
        detector = HardwareDetector()

        with patch.object(detector, "_get_vram_gb", return_value=8.0):
            with patch.object(detector, "_get_ram_gb", return_value=16.0):
                with patch.object(detector, "_save_cache"):
                    result = detector.detect()

        assert "vram_gb" in result
        assert "ram_gb" in result
        assert "profile" in result
        assert "model" in result
        assert "platform" in result

    def test_profile_light(self, tmp_path: Path) -> None:
        detector = HardwareDetector()
        profile = detector._get_profile(2.0, 4.0)
        assert profile == "light"

    def test_profile_medium(self, tmp_path: Path) -> None:
        detector = HardwareDetector()
        profile = detector._get_profile(8.0, 16.0)
        assert profile == "medium"

    def test_profile_heavy(self, tmp_path: Path) -> None:
        detector = HardwareDetector()
        profile = detector._get_profile(16.0, 64.0)
        assert profile == "heavy"

    def test_model_selection(self) -> None:
        detector = HardwareDetector()
        assert detector._get_model("light") == "qwen3:4b"
        assert detector._get_model("medium") == "qwen3:8b"
        assert detector._get_model("heavy") == "qwen3:14b"

    def test_cache_save_and_load(self, tmp_path: Path) -> None:
        cache_file = tmp_path / ".hardware_cache"
        with patch("core.hardware_detector.CACHE_FILE", cache_file):
            detector = HardwareDetector()
            detector._save_cache({"vram_gb": 8.0, "ram_gb": 16.0, "profile": "medium", "model": "qwen3:8b", "platform": "Linux", "cpu_cores": 4, "cpu_threads": 8})

            loaded = detector._load_cache()
            assert loaded is not None
            assert loaded["profile"] == "medium"

    def test_cache_expired(self, tmp_path: Path) -> None:
        cache_file = tmp_path / ".hardware_cache"
        with patch("core.hardware_detector.CACHE_FILE", cache_file):
            detector = HardwareDetector()
            old_data = {
                "vram_gb": 8.0,
                "ram_gb": 16.0,
                "profile": "medium",
                "model": "qwen3:8b",
                "platform": "Linux",
                "cpu_cores": 4,
                "cpu_threads": 8,
                "cached_at": "2020-01-01T00:00:00",
            }
            cache_file.write_text(json.dumps(old_data))

            loaded = detector._load_cache()
            assert loaded is None
