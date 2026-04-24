"""Exponential-backoff retry helpers for external API calls.

Wraps provider methods so transient failures (429, 529, 5xx, timeouts,
connection errors) don't immediately bubble up — we retry up to 3× with
1s/2s/4s delays plus jitter.
"""

import asyncio
import logging
import random
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TypeVar

import anthropic
import httpx
import openai

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _should_retry(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code in RETRYABLE_STATUS:
        return True
    if isinstance(exc, anthropic.APIConnectionError):
        return True
    if isinstance(exc, (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError)):
        return True
    if isinstance(exc, openai.APIStatusError) and getattr(exc, "status_code", None) in RETRYABLE_STATUS:
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in RETRYABLE_STATUS:
        return True
    # Google genai & generic providers — match on message text as fallback
    msg = str(exc).lower()
    if any(code in msg for code in (
        "429", "503", "504", "529",
        "overloaded", "unavailable", "resource_exhausted", "rate limit",
    )):
        return True
    return False


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    label: str,
    max_retries: int = 3,
) -> T:
    """Retry a one-shot API call on transient errors. Total attempts = max_retries + 1."""
    last: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last = e
            if attempt == max_retries or not _should_retry(e):
                raise
            delay = (2 ** attempt) + random.uniform(0, 0.5)
            logger.warning(
                "%s failed (attempt %d/%d): %s — retry in %.1fs",
                label, attempt + 1, max_retries + 1, type(e).__name__, delay,
            )
            await asyncio.sleep(delay)
    assert last is not None
    raise last


async def stream_with_retry(
    fn: Callable[[], AsyncIterator[T]],
    *,
    label: str,
    max_retries: int = 3,
) -> AsyncIterator[T]:
    """Retry a streaming API call, but only if it fails BEFORE the first chunk
    is yielded — otherwise we'd duplicate already-received tokens downstream.
    """
    for attempt in range(max_retries + 1):
        first = True
        try:
            async for chunk in fn():
                first = False
                yield chunk
            return
        except Exception as e:
            if not first or attempt == max_retries or not _should_retry(e):
                raise
            delay = (2 ** attempt) + random.uniform(0, 0.5)
            logger.warning(
                "%s stream failed before first chunk (attempt %d/%d): %s — retry in %.1fs",
                label, attempt + 1, max_retries + 1, type(e).__name__, delay,
            )
            await asyncio.sleep(delay)
