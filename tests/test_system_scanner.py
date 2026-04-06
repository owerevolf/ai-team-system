"""
Tests for SystemScanner
"""

import pytest
from unittest.mock import patch

from core.system_scanner import SystemScanner


class TestSystemScanner:
    def setup_method(self):
        self.scanner = SystemScanner()
    
    def test_get_info(self):
        info = self.scanner.get_info()
        
        assert "cpu" in info
        assert "ram" in info
        assert "gpu" in info
        assert "disk" in info
        assert "ollama" in info
    
    def test_cpu_info_has_keys(self):
        info = self.scanner.get_info()
        
        assert "cores" in info["cpu"]
        assert "threads" in info["cpu"]
    
    def test_ram_info_has_keys(self):
        info = self.scanner.get_info()
        
        assert "total_gb" in info["ram"]
        assert "available_gb" in info["ram"]
    
    def test_recommend_profile(self):
        profile = self.scanner.recommend_profile()
        
        assert profile in ["light", "medium", "heavy"]
    
    def test_check_requirements(self):
        results = self.scanner.check_requirements(["cuda", "ollama"])
        
        assert "cuda" in results
        assert "ollama" in results
