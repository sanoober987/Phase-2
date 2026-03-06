"""
Agent service — Groq integration with streaming, retry, and rate-limit protection.

Uses the OpenAI Python SDK pointed at Groq's OpenAI-compatible endpoint.
"""

import asyncio
import logging
import time
from typing import AsyncGenerator

from openai import (
    AsyncOpenAI,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
    APIStatusError,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Shared Groq client (OpenAI SDK with custom base_url)
# -------------------------------------------------------------------

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client

    if _client is None:
        settings = get_settings()

        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing. Add it to your .env file."
            )

        _client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            timeout=settings.groq_timeout,
            max_retries=0,  # we handle retries manually
        )

    return _client


async def close_client():
    global _client

    if _client:
        await _client.close()
        _client = None


# -------------------------------------------------------------------
# System Prompt
# -------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a helpful and intelligent AI assistant.

Rules:
- Answer clearly and accurately.
- Help users manage tasks if requested.
- Use markdown formatting when useful.
- If you don't know something, say so honestly.
"""


def build_system_message(user_id: str) -> dict:
    return {
        "role": "system",
        "content": f"{SYSTEM_PROMPT}\n\nUser ID: {user_id}",
    }


# -------------------------------------------------------------------
# Token estimation + trimming
# -------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def trim_messages(messages: list[dict], max_tokens: int) -> list[dict]:

    if not messages:
        return []

    total = sum(estimate_tokens(m.get("content", "")) for m in messages)

    if total <= max_tokens:
        return messages

    system = messages[0]
    last = messages[-1]

    history = messages[1:-1]

    budget = (
        max_tokens
        - estimate_tokens(system.get("content", ""))
        - estimate_tokens(last.get("content", ""))
    )

    while history and sum(estimate_tokens(m.get("content", "")) for m in history) > budget:
        history.pop(0)

    return [system] + history + [last]


# -------------------------------------------------------------------
# Per-user rate limiter
# -------------------------------------------------------------------

_user_requests: dict[str, list[float]] = {}


def check_rate_limit(user_id: str):

    settings = get_settings()

    max_rpm = settings.groq_user_rpm
    window = 60
    now = time.monotonic()

    if user_id not in _user_requests:
        _user_requests[user_id] = []

    _user_requests[user_id] = [
        t for t in _user_requests[user_id] if now - t < window
    ]

    if len(_user_requests[user_id]) >= max_rpm:
        raise RuntimeError(
            f"Rate limit exceeded ({max_rpm} messages per minute)."
        )

    _user_requests[user_id].append(now)


# -------------------------------------------------------------------
# Retry with exponential backoff
# -------------------------------------------------------------------


async def retry_with_backoff(coro_factory, retries=3):

    delay = 1

    for attempt in range(retries + 1):

        try:
            return await coro_factory()

        except RateLimitError:

            if attempt == retries:
                raise

            logger.warning("Rate limit hit. Retrying in %s seconds", delay)

            await asyncio.sleep(delay)

            delay *= 2

        except APIStatusError as e:

            if e.status_code >= 500 and attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                raise


# -------------------------------------------------------------------
# Error translation
# -------------------------------------------------------------------


def translate_error(e: Exception) -> RuntimeError:

    if isinstance(e, AuthenticationError):
        return RuntimeError("Invalid Groq API key.")

    if isinstance(e, RateLimitError):
        return RuntimeError(
            "Groq rate limit exceeded. Please wait and try again."
        )

    if isinstance(e, APIConnectionError):
        return RuntimeError(
            "Cannot connect to Groq. Check your internet connection."
        )

    if isinstance(e, APITimeoutError):
        return RuntimeError("Groq request timed out.")

    if isinstance(e, APIStatusError):
        return RuntimeError(f"Groq API error {e.status_code}: {e.message}")

    return RuntimeError(f"Unexpected error: {e}")


# -------------------------------------------------------------------
# Non-streaming agent call
# -------------------------------------------------------------------


async def run_agent(user_id: str, messages: list[dict]):

    settings = get_settings()

    check_rate_limit(user_id)

    system_message = build_system_message(user_id)

    full_messages = [system_message] + messages

    full_messages = trim_messages(
        full_messages,
        settings.groq_max_input_tokens,
    )

    logger.info(
        "Sending %s messages to Groq model=%s",
        len(full_messages),
        settings.groq_model,
    )

    try:

        response = await retry_with_backoff(
            lambda: get_client().chat.completions.create(
                model=settings.groq_model,
                messages=full_messages,
                max_tokens=settings.groq_max_tokens,
                temperature=0.7,
            )
        )

    except (
        AuthenticationError,
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        APIStatusError,
    ) as e:

        raise translate_error(e)

    if not response.choices:
        raise RuntimeError("Groq returned no response.")

    reply = response.choices[0].message.content

    return reply, []


# -------------------------------------------------------------------
# Streaming agent call
# -------------------------------------------------------------------


async def run_agent_stream(
    user_id: str,
    messages: list[dict],
) -> AsyncGenerator[str, None]:

    settings = get_settings()

    check_rate_limit(user_id)

    system_message = build_system_message(user_id)

    full_messages = [system_message] + messages

    full_messages = trim_messages(
        full_messages,
        settings.groq_max_input_tokens,
    )

    logger.info(
        "Streaming messages to Groq model=%s",
        settings.groq_model,
    )

    try:

        stream = await get_client().chat.completions.create(
            model=settings.groq_model,
            messages=full_messages,
            max_tokens=settings.groq_max_tokens,
            temperature=0.7,
            stream=True,
        )

        async for chunk in stream:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if delta and delta.content:
                yield delta.content

    except (
        AuthenticationError,
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        APIStatusError,
    ) as e:

        raise translate_error(e)


async def check_groq_health():

    settings = get_settings()

    if not settings.groq_api_key:
        return {
            "healthy": False,
            "error": "GROQ_API_KEY is not set",
        }

    try:

        client = get_client()

        # simple lightweight request
        await client.models.list()

        return {
            "healthy": True,
            "model": settings.groq_model
        }

    except AuthenticationError:
        return {
            "healthy": False,
            "error": "Invalid Groq API key"
        }

    except APIConnectionError:
        return {
            "healthy": False,
            "error": "Cannot connect to Groq"
        }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }
