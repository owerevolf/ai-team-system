"""
Token Tracker - Отслеживание использования токенов и стоимости
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


# Цены за 1M токенов (USD)
MODEL_PRICES = {
    "groq": {"input": 0.0, "output": 0.0},
    "deepseek": {"input": 0.14, "output": 0.28},
    "google": {"input": 0.0, "output": 0.0},
    "openrouter": {"input": 0.0, "output": 0.0},
    "xai": {"input": 0.20, "output": 0.60},
    "ollama": {"input": 0.0, "output": 0.0},
    "anthropic": {"input": 3.0, "output": 15.0},
    "openai": {"input": 2.5, "output": 10.0},
}


@dataclass
class TokenUsage:
    agent: str
    provider: str
    input_tokens: int
    output_tokens: int
    files_created: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def cost(self) -> float:
        prices = MODEL_PRICES.get(self.provider, {"input": 0, "output": 0})
        return (
            (self.input_tokens / 1_000_000) * prices["input"] +
            (self.output_tokens / 1_000_000) * prices["output"]
        )


class TokenTracker:
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path
        self.usage: List[TokenUsage] = []
    
    def record(self, agent: str, provider: str, 
               input_tokens: int = 0, output_tokens: int = 0,
               files_created: int = 0):
        """Запись использования"""
        self.usage.append(TokenUsage(
            agent=agent,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            files_created=files_created
        ))
    
    def get_total(self) -> Dict[str, Any]:
        """Общая статистика"""
        total_input = sum(u.input_tokens for u in self.usage)
        total_output = sum(u.output_tokens for u in self.usage)
        total_cost = sum(u.cost for u in self.usage)
        total_files = sum(u.files_created for u in self.usage)
        
        by_agent = {}
        for u in self.usage:
            if u.agent not in by_agent:
                by_agent[u.agent] = {"calls": 0, "tokens": 0, "files": 0}
            by_agent[u.agent]["calls"] += 1
            by_agent[u.agent]["tokens"] += u.total_tokens
            by_agent[u.agent]["files"] += u.files_created
        
        by_provider = {}
        for u in self.usage:
            if u.provider not in by_provider:
                by_provider[u.provider] = {"calls": 0, "tokens": 0, "cost": 0}
            by_provider[u.provider]["calls"] += 1
            by_provider[u.provider]["tokens"] += u.total_tokens
            by_provider[u.provider]["cost"] += u.cost
        
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost": round(total_cost, 4),
            "total_files": total_files,
            "total_calls": len(self.usage),
            "by_agent": by_agent,
            "by_provider": by_provider
        }
    
    def save(self):
        """Сохранение в файл"""
        if not self.project_path:
            return
        
        stats = self.get_total()
        stats["details"] = [
            {
                "agent": u.agent,
                "provider": u.provider,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "cost": round(u.cost, 4),
                "files_created": u.files_created,
                "timestamp": u.timestamp
            }
            for u in self.usage
        ]
        
        (self.project_path / "token_usage.json").write_text(
            json.dumps(stats, indent=2, ensure_ascii=False)
        )
    
    def format_report(self) -> str:
        """Форматированный отчёт"""
        stats = self.get_total()
        
        lines = [
            "═══ Token Usage Report ═══",
            f"Total calls: {stats['total_calls']}",
            f"Total tokens: {stats['total_tokens']:,}",
            f"Total cost: ${stats['total_cost']:.4f}",
            f"Files created: {stats['total_files']}",
            "",
            "By Agent:",
        ]
        
        for agent, data in stats["by_agent"].items():
            lines.append(f"  {agent}: {data['calls']} calls, {data['tokens']:,} tokens, {data['files']} files")
        
        lines.append("")
        lines.append("By Provider:")
        
        for provider, data in stats["by_provider"].items():
            lines.append(f"  {provider}: {data['calls']} calls, {data['tokens']:,} tokens, ${data['cost']:.4f}")
        
        return "\n".join(lines)
