"""
HFIP – Groq LLM Client
Uses the official Groq Python SDK.
Docs: https://console.groq.com/docs/quickstart
"""

from __future__ import annotations

import os
from typing import Optional

from groq import Groq
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class GroqClient:
    """
    Thin wrapper around the official Groq SDK.
    Supports all models available on https://console.groq.com/docs/models
    """

    DEFAULT_MODEL = "openai/gpt-oss-120b"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self._client = Groq(api_key=self.api_key)
        logger.info(f"GroqClient initialised (model={self.model})")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send a chat completion request to Groq.
        Returns the raw text content of the first choice.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        logger.debug(f"Groq response: {content[:200]}")
        return content

    def get_model_name(self) -> str:
        return self.model
