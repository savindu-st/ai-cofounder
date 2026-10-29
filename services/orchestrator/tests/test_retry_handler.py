import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from services.orchestrator.app.orchestration.retry_handler import (
    ProviderConfig,
    ProviderFallbackChain,
    RetryConfig,
    RetryExhaustedError,
    calculate_backoff,
    retry_async,
)


def test_backoff_is_exponential_capped_and_jittered():
    cfg = RetryConfig(base_delay=0.5, max_delay=3.0, jitter=False)
    assert calculate_backoff(0, cfg) == 0.5
    assert calculate_backoff(1, cfg) == 1.0
    assert calculate_backoff(4, cfg) == 3.0
    assert calculate_backoff(0, cfg, random_value=0.25) == 0.5

    jittered = RetryConfig(base_delay=1.0, max_delay=10.0, jitter=True)
    assert calculate_backoff(0, jittered, random_value=0.5) == 1.5
    assert calculate_backoff(0, jittered, random_value=5.0) == 2.0


def test_retry_async_succeeds_after_transient_failures():
    attempts = {"count": 0}
    sleeps = []

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    async def fake_sleep(delay):
        sleeps.append(delay)

    result = asyncio.run(
        retry_async(
            flaky,
            config=RetryConfig(max_attempts=3, base_delay=0.01, jitter=False),
            sleep=fake_sleep,
        )
    )
    assert result == "ok"
    assert attempts["count"] == 3
    assert sleeps == [0.01, 0.02]


def test_retry_async_raises_with_last_error():
    async def always_fail():
        raise ValueError("nope")

    with pytest.raises(RetryExhaustedError) as exc_info:
        asyncio.run(
            retry_async(
                always_fail,
                config=RetryConfig(max_attempts=2, base_delay=0, jitter=False),
                sleep=lambda delay: asyncio.sleep(0),
            )
        )
    assert exc_info.value.attempts == 2
    assert isinstance(exc_info.value.last_error, ValueError)


def test_provider_fallback_moves_to_next_provider():
    providers = [
        ProviderConfig("primary", "PRIMARY_KEY", "PRIMARY_MODEL", "x"),
        ProviderConfig("secondary", "SECONDARY_KEY", "SECONDARY_MODEL", "y"),
    ]

    class Broken:
        async def ainvoke(self, messages):
            raise RuntimeError("provider down")

    class Healthy:
        async def ainvoke(self, messages):
            return SimpleNamespace(content='{"status": "ok"}')

    chain = ProviderFallbackChain(
        providers=providers,
        llm_factory=lambda provider: Broken() if provider.name == "primary" else Healthy(),
        retry_config=RetryConfig(max_attempts=1, base_delay=0, jitter=False),
    )
    result = asyncio.run(chain.generate_json("hello"))
    assert result == {"status": "ok"}


class Answer(BaseModel):
    answer: int


def test_schema_correction_retries_once():
    calls = []

    class CorrectingModel:
        async def ainvoke(self, messages):
            calls.append(messages)
            if len(calls) == 1:
                return SimpleNamespace(content='{"answer": "invalid"}')
            return SimpleNamespace(content='{"answer": 7}')

    chain = ProviderFallbackChain(
        providers=[ProviderConfig("fake", "FAKE_KEY", "FAKE_MODEL", "fake")],
        llm_factory=lambda provider: CorrectingModel(),
        retry_config=RetryConfig(max_attempts=1, base_delay=0, jitter=False),
    )
    result = asyncio.run(chain.generate_json("question", schema=Answer))
    assert isinstance(result, Answer)
    assert result.answer == 7
    assert len(calls) == 2
    assert "invalid structured output" in calls[1][-1]["content"]


def test_no_configured_providers_raises():
    chain = ProviderFallbackChain(providers=[])
    with pytest.raises(Exception) as exc_info:
        asyncio.run(chain.generate_json("hello"))
    assert "No LLM providers configured" in str(exc_info.value)
