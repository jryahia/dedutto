import json
import time
from typing import Any, Dict, List, Optional

import httpx

from utils.helpers import log

PROVIDERS = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini", "gpt-4-turbo"],
        "auth_header": "Bearer",
    },
    "claude": {
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
        "auth_header": "x-api-key",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["openai/gpt-4o", "anthropic/claude-sonnet-4", "meta-llama/llama-3.3-70b-instruct"],
        "auth_header": "Bearer",
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "auth_header": "Bearer",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"],
        "auth_header": "Bearer",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"],
        "auth_header": "Bearer",
    },
    "custom": {
        "label": "Endpoint Personalizzato",
        "base_url": "",
        "models": [],
        "auth_header": "Bearer",
    },
}


class LLMAdapter:
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str = "",
        timeout: float = 60.0,
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

        info = PROVIDERS.get(provider, PROVIDERS["custom"])
        self.base_url = (base_url or info["base_url"]).rstrip("/")
        self.auth_type = info["auth_header"]

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.provider == "claude":
            h["x-api-key"] = self.api_key
            h["anthropic-version"] = "2023-06-01"
        else:
            h["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter":
            h["HTTP-Referer"] = "https://dedutto.app"
            h["X-Title"] = "Dedutto"
        return h

    def _chat_openai_compat(self, messages: List[Dict], temperature: float = 0.2) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _chat_claude_native(self, messages: List[Dict], system: str = "", temperature: float = 0.2) -> str:
        url = f"{self.base_url}/messages"
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if self.provider == "claude" and "anthropic.com" in self.base_url:
            return self._chat_claude_native(
                [{"role": "user", "content": user_prompt}],
                system=system_prompt,
                temperature=temperature,
            )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self._chat_openai_compat(messages, temperature=temperature)

    def complete_with_retry(self, system_prompt: str, user_prompt: str, retries: int = 1) -> Optional[str]:
        for attempt in range(retries + 1):
            try:
                return self.complete(system_prompt, user_prompt)
            except httpx.TimeoutException:
                if attempt < retries:
                    log.warning("LLM timeout, riprovo...")
                    time.sleep(2)
                else:
                    log.error("LLM timeout dopo tutti i tentativi")
                    return None
            except httpx.HTTPStatusError as e:
                log.error(f"LLM HTTP error {e.response.status_code}: {e.response.text[:200]}")
                return None
            except Exception as e:
                log.error(f"LLM error: {e}")
                return None
        return None


def build_adapter_from_settings() -> Optional[LLMAdapter]:
    from config.settings import get_setting
    provider = get_setting("llm_provider", "openai")
    api_key = get_setting("llm_api_key", "")
    model = get_setting("llm_model", "gpt-4o")
    base_url = get_setting("llm_base_url", "")
    if not api_key:
        return None
    return LLMAdapter(provider=provider, api_key=api_key, model=model, base_url=base_url)
