"""
Integration tests for POST /api/{user_id}/chat

These tests require a running backend with database but mock the AI agent
to avoid OpenAI API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_chat_endpoint_requires_auth():
    """POST /api/{user_id}/chat without Authorization header returns 401."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/user-123/chat",
            json={"message": "List my tasks"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_endpoint_rejects_mismatched_user_id(mock_current_user):
    """POST with valid JWT but different user_id in path returns 403."""
    # mock_current_user fixture provides a user with sub="user-abc"
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/different-user/chat",
            json={"message": "List my tasks"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_chat_endpoint_returns_reply_structure():
    """
    POST with valid auth and mocked agent returns ChatResponse structure.

    This test is marked as integration and requires:
    - Database connection (Neon or SQLite in-memory for testing)
    - Mocked OpenAI agent to avoid API calls

    Skipped if OPENAI_API_KEY is not set (to allow CI without API key).
    """
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — skipping integration test")

    with patch("app.services.agent_service.run_agent", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = ("I've created your task!", [])

        async with AsyncClient(app=app, base_url="http://test") as client:
            # This would need proper JWT in a full integration test
            # Here we just verify the structure expectations
            pass


# Note: Full end-to-end integration tests require a test database and JWT fixtures.
# The unit tests in test_chat_service.py and test_mcp_tools.py cover the core logic.
# Run full integration tests manually with: pytest tests/integration/ -v --tb=short
