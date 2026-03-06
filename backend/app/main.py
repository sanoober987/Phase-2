# backend/app/main.py

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.routes import auth, tasks, chat
from app.config import get_settings
from app.services.agent_service import (
    check_groq_health,
    close_client,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()

    # Startup
    logger.info("Starting backend (env=%s)...", settings.environment)
    await init_db()

    # Check Groq API key validity at startup (non-blocking — warn only)
    health = await check_groq_health()
    if health["healthy"]:
        logger.info("Groq OK — model=%s", settings.groq_model)
    else:
        logger.warning(
            "Groq health check FAILED: %s. Chat will fail until resolved.",
            health.get("error", "unknown"),
        )

    logger.info(
        "Config: model=%s, timeout=%ss, max_tokens=%d, max_input_tokens=%d, "
        "retries=%d, user_rpm=%d, history_depth=%d",
        settings.groq_model,
        settings.groq_timeout,
        settings.groq_max_tokens,
        settings.groq_max_input_tokens,
        settings.groq_max_retries,
        settings.groq_user_rpm,
        settings.chat_history_depth,
    )

    yield

    # Shutdown
    await close_client()
    logger.info("Backend shutdown complete.")


app = FastAPI(title="AI Task Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"message": "Backend is running successfully"}


@app.get("/health/ai", tags=["health"])
async def ai_health():
    """Check Groq API connectivity and key validity."""
    health = await check_groq_health()
    return {"groq": health}
