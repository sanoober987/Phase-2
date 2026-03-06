---
id: 002
title: Phase III AI Agent Constitution
stage: constitution
date: 2026-02-25
surface: agent
model: claude-sonnet-4-5-20250929
feature: none
branch: main
user: architext
command: /sp.constitution
labels: ["constitution","phase-iii","ai-agents","mcp","stateless","security"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - N/A
---

## Prompt

/sp.constitution

Project: Todo AI Chatbot — Phase III Intelligent Agent System

Project Objective:
Build an AI-powered conversational task management system using Agentic Dev Stack principles. The system must allow users to manage todos using natural language commands powered by AI agents, MCP tool servers, and stateless backend architecture.

Core Principles:
- Intelligence: AI must correctly interpret natural language commands.
- Stateless Design: Backend must not store session memory outside database persistence.
- Reliability: Agent tool execution must be deterministic and logged.
- Security: All operations must respect user authentication and data isolation.
- Reproducibility: AI decisions and tool calls must be traceable.

Architecture Standards:
- Frontend: OpenAI ChatKit or equivalent conversational UI.
- Backend: Python FastAPI.
- AI Framework: OpenAI Agents SDK.
- Tooling Layer: MCP Server using Official MCP SDK.
- Database: Neon Serverless PostgreSQL.
- Authentication: Better Auth with JWT verification.

Conversation Standards:
- Chat endpoint must be: POST /api/{user_id}/chat
- Server must: load history → append message → send to agent → execute tools → store response → return response.

AI Agent Behavior:
- Intent Mapping: Create Task → add_task, List Tasks → list_tasks, Complete Task → complete_task, Delete Task → delete_task, Update Task → update_task.

MCP Tool Standards: stateless, database-backed, validate user_id, return structured JSON.

Database Models: Task, Conversation, Message (with tool_calls field).

Security: JWT via BETTER_AUTH_SECRET, 401 on unauthorized.

Performance: indexed user_id queries.

Logging: agent decisions, tool calls, DB ops, errors.

Success Criteria: natural language task control, persistent chat history, correct MCP tool execution, no cross-user data leakage.

## Response snapshot

Updated constitution from v1.0.0 → v1.1.0 (MINOR bump).

Changes made to `.specify/memory/constitution.md`:
- Renamed project title to "Todo AI Chatbot — Phase III Intelligent Agent System"
- Expanded Principle II (Modularity) to include AI agent and MCP tool layers
- Added Principle IV: Stateless Design (new — backend MUST NOT retain in-memory session state)
- Added Principle V: Reliability (new — deterministic, logged, structured tool execution)
- Renumbered former IV (Responsiveness) → VI Maintainability
- Added Technology Stack rows: AI Framework (OpenAI Agents SDK), Tooling Layer (MCP Server)
- Added Conversation Standards section with chat endpoint pipeline contract
- Added AI Agent Behavior section (intent mapping table, MCP tool standards)
- Added Conversation and Message database models to Development Constraints
- Added OPENAI_API_KEY to required environment variables
- Updated Success Criteria checklist for Phase III

## Outcome

- ✅ Impact: Constitution updated to v1.1.0 covering Phase III AI agent architecture
- 🧪 Tests: N/A (documentation artifact)
- 📁 Files: .specify/memory/constitution.md (overwritten)
- 🔁 Next prompts: /sp.specify for Phase III feature spec
- 🧠 Reflection: Phase III adds significant architectural layers (AI, MCP) requiring 2 new principles and new sections; MINOR bump is appropriate as no prior principles were removed.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment: run /sp.specify for conversational chat feature
