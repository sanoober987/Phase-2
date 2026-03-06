"""
Unit tests for agent_service.py

Tests cover:
  - run_agent success, error translation, empty response
  - Per-user rate limiting
  - Token-aware message trimming
  - Retry with exponential backoff
  - Health check (success, no key, bad key)
"""

import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from openai import AuthenticationError, APIConnectionError, RateLimitError, APIStatusError


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------
def _mock_settings(**overrides):
    """Build a mock Settings object with sensible defaults."""
    defaults = {
        "openai_api_key": "sk-test-key",
        "openai_model": "gpt-4o-mini",
        "openai_timeout": 60.0,
        "openai_max_tokens": 2048,
        "openai_max_input_tokens": 8000,
        "openai_max_retries": 3,
        "openai_user_rpm": 20,
        "chat_history_depth": 20,
        "environment": "test",
    }
    defaults.update(overrides)
    s = MagicMock()
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_chat_response(content: str = "Hello!", model: str = "gpt-4o-mini"):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    response.model = model
    return response


def _mock_empty_response():
    message = MagicMock()
    message.content = ""
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    response.usage = None
    response.model = "gpt-4o-mini"
    return response


def _patch_settings(**overrides):
    """Return a patch context manager for get_settings."""
    return patch("app.services.agent_service.get_settings", return_value=_mock_settings(**overrides))


def _patch_client(mock_client):
    return patch("app.services.agent_service._get_client", return_value=mock_client)


def _make_client(create_return=None, create_side_effect=None):
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    if create_side_effect:
        mock_client.chat.completions.create = AsyncMock(side_effect=create_side_effect)
    else:
        mock_client.chat.completions.create = AsyncMock(return_value=create_return)
    return mock_client


# ---------------------------------------------------------------------------
# run_agent — success and error cases
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_agent_returns_string_and_list():
    """run_agent returns (str, list) on success."""
    client = _make_client(create_return=_mock_chat_response("I've added your task!"))

    with _patch_settings(), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent
        reply, tool_calls = await run_agent(
            user_id="user-123",
            messages=[{"role": "user", "content": "Add task: Buy milk"}],
        )

    assert reply == "I've added your task!"
    assert isinstance(tool_calls, list)
    assert len(tool_calls) == 0


@pytest.mark.asyncio
async def test_run_agent_user_id_in_system_prompt():
    """System prompt must contain the user_id."""
    captured_kwargs = {}

    async def mock_create(**kwargs):
        captured_kwargs.update(kwargs)
        return _mock_chat_response("Done")

    client = MagicMock()
    client.chat.completions.create = mock_create

    with _patch_settings(), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent
        await run_agent(user_id="my-special-user", messages=[])

    messages = captured_kwargs.get("messages", [])
    assert "my-special-user" in messages[0].get("content", "")


@pytest.mark.asyncio
async def test_run_agent_raises_on_auth_error():
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.headers = {}
    client = _make_client(create_side_effect=AuthenticationError(
        message="Invalid API key", response=mock_response,
        body={"error": {"message": "Invalid API key"}},
    ))

    with _patch_settings(), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent
        with pytest.raises(RuntimeError, match="API key is invalid"):
            await run_agent(user_id="u", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_run_agent_raises_on_connection_error():
    client = _make_client(create_side_effect=APIConnectionError(request=MagicMock()))

    with _patch_settings(), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent
        with pytest.raises(RuntimeError, match="Cannot connect to OpenAI"):
            await run_agent(user_id="u", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_run_agent_raises_on_empty_response():
    client = _make_client(create_return=_mock_empty_response())

    with _patch_settings(), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent
        with pytest.raises(RuntimeError, match="empty response"):
            await run_agent(user_id="u", messages=[{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Per-user rate limiting
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rate_limit_blocks_excessive_requests():
    """Exceeding OPENAI_USER_RPM raises RuntimeError."""
    client = _make_client(create_return=_mock_chat_response("ok"))

    # Set RPM to 2 for easy testing
    with _patch_settings(openai_user_rpm=2), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent

        await run_agent(user_id="rate-user", messages=[{"role": "user", "content": "1"}])
        await run_agent(user_id="rate-user", messages=[{"role": "user", "content": "2"}])

        with pytest.raises(RuntimeError, match="Rate limit"):
            await run_agent(user_id="rate-user", messages=[{"role": "user", "content": "3"}])


@pytest.mark.asyncio
async def test_rate_limit_is_per_user():
    """Different users have independent rate limits."""
    client = _make_client(create_return=_mock_chat_response("ok"))

    with _patch_settings(openai_user_rpm=1), _patch_client(client), \
         patch("app.services.agent_service._user_request_log", {}):
        from app.services.agent_service import run_agent

        await run_agent(user_id="user-a", messages=[{"role": "user", "content": "hi"}])
        # user-b should succeed even though user-a is at limit
        await run_agent(user_id="user-b", messages=[{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# Token-aware message trimming
# ---------------------------------------------------------------------------
def test_trim_messages_no_trim_needed():
    from app.services.agent_service import trim_messages
    msgs = [
        {"role": "system", "content": "You are an assistant."},
        {"role": "user", "content": "Hello"},
    ]
    result = trim_messages(msgs, max_input_tokens=8000)
    assert len(result) == 2


def test_trim_messages_drops_oldest_history():
    from app.services.agent_service import trim_messages
    msgs = [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "A" * 4000},      # ~1000 tokens
        {"role": "assistant", "content": "B" * 4000},  # ~1000 tokens
        {"role": "user", "content": "C" * 4000},       # ~1000 tokens
        {"role": "assistant", "content": "D" * 4000},  # ~1000 tokens
        {"role": "user", "content": "Current question"},
    ]
    # Budget of 600 tokens — must drop old history
    result = trim_messages(msgs, max_input_tokens=600)
    # System (first) and current user message (last) must always survive
    assert result[0]["role"] == "system"
    assert result[-1]["content"] == "Current question"
    assert len(result) < len(msgs)


def test_trim_messages_preserves_two_messages():
    """With only system + user, nothing can be trimmed."""
    from app.services.agent_service import trim_messages
    msgs = [
        {"role": "system", "content": "X" * 1000},
        {"role": "user", "content": "Y" * 1000},
    ]
    result = trim_messages(msgs, max_input_tokens=10)  # Way too small
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Retry with backoff
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retry_succeeds_after_rate_limit():
    """_retry_with_backoff retries on RateLimitError and succeeds."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {}

    call_count = 0

    async def flaky_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError(
                message="Rate limit", response=mock_resp,
                body={"error": {"message": "Rate limit"}},
            )
        return "success"

    with _patch_settings(openai_max_retries=3):
        from app.services.agent_service import _retry_with_backoff
        result = await _retry_with_backoff(flaky_call, retries=3, base_delay=0.01)

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    """_retry_with_backoff raises after exhausting retries."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {}

    async def always_fail():
        raise RateLimitError(
            message="Rate limit", response=mock_resp,
            body={"error": {"message": "Rate limit"}},
        )

    with _patch_settings(openai_max_retries=2):
        from app.services.agent_service import _retry_with_backoff
        with pytest.raises(RateLimitError):
            await _retry_with_backoff(always_fail, retries=2, base_delay=0.01)


@pytest.mark.asyncio
async def test_retry_does_not_retry_auth_errors():
    """Auth errors should not be retried."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.headers = {}

    call_count = 0

    async def auth_fail():
        nonlocal call_count
        call_count += 1
        raise AuthenticationError(
            message="Bad key", response=mock_resp,
            body={"error": {"message": "Bad key"}},
        )

    with _patch_settings(openai_max_retries=3):
        from app.services.agent_service import _retry_with_backoff
        with pytest.raises(AuthenticationError):
            await _retry_with_backoff(auth_fail, retries=3, base_delay=0.01)

    # Auth error should NOT be retried — called exactly once
    assert call_count == 1


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_openai_health_success():
    mock_client = MagicMock()
    mock_client.models = MagicMock()
    mock_client.models.retrieve = AsyncMock(return_value=MagicMock())

    with _patch_settings(openai_api_key="sk-test"), _patch_client(mock_client):
        from app.services.agent_service import check_openai_health
        result = await check_openai_health()

    assert result["healthy"] is True


@pytest.mark.asyncio
async def test_check_openai_health_no_key():
    with _patch_settings(openai_api_key=""):
        from app.services.agent_service import check_openai_health
        result = await check_openai_health()

    assert result["healthy"] is False
    assert "not set" in result["error"]


@pytest.mark.asyncio
async def test_check_openai_health_bad_key():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.headers = {}
    mock_client = MagicMock()
    mock_client.models.retrieve = AsyncMock(
        side_effect=AuthenticationError(
            message="Invalid key", response=mock_resp,
            body={"error": {"message": "Invalid key"}},
        )
    )

    with _patch_settings(openai_api_key="sk-bad"), _patch_client(mock_client):
        from app.services.agent_service import check_openai_health
        result = await check_openai_health()

    assert result["healthy"] is False
    assert "Invalid" in result["error"]
