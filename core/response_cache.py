"""
Response Cache - Кэширование ответов LLM для экономии токенов
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class ResponseCache:
    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        if cache_dir is None:
            cache_dir = Path.home() / ".ai_team" / "cache"
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_key(self, prompt: str, agent: str, model: str) -> str:
        """Генерация ключа кэша"""
        raw = f"{agent}:{model}:{prompt[:500]}"
        return hashlib.md5(raw.encode()).hexdigest()
    
    def get(self, prompt: str, agent: str, model: str) -> Optional[str]:
        """Получение из кэша"""
        key = self._get_key(prompt, agent, model)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            data = json.loads(cache_file.read_text())
            created = datetime.fromisoformat(data["created"])
            
            if datetime.now() - created > self.ttl:
                cache_file.unlink()
                return None
            
            return data["response"]
        except (json.JSONDecodeError, KeyError):
            return None
    
    def set(self, prompt: str, agent: str, model: str, response: str):
        """Сохранение в кэш"""
        key = self._get_key(prompt, agent, model)
        cache_file = self.cache_dir / f"{key}.json"
        
        data = {
            "agent": agent,
            "model": model,
            "response": response,
            "created": datetime.now().isoformat(),
            "prompt_preview": prompt[:100]
        }
        
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    def clear(self):
        """Очистка кэша"""
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
    
    def stats(self) -> Dict[str, Any]:
        """Статистика кэша"""
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "entries": len(files),
            "size_mb": round(total_size / (1024 * 1024), 2),
            "ttl_hours": self.ttl.total_seconds() / 3600
        }
