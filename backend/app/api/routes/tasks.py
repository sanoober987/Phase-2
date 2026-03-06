"""
Task CRUD endpoints.

RESTful API endpoints for task management with proper error handling.
"""

import logging
from typing import Optional
from uuid import UUID
from app.database import get_async_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import  get_current_user
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _db_error(operation: str, user_id: int, exc: Exception) -> HTTPException:
    """Log a database error and return a safe 503 HTTPException."""
    logger.error("Database error during %s for user %s: %s", operation, user_id, exc)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Database error during {operation}. Please try again.",
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    """Create a new task for the authenticated user."""
    logger.info("Creating task for user %s", current_user.id)
    try:
        task = await task_service.create_task(db, str(current_user.id), task_data)
        return TaskResponse.model_validate(task)
    except SQLAlchemyError as e:
        raise _db_error("create_task", current_user.id, e)


@router.get(
    "",
    response_model=TaskListResponse,
)
async def list_tasks(
    completed: Optional[bool] = Query(default=None, description="Filter by completion status"),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum number of tasks to return"),
    offset: int = Query(default=0, ge=0, description="Number of tasks to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends( get_async_session),
) -> TaskListResponse:
    """List tasks for the authenticated user with optional filtering and pagination."""
    logger.info("Listing tasks for user %s (completed=%s, limit=%s, offset=%s)",
                current_user.id, completed, limit, offset)
    try:
        tasks = await task_service.list_tasks(
            db, str(current_user.id), completed=completed, limit=limit, offset=offset
        )
        total = await task_service.count_tasks(db, str(current_user.id), completed=completed)
        return TaskListResponse(
            tasks=[TaskResponse.model_validate(t) for t in tasks],
            count=total,
        )
    except SQLAlchemyError as e:
        raise _db_error("list_tasks", current_user.id, e)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    """Get a specific task by ID for the authenticated user."""
    logger.info("Getting task %s for user %s", task_id, current_user.id)
    try:
        task = await task_service.get_task(db, str(current_user.id), task_id)
    except SQLAlchemyError as e:
        raise _db_error("get_task", current_user.id, e)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
async def patch_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    """Partially update a task for the authenticated user."""
    logger.info("Patching task %s for user %s", task_id, current_user.id)
    try:
        task = await task_service.update_task(db, str(current_user.id), task_id, task_data)
    except SQLAlchemyError as e:
        raise _db_error("patch_task", current_user.id, e)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a task for the authenticated user."""
    logger.info("Deleting task %s for user %s", task_id, current_user.id)
    try:
        deleted = await task_service.delete_task(db, str(current_user.id), task_id)
    except SQLAlchemyError as e:
        raise _db_error("delete_task", current_user.id, e)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.patch(
    "/{task_id}/complete",
    response_model=TaskResponse,
)
async def toggle_task_completion(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> TaskResponse:
    """Toggle task completion status for the authenticated user."""
    logger.info("Toggling completion for task %s for user %s", task_id, current_user.id)
    try:
        task = await task_service.toggle_task_completion(db, str(current_user.id), task_id)
    except SQLAlchemyError as e:
        raise _db_error("toggle_task_completion", current_user.id, e)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskResponse.model_validate(task)
