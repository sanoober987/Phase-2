"""
Message SQLModel definition.

Represents a single message in a conversation.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, JSON, Text
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Message(SQLModel, table=True):
    """Message database model — one per turn in a conversation."""

    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    conversation_id: UUID = Field(
        foreign_key="conversations.id",
        index=True,
        nullable=False,
    )
    role: str = Field(nullable=False)  # "user" | "assistant"
    content: str = Field(sa_column=Column(Text, nullable=False))
    tool_calls: Optional[list] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_type=DateTime(timezone=True),
    )
