"""
MCP Tool Server — stateless FastMCP server exposing 5 task management tools.

Each tool:
  - Validates user_id is a non-empty string.
  - Opens a fresh async database session per call (stateless by design).
  - Returns structured JSON: {status, data} on success or {status, error} on failure.
  - Delegates to existing task_service functions (no duplicated logic).

Run as subprocess:
  python -m backend.app.mcp_tools.server
"""

import asyncio
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("todo-tools")


def _require_user(user_id: str) -> Optional[dict]:
    """Return an error dict if user_id is invalid, else None."""
    if not user_id or not user_id.strip():
        return {"status": "error", "error": "user_id is required and must be non-empty"}
    return None


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
async def add_task(user_id: str, title: str, description: str = "") -> dict:
    """Create a new task for the user.

    Args:
        user_id: The authenticated user's ID.
        title: The task title (required).
        description: Optional task description.

    Returns:
        JSON with status and created task data.
    """
    err = _require_user(user_id)
    if err:
        return err
    if not title or not title.strip():
        return {"status": "error", "error": "title is required and must be non-empty"}

    try:
        from app.database import async_session_maker
        from app.services import task_service
        from app.schemas.task import TaskCreate
        async with async_session_maker() as db:
            task = await task_service.create_task(
                db, user_id, TaskCreate(title=title.strip(), description=description or None)
            )
            return {
                "status": "created",
                "data": {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                },
            }
    except Exception as exc:
        logger.exception("add_task failed for user %s: %s", user_id, exc)
        return {"status": "error", "error": str(exc)}


@mcp.tool()
async def list_tasks(user_id: str, completed: Optional[bool] = None) -> dict:
    """List tasks for the user, optionally filtered by completion status.

    Args:
        user_id: The authenticated user's ID.
        completed: If True, return only completed tasks; if False, only pending;
                   if None (default), return all tasks.

    Returns:
        JSON with status and list of task objects.
    """
    err = _require_user(user_id)
    if err:
        return err

    try:
        from app.database import async_session_maker
        from app.services import task_service
        async with async_session_maker() as db:
            tasks = await task_service.list_tasks(db, user_id, completed=completed)
            return {
                "status": "ok",
                "data": [
                    {
                        "id": str(t.id),
                        "title": t.title,
                        "description": t.description,
                        "completed": t.completed,
                    }
                    for t in tasks
                ],
            }
    except Exception as exc:
        logger.exception("list_tasks failed for user %s: %s", user_id, exc)
        return {"status": "error", "error": str(exc)}


@mcp.tool()
async def complete_task(user_id: str, task_id: str) -> dict:
    """Mark a task as completed.

    Args:
        user_id: The authenticated user's ID.
        task_id: The UUID of the task to complete.

    Returns:
        JSON with status and updated task data.
    """
    err = _require_user(user_id)
    if err:
        return err
    if not task_id or not task_id.strip():
        return {"status": "error", "error": "task_id is required"}

    try:
        from uuid import UUID
        from app.database import async_session_maker
        from app.services import task_service
        from app.schemas.task import TaskUpdate
        async with async_session_maker() as db:
            task = await task_service.update_task(
                db, user_id, UUID(task_id), TaskUpdate(completed=True)
            )
            if task is None:
                return {"status": "error", "error": f"Task {task_id} not found"}
            return {
                "status": "completed",
                "data": {"id": str(task.id), "title": task.title, "completed": task.completed},
            }
    except ValueError:
        return {"status": "error", "error": f"Invalid task_id format: {task_id}"}
    except Exception as exc:
        logger.exception("complete_task failed for user %s task %s: %s", user_id, task_id, exc)
        return {"status": "error", "error": str(exc)}


@mcp.tool()
async def delete_task(user_id: str, task_id: str) -> dict:
    """Delete a task permanently.

    Args:
        user_id: The authenticated user's ID.
        task_id: The UUID of the task to delete.

    Returns:
        JSON with status and deleted task ID.
    """
    err = _require_user(user_id)
    if err:
        return err
    if not task_id or not task_id.strip():
        return {"status": "error", "error": "task_id is required"}

    try:
        from uuid import UUID
        from app.database import async_session_maker
        from app.services import task_service
        async with async_session_maker() as db:
            deleted = await task_service.delete_task(db, user_id, UUID(task_id))
            if not deleted:
                return {"status": "error", "error": f"Task {task_id} not found"}
            return {"status": "deleted", "data": {"id": task_id}}
    except ValueError:
        return {"status": "error", "error": f"Invalid task_id format: {task_id}"}
    except Exception as exc:
        logger.exception("delete_task failed for user %s task %s: %s", user_id, task_id, exc)
        return {"status": "error", "error": str(exc)}


@mcp.tool()
async def update_task(
    user_id: str,
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Update a task's title and/or description.

    Args:
        user_id: The authenticated user's ID.
        task_id: The UUID of the task to update.
        title: New title (optional).
        description: New description (optional).

    Returns:
        JSON with status and updated task data.
    """
    err = _require_user(user_id)
    if err:
        return err
    if not task_id or not task_id.strip():
        return {"status": "error", "error": "task_id is required"}
    if title is None and description is None:
        return {"status": "error", "error": "At least one of title or description must be provided"}

    try:
        from uuid import UUID
        from app.database import async_session_maker
        from app.services import task_service
        from app.schemas.task import TaskUpdate
        async with async_session_maker() as db:
            task = await task_service.update_task(
                db, user_id, UUID(task_id), TaskUpdate(title=title, description=description)
            )
            if task is None:
                return {"status": "error", "error": f"Task {task_id} not found"}
            return {
                "status": "updated",
                "data": {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                },
            }
    except ValueError:
        return {"status": "error", "error": f"Invalid task_id format: {task_id}"}
    except Exception as exc:
        logger.exception("update_task failed for user %s task %s: %s", user_id, task_id, exc)
        return {"status": "error", "error": str(exc)}


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
