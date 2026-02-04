"""
Ollama API client for local LLM inference.
"""

import json
import logging
from collections.abc import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HOST = "http://localhost:11434"

# System prompt for concise, well-formatted responses
DEFAULT_SYSTEM_PROMPT = """You are a concise coding assistant. Rules:
- Wrap code in markdown blocks with language (```python)
- Be brief: 1-2 sentences before code, key points only after
- Code comments for non-obvious parts only
- Skip obvious explanations, focus on what matters"""


class OllamaClient:
    """Async client for Ollama API."""

    def __init__(self, host: str = DEFAULT_HOST, timeout: float = 120.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _parse_error(self, response: httpx.Response, model: str) -> str:
        """Parse error message from Ollama response."""
        try:
            data = response.json()
            if "error" in data:
                return data["error"]
        except (json.JSONDecodeError, ValueError):
            pass
        # Fallback to generic message
        if response.status_code == 400:
            return f"Model '{model}' not found. Run: ollama pull {model}"
        return f"HTTP {response.status_code}"

    async def generate(
        self,
        model: str,
        prompt: str,
        context: str | None = None,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate a response from Ollama, streaming tokens.

        Args:
            model: Model name (e.g., "llama3.1", "glm-4.7-flash:latest")
            prompt: User prompt
            context: Optional context (selected code, file content, etc.)
            system: Optional system prompt

        Yields:
            Response tokens as they arrive
        """
        url = f"{self.host}/api/generate"

        # Build the full prompt with context
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n```\n{context}\n```\n\nUser request: {prompt}"

        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": True,
            "system": system or DEFAULT_SYSTEM_PROMPT,
        }

        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout) as client,
                client.stream("POST", url, json=payload) as response,
            ):
                if response.status_code != 200:
                    # Read error body for details
                    await response.aread()
                    error_msg = self._parse_error(response, model)
                    yield f"[Error: {error_msg}]"
                    return
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield "[Error: Cannot connect to Ollama. Is it running?]"
        except httpx.TimeoutException:
            yield "[Error: Request timed out]"
        except Exception as e:
            logger.exception("Ollama API error")
            yield f"[Error: {e}]"

    async def chat(
        self,
        model: str,
        messages: list[dict],
        context: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Chat completion with message history, streaming tokens.

        Args:
            model: Model name
            messages: List of {"role": "user"|"assistant", "content": "..."}
            context: Optional context to prepend

        Yields:
            Response tokens as they arrive
        """
        url = f"{self.host}/api/chat"

        # Add context to the last user message if provided
        if context and messages:
            messages = messages.copy()
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    messages[i] = {
                        "role": "user",
                        "content": f"Context:\n```\n{context}\n```\n\n{messages[i]['content']}",
                    }
                    break

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        try:
            async with (
                httpx.AsyncClient(timeout=self.timeout) as client,
                client.stream("POST", url, json=payload) as response,
            ):
                if response.status_code != 200:
                    # Read error body for details
                    await response.aread()
                    error_msg = self._parse_error(response, model)
                    yield f"[Error: {error_msg}]"
                    return
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield "[Error: Cannot connect to Ollama. Is it running?]"
        except httpx.TimeoutException:
            yield "[Error: Request timed out]"
        except Exception as e:
            logger.exception("Ollama chat API error")
            yield f"[Error: {e}]"

    async def list_models(self) -> list[dict]:
        """
        List available models from Ollama.

        Returns:
            List of model info dicts with 'name', 'size', etc.
        """
        url = f"{self.host}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except Exception:
            logger.exception("Failed to list Ollama models")
            return []

    async def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
