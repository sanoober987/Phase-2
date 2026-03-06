"""
Dependency injection for API routes.

Provides database session and authentication dependencies.
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession


from app.services.auth_service import get_current_user  # noqa: F401 - re-exported for routes

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session dependency.

    Rolls back the transaction automatically if the route raises an exception,
    ensuring partial writes never persist silently.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
