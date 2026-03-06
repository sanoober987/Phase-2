# Research: Phase III Chat Agent

**Feature**: 001-phase-iii-chat-agent
**Date**: 2026-02-25
**Status**: Complete

---

## Item 1: OpenAI Agents SDK — Intent Routing and MCP Tool Dispatch

**Decision**: Use `openai-agents` Python SDK with MCP server integration via
`MCPServerStdio` transport. The Agent is constructed per-request with a `mcp_servers`
list pointing at the MCP server. Tool dispatch is automatic — the SDK handles the
function-call loop internally.

**Rationale**: The OpenAI Agents SDK natively supports MCP as a first-class tool
source. `Agent(model=..., mcp_servers=[mcp])` provides automatic intent routing from
the model's tool-calling output to MCP tool invocations. No custom intent parsing code
is needed. The SDK's `Runner.run()` returns the final assistant response after all
tool turns complete.

**Pattern**:
```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def run_agent(messages: list[dict], user_id: str) -> tuple[str, list]:
    async with MCPServerStdio(command="python",
                               args=["-m", "backend.app.mcp_tools.server"]) as mcp:
        agent = Agent(
            name="TodoAgent",
            model="gpt-4o-mini",
            instructions=f"You help user {user_id} manage their todo tasks.",
            mcp_servers=[mcp],
        )
        result = await Runner.run(agent, input=messages)
        return result.final_output, result.new_items
```

**Alternatives Considered**:
- LangChain agents: heavier dependency tree, more boilerplate for MCP integration
- Raw OpenAI function calling: requires manual tool dispatch loop
- LlamaIndex: adequate but less idiomatic for MCP

---

## Item 2: MCP Official SDK — Stateless Python MCP Server

**Decision**: Use `mcp` Python package (official MCP SDK) with `FastMCP` to build a
stateless server. Each tool function receives `user_id` as a parameter and opens a
fresh async DB session. The server is launched as a subprocess by the Agents SDK.

**Rationale**: The official `mcp` SDK provides `FastMCP`, which reduces boilerplate.
Stateless design (no shared state between tool calls) aligns with Principle IV.
Each tool call receives `user_id` injected by the agent's system prompt context and
validated inside the tool body.

**Pattern**:
```python
from mcp.server.fastmcp import FastMCP
from app.services.task_service import create_task as svc_create

mcp = FastMCP("todo-tools")

@mcp.tool()
async def add_task(user_id: str, title: str, description: str = "") -> dict:
    """Create a new task for the user."""
    if not user_id:
        return {"status": "error", "error": "user_id required"}
    async with get_async_session() as db:
        task = await svc_create(db, user_id, TaskCreate(title=title,
                                                         description=description))
        return {"status": "created", "data": {"id": str(task.id),
                                               "title": task.title}}
```

**Alternatives Considered**:
- Inline tools on the FastAPI process: tight coupling, harder to test independently
- HTTP-based MCP server (SSE): adds network hop; subprocess stdio is simpler for monorepo

---

## Item 3: Better Auth JWT Verification in FastAPI

**Decision**: Reuse the existing `get_current_user` dependency in
`backend/app/services/auth_service.py`. The `BETTER_AUTH_SECRET` env var maps to
`JWT_SECRET_KEY` in `config.py`. No code change needed to the verification logic —
only ensure `.env` sets `JWT_SECRET_KEY` = value of `BETTER_AUTH_SECRET`.

**Rationale**: The project already has a working JWT verify dependency. It uses PyJWT
with HS256. The `get_current_user` dependency is already used on all task routes. The
chat endpoint adds one additional check: `current_user["sub"] != user_id → 403`.

**Chat endpoint guard pattern**:
```python
@router.post("/api/{user_id}/chat")
async def chat(
    user_id: str,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user["sub"] != user_id:
        raise HTTPException(403, "Forbidden")
    ...
```

**Alternatives Considered**:
- Re-implementing verification with `python-jose`: redundant, existing PyJWT works
- Better Auth Python SDK: does not exist; Python side always validates JWT manually

---

## Item 4: Neon PostgreSQL + SQLModel Async Patterns for Conversation/Message Storage

**Decision**: Follow the established pattern in `database.py`: `create_async_engine`
with `asyncpg`, `async_session_maker` sessionmaker, `DateTime(timezone=True)` on all
timestamp fields. Add `Conversation` and `Message` models following the same pattern
as `Task`. Import them in `init_db()` so `create_all` registers the tables.

**Rationale**: The existing async engine and session factory work correctly with Neon.
The `DateTime(timezone=True)` fix must be applied to new models. `SQLModel.metadata
.create_all` in `init_db()` picks up new tables automatically when model files are
imported there.

**New model timestamp pattern**:
```python
from sqlalchemy import DateTime
from datetime import datetime, timezone

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True, nullable=False)
    created_at: datetime = Field(default_factory=_utcnow,
                                  sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=_utcnow,
                                  sa_type=DateTime(timezone=True))
```

**Alternatives Considered**:
- MongoDB for flexible message storage: adds another service, Neon already provisioned
- Redis for conversation cache: violates Principle IV (stateless, no in-memory state)

---

## Item 5: ChatKit UI vs Custom Chat Component

**Decision**: Build a lightweight custom React chat component (`ChatPanel.tsx`,
`ChatMessage.tsx`, `ChatInput.tsx`) using the existing Tailwind CSS setup and the
existing `api-client.ts` pattern. The component calls `POST /api/{user_id}/chat`
and renders the `{ reply, tool_calls, conversation_id }` response.

**Rationale**: The project uses Tailwind CSS and existing UI patterns. Building a
simple chat panel avoids adding a heavy third-party chat component with unknown
Tailwind compatibility. The existing `api-client.ts` handles auth headers, retries,
and error handling already. A custom component also gives full control over layout
integration with the existing task list dashboard.

**Alternatives Considered**:
- `@chatscope/chat-ui-kit-react`: ~200KB dependency, style conflicts with Tailwind
- Vercel AI SDK `useChat`: binds to specific Next.js streaming patterns, harder to retrofit

---

## Item 6: Stateless Chat Pipeline — Reconstructing Agent Context from DB Per Request

**Decision**: On every `POST /api/{user_id}/chat` request:
1. Load the last `CHAT_HISTORY_DEPTH` (default 20) messages from the `Message` table
2. Convert to OpenAI message format: `[{"role": "user"|"assistant", "content": "..."}]`
3. Append the new user message
4. Pass full list to `Runner.run(agent, input=messages)`
5. After agent completes, store user message + assistant reply in `Message` table
6. Return reply and conversation_id

**Rationale**: This is the exact pipeline mandated by Principle IV (Stateless Design)
and the constitution's Chat Endpoint Contract. No server-side session state is retained.
History depth of 20 messages balances context quality against token cost. Configurable
via `CHAT_HISTORY_DEPTH` env var. A `conversation_id` is passed in the request body
(optional on first message; backend creates `Conversation` record and returns the id).

**Alternatives Considered**:
- Always load all messages: unbounded token cost and latency risk
- Session-based context: violates Principle IV, breaks horizontal scaling
- Summarization of old messages: out of scope for Phase III
