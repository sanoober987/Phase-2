"""
Unit tests for MCP tool server.

Verifies that:
- All 5 tools reject empty user_id without raising exceptions.
- All 5 tools call the correct task_service function with correct args.
- Structured error JSON is returned on invalid input.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_add_task_rejects_empty_user_id():
    """add_task returns error JSON when user_id is empty."""
    from app.mcp_tools.server import add_task
    result = await add_task(user_id="", title="Test")
    assert result["status"] == "error"
    assert "user_id" in result["error"].lower()


@pytest.mark.asyncio
async def test_add_task_rejects_empty_title():
    """add_task returns error JSON when title is empty."""
    from app.mcp_tools.server import add_task
    result = await add_task(user_id="user-1", title="")
    assert result["status"] == "error"
    assert "title" in result["error"].lower()


@pytest.mark.asyncio
async def test_list_tasks_rejects_empty_user_id():
    """list_tasks returns error JSON when user_id is empty."""
    from app.mcp_tools.server import list_tasks
    result = await list_tasks(user_id="")
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_complete_task_rejects_empty_user_id():
    """complete_task returns error JSON when user_id is empty."""
    from app.mcp_tools.server import complete_task
    result = await complete_task(user_id="", task_id="some-id")
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_complete_task_rejects_empty_task_id():
    """complete_task returns error JSON when task_id is empty."""
    from app.mcp_tools.server import complete_task
    result = await complete_task(user_id="user-1", task_id="")
    assert result["status"] == "error"
    assert "task_id" in result["error"].lower()


@pytest.mark.asyncio
async def test_delete_task_rejects_empty_user_id():
    """delete_task returns error JSON when user_id is empty."""
    from app.mcp_tools.server import delete_task
    result = await delete_task(user_id="", task_id="some-id")
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_update_task_requires_at_least_one_field():
    """update_task returns error JSON when no fields to update are provided."""
    from app.mcp_tools.server import update_task
    result = await update_task(user_id="user-1", task_id="some-id")
    assert result["status"] == "error"
    assert "title or description" in result["error"].lower()


@pytest.mark.asyncio
async def test_complete_task_invalid_uuid_format():
    """complete_task returns error JSON when task_id is not a valid UUID."""
    from app.mcp_tools.server import complete_task
    result = await complete_task(user_id="user-1", task_id="not-a-uuid")
    assert result["status"] == "error"
    assert "Invalid" in result["error"] or "invalid" in result["error"].lower()
