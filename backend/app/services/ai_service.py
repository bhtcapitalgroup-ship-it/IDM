"""AI Service — OpenAI-compatible client with structured output support.

Works with any OpenAI-compatible endpoint (OpenAI, Anthropic via proxy,
local models via LM Studio/Ollama, Azure OpenAI, etc).

All calls are:
- Logged with request/response metadata
- Timeout-bounded
- Retried with exponential backoff on transient failures
- Inspectable via returned metadata
"""
import json
import time
import logging
from dataclasses import dataclass, field

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Transient HTTP status codes that warrant a retry
_RETRYABLE = {429, 500, 502, 503, 504}
_MAX_RETRIES = 2
_TIMEOUT_SECONDS = 60
_BASE_DELAY = 1.0  # seconds, doubled per retry


@dataclass
class AIResponse:
    """Structured result from an AI call, always inspectable."""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    retries: int = 0
    raw_response: dict = field(default_factory=dict)


@dataclass
class AIError:
    """Explicit failure from an AI call."""
    error: str
    status_code: int | None = None
    retries: int = 0
    latency_ms: int = 0


class AIService:
    def __init__(self):
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.base_url = "https://api.openai.com/v1"

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: dict | None = None,
    ) -> AIResponse | AIError:
        """Send a chat completion request. Returns AIResponse on success, AIError on failure."""
        if not self._is_configured():
            return AIError(error="AI_API_KEY not configured. Set it in .env to enable AI features.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        start = time.monotonic()
        last_error = ""
        retries = 0

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )

                elapsed_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    usage = data.get("usage", {})
                    content = choice.get("message", {}).get("content", "")

                    logger.info(
                        "AI call succeeded",
                        extra={
                            "model": self.model,
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "latency_ms": elapsed_ms,
                            "retries": retries,
                        },
                    )

                    return AIResponse(
                        content=content,
                        model=data.get("model", self.model),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        latency_ms=elapsed_ms,
                        retries=retries,
                        raw_response=data,
                    )

                # Non-200 response
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if resp.status_code in _RETRYABLE and attempt < _MAX_RETRIES:
                    retries += 1
                    delay = _BASE_DELAY * (2 ** attempt)
                    logger.warning(f"AI call failed ({resp.status_code}), retrying in {delay}s")
                    import asyncio
                    await asyncio.sleep(delay)
                    continue
                else:
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    logger.error(f"AI call failed permanently: {last_error}")
                    return AIError(
                        error=last_error,
                        status_code=resp.status_code,
                        retries=retries,
                        latency_ms=elapsed_ms,
                    )

            except httpx.TimeoutException:
                last_error = f"Timeout after {_TIMEOUT_SECONDS}s"
                if attempt < _MAX_RETRIES:
                    retries += 1
                    continue
            except httpx.ConnectError as e:
                last_error = f"Connection error: {e}"
                if attempt < _MAX_RETRIES:
                    retries += 1
                    continue
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.exception("AI call unexpected error")

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return AIError(error=last_error, retries=retries, latency_ms=elapsed_ms)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 4000,
    ) -> dict | AIError:
        """Request a JSON response. Parses the content as JSON.
        Returns parsed dict on success, AIError on failure."""
        result = await self.complete(
            system_prompt=system_prompt + "\n\nRespond with valid JSON only. No markdown, no explanation.",
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        if isinstance(result, AIError):
            return result

        try:
            parsed = json.loads(result.content)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"AI returned invalid JSON: {e}")
            return AIError(error=f"AI returned invalid JSON: {e}", latency_ms=result.latency_ms)


# Singleton
ai_service = AIService()
