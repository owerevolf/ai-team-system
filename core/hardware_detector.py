"""
Hardware Detector — определение характеристик системы и выбор профиля
Версия: 2.0
"""

import json
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import psutil
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_FILE = BASE_DIR / ".hardware_cache"
CACHE_TTL = timedelta(hours=24)


class HardwareDetector:
    def __init__(self) -> None:
        self._platform = platform.system()
        self._cache: Optional[Dict[str, Any]] = None

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        if not CACHE_FILE.exists():
            return None
        try:
            data = json.loads(CACHE_FILE.read_text())
            cached_at = datetime.fromisoformat(data.get("cached_at", ""))
            if datetime.now() - cached_at > CACHE_TTL:
                logger.debug("Кэш железа устарел")
                return None
            logger.debug("Использую кэш железа")
            return data
        except (json.JSONDecodeError, ValueError):
            return None

    def _save_cache(self, data: Dict[str, Any]) -> None:
        data["cached_at"] = datetime.now().isoformat()
        CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        logger.debug(f"Кэш железа сохранён: {CACHE_FILE}")

    def _get_vram_gb(self) -> float:
        vram = 0.0
        try:
            if self._platform == "Darwin":
                ram_bytes = int(subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"], text=True
                ).strip())
                vram = ram_bytes / (1024 ** 3)
                logger.debug(f"Apple Silicon: унифицированная память {vram:.1f} ГБ")
            else:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5, check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    vram = float(result.stdout.strip().split("\n")[0].strip()) / 1024
                    logger.debug(f"NVIDIA VRAM: {vram:.1f} ГБ")
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, subprocess.SubprocessError) as e:
            logger.debug(f"Не удалось определить VRAM: {e}")
        return vram

    def _get_ram_gb(self) -> float:
        try:
            mem = psutil.virtual_memory()
            return round(mem.total / (1024 ** 3), 2)
        except Exception as e:
            logger.warning(f"Не удалось определить RAM: {e}")
            return 8.0

    def _get_profile(self, vram_gb: float, ram_gb: float) -> str:
        if vram_gb > 12 or ram_gb > 32:
            return "heavy"
        elif vram_gb >= 6 or ram_gb >= 16:
            return "medium"
        else:
            return "light"

    def _get_model(self, profile: str) -> str:
        models = {
            "heavy": "qwen3:14b",
            "medium": "qwen3:8b",
            "light": "qwen3:4b",
        }
        return models.get(profile, "qwen3:8b")

    def detect(self) -> Dict[str, Any]:
        cached = self._load_cache()
        if cached:
            self._cache = cached
            return cached

        vram_gb = self._get_vram_gb()
        ram_gb = self._get_ram_gb()
        profile = self._get_profile(vram_gb, ram_gb)
        model = self._get_model(profile)

        result: Dict[str, Any] = {
            "vram_gb": round(vram_gb, 1),
            "ram_gb": ram_gb,
            "profile": profile,
            "model": model,
            "platform": self._platform,
            "cpu_cores": psutil.cpu_count(logical=False) or 1,
            "cpu_threads": psutil.cpu_count(logical=True) or 1,
        }

        self._save_cache(result)
        self._cache = result
        logger.info(f"Железо: VRAM={vram_gb}ГБ, RAM={ram_gb}ГБ → {profile} ({model})")
        return result

    def get_profile(self) -> str:
        if self._cache:
            return self._cache["profile"]
        return self.detect()["profile"]

    def get_model(self) -> str:
        if self._cache:
            return self._cache["model"]
        return self.detect()["model"]
