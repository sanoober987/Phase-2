<!--
  ============================================================================
  SYNC IMPACT REPORT
  ============================================================================
  Version change: 1.0.0 → 1.1.0 (MINOR - Phase III AI agent principles added)

  Modified principles:
    - II. Modularity → now includes AI agent and MCP tool layers
    - III. Reproducibility → no change
    - IV. Responsiveness → renamed to IV. Stateless Design (new principle)
    - V. Maintainability → now includes logging and traceability requirements

  Added sections:
    - Principle IV: Stateless Design (replaces Responsiveness for Phase III)
    - Principle VI: Responsiveness (moved to VI to accommodate new principle)
    - AI Agent Behavior (intent mapping, MCP tools, tool execution rules)
    - Conversation Standards (chat endpoint contract)
    - Phase III Database Models (Conversation, Message)

  Removed sections: None

  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ (compatible - no changes needed)
    - .specify/templates/spec-template.md ✅ (compatible - no changes needed)
    - .specify/templates/tasks-template.md ✅ (compatible - no changes needed)

  Follow-up TODOs: None
  ============================================================================
-->

# Todo AI Chatbot — Phase III Intelligent Agent System Constitution

## Core Principles

### I. Security (NON-NEGOTIABLE)

Every user MUST only access their own tasks and conversation history,
enforced via JWT authentication and strict user_id scoping.

- All API endpoints MUST verify JWT tokens before processing requests
- JWT tokens MUST be signed with `BETTER_AUTH_SECRET` shared between frontend and backend
- Tokens MUST expire after a maximum of 7 days
- Unauthorized access attempts MUST return HTTP 401
- Backend MUST filter all data queries by authenticated user ID
- MCP tools MUST validate `user_id` on every invocation; cross-user access is FORBIDDEN
- Tokens MUST NOT be exposed in URLs, logs, or client-side storage (except httpOnly cookies)
- Password hashing MUST use industry-standard algorithms (bcrypt, argon2)

**Rationale**: Multi-user applications require strict data isolation. A single
authorization bypass could expose all users' tasks and conversation data.

### II. Modularity

Clear separation of UI, AI logic, and database layers is REQUIRED.

- Frontend (conversational UI) handles user interaction and chat rendering only
- Backend (FastAPI) handles business logic, JWT verification, and AI orchestration
- AI layer (OpenAI Agents SDK) handles intent interpretation and tool dispatch
- MCP Server handles stateless, database-backed tool execution
- Database (Neon PostgreSQL) handles persistence via SQLModel ORM
- Authentication (Better Auth) handles identity and JWT issuance
- Each layer MUST communicate only through defined contracts; no cross-layer shortcuts

**Rationale**: Layered separation enables independent testing, scaling, and
replacement of any component without cascading changes.

### III. Reproducibility

All features MUST be implemented via the Agentic Dev Stack. No manual coding allowed.

- Every feature follows the workflow:
  1. Write spec (`/sp.specify`)
  2. Generate plan (`/sp.plan`)
  3. Break into tasks (`/sp.tasks`)
  4. Implement via Claude Code (`/sp.implement`)
- All code changes MUST be traceable to a spec or task
- Prompt History Records (PHR) MUST document all significant interactions
- Architecture Decision Records (ADR) MUST document significant design choices
- AI agent decisions and tool calls MUST be logged for traceability

**Rationale**: Spec-driven development ensures every change can be reproduced,
audited, or reverted systematically.

### IV. Stateless Design

Backend MUST NOT retain in-memory session state; all conversational context
MUST be persisted in the database.

- The chat endpoint MUST load conversation history from the database on every request
- No server-side session objects or in-memory caches for conversation context
- Agent state MUST be reconstructed from persisted `Message` records per request
- MCP tools MUST be stateless; all state lives in the database
- Horizontal scaling MUST be possible without session affinity

**Rationale**: Stateless architecture guarantees conversation persistence across
server restarts and enables reliable horizontal scaling.

### V. Reliability

Agent tool execution MUST be deterministic, logged, and free of silent failures.

- Every MCP tool call MUST return structured JSON output (success or error)
- Agent decisions, tool calls, database operations, and errors MUST be logged
- Failed tool calls MUST surface actionable error messages to the agent
- The chat endpoint MUST complete the full pipeline (load → append → agent →
  tools → store → respond) atomically or roll back
- Retry logic SHOULD be implemented for transient database failures

**Rationale**: Unreliable tool execution leads to inconsistent task state and
degrades user trust in the conversational interface.

### VI. Maintainability

Clear API structure, proper error handling, and environment configuration
are REQUIRED.

- RESTful API design with consistent endpoint naming
- All endpoints MUST return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request (validation errors)
  - 401: Unauthorized (missing/invalid token)
  - 403: Forbidden (valid token, wrong user)
  - 404: Not Found
  - 500: Internal Server Error
- Environment variables MUST be used for all configuration (no hardcoded secrets)
- Structured logging MUST be implemented for debugging and monitoring
- Error responses MUST include actionable messages (not stack traces in production)

**Rationale**: Maintainable code reduces debugging time and supports long-term
project health as the AI feature set grows.

## Technology Stack

| Layer          | Technology                    | Version/Notes                         |
|----------------|-------------------------------|---------------------------------------|
| Frontend       | Conversational UI (ChatKit)   | OpenAI ChatKit or equivalent          |
| Backend        | Python FastAPI                | Async endpoints, Pydantic models      |
| AI Framework   | OpenAI Agents SDK             | Intent mapping, tool dispatch         |
| Tooling Layer  | MCP Server (Official SDK)     | Stateless, database-backed tools      |
| ORM            | SQLModel                      | Type-safe database operations         |
| Database       | Neon Serverless PostgreSQL    | Connection pooling required           |
| Authentication | Better Auth                   | JWT token issuance, BETTER_AUTH_SECRET|
| Spec-Driven    | Claude Code + Spec-Kit Plus   | No manual coding                      |

## Conversation Standards

### Chat Endpoint Contract

```
POST /api/{user_id}/chat
Authorization: Bearer <token>
```

The server MUST execute this pipeline on every request:

1. Validate JWT; extract and verify `user_id`
2. Load conversation history from the `Message` table for this user
3. Append the new user message to history
4. Send full context (history + new message) to the AI agent
5. Execute any MCP tool calls returned by the agent
6. Store the assistant response as a `Message` record
7. Return the assistant response immediately

### Stateless Contract

- No pipeline step may depend on in-memory state from a prior request
- Tool outputs MUST be stored before the response is returned

## AI Agent Behavior

### Intent Mapping Rules

The AI MUST automatically map user intent to the correct MCP tool:

| User Intent    | MCP Tool        |
|----------------|-----------------|
| Create task    | `add_task`      |
| List tasks     | `list_tasks`    |
| Complete task  | `complete_task` |
| Delete task    | `delete_task`   |
| Update task    | `update_task`   |

### MCP Tool Standards

All tools MUST be stateless and database-backed.

Required tools: `add_task`, `list_tasks`, `complete_task`, `delete_task`,
`update_task`

Tool execution rules:
- MUST validate `user_id` on every call
- MUST NOT allow cross-user data access
- MUST return structured JSON output

## Development Constraints

### Database Models

**Task**

| Field         | Type      | Notes                    |
|---------------|-----------|--------------------------|
| id            | UUID/int  | Primary key              |
| user_id       | string    | FK, indexed              |
| title         | string    | Required                 |
| description   | string    | Optional                 |
| completed     | boolean   | Default false            |
| created_at    | datetime  | Auto                     |
| updated_at    | datetime  | Auto                     |

**Conversation**

| Field      | Type     | Notes       |
|------------|----------|-------------|
| id         | UUID/int | Primary key |
| user_id    | string   | FK, indexed |
| created_at | datetime | Auto        |
| updated_at | datetime | Auto        |

**Message**

| Field           | Type     | Notes                          |
|-----------------|----------|--------------------------------|
| id              | UUID/int | Primary key                    |
| conversation_id | UUID/int | FK → Conversation              |
| role            | string   | user \| assistant \| tool      |
| content         | text     | Message body                   |
| tool_calls      | JSON     | Agent tool call records        |
| created_at      | datetime | Auto                           |

### Required API Endpoints

- `POST /api/{user_id}/chat` — Conversational task management (primary)
- `GET /api/tasks` — List tasks for authenticated user
- `POST /api/tasks` — Create a task
- `GET /api/tasks/{id}` — Retrieve a task
- `PUT /api/tasks/{id}` — Update a task
- `DELETE /api/tasks/{id}` — Delete a task
- `PATCH /api/tasks/{id}/toggle` — Toggle completion status

### Environment Variables

Required (MUST NOT be hardcoded):

```
# Shared secret between Better Auth and FastAPI
BETTER_AUTH_SECRET=<minimum 32 characters>

# Database connection
DATABASE_URL=postgresql://...@neon.tech/...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# AI
OPENAI_API_KEY=<key>
```

### JWT Token Requirements

- Payload MUST include: `sub` (user ID), `email`, `exp` (expiration)
- Tokens MUST be verified on every protected endpoint
- Frontend API client MUST automatically attach token to all requests
- Token refresh flow SHOULD be implemented for better UX

### Testing Requirements

- All API endpoints MUST be testable
- Authentication flow MUST be verified (signup, signin, token validation)
- Task isolation MUST be tested (User A cannot access User B's tasks)
- MCP tool calls MUST be verifiable with mock user context
- Chat endpoint pipeline MUST be integration-tested end-to-end
- Error responses MUST be verified for all failure scenarios

## Governance

This constitution supersedes all other development practices for this project.

### Amendment Process

1. Proposed changes MUST be documented with rationale
2. Changes MUST be reviewed for impact on existing code
3. Version MUST be incremented according to semantic versioning:
   - MAJOR: Principle removal or backward-incompatible changes
   - MINOR: New principles or expanded guidance
   - PATCH: Clarifications and typo fixes
4. All dependent artifacts MUST be updated to reflect changes

### Compliance

- All pull requests MUST verify compliance with these principles
- Security principle violations block merge
- Complexity additions MUST be justified in writing
- Runtime development guidance is maintained in `CLAUDE.md`

### Success Criteria

A compliant implementation MUST demonstrate:

- [ ] Users can control tasks using natural language via the chat endpoint
- [ ] Chat history persists across server restarts (database-backed)
- [ ] MCP tools execute correctly and return structured JSON
- [ ] AI agent correctly maps all 5 intent types to the right tool
- [ ] No data leakage between users (task and conversation isolation verified)
- [ ] All CRUD operations functional for each authenticated user
- [ ] API returns proper HTTP codes for success and error conditions
- [ ] JWT auth correctly implemented: token verification, expiration, stateless
- [ ] Frontend displays correct chat and task data per user
- [ ] Secure and ready for deployment with documented setup

**Version**: 1.1.0 | **Ratified**: 2026-02-01 | **Last Amended**: 2026-02-25
