# Tasks: Phase III — Todo AI Chat Agent

**Feature**: 001-phase-iii-chat-agent
**Branch**: 001-phase-iii-chat-agent
**Date**: 2026-02-25
**Spec**: specs/001-phase-iii-chat-agent/spec.md
**Plan**: specs/001-phase-iii-chat-agent/plan.md
**Data Model**: specs/001-phase-iii-chat-agent/data-model.md
**API Contract**: specs/001-phase-iii-chat-agent/contracts/api.yaml

---

## Format: `[ID] [P?] [Story?] Description — exact file path`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[USn]**: Maps task to User Story for traceability
- Every task includes an exact file path

---

## Phase 1: Setup & Dependencies

**Goal**: Add new Python dependencies and environment configuration.
**Blocks**: All phases that follow.

- [x] T001 Add `openai-agents>=0.0.6` and `mcp>=1.3.0` to `backend/requirements.txt`
- [x] T002 [P] Add `OPENAI_API_KEY: str` and `CHAT_HISTORY_DEPTH: int = 20` to the `Settings` class in `backend/app/config.py`
- [x] T003 [P] Add `OPENAI_API_KEY=` and `CHAT_HISTORY_DEPTH=20` entries (with comments) to `backend/.env.example`

**Checkpoint**: Dependencies declared; configuration class updated; `.env.example` reflects new vars.

---

## Phase 2: Foundational — Database Models

**Goal**: Create Conversation and Message SQLModel tables that underpin all user stories.

**User Story**: US5 — Conversation history persists across messages (also required by US1–US4)

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [x] T004 [P] Create `backend/app/models/conversation.py` — SQLModel table with fields: `id: UUID` (PK, default uuid4), `user_id: str` (indexed), `created_at: DateTime(timezone=True)`, `updated_at: DateTime(timezone=True)` (onupdate)
- [x] T005 [P] Create `backend/app/models/message.py` — SQLModel table with fields: `id: UUID` (PK, default uuid4), `conversation_id: UUID` (FK → conversation.id, indexed), `role: str` ("user" | "assistant"), `content: str` (mapped to `Text` column type), `tool_calls: Optional[dict]` (JSON column, nullable), `created_at: DateTime(timezone=True)`
- [x] T006 Modify `backend/app/database.py` — inside `init_db()` add `from app.models.conversation import Conversation` and `from app.models.message import Message` so `SQLModel.metadata.create_all` registers both new tables
- [x] T007 [P] Create `backend/app/services/chat_service.py` with four async functions:
  - `get_or_create_conversation(db: Session, user_id: str, conversation_id: Optional[UUID] = None) -> Conversation` — if `conversation_id` is provided, query DB and verify `conversation.user_id == user_id` (raise `HTTPException(403)` on mismatch); if `conversation_id` is None, create and commit new `Conversation`
  - `load_history(db: Session, conversation_id: UUID, limit: int = 20) -> list[Message]` — query messages ordered by `created_at` ASC, limit to `limit` rows
  - `append_user_message(db: Session, conversation_id: UUID, content: str) -> Message` — create and commit `Message(role="user", ...)`
  - `append_assistant_message(db: Session, conversation_id: UUID, content: str, tool_calls: Optional[list] = None) -> Message` — create and commit `Message(role="assistant", ...)`

**Checkpoint**: `init_db()` creates both tables in Neon; `chat_service` unit tests pass.

---

## Phase 3: MCP Tool Server [US1, US2, US3, US4]

**Goal**: Stateless FastMCP server exposing 5 task management tools that the AI agent calls.

**User Stories**: US1 (create), US2 (complete/update), US3 (delete), US4 (list/query)

- [x] T008 Create `backend/app/mcp_tools/__init__.py` — empty init file to make the directory a Python package
- [x] T009 [P] [US1] [US2] [US3] [US4] Create `backend/app/mcp_tools/server.py` — FastMCP instance (`mcp = FastMCP("TodoTools")`) with 5 tools:

  **Tool signatures and behaviour**:
  - `add_task(user_id: str, title: str, description: str = "") -> dict`
    Validates `user_id` non-empty → calls `task_service.create_task`; returns `{"status": "created", "data": {"id": ..., "title": ...}}`
  - `list_tasks(user_id: str, completed: Optional[bool] = None) -> dict`
    Validates `user_id` → calls `task_service.get_tasks(user_id, completed)`; returns `{"status": "ok", "data": [{"id": ..., "title": ..., "completed": ...}]}`
  - `complete_task(user_id: str, task_id: str) -> dict`
    Validates `user_id` and `task_id` non-empty → calls `task_service.update_task(user_id, task_id, completed=True)`; returns `{"status": "completed", "data": {"id": ..., "title": ...}}`
  - `update_task(user_id: str, task_id: str, title: Optional[str] = None, description: Optional[str] = None) -> dict`
    Validates `user_id` and `task_id` → calls `task_service.update_task`; returns `{"status": "updated", "data": {"id": ..., "title": ...}}`
  - `delete_task(user_id: str, task_id: str) -> dict`
    Validates `user_id` and `task_id` → calls `task_service.delete_task`; returns `{"status": "deleted", "data": {"id": ...}}`

  **Validation rule for ALL tools**: if `user_id` is empty string or None, return `{"status": "error", "error": "user_id required"}` immediately (do not raise exception).

  Add `if __name__ == "__main__": mcp.run()` entrypoint.

**Checkpoint**: All 5 tools pass unit tests with mocked `task_service`; empty `user_id` returns error dict (not exception).

---

## Phase 4: AI Agent Service [US1, US2, US3, US4, US5]

**Goal**: OpenAI Agents SDK orchestration layer that wires conversation history to MCP tools.

- [x] T010 [US1] [US2] [US3] [US4] [US5] Create `backend/app/services/agent_service.py` with async function `run_agent(user_id: str, messages: list[dict]) -> tuple[str, list[dict]]`:
  - Imports: `from agents import Agent, Runner` and `from agents.mcp import MCPServerStdio`
  - Construct: `MCPServerStdio(command="python", args=["-m", "backend.app.mcp_tools.server"])`
  - System prompt (embed `user_id`):
    ```
    You are a helpful task management assistant for user {user_id}.
    Use the available tools to create, list, complete, update, or delete tasks.
    Always confirm what action you took. If intent is unclear, ask a clarifying question.
    Never delete tasks without explicit instruction.
    ```
  - Build `Agent` with `model=settings.OPENAI_MODEL` (default `"gpt-4o-mini"`), `name="TodoAgent"`, `mcp_servers=[mcp_server]`
  - Call `result = await Runner.run(agent, input=messages)`
  - Return `(result.final_output, [item for item in result.new_items if hasattr(item, "tool")])`

**Checkpoint**: Unit test with mocked `MCPServerStdio` and `Runner.run` verifies return type is `tuple[str, list]`.

---

## Phase 5: Chat API Endpoint [US1, US2, US3, US4, US5]

**Goal**: `POST /api/{user_id}/chat` implementing the full stateless pipeline with JWT guard.

- [x] T011 [P] [US1] Create `backend/app/schemas/chat.py` with Pydantic models:
  - `ToolCallRecord(tool: str, arguments: dict, result: dict)`
  - `ChatRequest(message: str, conversation_id: Optional[UUID] = None)`
  - `ChatResponse(reply: str, tool_calls: list[ToolCallRecord] = [], conversation_id: str)`

- [x] T012 [US1] [US2] [US3] [US4] [US5] Create `backend/app/api/routes/chat.py` with `POST /api/{user_id}/chat`:

  **Dependencies**: `current_user: dict = Depends(get_current_user)`, `db: Session = Depends(get_db)`

  **Pipeline** (execute in order):
  1. If `current_user["sub"] != user_id` → raise `HTTPException(status_code=403, detail="Forbidden")`
  2. `conv = await get_or_create_conversation(db, user_id, body.conversation_id)`
  3. `history = await load_history(db, conv.id, limit=settings.CHAT_HISTORY_DEPTH)`
  4. `messages = [{"role": m.role, "content": m.content} for m in history]`
  5. `messages.append({"role": "user", "content": body.message})`
  6. `reply, tool_calls = await run_agent(user_id, messages)` ← wrap steps 6–8 in try/except; on any exception raise `HTTPException(500, "Chat service error")`
  7. `await append_user_message(db, conv.id, body.message)`
  8. `await append_assistant_message(db, conv.id, reply, tool_calls)`
  9. Return `ChatResponse(reply=reply, tool_calls=tool_calls, conversation_id=str(conv.id))`

- [x] T013 [US1] Modify `backend/app/main.py` — import `chat_router` from `app.api.routes.chat` and call `app.include_router(chat_router, prefix="/api")`

**Checkpoint**: `curl -X POST http://localhost:8000/api/{user_id}/chat -H "Authorization: Bearer <token>" -d '{"message": "Add a task called Test"}'` returns HTTP 200 with non-empty `reply` field.

---

## Phase 6: Frontend Chat UI [US1, US2, US3, US4, US5]

**Goal**: Conversational chat panel embedded in the existing dashboard; task list auto-refreshes after AI actions.

**User Story**: US2 — Update or Complete a Task by Chatting (frontend visibility); US5 — Conversation history visible on reload

- [x] T014 [P] [US1] [US2] Modify `frontend/types/index.ts` — append the following TypeScript types:
  - `ChatMessage { id: string; role: "user" | "assistant"; content: string; }`
  - `ChatRequest { message: string; conversation_id?: string; }`
  - `ToolCallRecord { tool: string; arguments: Record<string, unknown>; result: Record<string, unknown>; }`
  - `ChatResponse { reply: string; tool_calls: ToolCallRecord[]; conversation_id: string; }`

- [x] T015 [P] [US1] Modify `frontend/services/api-client.ts` — add `sendChatMessage(userId: string, req: ChatRequest): Promise<ChatResponse>` using the existing `Authorization: Bearer <token>` header pattern; POST to `/api/${userId}/chat`

- [x] T016 [US1] [US5] Create `frontend/hooks/useChat.ts`:
  - State: `messages: ChatMessage[]`, `conversationId: string | null`, `isLoading: boolean`, `error: string | null`
  - `sendMessage(text: string)`: (a) optimistically append `{role: "user", content: text}` to `messages`; (b) call `sendChatMessage`; (c) append `{role: "assistant", content: response.reply}`; (d) set `conversationId` from response; (e) call `onTasksChanged?.()` to refresh task list
  - Export: `useChat(userId: string, onTasksChanged?: () => void)`

- [x] T017 [P] [US1] Create `frontend/components/chat/ChatMessage.tsx` — renders a single message bubble; user messages right-aligned with blue background; assistant messages left-aligned with gray background; displays `content` text

- [x] T018 [P] [US1] Create `frontend/components/chat/ChatInput.tsx` — controlled `<textarea>` (maxLength 4000) + Send button; both disabled when `isLoading` prop is true; calls `onSend(text)` on button click or `Cmd/Ctrl+Enter` keydown; clears input after send

- [x] T019 [US1] [US5] Create `frontend/components/chat/ChatPanel.tsx` — composes scrollable `<div>` of `<ChatMessage>` items + `<ChatInput>`; accepts `userId: string` and `onTasksChanged?: () => void` props; uses `useChat` hook; auto-scrolls to bottom on new message; shows spinner when `isLoading` is true

- [x] T020 [US1] [US2] [US3] [US4] Modify `frontend/app/dashboard/page.tsx` — import `ChatPanel`; render `<ChatPanel userId={session.user.id} onTasksChanged={fetchTasks} />` in a side panel or below the task list; pass `fetchTasks` as `onTasksChanged` so task list auto-refreshes after AI actions

**Checkpoint**: User can type a message in the browser, receive an AI reply, and see the task list update — all without navigating away from the dashboard.

---

## Phase 7: Security Hardening [US1, US2, US3]

**Goal**: Confirm JWT enforcement, user isolation, and input validation across all new code.

**User Story**: US3 — Delete a Task by Chatting (requires isolation); also enforces US1 and US2 security requirements.

- [x] T021 [P] [US3] Verify `backend/.env.example` — confirm `BETTER_AUTH_SECRET` entry exists and add a comment: `# BETTER_AUTH_SECRET is shared with FastAPI as JWT_SECRET_KEY for token verification`
- [x] T022 [P] [US1] [US2] [US3] Add explicit input validation to all 5 MCP tools in `backend/app/mcp_tools/server.py`:
  - `user_id` must be a non-empty string in every tool
  - `task_id` must be a non-empty string in `complete_task`, `update_task`, `delete_task`
  - Return `{"status": "error", "error": "<field> required"}` (not raise exception) when validation fails
- [x] T023 [US3] Add conversation ownership verification in `backend/app/services/chat_service.py` — in `get_or_create_conversation`, when a `conversation_id` is supplied, query `db.get(Conversation, conversation_id)`; if result is None or `result.user_id != user_id` raise `HTTPException(status_code=403, detail="Conversation not found or access denied")`

**Checkpoint**: All three auth/isolation integration tests pass (401 no-token, 403 user mismatch, 403 conversation ownership).

---

## Phase 8: Testing [US1, US2, US3, US4, US5]

**Goal**: Full test coverage for the three user-story acceptance scenarios.

- [x] T024 [P] Create `backend/tests/unit/test_chat_service.py`:
  - Test `get_or_create_conversation` creates new `Conversation` record when no `conversation_id` given
  - Test `get_or_create_conversation` raises 403 when `conversation_id` belongs to a different `user_id`
  - Test `load_history` returns messages ordered by `created_at` ASC, limited to `limit`
  - Test `append_user_message` saves `role="user"` and correct `content`
  - Test `append_assistant_message` saves `role="assistant"`, `content`, and `tool_calls`

- [x] T025 [P] Create `backend/tests/unit/test_mcp_tools.py`:
  - Test each of 5 tools calls the correct `task_service` function with mocked session
  - Test that empty `user_id` (`""`) returns `{"status": "error", "error": "user_id required"}` — no exception raised
  - Test that `None` `user_id` returns same error dict
  - Test that `complete_task`, `update_task`, `delete_task` with empty `task_id` return error dict

- [x] T026 [P] Create `backend/tests/unit/test_agent_service.py`:
  - Mock `MCPServerStdio` and `Runner.run` to return a fake result
  - Assert `run_agent(user_id, messages)` returns `(str, list)` tuple
  - Assert system prompt passed to `Agent` contains the `user_id` value

- [x] T027 Create `backend/tests/integration/test_chat_endpoint.py`:
  - `POST /api/{user_id}/chat` with valid JWT and `"message": "Add a task called Buy milk"` → HTTP 200, `reply` is non-empty string, `conversation_id` is a valid UUID string
  - `POST /api/{user_id}/chat` without `Authorization` header → HTTP 401
  - `POST /api/{user_id}/chat` with valid JWT but different `user_id` in path → HTTP 403
  - Two sequential requests with same `conversation_id` → second response returns the same `conversation_id`; DB contains exactly 4 `Message` records for that conversation
  - `POST /api/{user_id}/chat` with task-creation intent followed by `GET /api/{user_id}/tasks` → newly created task appears in task list

**Checkpoint**: All 27 tasks complete; `pytest backend/tests/ -q` exits 0; all 5 integration test cases pass.

---

## Dependencies

```
T001 → T002, T003 (dependencies first)
T004, T005 → T006 → T007 (DB models before service)
T007 → T009 (chat_service before MCP tools)
T009 → T010 (MCP server before agent service)
T010, T011 → T012 (agent + schemas before route)
T012 → T013 (route before main.py include)
T014, T015 → T016 (types + client before hook)
T016, T017, T018 → T019 (components before panel)
T019 → T020 (panel before dashboard modification)
T013, T020 → T021, T022, T023 (security after core implemented)
T023 → T024, T025, T026 (tests after security hardening)
T024, T025, T026 → T027 (unit tests before integration tests)
```

## Parallel Execution Groups

```
Group A — run together immediately after T001:
  T002, T003, T004, T005

Group B — run together after T006:
  T007, T008

Group C — run together after T007:
  T009, T011

Group D — run together after T009 AND T011:
  T010, T012

Group E — frontend (independent of backend after T001):
  T014, T015

Group F — run together after T014 AND T015:
  T016, T017, T018

Group G — security (run together after T013 AND T020):
  T021, T022, T023

Group H — unit tests (run together after T023):
  T024, T025, T026
  Then → T027 (after all unit tests pass)
```

---

## Independent Test Criteria (per User Story)

| Story | Done When |
|-------|-----------|
| US1 (Create via chat) | `curl -X POST .../chat -H "Authorization: Bearer <token>" -d '{"message":"Add a task called Test"}'` returns 200 with non-empty `reply`; task appears in `GET /api/{user_id}/tasks` |
| US2 (Complete/Update via chat) | Chat message "mark my Test task as done" returns 200 with completion confirmation; task `completed=true` in DB |
| US3 (Delete via chat) | Chat message "delete the Test task" returns 200 with deletion confirmation; task absent from `GET /api/{user_id}/tasks` |
| US4 (Query via chat) | Chat message "what tasks do I have?" returns 200 with a plain-language list of the user's tasks |
| US5 (History persists) | Two sequential messages with same `conversation_id` → DB has 4 Message records; second AI reply references first message context |

---

## Security Acceptance (US3 / Phase 7)

- Unauthenticated request → HTTP 401
- Valid token, mismatched `user_id` in path → HTTP 403
- Valid token, valid `user_id`, but `conversation_id` owned by another user → HTTP 403
- MCP tool called with empty `user_id` → returns `{"status": "error"}`, no exception, no DB access

---

## MVP Scope

| Scope | Tasks | Deliverable |
|-------|-------|-------------|
| Backend MVP (curl-testable) | T001–T013 | Chat endpoint functional, AI creates/updates/deletes/lists tasks |
| Full UI | T001–T020 | Chat panel in dashboard, task list auto-refreshes |
| Hardened | T001–T023 | JWT + isolation enforced |
| Fully Tested | T001–T027 | All unit + integration tests pass |
