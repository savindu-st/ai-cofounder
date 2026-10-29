"""Self-healing retry and provider fallback utilities.

Provides deterministic exponential backoff with jitter for transient failures,
plus an OpenAI -> Anthropic -> Gemini provider chain with one-shot schema
correction when a model returns malformed structured output.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    """Raised after every retry attempt for an operation fails."""

    def __init__(self, operation_name: str, attempts: int, last_error: BaseException):
        self.operation_name = operation_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Operation '{operation_name}' failed after {attempts} attempt(s): {last_error}"
        )


class ProviderUnavailableError(RuntimeError):
    """Raised when no configured LLM provider can complete the request."""


class SchemaCorrectionError(RuntimeError):
    """Raised when a provider still returns invalid structured output after correction."""


@dataclass(frozen=True)
class RetryConfig:
    """Retry policy for external calls and node operations."""

    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    jitter: bool = True
    retry_exceptions: Tuple[type[BaseException], ...] = (Exception,)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < 0 or self.max_delay < 0:
            raise ValueError("retry delays must be non-negative")


def calculate_backoff(
    attempt: int,
    config: Optional[RetryConfig] = None,
    random_value: Optional[float] = None,
) -> float:
    """Calculate capped exponential backoff, optionally with uniform jitter.

    ``attempt`` is zero-indexed: attempt 0 -> base delay, attempt 1 -> 2x base.
    The jitter component is uniform(0, 1) seconds, per the architecture spec.
    """
    cfg = config or RetryConfig()
    exp_delay = cfg.base_delay * (2 ** max(attempt, 0))
    if cfg.jitter:
        rv = random.random() if random_value is None else random_value
        exp_delay += max(0.0, min(1.0, rv))
    return min(cfg.max_delay, exp_delay)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def retry_async(
    operation: Callable[..., Any],
    *args: Any,
    config: Optional[RetryConfig] = None,
    operation_name: Optional[str] = None,
    on_retry: Optional[Callable[[BaseException, int, float], Any]] = None,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    **kwargs: Any,
) -> Any:
    """Execute a sync or async operation with exponential backoff."""
    cfg = config or RetryConfig()
    name = operation_name or getattr(operation, "__name__", "operation")
    last_error: Optional[BaseException] = None

    for attempt_index in range(cfg.max_attempts):
        try:
            return await _maybe_await(operation(*args, **kwargs))
        except cfg.retry_exceptions as exc:
            last_error = exc
            attempt_number = attempt_index + 1
            if attempt_number >= cfg.max_attempts:
                break
            delay = calculate_backoff(attempt_index, cfg)
            logger.warning(
                "[Retry] %s failed (attempt %s/%s): %s. Retrying in %.2fs.",
                name,
                attempt_number,
                cfg.max_attempts,
                exc,
                delay,
            )
            if on_retry is not None:
                await _maybe_await(on_retry(exc, attempt_number, delay))
            await sleep(delay)

    assert last_error is not None
    raise RetryExhaustedError(name, cfg.max_attempts, last_error) from last_error


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration required to instantiate one supported LLM provider."""

    name: str
    api_key_env: str
    model_env: str
    default_model: str


PROVIDER_CHAIN: Tuple[ProviderConfig, ...] = (
    ProviderConfig("openai", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini"),
    ProviderConfig("anthropic", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
    ProviderConfig("gemini", "GOOGLE_API_KEY", "GEMINI_MODEL", "gemini-1.5-pro"),
)


def configured_providers(
    environ: Optional[Mapping[str, str]] = None,
    chain: Sequence[ProviderConfig] = PROVIDER_CHAIN,
) -> list[ProviderConfig]:
    """Return providers whose API key is present and not a placeholder."""
    env = environ if environ is not None else os.environ
    available: list[ProviderConfig] = []
    for provider in chain:
        key = env.get(provider.api_key_env, "")
        if key and not key.startswith("your-") and key.lower() != "mock":
            available.append(provider)
    return available


def _response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", item.get("content", ""))))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def _strip_json_fences(text: str) -> str:
    clean = text.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in clean:
        clean = clean.split("```", 1)[1].split("```", 1)[0]
    return clean.strip()


def parse_structured_response(text: str, schema: Any = None) -> Any:
    """Parse JSON from an LLM response and validate it against an optional schema."""
    data = json.loads(_strip_json_fences(text))
    if schema is None:
        return data
    if hasattr(schema, "model_validate"):
        return schema.model_validate(data)
    if isinstance(schema, type):
        return schema(**data) if isinstance(data, dict) else schema(data)
    return data


class ProviderFallbackChain:
    """Try configured LLM providers in order, with transient retries and schema repair."""

    def __init__(
        self,
        providers: Optional[Sequence[ProviderConfig]] = None,
        retry_config: Optional[RetryConfig] = None,
        llm_factory: Optional[Callable[[ProviderConfig], Any]] = None,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        environ: Optional[Mapping[str, str]] = None,
    ):
        self.providers = list(providers) if providers is not None else configured_providers(environ)
        self.retry_config = retry_config or RetryConfig()
        self.llm_factory = llm_factory or self._default_llm_factory
        self.sleep = sleep

    @staticmethod
    def _default_llm_factory(provider: ProviderConfig) -> Any:
        api_key = os.getenv(provider.api_key_env)
        model = os.getenv(provider.model_env, provider.default_model)
        if provider.name == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model, api_key=api_key, temperature=0.1)
        if provider.name == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model, api_key=api_key, temperature=0.1)
        if provider.name == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0.1)
        raise ProviderUnavailableError(f"Unsupported LLM provider '{provider.name}'.")

    async def _invoke(self, llm: Any, messages: list[dict[str, str]]) -> Any:
        if hasattr(llm, "ainvoke"):
            return await retry_async(
                llm.ainvoke,
                messages,
                config=self.retry_config,
                operation_name="llm.ainvoke",
                sleep=self.sleep,
            )
        if hasattr(llm, "invoke"):
            return await retry_async(
                llm.invoke,
                messages,
                config=self.retry_config,
                operation_name="llm.invoke",
                sleep=self.sleep,
            )
        raise ProviderUnavailableError(f"LLM object {type(llm).__name__} has no invoke method.")

    async def generate_json(
        self,
        prompt: str,
        schema: Any = None,
        system_prompt: Optional[str] = None,
        allow_schema_correction: bool = True,
    ) -> Any:
        """Generate schema-valid JSON using the first healthy provider in the chain."""
        if not self.providers:
            names = ", ".join(p.api_key_env for p in PROVIDER_CHAIN)
            raise ProviderUnavailableError(f"No LLM providers configured. Set one of: {names}.")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        errors: list[str] = []
        for provider in self.providers:
            try:
                llm = self.llm_factory(provider)
                response = await self._invoke(llm, messages)
                text = _response_text(response)
                try:
                    return parse_structured_response(text, schema)
                except Exception as first_error:
                    if not allow_schema_correction:
                        raise SchemaCorrectionError(
                            f"{provider.name} returned invalid structured output: {first_error}"
                        ) from first_error

                    logger.warning(
                        "[ProviderFallback] %s returned invalid schema (%s); attempting one-shot correction.",
                        provider.name,
                        first_error,
                    )
                    correction_messages = messages + [
                        {"role": "assistant", "content": text},
                        {
                            "role": "user",
                            "content": (
                                "Your previous response was invalid structured output. "
                                f"Validation error: {first_error}. "
                                "Return ONLY corrected, valid JSON with no markdown fences."
                            ),
                        },
                    ]
                    corrected = await self._invoke(llm, correction_messages)
                    try:
                        return parse_structured_response(_response_text(corrected), schema)
                    except Exception as second_error:
                        raise SchemaCorrectionError(
                            f"{provider.name} failed schema correction: {second_error}"
                        ) from second_error
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                logger.warning("[ProviderFallback] Provider %s failed: %s", provider.name, exc)

        raise ProviderUnavailableError(
            "All configured LLM providers failed. " + " | ".join(errors)
        )


async def generate_json_with_fallback(
    prompt: str,
    schema: Any = None,
    system_prompt: Optional[str] = None,
) -> Any:
    """Convenience wrapper around the default configured provider chain."""
    return await ProviderFallbackChain().generate_json(
        prompt=prompt,
        schema=schema,
        system_prompt=system_prompt,
    )
