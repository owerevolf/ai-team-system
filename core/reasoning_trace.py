"""
Reasoning Trace - Отслеживание хода мыслей агентов
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReasoningStep:
    step: int
    action: str
    thought: str
    result: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ReasoningTrace:
    agent: str
    task: str
    steps: List[ReasoningStep] = field(default_factory=list)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    status: str = "in_progress"
    
    def add_step(self, action: str, thought: str, result: str = ""):
        self.steps.append(ReasoningStep(
            step=len(self.steps) + 1,
            action=action,
            thought=thought,
            result=result
        ))
    
    def complete(self, status: str = "success"):
        self.status = status
        self.end_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "task": self.task,
            "steps": [
                {"step": s.step, "action": s.action, "thought": s.thought, "result": s.result, "timestamp": s.timestamp}
                for s in self.steps
            ],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status
        }


class TraceManager:
    def __init__(self, traces_dir: Optional[Path] = None):
        if traces_dir is None:
            traces_dir = Path.home() / ".ai_team" / "traces"
        
        self.traces_dir = traces_dir
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.traces: Dict[str, ReasoningTrace] = {}
    
    def start_trace(self, agent: str, task: str) -> str:
        """Начать трассировку"""
        trace_id = f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.traces[trace_id] = ReasoningTrace(agent=agent, task=task)
        return trace_id
    
    def add_step(self, trace_id: str, action: str, thought: str, result: str = ""):
        """Добавить шаг"""
        trace = self.traces.get(trace_id)
        if trace:
            trace.add_step(action, thought, result)
    
    def complete_trace(self, trace_id: str, status: str = "success"):
        """Завершить трассировку"""
        trace = self.traces.get(trace_id)
        if trace:
            trace.complete(status)
            self._save_trace(trace_id)
    
    def _save_trace(self, trace_id: str):
        """Сохранить трассировку"""
        trace = self.traces.get(trace_id)
        if trace:
            trace_file = self.traces_dir / f"{trace_id}.json"
            trace_file.write_text(json.dumps(trace.to_dict(), indent=2, ensure_ascii=False))
    
    def get_trace(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Получить трассировку"""
        return self.traces.get(trace_id)
    
    def get_all_traces(self) -> List[ReasoningTrace]:
        """Получить все трассировки"""
        return list(self.traces.values())
    
    def get_summary(self) -> Dict[str, Any]:
        """Сводка"""
        total = len(self.traces)
        completed = sum(1 for t in self.traces.values() if t.status != "in_progress")
        total_steps = sum(len(t.steps) for t in self.traces.values())
        
        return {
            "total_traces": total,
            "completed": completed,
            "in_progress": total - completed,
            "total_steps": total_steps,
            "avg_steps_per_trace": round(total_steps / total, 1) if total > 0 else 0
        }
