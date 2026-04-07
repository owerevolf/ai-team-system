"""
Mode Switcher - Переключатель "Простой ↔ Продвинутый"
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ModeConfig:
    name: str
    description: str
    agents: list
    parallel: bool
    auto_fix: bool
    security_scan: bool
    memory_enabled: bool
    rag_enabled: bool
    fallback_enabled: bool
    learning_mode: bool
    max_iterations: int


MODES: Dict[str, ModeConfig] = {
    "simple": ModeConfig(
        name="Простой",
        description="Один агент, прямой запрос → ответ",
        agents=["backend"],
        parallel=False,
        auto_fix=False,
        security_scan=False,
        memory_enabled=False,
        rag_enabled=False,
        fallback_enabled=True,
        learning_mode=False,
        max_iterations=1
    ),
    "learning": ModeConfig(
        name="Обучение",
        description="Интерактивный тур с подсказками",
        agents=["teamlead", "architect", "backend", "tester", "documentalist"],
        parallel=False,
        auto_fix=True,
        security_scan=False,
        memory_enabled=True,
        rag_enabled=True,
        fallback_enabled=True,
        learning_mode=True,
        max_iterations=2
    ),
    "advanced": ModeConfig(
        name="Продвинутый",
        description="Полная мультиагентная система",
        agents=["teamlead", "architect", "backend", "frontend", "devops", "tester", "documentalist"],
        parallel=True,
        auto_fix=True,
        security_scan=True,
        memory_enabled=True,
        rag_enabled=True,
        fallback_enabled=True,
        learning_mode=False,
        max_iterations=3
    )
}


class ModeSwitcher:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".ai_team" / "mode_config.json"
        
        self.config_path = config_path
        self.current_mode = self._load_mode()
    
    def _load_mode(self) -> str:
        """Загрузка текущего режима"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                mode = data.get("mode", "advanced")
                if mode in MODES:
                    return mode
            except (json.JSONDecodeError, KeyError):
                pass
        return "advanced"
    
    def save_mode(self, mode: str):
        """Сохранение режима"""
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        
        self.current_mode = mode
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({"mode": mode}, indent=2))
    
    def get_config(self) -> ModeConfig:
        """Получить конфигурацию текущего режима"""
        return MODES[self.current_mode]
    
    def get_available_modes(self) -> Dict[str, Dict[str, Any]]:
        """Список доступных режимов"""
        return {
            name: {
                "name": config.name,
                "description": config.description,
                "agents": len(config.agents),
                "parallel": config.parallel
            }
            for name, config in MODES.items()
        }
    
    def switch(self, mode: str) -> Dict[str, Any]:
        """Переключение режима"""
        old_mode = self.current_mode
        self.save_mode(mode)
        
        return {
            "old_mode": old_mode,
            "new_mode": mode,
            "config": {
                "name": MODES[mode].name,
                "description": MODES[mode].description,
                "agents": MODES[mode].agents,
                "parallel": MODES[mode].parallel
            }
        }
