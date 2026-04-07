"""
Event Bus - Event-driven коммуникация между агентами
"""

import json
import queue
import threading
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Event:
    type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id
        }


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._history: List[Event] = []
        self._lock = threading.Lock()
        self._queues: Dict[str, queue.Queue] = {}
    
    def on(self, event_type: str, handler: Callable):
        """Регистрация обработчика"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def emit(self, event: Event):
        """Отправка события"""
        with self._lock:
            self._history.append(event)
        
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                pass
    
    def subscribe(self, agent: str) -> queue.Queue:
        """Подписка агента на события"""
        q = queue.Queue()
        self._queues[agent] = q
        
        def forward_handler(event: Event):
            q.put(event)
        
        self.on("*", forward_handler)
        return q
    
    def get_history(self, limit: int = 100, event_type: str = None) -> List[Event]:
        """История событий"""
        history = self._history
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        return history[-limit:]
    
    def get_trace(self, correlation_id: str) -> List[Event]:
        """Трассировка по correlation_id"""
        return [e for e in self._history if e.correlation_id == correlation_id]
    
    def stats(self) -> Dict[str, Any]:
        """Статистика"""
        event_counts = {}
        for e in self._history:
            event_counts[e.type] = event_counts.get(e.type, 0) + 1
        
        return {
            "total_events": len(self._history),
            "event_types": event_counts,
            "subscribers": len(self._queues)
        }
    
    def save_trace(self, path: Path):
        """Сохранение трассировки"""
        data = [e.to_dict() for e in self._history]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    def load_trace(self, path: Path):
        """Загрузка трассировки"""
        if not path.exists():
            return
        
        data = json.loads(path.read_text())
        self._history = [Event(**d) for d in data]
