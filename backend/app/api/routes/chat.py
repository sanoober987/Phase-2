"""
Chat API routes:
  - POST /api/{user_id}/chat          — blocking JSON response
  - POST /api/{user_id}/chat/stream   — real-time SSE streaming

Both endpoints share the same pipeline:
  1. Verify JWT matches user_id path param.
  2. Get or create conversation.
  3. Load conversation history from DB.
  4. Build message list for the LLM.
  5. Persist the user message (before calling the model).
  6. Call agent (blocking or streaming).
  7. Persist the assistant reply.
  8. Return response.
"""

import json
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_async_session
from app.config import get_settings
from app.schemas.chat import ChatRequest, ChatResponse, ToolCallRecord
from app.services.chat_service import (
    append_assistant_message,
    append_user_message,
    get_or_create_conversation,
    load_history,
)
from app.services.agent_service import run_agent, run_agent_stream

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _verify_user(current_user, user_id: str) -> str:
    """Verify JWT user matches path param. Returns token_user_id."""
    token_user_id = str(current_user.id)
    if not token_user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication user.")
    if str(token_user_id) != str(user_id):
        raise HTTPException(
            status_code=403,
            detail="The authenticated user does not match the requested user_id.",
        )
    return token_user_id


async def _prepare_chat(
    db: AsyncSession,
    user_id: str,
    body: ChatRequest,
) -> tuple:
    """
    Shared setup: validate, get conversation, load history, build messages.
    Returns (conversation, messages_for_agent).
    """
    if not body.message or not body.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    conversation = await get_or_create_conversation(
        db, user_id=user_id, conversation_id=body.conversation_id
    )

    settings = get_settings()
    history = await load_history(db, conversation.id, limit=settings.chat_history_depth)

    messages: List[Dict[str, Any]] = [
        {"role": m.role, "content": m.content} for m in history
    ]
    messages.append({"role": "user", "content": body.message.strip()})

    return conversation, messages


# ---------------------------------------------------------------------------
# POST /api/{user_id}/chat — blocking JSON response
# ---------------------------------------------------------------------------
@router.post(
    "/api/{user_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI task agent (blocking)",
)
async def chat(
    user_id: str,
    body: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> ChatResponse:
    """
    Blocking chat endpoint. Waits for the full AI response before returning.
    Use /chat/stream for real-time token-by-token delivery.
    """
    _verify_user(current_user, user_id)
    conversation = None

    try:
        conversation, messages = await _prepare_chat(db, user_id, body)

        # Persist user message FIRST (so it's saved even if the model call fails)
        await append_user_message(db, conversation.id, body.message.strip())

        # Call Groq (blocking, with retry)
        reply, raw_tool_calls = await run_agent(user_id, messages)

        # Persist assistant reply
        await append_assistant_message(
            db, conversation.id, reply, raw_tool_calls or None
        )

    except HTTPException:
        raise

    except RuntimeError as exc:
        logger.error(
            "Agent error | user=%s | conv=%s | %s",
            user_id,
            getattr(conversation, "id", "N/A"),
            exc,
        )
        # Map specific errors to appropriate HTTP codes
        detail = str(exc)
        status_code = status.HTTP_502_BAD_GATEWAY
        if "rate limit" in detail.lower() or "Rate limit" in detail:
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif "API key" in detail:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        raise HTTPException(status_code=status_code, detail=detail) from exc

    except Exception as exc:
        logger.exception(
            "Chat pipeline failed | user=%s | conv=%s",
            user_id,
            getattr(conversation, "id", "N/A"),
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {type(exc).__name__}: {exc}",
        ) from exc

    tool_calls = [
        ToolCallRecord(
            tool=tc.get("tool", "unknown"),
            arguments=tc.get("arguments", {}),
            result=tc.get("result", {}),
        )
        for tc in (raw_tool_calls or [])
    ]

    return ChatResponse(
        reply=reply,
        tool_calls=tool_calls,
        conversation_id=str(conversation.id),
    )


# ---------------------------------------------------------------------------
# POST /api/{user_id}/chat/stream — SSE streaming response
# ---------------------------------------------------------------------------
@router.post(
    "/api/{user_id}/chat/stream",
    summary="Send a message to the AI task agent (streaming SSE)",
)
async def chat_stream(
    user_id: str,
    body: ChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Streaming chat endpoint. Returns Server-Sent Events (SSE) with:
      - event: token   -> individual text chunks from the AI
      - event: done    -> final message with conversation_id
      - event: error   -> error details if something goes wrong

    The frontend should use fetch + ReadableStream to consume.
    """
    _verify_user(current_user, user_id)

    # Prepare chat (validate, load history) BEFORE starting the stream
    try:
        conversation, messages = await _prepare_chat(db, user_id, body)

        # Persist user message BEFORE streaming starts.
        # This way the user's message is never lost even if the client
        # disconnects or the model call fails mid-stream.
        await append_user_message(db, conversation.id, body.message.strip())

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Stream preparation failed for user=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    async def event_generator():
        """SSE event generator. Yields text/event-stream formatted data."""
        full_reply = ""
        try:
            async for chunk in run_agent_stream(user_id, messages):
                full_reply += chunk
                yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"

            # Stream complete — persist assistant reply
            await append_assistant_message(db, conversation.id, full_reply, None)

            yield f"event: done\ndata: {json.dumps({'conversation_id': str(conversation.id), 'full_reply': full_reply})}\n\n"

        except RuntimeError as exc:
            logger.error("Stream agent error: %s", exc)
            # Save partial reply if we got anything before the error
            if full_reply:
                try:
                    await append_assistant_message(
                        db, conversation.id, full_reply + "\n\n[Error: response interrupted]", None
                    )
                except Exception:
                    logger.warning("Failed to save partial stream reply")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

        except Exception as exc:
            logger.exception("Stream pipeline failed for user=%s", user_id)
            yield f"event: error\ndata: {json.dumps({'error': f'{type(exc).__name__}: {exc}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
