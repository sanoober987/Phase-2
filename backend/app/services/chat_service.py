"""
Chat service — conversation and message persistence.

All functions are stateless (no in-memory state); they read from and write to
the database on every call, in accordance with Principle IV (Stateless Design).
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    db: AsyncSession,
    user_id: str,
    conversation_id: Optional[UUID] = None,
) -> Conversation:
    """
    Return an existing conversation (verified to belong to user_id) or create a new one.

    Raises HTTPException(403) if conversation_id is provided but belongs to another user.
    """
    if conversation_id is not None:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this conversation is forbidden.",
            )
        return conversation

    # Create a new conversation
    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    logger.info("Created new conversation %s for user %s", conversation.id, user_id)
    return conversation


async def load_history(
    db: AsyncSession,
    conversation_id: UUID,
    limit: int = 20,
) -> list[Message]:
    """
    Load the most recent `limit` messages for a conversation, ordered oldest-first
    so the AI agent receives them in chronological order.
    """
    # Fetch the most recent `limit` messages (desc), then reverse to chronological order
    subq = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .subquery()
    )
    result = await db.execute(
        select(Message)
        .where(Message.id == subq.c.id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def append_user_message(
    db: AsyncSession,
    conversation_id: UUID,
    content: str,
) -> Message:
    """Persist a user message to the conversation."""
    msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def append_assistant_message(
    db: AsyncSession,
    conversation_id: UUID,
    content: str,
    tool_calls: Optional[list] = None,
) -> Message:
    """Persist an assistant (AI) response to the conversation."""
    msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        tool_calls=tool_calls,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
