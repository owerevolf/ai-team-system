"""
System Scanner - Сканирование железа и оптимизация
"""

import platform
import psutil
from typing import Dict, Any, Optional


class SystemScanner:
    def __init__(self):
        self.platform = platform.system()
    
    def get_info(self) -> Dict[str, Any]:
        """Получение полной информации о системе"""
        return {
            "cpu": self._get_cpu_info(),
            "ram": self._get_ram_info(),
            "gpu": self._get_gpu_info(),
            "disk": self._get_disk_info(),
            "ollama": self._check_ollama()
        }
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """Информация о CPU"""
        return {
            "name": platform.processor() or "Unknown",
            "cores": psutil.cpu_count(logical=False) or 1,
            "threads": psutil.cpu_count(logical=True) or 1,
            "usage_percent": psutil.cpu_percent(interval=1)
        }
    
    def _get_ram_info(self) -> Dict[str, Any]:
        """Информация о RAM"""
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent
        }
    
    def _get_gpu_info(self) -> Dict[str, Any]:
        """Информация о GPU"""
        gpu_info = {
            "name": None,
            "vram_gb": None,
            "available": False
        }
        
        if self.platform == "Linux":
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    if lines:
                        name, memory = lines[0].split(",")
                        gpu_info["name"] = name.strip()
                        gpu_info["vram_gb"] = round(int(memory.strip().replace(" MiB", "")) / 1024, 1)
                        gpu_info["available"] = True
                        
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
        
        elif self.platform == "Windows":
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    if lines:
                        name, memory = lines[0].split(",")
                        gpu_info["name"] = name.strip()
                        gpu_info["vram_gb"] = round(int(memory.strip().replace(" MiB", "")) / 1024, 1)
                        gpu_info["available"] = True
                        
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
        
        return gpu_info
    
    def _get_disk_info(self) -> Dict[str, Any]:
        """Информация о диске"""
        disk = psutil.disk_usage("/")
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        }
    
    def _check_ollama(self) -> Dict[str, Any]:
        """Проверка Ollama"""
        ollama_info = {
            "available": False,
            "version": None,
            "models": []
        }
        
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    import json
                    data = json.loads(response.read().decode("utf-8"))
                    ollama_info["available"] = True
                    ollama_info["models"] = [m["name"] for m in data.get("models", [])]
                    
        except Exception:
            pass
        
        return ollama_info
    
    def recommend_profile(self) -> str:
        """Рекомендация профиля на основе железа"""
        info = self.get_info()
        
        if not info["ollama"]["available"]:
            return "heavy"
        
        vram = info["gpu"]["vram_gb"] or 0
        ram = info["ram"]["total_gb"]
        cores = info["cpu"]["cores"]
        
        if vram >= 16 and ram >= 32 and cores >= 8:
            return "heavy"
        elif vram >= 8 and ram >= 16 and cores >= 4:
            return "medium"
        else:
            return "light"
    
    def check_requirements(self, requirements: list) -> Dict[str, bool]:
        """Проверка требований"""
        info = self.get_info()
        results = {}
        
        for req in requirements:
            if req == "cuda" and info["gpu"]["available"]:
                results["cuda"] = True
            elif req == "ollama" and info["ollama"]["available"]:
                results["ollama"] = True
            elif req == "16gb_ram" and info["ram"]["total_gb"] >= 16:
                results["16gb_ram"] = True
            elif req == "8gb_vram" and info["gpu"]["vram_gb"] >= 8:
                results["8gb_vram"] = True
            else:
                results[req] = False
        
        return results
