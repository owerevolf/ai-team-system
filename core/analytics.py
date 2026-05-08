"""
Analytics — tracking agent usage, token consumption, response times.

Collects:
- Agent calls (count, duration, success/failure)
- Token usage (input/output, cost)
- Response times (avg, min, max)
- Error rates
- User interactions
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
ANALYTICS_DIR = BASE_DIR / "data" / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
ANALYTICS_FILE = ANALYTICS_DIR / "metrics.jsonl"
AGGREGATED_FILE = ANALYTICS_DIR / "aggregated.json"


@dataclass
class AgentCallMetric:
    """Single agent call metric"""
    agent: str
    model: str
    provider: str
    success: bool
    duration_ms: float
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AnalyticsManager:
    """Collects and aggregates usage analytics"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._recent_calls: deque = deque(maxlen=500)
        self._hourly_stats: Dict[str, Dict] = defaultdict(lambda: {
            "calls": 0, "success": 0, "errors": 0,
            "total_duration_ms": 0, "tokens_input": 0, "tokens_output": 0,
            "cost": 0.0,
        })
    
    def record_call(self, metric: AgentCallMetric):
        """Record a single agent call"""
        with self._lock:
            self._recent_calls.append(metric)
            
            # Aggregate by hour
            hour_key = metric.timestamp[:13]  # YYYY-MM-DDTHH
            stats = self._hourly_stats[hour_key]
            stats["calls"] += 1
            if metric.success:
                stats["success"] += 1
            else:
                stats["errors"] += 1
            stats["total_duration_ms"] += metric.duration_ms
            stats["tokens_input"] += metric.tokens_input
            stats["tokens_output"] += metric.tokens_output
            stats["cost"] += metric.cost
        
        # Persist to file
        self._persist_metric(metric)
    
    def _persist_metric(self, metric: AgentCallMetric):
        """Append metric to JSONL file"""
        try:
            with open(ANALYTICS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(metric), ensure_ascii=False) + "\n")
        except Exception:
            pass
    
    def get_summary(self, hours: int = 24) -> Dict:
        """Get summary for last N hours"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._lock:
            recent = [m for m in self._recent_calls if m.timestamp >= cutoff]
        
        if not recent:
            return {
                "period_hours": hours,
                "total_calls": 0,
                "success_rate": 0,
                "avg_duration_ms": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "by_agent": {},
                "by_model": {},
            }
        
        total = len(recent)
        successes = sum(1 for m in recent if m.success)
        total_duration = sum(m.duration_ms for m in recent)
        total_input = sum(m.tokens_input for m in recent)
        total_output = sum(m.tokens_output for m in recent)
        total_cost = sum(m.cost for m in recent)
        
        # Aggregate by agent
        by_agent = defaultdict(lambda: {"calls": 0, "success": 0, "avg_duration_ms": 0})
        for m in recent:
            a = by_agent[m.agent]
            a["calls"] += 1
            if m.success:
                a["success"] += 1
            a["avg_duration_ms"] = (a["avg_duration_ms"] * (a["calls"] - 1) + m.duration_ms) / a["calls"]
        
        # Aggregate by model
        by_model = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0})
        for m in recent:
            by_model[m.model]["calls"] += 1
            by_model[m.model]["tokens"] += m.tokens_input + m.tokens_output
            by_model[m.model]["cost"] += m.cost
        
        return {
            "period_hours": hours,
            "total_calls": total,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "avg_duration_ms": round(total_duration / total, 0) if total else 0,
            "total_tokens": total_input + total_output,
            "total_cost": round(total_cost, 4),
            "by_agent": dict(by_agent),
            "by_model": dict(by_model),
        }
    
    def get_hourly_breakdown(self, hours: int = 24) -> List[Dict]:
        """Get hourly breakdown"""
        result = []
        now = datetime.now()
        for h in range(hours):
            hour = now - timedelta(hours=h)
            key = hour.strftime("%Y-%m-%dT%H")
            stats = self._hourly_stats.get(key, {})
            result.append({
                "hour": key,
                "calls": stats.get("calls", 0),
                "success": stats.get("success", 0),
                "errors": stats.get("errors", 0),
                "tokens": stats.get("tokens_input", 0) + stats.get("tokens_output", 0),
                "cost": round(stats.get("cost", 0), 4),
            })
        return list(reversed(result))
    
    def get_dashboard_data(self) -> Dict:
        """Get data for analytics dashboard"""
        return {
            "summary_24h": self.get_summary(24),
            "summary_7d": self.get_summary(168),
            "hourly": self.get_hourly_breakdown(24),
            "recent_calls": [
                {
                    "agent": m.agent,
                    "model": m.model,
                    "success": m.success,
                    "duration_ms": round(m.duration_ms, 0),
                    "tokens": m.tokens_input + m.tokens_output,
                    "timestamp": m.timestamp,
                }
                for m in list(self._recent_calls)[-20:]
            ],
        }


analytics_manager = AnalyticsManager()
