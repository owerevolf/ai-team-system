"""
Model Router - Маршрутизация запросов к разным моделям
Поддержка Ollama и облачных API (OpenAI, Anthropic)
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class ModelRouter:
    def __init__(self, profile: str = "medium"):
        self.profile = profile
        
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        self.providers = self._detect_providers()
    
    def _detect_providers(self) -> Dict[str, bool]:
        """Определение доступных провайдеров"""
        providers = {
            "ollama": self._check_ollama(),
            "anthropic": bool(self.anthropic_api_key),
            "openai": bool(self.openai_api_key)
        }
        return providers
    
    def _check_ollama(self) -> bool:
        """Проверка доступности Ollama"""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.ollama_base_url}/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except:
            return False
    
    def _get_available_model(self) -> str:
        """Получение доступной модели"""
        if self.providers["ollama"]:
            return f"ollama/{self.ollama_model}"
        elif self.providers["anthropic"]:
            return "anthropic/claude-3-5-sonnet"
        elif self.providers["openai"]:
            return "openai/gpt-4"
        else:
            raise RuntimeError("Нет доступных провайдеров. Настройте Ollama или API ключи.")
    
    def generate(self, prompt: str, agent: str = None, **kwargs) -> str:
        """Генерация ответа от модели"""
        model = self._get_available_model()
        
        if model.startswith("ollama/"):
            return self._generate_ollama(
                prompt, 
                model.replace("ollama/", ""),
                **kwargs
            )
        elif model.startswith("anthropic/"):
            return self._generate_anthropic(prompt, **kwargs)
        elif model.startswith("openai/"):
            return self._generate_openai(prompt, **kwargs)
        
        raise ValueError(f"Неизвестный провайдер: {model}")
    
    def _generate_ollama(self, prompt: str, model: str, **kwargs) -> str:
        """Генерация через Ollama"""
        import urllib.request
        import urllib.error
        
        num_ctx = kwargs.get("num_ctx", 8192)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "temperature": 0.7
            }
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
                
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama недоступна: {e}")
    
    def _generate_anthropic(self, prompt: str, **kwargs) -> str:
        """Генерация через Anthropic API"""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("Установите anthropic: pip install anthropic")
        
        client = Anthropic(api_key=self.anthropic_api_key)
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    
    def _generate_openai(self, prompt: str, **kwargs) -> str:
        """Генерация через OpenAI API"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Установите openai: pip install openai")
        
        client = OpenAI(api_key=self.openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    
    def list_models(self) -> Dict[str, list]:
        """Список доступных моделей"""
        models = {}
        
        if self.providers["ollama"]:
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{self.ollama_base_url}/api/tags",
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    models["ollama"] = [m["name"] for m in data.get("models", [])]
            except:
                models["ollama"] = []
        
        if self.providers["anthropic"]:
            models["anthropic"] = ["claude-3-5-sonnet", "claude-3-opus"]
        
        if self.providers["openai"]:
            models["openai"] = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        
        return models
