"""
Agent Model Config - Разные модели для разных агентов
TeamLead работает на дешёвой модели, Backend на мощной
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AgentModelConfig:
    model: str
    provider: str
    max_tokens: int = 4096
    temperature: float = 0.7
    num_ctx: int = 8192


# Профили моделей для разного железа
MODEL_PROFILES: Dict[str, Dict[str, AgentModelConfig]] = {
    "light": {
        "teamlead": AgentModelConfig(
            model="qwen2.5-coder:3b",
            provider="ollama",
            max_tokens=2048,
            temperature=0.5,
            num_ctx=4096
        ),
        "architect": AgentModelConfig(
            model="qwen2.5-coder:3b",
            provider="ollama",
            max_tokens=2048,
            temperature=0.6,
            num_ctx=4096
        ),
        "backend": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.7,
            num_ctx=8192
        ),
        "frontend": AgentModelConfig(
            model="qwen2.5-coder:3b",
            provider="ollama",
            max_tokens=2048,
            temperature=0.7,
            num_ctx=4096
        ),
        "devops": AgentModelConfig(
            model="qwen2.5-coder:3b",
            provider="ollama",
            max_tokens=2048,
            temperature=0.5,
            num_ctx=4096
        ),
        "tester": AgentModelConfig(
            model="qwen2.5-coder:3b",
            provider="ollama",
            max_tokens=2048,
            temperature=0.3,
            num_ctx=4096
        ),
        "documentalist": AgentModelConfig(
            model="qwen2.5-coder:3b",
            provider="ollama",
            max_tokens=2048,
            temperature=0.8,
            num_ctx=4096
        )
    },
    "medium": {
        "teamlead": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.5,
            num_ctx=8192
        ),
        "architect": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.6,
            num_ctx=8192
        ),
        "backend": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=8192,
            temperature=0.7,
            num_ctx=16384
        ),
        "frontend": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.7,
            num_ctx=8192
        ),
        "devops": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.5,
            num_ctx=8192
        ),
        "tester": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.3,
            num_ctx=8192
        ),
        "documentalist": AgentModelConfig(
            model="qwen2.5-coder:7b",
            provider="ollama",
            max_tokens=4096,
            temperature=0.8,
            num_ctx=8192
        )
    },
    "heavy": {
        "teamlead": AgentModelConfig(
            model="claude-3-haiku",
            provider="anthropic",
            max_tokens=4096,
            temperature=0.5,
            num_ctx=16384
        ),
        "architect": AgentModelConfig(
            model="claude-3-5-sonnet",
            provider="anthropic",
            max_tokens=8192,
            temperature=0.6,
            num_ctx=32768
        ),
        "backend": AgentModelConfig(
            model="claude-3-5-sonnet",
            provider="anthropic",
            max_tokens=16384,
            temperature=0.7,
            num_ctx=32768
        ),
        "frontend": AgentModelConfig(
            model="claude-3-5-sonnet",
            provider="anthropic",
            max_tokens=8192,
            temperature=0.7,
            num_ctx=16384
        ),
        "devops": AgentModelConfig(
            model="claude-3-haiku",
            provider="anthropic",
            max_tokens=4096,
            temperature=0.5,
            num_ctx=16384
        ),
        "tester": AgentModelConfig(
            model="claude-3-5-sonnet",
            provider="anthropic",
            max_tokens=8192,
            temperature=0.3,
            num_ctx=16384
        ),
        "documentalist": AgentModelConfig(
            model="claude-3-haiku",
            provider="anthropic",
            max_tokens=4096,
            temperature=0.8,
            num_ctx=16384
        )
    }
}


def get_agent_model_config(profile: str, agent: str) -> Optional[AgentModelConfig]:
    """Получить конфигурацию модели для агента"""
    return MODEL_PROFILES.get(profile, {}).get(agent)


def list_agent_models(profile: str) -> Dict[str, str]:
    """Список моделей для всех агентов в профиле"""
    configs = MODEL_PROFILES.get(profile, {})
    return {
        agent: f"{config.provider}/{config.model}"
        for agent, config in configs.items()
    }
