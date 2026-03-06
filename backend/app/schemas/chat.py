"""
Chat schemas — request and response Pydantic models for the chat endpoint.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /api/{user_id}/chat."""

    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="Existing conversation ID. Omit on first message — backend creates one.",
    )


class ToolCallRecord(BaseModel):
    """Record of a single MCP tool call made by the agent."""

    tool: str
    arguments: dict = Field(default_factory=dict)
    result: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response body for POST /api/{user_id}/chat."""

    reply: str = Field(..., description="The agent's plain-language response.")
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list,
        description="Log of MCP tool calls made during this turn.",
    )
    conversation_id: str = Field(..., description="UUID of the conversation (new or existing).")
