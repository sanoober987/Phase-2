"""
Unit tests for chat_service.py

Tests conversation creation, history loading, and message persistence.
Uses in-memory SQLite via pytest-asyncio fixtures.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_service import (
    get_or_create_conversation,
    load_history,
    append_user_message,
    append_assistant_message,
)
from app.models.conversation import Conversation
from app.models.message import Message


@pytest.fixture
def mock_db():
    """Mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_get_or_create_conversation_creates_new_when_no_id(mock_db):
    """When conversation_id is None, a new Conversation is created."""
    user_id = "user-123"

    # refresh should populate the conversation with an id
    async def fake_refresh(obj):
        obj.id = uuid4()
        obj.user_id = user_id

    mock_db.refresh.side_effect = fake_refresh

    conv = await get_or_create_conversation(mock_db, user_id, conversation_id=None)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert isinstance(conv, Conversation)
    assert conv.user_id == user_id


@pytest.mark.asyncio
async def test_get_or_create_conversation_raises_403_on_wrong_user(mock_db):
    """When conversation belongs to a different user, raises 403."""
    from fastapi import HTTPException

    existing_conv = Conversation(id=uuid4(), user_id="other-user")

    # Mock the execute + scalar_one_or_none chain
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_conv
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await get_or_create_conversation(mock_db, "requesting-user", conversation_id=existing_conv.id)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_append_user_message_saves_correct_role(mock_db):
    """append_user_message creates a Message with role='user'."""
    conversation_id = uuid4()

    async def fake_refresh(obj):
        obj.id = uuid4()

    mock_db.refresh.side_effect = fake_refresh

    msg = await append_user_message(mock_db, conversation_id, "Hello agent")

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert isinstance(msg, Message)
    assert msg.role == "user"
    assert msg.content == "Hello agent"


@pytest.mark.asyncio
async def test_append_assistant_message_saves_tool_calls(mock_db):
    """append_assistant_message stores tool_calls as JSON."""
    conversation_id = uuid4()
    tool_calls = [{"tool": "add_task", "arguments": {"title": "Buy milk"}, "result": {"status": "created"}}]

    async def fake_refresh(obj):
        obj.id = uuid4()

    mock_db.refresh.side_effect = fake_refresh

    msg = await append_assistant_message(
        mock_db, conversation_id, "I've added 'Buy milk' to your tasks.", tool_calls
    )

    assert msg.role == "assistant"
    assert msg.tool_calls == tool_calls
