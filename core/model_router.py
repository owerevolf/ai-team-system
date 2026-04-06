"""
Model Router v2 - Поддержка бесплатных API
Groq, DeepSeek, Google AI, OpenRouter, xAI, Cerebras
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()


class ModelRouter:
    def __init__(self, profile: str = "medium"):
        self.profile = profile
        
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        
        self.providers = self._init_providers()
        self.priority = self._get_priority()
    
    def _init_providers(self) -> Dict[str, Dict]:
        return {
            "groq": {
                "enabled": bool(os.getenv("GROQ_API_KEY")),
                "api_key": os.getenv("GROQ_API_KEY"),
                "base_url": "https://api.groq.com/openai/v1",
                "models": ["llama-3.3-70b-versatile", "qwen-3.5-32b", "llama-3.1-8b-instant"]
            },
            "deepseek": {
                "enabled": bool(os.getenv("DEEPSEEK_API_KEY")),
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.com",
                "models": ["deepseek-chat", "deepseek-coder"]
            },
            "google": {
                "enabled": bool(os.getenv("GOOGLE_AI_STUDIO_KEY")),
                "api_key": os.getenv("GOOGLE_AI_STUDIO_KEY"),
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "models": ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
            },
            "openrouter": {
                "enabled": bool(os.getenv("OPENROUTER_API_KEY")),
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "base_url": "https://openrouter.ai/api/v1",
                "models": ["deepseek/deepseek-r1", "meta-llama/llama-4-scout", "qwen/qwen3-32b"]
            },
            "xai": {
                "enabled": bool(os.getenv("XAI_API_KEY")),
                "api_key": os.getenv("XAI_API_KEY"),
                "base_url": "https://api.x.ai/v1",
                "models": ["grok-4", "grok-2"]
            },
            "ollama": {
                "enabled": self._check_ollama(),
                "base_url": self.ollama_base_url,
                "models": [self.ollama_model]
            },
            "anthropic": {
                "enabled": bool(os.getenv("ANTHROPIC_API_KEY")),
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
            },
            "openai": {
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
                "api_key": os.getenv("OPENAI_API_KEY"),
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
            }
        }
    
    def _check_ollama(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.ollama_base_url}/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5):
                return True
        except:
            return False
    
    def _get_priority(self) -> List[str]:
        if self.profile == "light":
            return ["groq", "deepseek", "google", "openrouter", "ollama"]
        elif self.profile == "medium":
            return ["ollama", "groq", "deepseek", "google", "openrouter", "xai"]
        else:
            return ["anthropic", "openai", "deepseek", "google", "xai", "ollama"]
    
    def _get_available_provider(self) -> Optional[str]:
        for provider in self.priority:
            if self.providers[provider]["enabled"]:
                return provider
        return None
    
    def generate(self, prompt: str, agent: str = None, model: str = None, **kwargs) -> str:
        provider = self._get_available_provider()
        
        if not provider:
            raise RuntimeError("Нет доступных провайдеров! Настройте .env файл.")
        
        if provider == "groq":
            return self._generate_groq(prompt, model)
        elif provider == "deepseek":
            return self._generate_deepseek(prompt, model)
        elif provider == "google":
            return self._generate_google(prompt, model)
        elif provider == "openrouter":
            return self._generate_openrouter(prompt, model)
        elif provider == "xai":
            return self._generate_xai(prompt, model)
        elif provider == "ollama":
            return self._generate_ollama(prompt, model)
        elif provider == "anthropic":
            return self._generate_anthropic(prompt, model)
        elif provider == "openai":
            return self._generate_openai(prompt, model)
        
        raise ValueError(f"Неизвестный провайдер: {provider}")
    
    def _generate_groq(self, prompt: str, model: str = None) -> str:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=self.providers["groq"]["api_key"],
            base_url=self.providers["groq"]["base_url"]
        )
        
        model = model or "llama-3.3-70b-versatile"
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    def _generate_deepseek(self, prompt: str, model: str = None) -> str:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=self.providers["deepseek"]["api_key"],
            base_url=self.providers["deepseek"]["base_url"]
        )
        
        model = model or "deepseek-chat"
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    
    def _generate_google(self, prompt: str, model: str = None) -> str:
        model = model or "gemini-2.0-flash"
        api_key = self.providers["google"]["api_key"]
        
        url = f"{self.providers['google']['base_url']}/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    
    def _generate_openrouter(self, prompt: str, model: str = None) -> str:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=self.providers["openrouter"]["api_key"],
            base_url=self.providers["openrouter"]["base_url"]
        )
        
        model = model or "deepseek/deepseek-r1:free"
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    def _generate_xai(self, prompt: str, model: str = None) -> str:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=self.providers["xai"]["api_key"],
            base_url=self.providers["xai"]["base_url"]
        )
        
        model = model or "grok-4"
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    def _generate_ollama(self, prompt: str, model: str = None) -> str:
        model = model or self.ollama_model
        num_ctx = 8192
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "temperature": 0.7
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama недоступна: {e}")
    
    def _generate_anthropic(self, prompt: str, model: str = None) -> str:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=self.providers["anthropic"]["api_key"])
        
        model = model or "claude-3-5-sonnet-20241022"
        
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text
    
    def _generate_openai(self, prompt: str, model: str = None) -> str:
        from openai import OpenAI
        
        client = OpenAI(api_key=self.providers["openai"]["api_key"])
        
        model = model or "gpt-4o"
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        
        return response.choices[0].message.content
    
    def list_models(self) -> Dict[str, List[str]]:
        models = {}
        
        for name, config in self.providers.items():
            if config["enabled"]:
                if name == "ollama":
                    try:
                        req = urllib.request.Request(
                            f"{self.ollama_base_url}/api/tags",
                            headers={"Content-Type": "application/json"}
                        )
                        with urllib.request.urlopen(req, timeout=5) as response:
                            data = json.loads(response.read().decode("utf-8"))
                            models[name] = [m["name"] for m in data.get("models", [])]
                    except:
                        models[name] = config["models"]
                else:
                    models[name] = config["models"]
        
        return models
    
    def get_status(self) -> Dict[str, Any]:
        status = {"active_provider": self._get_available_provider()}
        available = []
        
        for name, config in self.providers.items():
            if config["enabled"]:
                available.append(name)
        
        status["available_providers"] = available
        status["profile"] = self.profile
        
        return status
