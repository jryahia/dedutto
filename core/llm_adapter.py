"""Unified LLM adapter supporting multiple providers.

Supports: OpenAI, Anthropic Claude, OpenRouter, Google Gemini, Groq,
DeepSeek, and any custom OpenAI-compatible endpoint.
"""
import json
import time
from typing import Any, Dict, List, Optional

from utils.logging import get_logger

log = get_logger(__name__)

PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "claude": {
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-haiku-4-5-20251001",
        "models": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "mistralai/mistral-7b-instruct",
        "models": [
            "mistralai/mistral-7b-instruct",
            "meta-llama/llama-3.1-8b-instruct:free",
            "google/gemma-2-9b-it:free",
            "anthropic/claude-3.5-haiku",
            "openai/gpt-4o-mini",
        ],
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-1.5-flash",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.1-8b-instant",
        "models": [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "custom": {
        "base_url": "",
        "default_model": "",
        "models": [],
    },
}


class LLMAdapter:
    """Unified interface to multiple LLM providers."""

    def __init__(
        self,
        provider: str = "openai",
        api_key: str = "",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
    ):
        if provider not in PROVIDERS:
            raise ValueError(f"Provider sconosciuto: {provider}. Validi: {list(PROVIDERS)}")
        self.provider = provider
        self.api_key = api_key
        self.timeout = timeout

        cfg = PROVIDERS[provider]
        self.base_url = (base_url or cfg["base_url"]).rstrip("/")
        self.model = model or cfg["default_model"]

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """Send a chat completion request and return the assistant message."""
        if not self.api_key:
            raise ValueError("Chiave API mancante")

        if self.provider == "claude":
            return self._complete_anthropic(messages, temperature, max_tokens)
        else:
            return self._complete_openai_compat(messages, temperature, max_tokens)

    def _complete_openai_compat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """OpenAI-compatible API call (used by OpenAI, OpenRouter, Gemini, Groq, DeepSeek, custom)."""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai non installato. Eseguire: pip install openai")

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        extra_headers = {}
        if self.provider == "openrouter":
            extra_headers["HTTP-Referer"] = "https://dedutto.app"
            extra_headers["X-Title"] = "Dedutto"

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_headers=extra_headers if extra_headers else None,
        )
        return response.choices[0].message.content or ""

    def _complete_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Anthropic native API."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic non installato. Eseguire: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)

        # Split system message from user messages
        system_msg = ""
        chat_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_msgs.append({"role": msg["role"], "content": msg["content"]})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat_msgs,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    @staticmethod
    def available_providers() -> List[str]:
        return list(PROVIDERS.keys())

    @staticmethod
    def models_for_provider(provider: str) -> List[str]:
        return PROVIDERS.get(provider, {}).get("models", [])

    @staticmethod
    def default_model_for_provider(provider: str) -> str:
        return PROVIDERS.get(provider, {}).get("default_model", "")
