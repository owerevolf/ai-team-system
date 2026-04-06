"""
Logger - Логирование системы
"""

import os
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """Настройка логгера"""
    
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    log_dir = Path.home() / ".logs" / "ai_team"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    file_handler = RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


class ProjectLogger:
    """Логгер для конкретного проекта"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.log_dir = self.project_path / ".logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.timeline_file = self.log_dir / "timeline.json"
        self.agents_log = self.log_dir / "agents.log"
        self.errors_log = self.log_dir / "errors.log"
        
        self._init_files()
    
    def _init_files(self):
        """Инициализация файлов логов"""
        if not self.timeline_file.exists():
            self.timeline_file.write_text("[]")
        
        if not self.agents_log.exists():
            self.agents_log.write_text("")
        
        if not self.errors_log.exists():
            self.errors_log.write_text("")
    
    def log_agent_action(self, agent: str, action: str, details: str):
        """Логирование действия агента"""
        timestamp = datetime.now().isoformat()
        line = f"{timestamp} | {agent} | {action} | {details}\n"
        
        with open(self.agents_log, "a", encoding="utf-8") as f:
            f.write(line)
    
    def log_error(self, error: str, context: str = None):
        """Логирование ошибки"""
        timestamp = datetime.now().isoformat()
        line = f"{timestamp} | {error}"
        if context:
            line += f" | Context: {context}"
        line += "\n"
        
        with open(self.errors_log, "a", encoding="utf-8") as f:
            f.write(line)
    
    def add_timeline_event(self, event: dict):
        """Добавление события в timeline"""
        import json
        
        events = json.loads(self.timeline_file.read_text())
        events.append({
            **event,
            "timestamp": datetime.now().isoformat()
        })
        
        self.timeline_file.write_text(json.dumps(events, indent=2, ensure_ascii=False))
    
    def get_timeline(self) -> list:
        """Получение timeline"""
        import json
        return json.loads(self.timeline_file.read_text())
    
    def get_errors(self) -> list:
        """Получение ошибок"""
        errors = []
        for line in self.errors_log.read_text().strip().split("\n"):
            if line:
                parts = line.split(" | ")
                errors.append({
                    "timestamp": parts[0] if len(parts) > 0 else "",
                    "error": parts[1] if len(parts) > 1 else "",
                    "context": parts[2] if len(parts) > 2 else None
                })
        return errors
